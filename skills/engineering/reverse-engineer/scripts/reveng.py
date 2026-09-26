#!/usr/bin/env python3
"""reverse-engineer pipeline CLI (stdlib only, Python 3.9+).

Commands:
  init     create a run workspace and its manifest
  recon    inventory, module dependencies and git metrics per repo, then integration signals
  status   phases, recon progress and plan tasks still missing outputs
  mark     record a phase status in the manifest
  check    mechanical evidence check over every findings file
  digest   merge findings, checks and verdicts into synthesis/digest.md
  lint     language and structure check of the report source (synthesis/lint.md)
  render   lint, then build the self-contained report.html at the workspace root
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the installed skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))

from reveng_lib import common as C  # noqa: E402
from reveng_lib import digest, evidence, gitmetrics, imports, inventory, report, signals, workspace  # noqa: E402


def _recon(ws: Path, only: str | None, force: bool) -> str:
    manifest = C.read_json(ws / "manifest.json")
    out, sig = [], {}
    summary = {}
    for r in manifest["repos"]:
        name, path = r["name"], Path(r["path"])
        rdir = ws / "recon" / name
        if not r.get("exists", True) or not path.is_dir():
            out.append(f"{name}: SKIPPED, path not found")
            continue
        inv_path = rdir / "inventory.json"
        cached = inv_path.exists() and not force and (only is None or only != name)
        if cached:
            inv = C.read_json(inv_path)
            cached = inv.get("head") == (C.git_head(path) if C.is_git_repo(path) else None)
        if not cached:
            inv = inventory.build(name, path, exclude_abs=[ws])
            C.write_json(inv_path, inv)
            C.write_text(rdir / "inventory.md", inventory.to_markdown(inv))
            imp = imports.build(name, path, inv)
            C.write_json(rdir / "imports.json", imp)
            C.write_text(rdir / "imports.md", imports.to_markdown(imp))
            gm = gitmetrics.build(name, path, inv)
            C.write_json(rdir / "git-metrics.json", gm)
            C.write_text(rdir / "git-metrics.md", gitmetrics.to_markdown(gm))
        imp = C.read_json(rdir / "imports.json")
        gm = C.read_json(rdir / "git-metrics.json")
        sig[name] = signals.build_repo(name, path, inv)
        t = inv["totals"]
        langs = ", ".join(f"{l['language']} {round(100 * l['loc'] / (t['source_loc'] or 1))}%" for l in inv["languages"][:3])
        sections = inv["sections"]
        summary[name] = {
            "source_files": t["source_files"], "source_loc": t["source_loc"], "test_files": t["test_files"],
            "languages": langs, "modules": len(inv["modules"]), "monorepo": inv["monorepo"]["detected"],
            "iac": sorted({x["kind"] for x in sections.get("iac", [])}),
            "ci": sorted({x["kind"] for x in sections.get("ci", [])}),
            "contracts": len(sections.get("contracts", [])),
            "migrations": any(x["kind"] == "migration" for x in sections.get("data", [])),
            "observability_as_code": len(sections.get("observability", [])),
            "import_coverage": imp["coverage"]["supported_share"], "cycles": len(imp["cycles"]),
            "commits": gm.get("commits_total", 0) if gm.get("available") else 0,
            "git_history": "shallow" if gm.get("shallow") else ("full" if gm.get("available") else "none"),
            "routes": sig[name]["routes_total"], "messaging_names": len({m["name"] for m in sig[name]["messaging"]}),
        }
        s = summary[name]
        out.append(f"{name}{' (cached)' if cached else ''}: {s['source_files']} source files, {s['source_loc']} LOC ({langs}); "
                   f"{s['modules']} modules{', monorepo' if s['monorepo'] else ''}; {s['commits']} commits ({s['git_history']} history); "
                   f"IaC {s['iac'] or 'none'}; CI {s['ci'] or 'none'}; contracts {s['contracts']}; migrations {s['migrations']}; "
                   f"routes {s['routes']}; messaging names {s['messaging_names']}; import coverage {s['import_coverage']}%")
    edges = signals.cross_repo(sig)
    C.write_json(ws / "recon" / "signals.json", {"repos": sig, "cross_repo_edges": edges})
    C.write_text(ws / "recon" / "signals.md", signals.to_markdown(sig, edges))
    C.write_json(ws / "recon" / "summary.json", {"repos": summary, "cross_repo_candidate_edges": len(edges)})
    if len(sig) > 1:
        out.append(f"cross-repo candidate edges: {len(edges)} (recon/signals.md)")
    workspace.mark(ws, "recon", "done", "scripts")
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="reveng", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--workspace", required=True)
    s.add_argument("--repo", action="append", required=True, help="PATH or NAME=PATH (repeatable)")
    s.add_argument("--focus", action="append", default=[], help="focus question (repeatable)")
    s.add_argument("--language", default="en")
    s.add_argument("--runtime", action="store_true", help="the user opted in to runtime probing")
    s.add_argument("--audience", default="dev", choices=["dev", "lead", "non-technical"],
                   help="who the report is written for")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("recon")
    s.add_argument("--workspace", required=True)
    s.add_argument("--repo", help="recompute only this repo")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("--workspace", required=True)
    s = sub.add_parser("mark")
    s.add_argument("--workspace", required=True)
    s.add_argument("--phase", required=True)
    s.add_argument("--state", required=True, choices=["pending", "running", "done", "skipped", "failed"])
    s.add_argument("--note")
    s = sub.add_parser("check")
    s.add_argument("--workspace", required=True)
    s = sub.add_parser("digest")
    s.add_argument("--workspace", required=True)
    s = sub.add_parser("lint")
    s.add_argument("--workspace", required=True)
    s.add_argument("--file", help="report source, default synthesis/report.md")
    s = sub.add_parser("render")
    s.add_argument("--workspace", required=True)
    s.add_argument("--file", help="report source, default synthesis/report.md")
    s.add_argument("--open", action="store_true", help="open report.html in the default browser")
    a = p.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

    ws = Path(a.workspace).expanduser().resolve()
    if a.cmd != "init" and not (ws / "manifest.json").exists():
        print(f"No manifest at {C.posix(ws)}. Run init first.", file=sys.stderr)
        return 2
    if a.cmd == "init":
        print(workspace.init(ws, a.repo, a.focus, a.language, a.runtime, a.force, a.audience))
    elif a.cmd == "recon":
        print(_recon(ws, a.repo, a.force))
    elif a.cmd == "status":
        print(workspace.status(ws))
    elif a.cmd == "mark":
        print(workspace.mark(ws, a.phase, a.state, a.note))
    elif a.cmd == "check":
        r = evidence.check(ws)
        t = r["totals"]
        print(f"{t['findings']} findings: {t['ok']} ok, {t['evidence_error']} evidence errors, {t['schema_error']} schema errors, "
              f"{t['relocated']} relocated; duplicates {len(r['duplicates'])}. Report: verification/mechanical.md")
    elif a.cmd == "digest":
        d = digest.build(ws)
        t = d["totals"]
        print(f"{t['findings']} findings kept, {t['refuted']} refuted; by certainty {t['by_certainty']}. "
              f"Digest: synthesis/digest.md")
    elif a.cmd == "lint":
        r = report.lint_only(ws, a.file)
        print(f"lint: {r['errors']} errors, {r['warnings']} warnings. Report: synthesis/lint.md")
    elif a.cmd == "render":
        r = report.build(ws, a.file)
        print(f"lint: {r['errors']} errors, {r['warnings']} warnings (synthesis/lint.md); {r['terms']} terms with tooltips.")
        print(f"html: {r['html']}")
        if a.open:
            _open(r["html"])
    return 0


def _open(path: str) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main())
