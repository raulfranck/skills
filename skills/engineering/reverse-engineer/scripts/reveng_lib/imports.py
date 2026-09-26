"""Module dependency graph from import statements (best effort, regex based).

Supported: JavaScript/TypeScript, Python, Java/Kotlin/Scala/Groovy, Go, C#, PHP.
Reports afferent/efferent coupling and instability (R. C. Martin) and cycles (Tarjan SCC).
"""
from __future__ import annotations

import json
import posixpath
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from . import common as C

JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte")
JS_RESOLVE_EXT = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte", ".d.ts"]
JS_IMPORT = re.compile(r"""(?:^|[\s;}])(?:import|export)\s+(?:type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?['"]([^'"\n]+)['"]""")
JS_REQUIRE = re.compile(r"""\brequire\(\s*['"]([^'"\n]+)['"]\s*\)""")
JS_DYNAMIC = re.compile(r"""\bimport\(\s*['"]([^'"\n]+)['"]\s*\)""")

PY_IMPORT = re.compile(r"^[ \t]*import[ \t]+([\w.]+(?:[ \t]+as[ \t]+\w+)?(?:[ \t]*,[ \t]*[\w.]+(?:[ \t]+as[ \t]+\w+)?)*)", re.M)
PY_FROM = re.compile(r"^[ \t]*from[ \t]+(\.*[\w.]*)[ \t]+import[ \t]+(\([^)]*\)|[\w*, \t]+)", re.M)

JVM_EXT = (".java", ".kt", ".kts", ".scala", ".groovy")
JVM_PACKAGE = re.compile(r"^[ \t]*package[ \t]+([\w.]+)", re.M)
JVM_IMPORT = re.compile(r"^[ \t]*import[ \t]+(?:static[ \t]+)?([\w.]+?)(?:\.\*)?(?:[ \t]+as[ \t]+\w+)?[ \t]*;?[ \t]*$", re.M)

GO_SINGLE = re.compile(r'^[ \t]*import[ \t]+(?:[\w.]+[ \t]+)?"([^"]+)"', re.M)
GO_BLOCK = re.compile(r"^[ \t]*import[ \t]*\(([^)]*)\)", re.M)
GO_SPEC = re.compile(r'(?:[\w.]+[ \t]+)?"([^"]+)"')

CS_NAMESPACE = re.compile(r"^[ \t]*namespace[ \t]+([\w.]+)", re.M)
CS_USING = re.compile(r"^[ \t]*(?:global[ \t]+)?using[ \t]+(?:static[ \t]+)?([\w.]+)[ \t]*;", re.M)

PHP_NAMESPACE = re.compile(r"^[ \t]*namespace[ \t]+([\w\\]+)[ \t]*;", re.M)
PHP_USE = re.compile(r"^[ \t]*use[ \t]+(?:function[ \t]+|const[ \t]+)?([\w\\]+)", re.M)

PY_STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

NODE_BUILTINS = {
    "fs", "path", "os", "http", "https", "url", "util", "crypto", "stream", "events", "child_process",
    "buffer", "querystring", "zlib", "net", "tls", "dns", "assert", "readline", "cluster", "worker_threads",
    "timers", "process", "module", "vm", "perf_hooks", "async_hooks", "string_decoder",
}


