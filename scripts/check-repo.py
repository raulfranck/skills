#!/usr/bin/env python3
"""Check the repository invariants described in CLAUDE.md. Exit code 1 when any fails."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIFECYCLE = {"in-progress", "misc", "deprecated"}
UNEXPECTED_ROOT = ["commands", "hooks", "bin", "output-styles", "monitors", "themes", "workflows",
                   ".mcp.json", ".lsp.json", "settings.json"]

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        err(f"{rel(path)}: no frontmatter")
        return {}
    data = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if not km:
            continue
        key, value = km.group(1), km.group(2).strip()
        if value and value[0] not in "\"'[{|>" and ": " in value:
            err(f"{rel(path)}: `{key}` holds an unquoted ': ', which breaks YAML; quote it or rephrase")
        data[key] = value.strip("\"'")
    return data


def main() -> int:
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    name = plugin.get("name")
    entries = market.get("plugins", [])
    if len(entries) != 1 or entries[0].get("name") != name or entries[0].get("source") not in ("./", "."):
        err(f"marketplace.json must hold one entry named {name!r} with source \"./\"")
    if "version" in plugin or any("version" in e for e in entries):
        err("remove `version` from plugin.json and the marketplace entry: releases follow commits (ADR 0004)")

    for item in UNEXPECTED_ROOT:
        if (ROOT / item).exists():
            err(f"{item} at the root ships to every user; add it on purpose and update this check")

    listed = {s.rstrip("/") for s in plugin.get("skills", [])}
    areas = sorted(d.name for d in (ROOT / "skills").iterdir() if d.is_dir() and d.name not in LIFECYCLE)
    for s in listed:
        if not (ROOT / s).is_dir():
            err(f"plugin.json lists {s}, which does not exist")
        if s.split("/")[-1] in LIFECYCLE:
            err(f"plugin.json lists the lifecycle bucket {s}")
    for loose in (ROOT / "skills").glob("*/SKILL.md"):
        err(f"{rel(loose)}: a skill directly under skills/ would ship through the default scan; move it into an area")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    area_readmes = ""
    summary = []
    for area in areas:
        adir = ROOT / "skills" / area
        if f"./skills/{area}" not in listed:
            err(f"area {area} is not listed in plugin.json skills")
        area_readme = (adir / "README.md").read_text(encoding="utf-8") if (adir / "README.md").exists() else ""
        if not area_readme:
            err(f"area {area}: missing README.md")
        area_readmes += area_readme
        for sdir in sorted(p for p in adir.iterdir() if p.is_dir()):
            if not (sdir / "SKILL.md").exists():
                err(f"{rel(sdir)}: folder without SKILL.md inside an area")
                continue
            fm = frontmatter(sdir / "SKILL.md")
            if fm.get("name") and fm["name"] != sdir.name:
                err(f"{rel(sdir)}: frontmatter name {fm['name']!r} differs from the folder name")
            if not fm.get("description"):
                err(f"{rel(sdir)}: SKILL.md has no description")
            if f"skills/{area}/{sdir.name}/SKILL.md" not in readme:
                err(f"{rel(sdir)}: not linked from the top-level README.md")
            if f"./{sdir.name}/SKILL.md" not in area_readme:
                err(f"{rel(sdir)}: not linked from skills/{area}/README.md")
            if not (ROOT / "docs" / area / f"{sdir.name}.md").exists():
                err(f"{rel(sdir)}: missing docs/{area}/{sdir.name}.md")
            summary.append(f"/{name}:{sdir.name}" + (" (user-invoked)" if fm.get("disable-model-invocation") == "true" else ""))

    agents = []
    agents_dir = ROOT / "agents"
    if agents_dir.exists():
        for sub in agents_dir.iterdir():
            if sub.is_dir():
                err(f"{rel(sub)}: agent subfolders do not load; keep agents flat (ADR 0002)")
        for af in sorted(agents_dir.glob("*.md")):
            fm = frontmatter(af)
            for key in ("name", "description", "tools", "model"):
                if not fm.get(key):
                    err(f"{rel(af)}: missing {key}")
            tools = {t.strip() for t in fm.get("tools", "").split(",")}
            if tools & {"Agent", "Task", "Skill"}:
                err(f"{rel(af)}: workers must not hold Agent, Task or Skill tools (ADR 0002)")
            prefix = fm.get("name", "").split("-")[0]
            if prefix and prefix + "-" not in area_readmes:
                err(f"{rel(af)}: prefix {prefix}- is not documented in any area README")
            agents.append(f"{name}:{fm.get('name', af.stem)}")

    for bucket in LIFECYCLE:
        if not (ROOT / "skills" / bucket / "README.md").exists():
            err(f"skills/{bucket}: missing README.md")

    claude = shutil.which("claude")
    if claude:
        proc = subprocess.run([claude, "plugin", "validate", "."], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0 or "Validation failed" in proc.stdout:
            err(f"claude plugin validate . failed:\n{proc.stdout.strip()}")
    else:
        print("claude CLI not found: manifest validation skipped")

    print(f"plugin {name}")
    print("skills: " + (", ".join(summary) or "none"))
    print("agents: " + (", ".join(agents) or "none"))
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print(f"- {e}")
        return 1
    print("\nAll repository checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
