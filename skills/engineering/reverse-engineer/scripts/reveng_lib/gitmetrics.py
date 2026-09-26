"""Behavioural code analysis from git history: hotspots, change coupling, knowledge
distribution, code age, timeline and milestones (after Tornhill, Your Code as a Crime Scene)."""
from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

from . import common as C

CONVENTIONAL_RE = re.compile(r"^(feat|fix|chore|docs|refactor|test|tests|perf|build|ci|style|revert)(\([^)]*\))?!?:", re.I)


def _date(s: str) -> datetime:
    try:
        d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _parse_log(raw: str) -> list[dict]:
    commits = []
    for rec in raw.split("\x1e")[1:]:
        lines = rec.split("\n")
        header = lines[0].split("\x1f")
        if len(header) < 4:
            continue
        files = []
        for ln in lines[1:]:
            parts = ln.split("\t")
            if len(parts) != 3:
                continue
            a, d, path = parts
            files.append((C.posix(path.strip()), int(a) if a.isdigit() else 0, int(d) if d.isdigit() else 0))
        commits.append({"sha": header[0], "author": header[1], "date": _date(header[2]),
                        "subject": "\x1f".join(header[3:]).strip(), "files": files})
    return commits


def build(repo_name: str, repo_path: str | Path, inventory: dict, window_months: int = 12,
          max_commits: int = 20000, max_files_per_commit: int = 30) -> dict:
    repo = Path(repo_path).resolve()
    if not C.is_git_repo(repo):
        return {"repo": repo_name, "available": False, "reason": "not a git repository"}
    shallow = C.run_git(repo, ["rev-parse", "--is-shallow-repository"]).strip() == "true"
    total = int((C.run_git(repo, ["rev-list", "--count", "--no-merges", "HEAD", "--", "."]) or "0").strip() or 0)
    raw = C.run_git(repo, ["-c", "core.quotepath=false", "log", "--no-merges", "--no-renames", "--relative",
                           "--numstat", "--date=iso-strict", f"--max-count={max_commits}",
                           "--format=%x1e%H%x1f%aN%x1f%aI%x1f%s", "--", "."])
    commits = _parse_log(raw)
    if not commits:
        return {"repo": repo_name, "available": False, "reason": "no commits found", "shallow": shallow}

    prefixes = inventory.get("module_prefixes", [])
    current = set(C.list_files(repo))
    code_now = {p for p in current if C.category_of(C.language_of(p)) == "code" and not C.is_generated(p)}

    last = max(c["date"] for c in commits)
    first = min(c["date"] for c in commits)
    window_start = last - timedelta(days=int(window_months * 30.44))
    window = [c for c in commits if c["date"] >= window_start]

    fstats: dict[str, dict] = defaultdict(lambda: {"revs": 0, "revs_window": 0, "added": 0, "deleted": 0,
                                                   "authors": Counter(), "first": None, "last": None})
    for c in commits:
        in_window = c["date"] >= window_start
        for path, a, d in c["files"]:
            fs = fstats[path]
            fs["revs"] += 1
            fs["revs_window"] += 1 if in_window else 0
            fs["added"] += a
            fs["deleted"] += d
            fs["authors"][c["author"]] += max(a, 1)
            fs["first"] = c["date"] if fs["first"] is None or c["date"] < fs["first"] else fs["first"]
            fs["last"] = c["date"] if fs["last"] is None or c["date"] > fs["last"] else fs["last"]

    # Hotspots: change frequency (recent window) overlaid with indentation complexity.
    use_window = any(fstats[p]["revs_window"] for p in code_now if p in fstats)
    key = "revs_window" if use_window else "revs"
    cands = sorted((p for p in code_now if p in fstats and not C.is_test(p)), key=lambda p: -fstats[p][key])[:60]
    rows = []
    for p in cands:
        text = C.read_text(repo / p)
        loc, cx, _ = C.text_stats(text) if text else (0, 0.0, 0)
        rows.append({"path": p, "module": C.module_of(p, prefixes), "revisions": fstats[p][key],
                     "revisions_total": fstats[p]["revs"], "loc": loc, "complexity": cx,
                     "authors": len(fstats[p]["authors"])})
    max_rev = max((r["revisions"] for r in rows), default=1) or 1
    max_cx = max((r["complexity"] for r in rows), default=1) or 1
    for r in rows:
        r["score"] = round((r["revisions"] / max_rev) * (r["complexity"] / max_cx), 3)
    hotspots = sorted(rows, key=lambda r: -r["score"])[:25]

    # Change coupling (logical coupling): files that change together in the window.
    min_shared = 5 if len(window) >= 300 else 3
    pair_counts: Counter = Counter()
    revs: Counter = Counter()
    mod_pairs: Counter = Counter()
    mod_revs: Counter = Counter()
    for c in window:
        fs = sorted({p for p, _, _ in c["files"] if p in code_now})
        if not fs or len(fs) > max_files_per_commit:
            continue
        for p in fs:
            revs[p] += 1
        if len(fs) >= 2:
            for a, b in combinations(fs, 2):
                pair_counts[(a, b)] += 1
        mods = sorted({C.module_of(p, prefixes) for p in fs})
        for m in mods:
            mod_revs[m] += 1
        for a, b in combinations(mods, 2):
            mod_pairs[(a, b)] += 1
    coupling = []
    for (a, b), shared in pair_counts.items():
        if shared < min_shared:
            continue
        degree = round(100 * shared / ((revs[a] + revs[b]) / 2), 1)
        ma, mb = C.module_of(a, prefixes), C.module_of(b, prefixes)
        coupling.append({"a": a, "b": b, "shared_commits": shared, "degree": degree,
                         "cross_module": ma != mb, "module_a": ma, "module_b": mb})
    coupling.sort(key=lambda x: (-x["degree"], -x["shared_commits"]))
    module_coupling = []
    for (a, b), shared in mod_pairs.items():
        if shared < min_shared:
            continue
        module_coupling.append({"a": a, "b": b, "shared_commits": shared,
                                "degree": round(100 * shared / ((mod_revs[a] + mod_revs[b]) / 2), 1)})
    module_coupling.sort(key=lambda x: (-x["degree"], -x["shared_commits"]))

    # Knowledge distribution per module and a truck-factor approximation.
    mod_authors: dict[str, Counter] = defaultdict(Counter)
    owners: dict[str, str] = {}
    for p in code_now:
        if p not in fstats:
            continue
        mod_authors[C.module_of(p, prefixes)].update(fstats[p]["authors"])
        owners[p] = fstats[p]["authors"].most_common(1)[0][0]
    knowledge = []
    for mod, cnt in sorted(mod_authors.items(), key=lambda kv: -sum(kv[1].values())):
        tot = sum(cnt.values()) or 1
        top = cnt.most_common(3)
        knowledge.append({"module": mod, "authors": len(cnt), "main_author": top[0][0],
                          "main_share": round(100 * top[0][1] / tot, 1),
                          "top_authors": [{"author": a, "share": round(100 * v / tot, 1)} for a, v in top]})
    owned = Counter(owners.values())
    removed: set[str] = set()
    truck = 0
    for author, _ in owned.most_common():
        orphan = sum(1 for o in owners.values() if o in removed)
        if orphan > 0.5 * len(owners):
            break
        removed.add(author)
        truck += 1
    truck_factor = {"value": truck, "files_considered": len(owners),
                    "top_owners": [{"author": a, "files_owned": n, "share": round(100 * n / (len(owners) or 1), 1)}
                                   for a, n in owned.most_common(8)],
                    "method": "main author per file by lines added; greedy removal until >50% of files lose their owner"}

    # Code age per module (months since last change of each current file).
    ages: dict[str, list[float]] = defaultdict(list)
    for p in code_now:
        if p in fstats and fstats[p]["last"]:
            ages[C.module_of(p, prefixes)].append((last - fstats[p]["last"]).days / 30.44)
    code_age = [{"module": m, "median_months_since_change": round(statistics.median(v), 1), "files": len(v)}
                for m, v in sorted(ages.items())]

    per_month: Counter = Counter(c["date"].strftime("%Y-%m") for c in commits)
    authors_all = Counter(c["author"] for c in commits)
    authors_window = {c["author"] for c in window}
    bots = {a for a in authors_all if "bot" in a.lower()}
    conventional = Counter()
    for c in commits:
        m = CONVENTIONAL_RE.match(c["subject"])
        conventional[m.group(1).lower() if m else "(other)"] += 1
    big = sorted((c for c in commits if len(c["files"]) >= 50), key=lambda c: -len(c["files"]))[:15]
    tags_raw = C.run_git(repo, ["for-each-ref", "--sort=-creatordate", "--count=30",
                                "--format=%(refname:short)%1f%(creatordate:iso-strict)", "refs/tags"])
    tags = [{"tag": t.split("\x1f")[0], "date": t.split("\x1f")[1][:10]} for t in tags_raw.splitlines() if "\x1f" in t]

    return {
        "repo": repo_name,
        "available": True,
        "head": C.git_head(repo),
        "generated_at": C.now_iso(),
        "shallow": shallow,
        "commits_total": total,
        "commits_parsed": len(commits),
        "first_commit": first.date().isoformat(),
        "last_commit": last.date().isoformat(),
        "window": {"months": window_months, "start": window_start.date().isoformat(), "commits": len(window),
                   "hotspot_basis": key},
        "authors": {"total": len(authors_all), "active_in_window": len(authors_window),
                    "bot_commit_share": round(100 * sum(authors_all[b] for b in bots) / len(commits), 1)},
        "hotspots": hotspots,
        "change_coupling": coupling[:40],
        "module_coupling": module_coupling[:20],
        "coupling_params": {"min_shared_commits": min_shared, "max_files_per_commit": max_files_per_commit},
        "knowledge": knowledge,
        "truck_factor": truck_factor,
        "code_age": code_age,
        "commits_per_month": dict(sorted(per_month.items())),
        "conventional_commits": dict(conventional.most_common()),
        "large_commits": [{"sha": c["sha"][:12], "date": c["date"].date().isoformat(), "author": c["author"],
                           "files": len(c["files"]), "subject": c["subject"][:120]} for c in big],
        "tags": tags,
        "limitations": [
            "Renames are not followed (--no-renames): a moved file starts a new history.",
            "Squash merges collapse many changes into one commit, which weakens coupling signals.",
            "Merge commits are excluded.",
        ] + (["The clone is shallow: history is truncated, so age, knowledge and timeline are partial."] if shallow else []),
    }