def _strip_json_comments(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        else:
            out.append(ch)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def _npm_package_name(spec: str) -> str:
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") and len(parts) > 1 else parts[0]


class Resolver:
    def __init__(self, repo: Path, files: list[str], inventory: dict):
        self.repo = repo
        self.files = set(files)
        self.prefixes = inventory.get("module_prefixes", [])
        self.ts_aliases: dict[str, list[tuple[str, list[str]]]] = {}
        self.workspace_packages: dict[str, str] = {}
        self.go_modules: list[tuple[str, str]] = []
        for man in inventory.get("manifests", []):
            d = str(PurePosixPath(man["path"]).parent)
            d = "" if d == "." else d
            if man.get("type") == "npm" and man.get("name"):
                self.workspace_packages[man["name"]] = d
            if man.get("type") == "go" and man.get("name"):
                self.go_modules.append((man["name"], d))
        self.go_modules.sort(key=lambda x: -len(x[0]))
        for f in files:
            if PurePosixPath(f).name.startswith(("tsconfig", "jsconfig")) and f.endswith(".json") and not C.is_generated(f):
                self._load_tsconfig(f)
        self.py_index: dict[str, set[str]] = defaultdict(set)
        self.jvm_packages: dict[str, set[str]] = defaultdict(set)
        self.cs_namespaces: dict[str, set[str]] = defaultdict(set)
        self.php_namespaces: dict[str, set[str]] = defaultdict(set)

    def _load_tsconfig(self, rel: str) -> None:
        text = C.read_text(self.repo / rel)
        if not text:
            return
        try:
            data = json.loads(_strip_json_comments(text))
        except ValueError:
            return
        opts = data.get("compilerOptions", {}) or {}
        paths = opts.get("paths") or {}
        if not paths:
            return
        base_dir = str(PurePosixPath(rel).parent)
        base_dir = "" if base_dir == "." else base_dir
        base = posixpath.normpath(posixpath.join(base_dir, opts.get("baseUrl", "."))) if (base_dir or opts.get("baseUrl")) else ""
        base = "" if base == "." else base
        aliases = []
        for pattern, targets in paths.items():
            wildcard = pattern.endswith("*")
            tgts = []
            for t in targets if isinstance(targets, list) else []:
                if not isinstance(t, str):
                    continue
                path = posixpath.normpath(posixpath.join(base, t.rstrip("*")))
                path = "" if path == "." else path
                tgts.append(path + "/" if t.endswith("*") else path)
            aliases.append((pattern.rstrip("*"), wildcard, tgts))
        aliases.sort(key=lambda a: -len(a[0]))
        self.ts_aliases[base_dir] = aliases

    # ---------------- JS/TS
    def _js_file(self, cand: str) -> str | None:
        cand = posixpath.normpath(cand)
        if cand in self.files:
            return cand
        for ext in JS_RESOLVE_EXT:
            if cand + ext in self.files:
                return cand + ext
        for ext in JS_RESOLVE_EXT:
            if f"{cand}/index{ext}" in self.files:
                return f"{cand}/index{ext}"
        return None

    def _aliases_for(self, importer: str) -> list[tuple[str, list[str]]]:
        d = str(PurePosixPath(importer).parent)
        while True:
            key = "" if d == "." else d
            if key in self.ts_aliases:
                return self.ts_aliases[key]
            if key == "":
                return []
            d = str(PurePosixPath(key).parent)

    def resolve_js(self, importer: str, spec: str):
        """Returns ('internal', file_or_dir) | ('external', name) | ('unresolved', kind) | None."""
        if spec.startswith("."):
            target = self._js_file(posixpath.join(str(PurePosixPath(importer).parent), spec))
            return ("internal", target) if target else ("unresolved", "relative")
        for pfx, wildcard, targets in self._aliases_for(importer):
            if not pfx or not (spec.startswith(pfx) if wildcard else spec == pfx):
                continue
            rest = spec[len(pfx):] if wildcard else ""
            for t in targets:
                if t.endswith("/"):
                    cand = t + rest if t != "/" else rest
                else:
                    cand = t
                target = self._js_file(cand) if cand else None
                if target:
                    return ("internal", target)
            return ("unresolved", "alias")
        name = _npm_package_name(spec)
        if name in self.workspace_packages:
            return ("internal", (self.workspace_packages[name] + "/package.json").lstrip("/"))
        if spec.startswith("node:") or name in NODE_BUILTINS:
            return None
        if spec.startswith(("@/", "~/", "#")):
            return ("unresolved", "alias")
        return ("external", name)

    # ---------------- Python
    def index_python(self, rel: str) -> None:
        p = PurePosixPath(rel)
        parts = list(p.parent.parts) + ([] if p.stem == "__init__" else [p.stem])
        for i in range(len(parts)):
            self.py_index[".".join(parts[i:])].add(rel)

    def resolve_py(self, importer: str, dotted: str, names: list[str]):
        norm = posixpath.normpath
        if dotted.startswith("."):
            level = len(dotted) - len(dotted.lstrip("."))
            base = PurePosixPath(importer).parent
            for _ in range(level - 1):
                base = base.parent
            rest = dotted.lstrip(".")
            cand_dir = norm(str(base / rest.replace(".", "/")) if rest else str(base))
            for cand in (cand_dir + ".py", cand_dir + "/__init__.py"):
                if norm(cand) in self.files:
                    return ("internal", norm(cand))
            for n in names:
                for cand in (f"{cand_dir}/{n}.py", f"{cand_dir}/{n}/__init__.py"):
                    if norm(cand) in self.files:
                        return ("internal", norm(cand))
            if cand_dir in (".", ""):
                return ("unresolved", "relative")
            return ("internal", norm(cand_dir + "/__init__.py"))
        parts = dotted.split(".")
        if parts[0] in PY_STDLIB:
            return None
        for i in range(len(parts), 0, -1):
            key = ".".join(parts[:i])
            hits = self.py_index.get(key)
            if not hits:
                continue
            if i == 1:
                # A bare name is internal only when it is a sibling module or a top-level
                # package/module (its parent directory is not itself a package).
                imp_dir = str(PurePosixPath(importer).parent)
                good = {h for h in hits if str(PurePosixPath(h).parent) == imp_dir or self._top_level(h, key)}
                if not good:
                    continue
                return ("internal", self._closest(importer, good))
            return ("internal", self._closest(importer, hits))
        return ("external", parts[0])

    def _top_level(self, hit: str, key: str) -> bool:
        p = PurePosixPath(hit)
        root = p.parent.parent if p.name == "__init__.py" else p.parent
        root_s = "" if str(root) == "." else str(root)
        return f"{root_s}/__init__.py".lstrip("/") not in self.files

    @staticmethod
    def _closest(importer: str, hits: set[str]) -> str:
        def common(a: str, b: str) -> int:
            n = 0
            for x, y in zip(a.split("/"), b.split("/")):
                if x != y:
                    break
                n += 1
            return n
        return max(sorted(hits), key=lambda h: (common(importer, h), -len(h)))

    # ---------------- JVM / C# / PHP namespaces
    @staticmethod
    def _resolve_ns(name: str, index: dict[str, set[str]], sep: str):
        parts = name.split(sep)
        for i in range(len(parts), 0, -1):
            hits = index.get(sep.join(parts[:i]))
            if hits:
                return ("internal", sorted(hits)[0])
        return ("external", sep.join(parts[:2]))

    # ---------------- Go
    def resolve_go(self, spec: str):
        for mod_path, mod_dir in self.go_modules:
            if spec == mod_path or spec.startswith(mod_path + "/"):
                rest = spec[len(mod_path):].lstrip("/")
                d = "/".join(x for x in (mod_dir, rest) if x)
                return ("internal", f"{d}/_.go" if d else "_.go")
        first = spec.split("/")[0]
        if "." not in first:
            return None  # standard library
        return ("external", "/".join(spec.split("/")[:3]))


def build(repo_name: str, repo_path: str | Path, inventory: dict) -> dict:
    repo = Path(repo_path).resolve()
    files = C.list_files(repo)
    res = Resolver(repo, files, inventory)
    code = [f for f in files if C.category_of(C.language_of(f)) == "code" and not C.is_generated(f) and not C.is_test(f)]
    texts: dict[str, str] = {}
    for f in code:
        t = C.read_text(repo / f)
        if t is not None:
            texts[f] = t
    for f, t in texts.items():
        if f.endswith(".py"):
            res.index_python(f)
        elif f.endswith(JVM_EXT):
            for m in JVM_PACKAGE.finditer(t[:5000]):
                res.jvm_packages[m.group(1)].add(f)
                break
        elif f.endswith(".cs"):
            for m in CS_NAMESPACE.finditer(t):
                res.cs_namespaces[m.group(1)].add(f)
        elif f.endswith(".php"):
            for m in PHP_NAMESPACE.finditer(t[:5000]):
                res.php_namespaces[m.group(1)].add(f)

    edges: Counter = Counter()
    samples: dict[tuple[str, str], list[str]] = defaultdict(list)
    external: dict[str, Counter] = defaultdict(Counter)
    unresolved: Counter = Counter()
    unresolved_samples: list[str] = []
    supported: Counter = Counter()
    unsupported: Counter = Counter()

    def record(importer: str, line: int, result) -> None:
        if result is None:
            return
        kind, value = result
        src = C.module_of(importer, res.prefixes)
        if kind == "internal":
            dst = C.module_of(value, res.prefixes)
            if dst != src:
                edges[(src, dst)] += 1
                if len(samples[(src, dst)]) < 3:
                    samples[(src, dst)].append(f"{importer}:{line}")
        elif kind == "external":
            external[src][value] += 1
        else:
            unresolved[value] += 1
            if len(unresolved_samples) < 15:
                unresolved_samples.append(f"{importer}:{line}")

    for f, t in texts.items():
        lang = C.language_of(f)
        idx = C.LineIndex(t)
        if f.endswith(JS_EXT):
            supported[lang] += 1
            for rx in (JS_IMPORT, JS_REQUIRE, JS_DYNAMIC):
                for m in rx.finditer(t):
                    record(f, idx.line(m.start(1)), res.resolve_js(f, m.group(1)))
        elif f.endswith(".py"):
            supported[lang] += 1
            for m in PY_IMPORT.finditer(t):
                for part in m.group(1).split(","):
                    dotted = part.strip().split()[0]
                    record(f, idx.line(m.start(1)), res.resolve_py(f, dotted, []))
            for m in PY_FROM.finditer(t):
                names = [n.strip().split()[0] for n in m.group(2).strip("() \t\n").split(",") if n.strip()]
                record(f, idx.line(m.start(1)), res.resolve_py(f, m.group(1), names))
        elif f.endswith(JVM_EXT):
            supported[lang] += 1
            for m in JVM_IMPORT.finditer(t):
                if not m.group(1).startswith(("java.", "kotlin.", "scala.", "groovy.")):
                    record(f, idx.line(m.start(1)), res._resolve_ns(m.group(1), res.jvm_packages, "."))
        elif f.endswith(".go"):
            supported[lang] += 1
            specs = [(m.start(1), m.group(1)) for m in GO_SINGLE.finditer(t)]
            for b in GO_BLOCK.finditer(t):
                specs += [(b.start(1) + s.start(1), s.group(1)) for s in GO_SPEC.finditer(b.group(1))]
            for pos, spec in specs:
                record(f, idx.line(pos), res.resolve_go(spec))
        elif f.endswith(".cs"):
            supported[lang] += 1
            for m in CS_USING.finditer(t):
                if not m.group(1).startswith("System"):
                    record(f, idx.line(m.start(1)), res._resolve_ns(m.group(1), res.cs_namespaces, "."))
        elif f.endswith(".php"):
            supported[lang] += 1
            for m in PHP_USE.finditer(t):
                record(f, idx.line(m.start(1)), res._resolve_ns(m.group(1), res.php_namespaces, "\\"))
        else:
            unsupported[lang] += 1

    modules = sorted({C.module_of(f, res.prefixes) for f in code})
    ca: dict[str, set] = defaultdict(set)
    ce: dict[str, set] = defaultdict(set)
    for (a, b) in edges:
        ce[a].add(b)
        ca[b].add(a)
    module_rows = []
    for m in modules:
        a_, e_ = len(ca[m]), len(ce[m])
        module_rows.append({"module": m, "ca": a_, "ce": e_,
                            "instability": round(e_ / (a_ + e_), 2) if (a_ + e_) else None,
                            "external_top": [n for n, _ in external[m].most_common(8)]})
    module_rows.sort(key=lambda r: -(r["ca"] + r["ce"]))

    cycles = _tarjan(modules, {m: sorted(ce[m]) for m in modules})
    cycle_rows = []
    for comp in cycles:
        inner = [{"from": a, "to": b, "imports": edges[(a, b)]} for (a, b) in edges if a in comp and b in comp]
        cycle_rows.append({"modules": sorted(comp), "edges": sorted(inner, key=lambda e: -e["imports"])})

    total_supported = sum(supported.values())
    return {
        "repo": repo_name,
        "generated_at": C.now_iso(),
        "coverage": {
            "code_files": len(code),
            "supported_files": total_supported,
            "supported_share": round(100 * total_supported / (len(code) or 1), 1),
            "by_language": dict(supported),
            "unsupported_languages": dict(unsupported),
        },
        "modules": module_rows,
        "edges": [{"from": a, "to": b, "imports": n, "samples": samples[(a, b)]}
                  for (a, b), n in edges.most_common()],
        "cycles": cycle_rows,
        "unresolved": {"counts": dict(unresolved), "samples": unresolved_samples},
        "notes": [
            "Regex-based extraction: imports inside comments or strings may be counted; dynamic loading, DI containers and reflection are invisible.",
            "Test files are excluded from the graph.",
        ],
    }


def _tarjan(nodes: list[str], graph: dict[str, list[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []
    counter = [0]

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, []):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                result.append(comp)

    for v in nodes:
        if v not in index:
            strong(v)
    return result


def to_markdown(g: dict) -> str:
    cov = g["coverage"]
    lines = [f"# Module dependencies: {g['repo']}", "",
             f"Parsed {cov['supported_files']} of {cov['code_files']} non-test code files ({cov['supported_share']}%). "
             f"Unsupported: {', '.join(f'{k} ({v})' for k, v in cov['unsupported_languages'].items()) or 'none'}. "
             f"Unresolved imports: {', '.join(f'{k} {v}' for k, v in g['unresolved']['counts'].items()) or 'none'}.", ""]
    lines += ["## Modules (Ca = modules depending on it, Ce = modules it depends on, I = Ce/(Ca+Ce))",
              C.md_table(["Module", "Ca", "Ce", "I", "Top external deps"],
                         [[f"`{m['module']}`", m["ca"], m["ce"], m["instability"] if m["instability"] is not None else "-",
                           ", ".join(m["external_top"][:6])] for m in g["modules"]], 40)]
    lines += ["", "## Dependencies between modules (by import count)",
              C.md_table(["From", "To", "Imports", "Samples"],
                         [[f"`{e['from']}`", f"`{e['to']}`", e["imports"], ", ".join(f"`{s}`" for s in e["samples"])]
                          for e in g["edges"]], 40)]
    lines += ["", f"## Cycles ({len(g['cycles'])})"]
    if not g["cycles"]:
        lines.append("None detected.")
    for c in g["cycles"]:
        lines.append(f"- {' ↔ '.join(f'`{m}`' for m in c['modules'])}: " +
                     ", ".join(f"{e['from']}→{e['to']} ({e['imports']})" for e in c["edges"][:8]))
    lines += ["", "## Notes"] + [f"- {n}" for n in g["notes"]]
    return "\n".join(lines)
