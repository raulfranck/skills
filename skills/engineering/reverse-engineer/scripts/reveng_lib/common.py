"""Shared helpers: file listing, classification, text stats, git, JSON and module mapping."""
from __future__ import annotations

import bisect
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

# Directories skipped when the repository is not a git work tree (git ls-files
# already honours .gitignore, so this list only matters for plain folders).
WALK_SKIP_DIRS = {
    ".git", "node_modules", "bower_components", "vendor", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", "target", "out", ".next", ".nuxt",
    ".svelte-kit", "coverage", ".gradle", ".idea", ".vs", ".terraform", ".serverless", ".reveng",
    "Pods", "DerivedData", ".dart_tool", ".angular", ".cache", "obj",
}

# Always excluded, even when tracked by git.
ALWAYS_SKIP_PREFIXES = (".reveng/",)

# Path segments and file patterns that mark vendored or generated files. They stay in the
# listing but are excluded from size, complexity and churn statistics.
GENERATED_SEGMENTS = {
    "node_modules", "vendor", "third_party", "third-party", "dist", "build", "out", "target",
    ".next", "generated", "__generated__", "gen", "bower_components",
}
GENERATED_FILE_RE = re.compile(
    r"(\.min\.(js|css)$|\.map$|\.lock$|^package-lock\.json$|^yarn\.lock$|^pnpm-lock\.yaml$|"
    r"\.pb\.go$|_pb2(_grpc)?\.py$|\.g\.dart$|\.designer\.cs$|\.generated\.|\.snap$)",
    re.IGNORECASE,
)

LANGUAGES = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala", ".groovy": "Groovy",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".fs": "F#",
    ".vb": "Visual Basic", ".c": "C", ".h": "C/C++", ".cc": "C++", ".cpp": "C++", ".cxx": "C++",
    ".hpp": "C++", ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C", ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".clj": "Clojure", ".hs": "Haskell",
    ".lua": "Lua", ".r": "R", ".jl": "Julia", ".pl": "Perl", ".sh": "Shell", ".bash": "Shell",
    ".zsh": "Shell", ".ps1": "PowerShell", ".sql": "SQL", ".vue": "Vue", ".svelte": "Svelte",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS",
    ".less": "LESS", ".tf": "Terraform", ".hcl": "HCL", ".proto": "Protobuf",
    ".graphql": "GraphQL", ".gql": "GraphQL", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".xml": "XML", ".toml": "TOML", ".ini": "INI", ".properties": "Properties",
    ".md": "Markdown", ".mdx": "Markdown", ".rst": "reStructuredText", ".txt": "Text",
}
FILENAME_LANGUAGES = {
    "dockerfile": "Dockerfile", "makefile": "Makefile", "jenkinsfile": "Groovy",
    "gemfile": "Ruby", "rakefile": "Ruby", "procfile": "Procfile",
}

CODE_LANGUAGES = {
    "Python", "JavaScript", "TypeScript", "Java", "Kotlin", "Scala", "Groovy", "Go", "Rust", "Ruby",
    "PHP", "C#", "F#", "Visual Basic", "C", "C/C++", "C++", "Swift", "Objective-C", "Dart",
    "Elixir", "Erlang", "Clojure", "Haskell", "Lua", "R", "Julia", "Perl", "Shell", "PowerShell",
    "SQL", "Vue", "Svelte",
}
MARKUP_LANGUAGES = {"HTML", "CSS", "SCSS", "LESS"}
CONFIG_LANGUAGES = {
    "YAML", "JSON", "XML", "TOML", "INI", "Properties", "HCL", "Terraform", "Dockerfile",
    "Makefile", "Procfile", "Protobuf", "GraphQL",
}
DOC_LANGUAGES = {"Markdown", "reStructuredText", "Text"}

TEST_PATH_RE = re.compile(
    r"(^|/)(test|tests|__tests__|spec|specs|e2e|testing|test_utils|testdata|fixtures)(/|$)",
    re.IGNORECASE,
)
TEST_FILE_RE = re.compile(
    r"(_test\.go$|^test_.*\.py$|_test\.py$|\.(test|spec)\.[cm]?[jt]sx?$|Tests?\.(java|kt|cs|php)$|"
    r"_spec\.rb$|Spec\.(scala|kt)$|\.spec\.dart$|_test\.dart$)"
)

# Directories that hold modules rather than being modules themselves.
CONTAINER_DIRS = {
    "src", "lib", "libs", "app", "apps", "packages", "services", "modules", "internal", "pkg",
    "cmd", "components", "projects", "source", "sources", "main",
}