def to_markdown(g: dict) -> str:
    if not g.get("available"):
        return f"# Git metrics: {g['repo']}\n\nNot available: {g.get('reason')}."
    w = g["window"]
    lines = [f"# Git metrics: {g['repo']}", "",
             f"{g['commits_total']} commits (no merges), {g['first_commit']} → {g['last_commit']} · "
             f"{g['authors']['total']} authors ({g['authors']['active_in_window']} active in window) · "
             f"bot commits {g['authors']['bot_commit_share']}% · shallow: {g['shallow']}",
             f"Window for hotspots and coupling: last {w['months']} months before the last commit "
             f"(from {w['start']}, {w['commits']} commits; basis `{w['hotspot_basis']}`).", ""]
    lines += ["## Hotspots (change frequency × indentation complexity)",
              C.md_table(["File", "Module", "Revisions", "LOC", "Complexity", "Authors", "Score"],
                         [[f"`{h['path']}`", h["module"], h["revisions"], h["loc"], h["complexity"], h["authors"], h["score"]]
                          for h in g["hotspots"]], 15)]
    cross = [c for c in g["change_coupling"] if c["cross_module"]]
    lines += ["", f"## Change coupling (min {g['coupling_params']['min_shared_commits']} shared commits; "
                  f"{len(cross)} cross-module pairs)",
              C.md_table(["File A", "File B", "Shared", "Degree %", "Cross-module"],
                         [[f"`{c['a']}`", f"`{c['b']}`", c["shared_commits"], c["degree"], "yes" if c["cross_module"] else ""]
                          for c in g["change_coupling"]], 20)]
    lines += ["", "## Module coupling", C.md_table(["Module A", "Module B", "Shared", "Degree %"],
                                                   [[c["a"], c["b"], c["shared_commits"], c["degree"]] for c in g["module_coupling"]], 15)]
    tf = g["truck_factor"]
    lines += ["", f"## Knowledge distribution (truck factor ≈ {tf['value']} over {tf['files_considered']} files)",
              C.md_table(["Module", "Authors", "Main author", "Main share %"],
                         [[k["module"], k["authors"], k["main_author"], k["main_share"]] for k in g["knowledge"]], 20)]
    lines += ["", "## Code age (median months since last change)",
              C.md_table(["Module", "Median months", "Files"],
                         [[a["module"], a["median_months_since_change"], a["files"]] for a in g["code_age"]], 25)]
    months = list(g["commits_per_month"].items())
    lines += ["", "## Activity (commits per month, last 18 months)",
              " · ".join(f"{m}: {n}" for m, n in months[-18:])]
    lines += ["", "## Conventional commit types", ", ".join(f"{k}: {v}" for k, v in g["conventional_commits"].items())]
    if g["large_commits"]:
        lines += ["", "## Large commits (≥ 50 files; restructurings, imports, mass renames)",
                  C.md_table(["SHA", "Date", "Files", "Subject"],
                             [[c["sha"], c["date"], c["files"], c["subject"]] for c in g["large_commits"]], 15)]
    if g["tags"]:
        lines += ["", "## Recent tags", ", ".join(f"{t['tag']} ({t['date']})" for t in g["tags"][:20])]
    lines += ["", "## Limitations"] + [f"- {x}" for x in g["limitations"]]
    return "\n".join(lines)
