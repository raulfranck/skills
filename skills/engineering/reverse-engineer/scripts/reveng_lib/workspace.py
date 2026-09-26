"""Run workspace: creation, manifest, phase tracking and resumable status."""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C

SUBDIRS = ("inputs", "recon", "lenses", "verification", "synthesis", "runtime", "repos")
PHASES = ("scope", "recon", "plan", "wave-A", "wave-B", "verification", "synthesis")


def _repo_entry(name: str, path: Path) -> dict:
    entry = {"name": name, "path": C.posix(path), "exists": path.is_dir(), "is_git": False}
    if not path.is_dir():
        return entry
    if C.is_git_repo(path):
        entry.update({
            "is_git": True,
            "head": C.git_head(path),
            "branch": C.run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip(),
            "shallow": C.run_git(path, ["rev-parse", "--is-shallow-repository"]).strip() == "true",
            "commits": int((C.run_git(path, ["rev-list", "--count", "HEAD", "--", "."]).strip() or "0")),
            "dirty": bool(C.run_git(path, ["status", "--porcelain", "--", "."]).strip()),
        })
    return entry


def _exclude_from_git(workspace: Path) -> str | None:
    """Keep the workspace out of any git work tree it lives in (local .git/info/exclude)."""
    probe = workspace.parent
    top = C.run_git(probe, ["rev-parse", "--show-toplevel"]).strip()
    if not top:
        return None
    top_p = Path(top).resolve()
    try:
        rel = C.posix(workspace.resolve().relative_to(top_p))
    except ValueError:
        return None
    git_dir = C.run_git(probe, ["rev-parse", "--git-common-dir"]).strip()
    if not git_dir:
        return None
    git_dir_p = Path(git_dir) if Path(git_dir).is_absolute() else (probe / git_dir)
    exclude = (git_dir_p / "info" / "exclude").resolve()
    pattern = "/" + rel.split("/")[0] + "/"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    current = exclude.read_text(encoding="utf-8", errors="replace") if exclude.exists() else ""
    if pattern not in current.splitlines():
        with open(exclude, "a", encoding="utf-8") as fh:
            fh.write(("" if current.endswith("\n") or not current else "\n") + pattern + "\n")
        return f"added {pattern} to {C.posix(exclude)}"
    return None


def init(workspace: str | Path, repos: list[str], focus: list[str], language: str, runtime: bool, force: bool = False) -> str:
    ws = Path(workspace).resolve()
    manifest_path = ws / "manifest.json"
    if manifest_path.exists() and not force:
        return "Workspace already exists; not overwritten.\n\n" + status(ws)
    entries, used = [], set()
    for spec in repos:
        if "=" in spec and not re.match(r"^[A-Za-z]:[\\/]", spec):
            name, raw = spec.split("=", 1)
        else:
            name, raw = "", spec
        path = Path(raw).expanduser().resolve()
        name = C.slug(name or path.name)
        base, n = name, 2
        while name in used:
            name, n = f"{base}-{n}", n + 1
        used.add(name)
        entries.append(_repo_entry(name, path))
    for d in SUBDIRS:
        (ws / d).mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": ws.name,
        "created_at": C.now_iso(),
        "workspace": C.posix(ws),
        "report_language": language,
        "focus": focus,
        "runtime_opt_in": runtime,
        "repos": entries,
        "phases": {p: {"status": "pending"} for p in PHASES},
    }
    manifest["phases"]["scope"] = {"status": "done", "at": C.now_iso()}
    C.write_json(manifest_path, manifest)
    scope_md = [f"# Scope: {ws.name}", "", f"- Report language: {language}", f"- Runtime probing: {'yes' if runtime else 'no'}",
                "- Focus questions:" if focus else "- Focus questions: none"]
    scope_md += [f"  - {q}" for q in focus]
    scope_md += ["", "## Repositories"] + [
        f"- **{e['name']}**: `{e['path']}` · " + (
            f"git {str(e.get('head'))[:12]} on {e.get('branch')}, {e.get('commits')} commits"
            + (", SHALLOW" if e.get("shallow") else "") + (", uncommitted changes" if e.get("dirty") else "")
            if e["is_git"] else ("not a git repository" if e["exists"] else "PATH NOT FOUND"))
        for e in entries]
    C.write_text(ws / "inputs" / "scope.md", "\n".join(scope_md))
    note = _exclude_from_git(ws)
    missing = [e["name"] for e in entries if not e["exists"]]
    out = [f"Initialised {C.posix(ws)} with {len(entries)} repo(s)."]
    if note:
        out.append(note)
    if missing:
        out.append(f"WARNING: paths not found for {', '.join(missing)}.")
    return "\n".join(out)


def mark(workspace: str | Path, phase: str, state: str, note: str | None = None) -> str:
    ws = Path(workspace).resolve()
    manifest = C.read_json(ws / "manifest.json")
    entry = {"status": state, "at": C.now_iso()}
    if note:
        entry["note"] = note
    manifest.setdefault("phases", {})[phase] = entry
    C.write_json(ws / "manifest.json", manifest)
    return f"{phase}: {state}"


def _outputs(task: dict) -> list[str]:
    outs = task.get("outputs") or {}
    paths: list[str] = []
    for v in outs.values() if isinstance(outs, dict) else outs:
        paths += v if isinstance(v, list) else [v]
    return [p for p in paths if isinstance(p, str)]


def status(workspace: str | Path) -> str:
    ws = Path(workspace).resolve()
    manifest = C.read_json(ws / "manifest.json")
    lines = [f"Run {manifest['run_id']} · language {manifest.get('report_language')} · runtime {manifest.get('runtime_opt_in')}"]
    lines.append("Phases: " + ", ".join(f"{k}={v.get('status')}" for k, v in manifest.get("phases", {}).items()))
    for r in manifest["repos"]:
        name = r["name"]
        have = [x for x in ("inventory.json", "imports.json", "git-metrics.json") if (ws / "recon" / name / x).exists()]
        agent = (ws / "recon" / f"{name}.md").exists()
        lines.append(f"Recon {name}: scripts {len(have)}/3, recon agent {'done' if agent else 'pending'}")
    plan_path = ws / "plan.json"
    if not plan_path.exists():
        lines.append("Plan: not written yet.")
        return "\n".join(lines)
    plan = C.read_json(plan_path)
    pending = []
    for wave in plan.get("waves", []):
        done = 0
        tasks = wave.get("tasks", [])
        for t in tasks:
            outs = _outputs(t)
            ok = bool(outs) and all((ws / o).exists() and (ws / o).stat().st_size > 0 for o in outs)
            done += ok
            if not ok:
                pending.append(f"{t.get('id')} ({t.get('agent')}, {','.join(t.get('lenses', [])) or '-'}, {t.get('repo') or 'all'})")
        lines.append(f"Wave {wave.get('wave')}: {done}/{len(tasks)} tasks have their outputs")
    lines.append("Pending tasks: " + ("; ".join(pending) if pending else "none"))
    return "\n".join(lines)