MAX_TEXT_BYTES = 1_500_000


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def posix(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def language_of(rel: str) -> str | None:
    name = PurePosixPath(rel).name
    lower = name.lower()
    if lower in FILENAME_LANGUAGES:
        return FILENAME_LANGUAGES[lower]
    if lower.startswith("dockerfile") or lower.endswith(".dockerfile"):
        return "Dockerfile"
    return LANGUAGES.get(PurePosixPath(lower).suffix)


def category_of(language: str | None) -> str:
    if language is None:
        return "other"
    if language in CODE_LANGUAGES:
        return "code"
    if language in MARKUP_LANGUAGES:
        return "markup"
    if language in CONFIG_LANGUAGES:
        return "config"
    if language in DOC_LANGUAGES:
        return "docs"
    return "other"


def is_generated(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in GENERATED_SEGMENTS for p in parts[:-1]):
        return True
    return bool(GENERATED_FILE_RE.search(parts[-1]))


def is_test(rel: str) -> bool:
    return bool(TEST_PATH_RE.search(rel) or TEST_FILE_RE.search(PurePosixPath(rel).name))


# ---------------------------------------------------------------- git

def run_git(repo: str | Path, args: list[str], check: bool = False) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        return ""
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout if proc.returncode == 0 else ""


def is_git_repo(repo: str | Path) -> bool:
    return run_git(repo, ["rev-parse", "--is-inside-work-tree"]).strip() == "true"


def git_head(repo: str | Path) -> str | None:
    head = run_git(repo, ["rev-parse", "HEAD"]).strip()
    return head or None


def list_files(repo: str | Path, exclude_abs: Iterable[str | Path] = ()) -> list[str]:
    """Relative posix paths of the files that belong to the repository."""
    repo = Path(repo).resolve()
    excluded = []
    for e in exclude_abs:
        try:
            excluded.append(posix(Path(e).resolve().relative_to(repo)).rstrip("/") + "/")
        except ValueError:
            continue
    files: list[str] = []
    if is_git_repo(repo):
        out = run_git(repo, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"])
        for rel in out.split("\0"):
            if rel and (repo / rel).is_file():
                files.append(posix(rel))
    else:
        for root, dirs, names in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in WALK_SKIP_DIRS]
            for n in names:
                files.append(posix(Path(root, n).relative_to(repo)))
    result = []
    for rel in sorted(set(files)):
        if rel.startswith(ALWAYS_SKIP_PREFIXES) or any(rel.startswith(x) for x in excluded):
            continue
        result.append(rel)
    return result


# ---------------------------------------------------------------- text

def read_text(path: str | Path, max_bytes: int = MAX_TEXT_BYTES) -> str | None:
    """File content as text, or None for binary or oversized files."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(max_bytes + 1)
    except OSError:
        return None
    if len(data) > max_bytes or b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def text_stats(text: str) -> tuple[int, float, int]:
    """(non-blank lines, indentation complexity, max indentation level).

    Indentation complexity is the language-neutral proxy from behavioural code analysis
    (Tornhill): the sum of logical indentation levels over non-blank lines.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        return 0, 0.0, 0
    widths = []
    for ln in lines:
        lead = ln[: len(ln) - len(ln.lstrip(" \t"))]
        widths.append(lead.count(" ") + lead.count("\t") * 4)
    nonzero = [w for w in widths if w > 0]
    unit = min(nonzero) if nonzero else 4
    unit = max(2, min(unit, 8))
    levels = [w / unit for w in widths]
    return len(lines), round(sum(levels), 1), int(max(levels))


class LineIndex:
    """Maps character offsets to 1-based line numbers."""

    def __init__(self, text: str):
        self.starts = [0]
        for m in re.finditer("\n", text):
            self.starts.append(m.end())

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.starts, offset)


def snippet(text: str, start: int, width: int = 120) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()[:width]


# ---------------------------------------------------------------- modules

def compute_module_prefixes(source_files: list[str], package_roots: list[str]) -> list[str]:
    """Pick module prefixes so that no module dominates the repository.

    Start from package roots (monorepo) or first-level directories, then descend into any
    module holding more than half of the files, collapsing single-child chains such as
    src/main/java/com/acme. This recovers useful module boundaries for most layouts
    without language-specific rules.
    """
    roots = sorted({r.rstrip("/") for r in package_roots if r}, key=len, reverse=True)

    def initial(rel: str) -> str:
        for r in roots:
            if rel.startswith(r + "/"):
                return r
        parts = rel.split("/")
        return parts[0] if len(parts) > 1 else "(root)"

    assign = {rel: initial(rel) for rel in source_files}
    for _ in range(12):
        groups: dict[str, list[str]] = {}
        for rel, mod in assign.items():
            groups.setdefault(mod, []).append(rel)
        total = len(assign) or 1
        count = len(groups)
        changed = False
        for mod, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if mod == "(root)":
                continue
            children: dict[str, list[str]] = {}
            for rel in members:
                rest = rel[len(mod) + 1:]
                if "/" in rest:
                    children.setdefault(mod + "/" + rest.split("/")[0], []).append(rel)
            if not children:
                continue
            single_chain = len(children) == 1 and len(children[next(iter(children))]) == len(members)
            share = len(members) / total
            if mod in roots:
                # A package stays whole unless it dominates the repository.
                if share <= 0.5:
                    continue
                wants_split = True
            else:
                wants_split = share > 0.5 or mod.split("/")[-1] in CONTAINER_DIRS
            if single_chain or (wants_split and count - 1 + len(children) <= 40):
                for child, rels in children.items():
                    for rel in rels:
                        assign[rel] = child
                if not single_chain:
                    count += len(children) - 1
                changed = True
        if not changed:
            break
    return sorted(set(assign.values()) - {"(root)"}, key=len, reverse=True)


def module_of(rel: str, prefixes: list[str]) -> str:
    for p in prefixes:
        if rel == p or rel.startswith(p + "/"):
            return p
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else "(root)"


# ---------------------------------------------------------------- output

def write_json(path: str | Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def read_json(path: str | Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")


def md_table(headers: list[str], rows: list[list], limit: int | None = None) -> str:
    shown = rows if limit is None else rows[:limit]
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in shown:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    if limit is not None and len(rows) > limit:
        out.append(f"\n_(+{len(rows) - limit} more in the JSON file)_")
    return "\n".join(out)


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-").lower()
    return s or "repo"
