"""Mechanical evidence check: schema of every finding, and whether each cited file, line
range, quote, commit and artifact exists. Semantic support is the verifier agent's job."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import common as C

LENSES = {"recon", "domain", "data", "integrations", "structure", "infra", "evolution", "flows", "risk",
          "runtime", "synthesis"}
CERTAINTIES = ("fact", "inference", "hypothesis", "unknown")
IMPACTS = ("high", "medium", "low")
ID_RX = re.compile(r"^[A-Z]+[0-9]*-[0-9]{3,}$")
GAP_RX = re.compile(r"<REDACTED>|\.\.\.|…")
STOPWORDS = {
    "en": {"the", "and", "is", "are", "with", "of", "that", "which", "for", "when", "without", "from", "this", "not", "it"},
    "pt": {"de", "que", "e", "o", "a", "os", "as", "com", "não", "para", "um", "uma", "no", "na", "do", "da", "se", "por", "em"},
    "es": {"de", "que", "y", "el", "la", "los", "las", "con", "no", "para", "un", "una", "en", "por", "se"},
}
FINDING_GLOBS = ("recon/*.findings.jsonl", "lenses/*.findings.jsonl", "runtime/*.findings.jsonl",
                 "synthesis/*.findings.jsonl")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _quote_in(hay: str, quote: str) -> bool:
    parts = [_norm(p) for p in GAP_RX.split(quote)]
    parts = [p for p in parts if len(p) >= 3] or [_norm(quote)]
    hay = _norm(hay)
    pos = 0
    for p in parts:
        i = hay.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def wrong_language(text: str, report_language: str) -> bool:
    """True when prose written for a pt/es/en report reads as another of those languages."""
    target = (report_language or "").lower()[:2]
    if target not in STOPWORDS:
        return False
    words = re.findall(r"[a-záéíóúâêôãõçñ]+", text.lower())
    if len(words) < 6:
        return False
    scores = {lang: sum(w in sw for w in words) for lang, sw in STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best != target and scores[best] >= 3 and scores[best] > 1.5 * scores[target]


def _parse_lines(value) -> tuple[int, int] | None:
    if isinstance(value, int):
        return value, value
    if not isinstance(value, str):
        return None
    m = re.match(r"^\s*L?(\d+)\s*(?:[-–:]\s*L?(\d+))?\s*$", value)
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2) or a)
    return (a, b) if a <= b else (b, a)


def load_findings(workspace: Path) -> tuple[list[dict], dict[str, dict]]:
    """All findings with their source file, plus per-file parse reports."""
    findings, files = [], {}
    for pattern in FINDING_GLOBS:
        for path in sorted(workspace.glob(pattern)):
            rel = C.posix(path.relative_to(workspace))
            report = {"findings": 0, "parse_errors": []}
            with open(path, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError as exc:
                        report["parse_errors"].append(f"line {n}: {str(exc)[:120]}")
                        continue
                    if not isinstance(obj, dict):
                        report["parse_errors"].append(f"line {n}: not a JSON object")
                        continue
                    obj["_file"] = rel
                    obj["_line"] = n
                    findings.append(obj)
                    report["findings"] += 1
            files[rel] = report
    return findings, files


def _schema(f: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    fid = f.get("id")
    if not isinstance(fid, str) or not ID_RX.match(fid):
        errors.append(f"id {fid!r} does not match TASK-NNN (for example A1-007)")
    for key in ("lens", "kind", "certainty", "claim", "impact"):
        if not f.get(key):
            errors.append(f"missing {key}")
    if f.get("lens") and f["lens"] not in LENSES:
        warnings.append(f"unknown lens {f['lens']!r}")
    cert = f.get("certainty")
    if cert and cert not in CERTAINTIES:
        errors.append(f"certainty must be one of {', '.join(CERTAINTIES)}")
    if f.get("impact") and f["impact"] not in IMPACTS:
        errors.append(f"impact must be one of {', '.join(IMPACTS)}")
    ev = f.get("evidence") or []
    if not isinstance(ev, list):
        errors.append("evidence must be a list")
        ev = []
    if cert == "fact" and not any(isinstance(e, dict) and ("path" in e or "commit" in e or "artifact" in e or "search" in e) for e in ev):
        errors.append("a fact needs at least one file, commit, artifact or search evidence item")
    if cert == "inference" and not f.get("reasoning"):
        errors.append("an inference needs reasoning")
    if cert == "inference" and not ev and not f.get("based_on"):
        errors.append("an inference needs evidence or based_on")
    if cert == "hypothesis" and not f.get("how_to_verify"):
        errors.append("a hypothesis needs how_to_verify")
    if cert == "unknown" and not f.get("why_unknown"):
        errors.append("an unknown needs why_unknown")
    if len(str(f.get("claim", ""))) > 600:
        warnings.append("claim longer than 600 characters")
    return errors, warnings


def check(workspace: str | Path) -> dict:
    workspace = Path(workspace).resolve()
    manifest = C.read_json(workspace / "manifest.json")
    repos = {r["name"]: Path(r["path"]) for r in manifest["repos"]}
    default_repo = next(iter(repos)) if len(repos) == 1 else None
    findings, files = load_findings(workspace)
    ids: dict[str, str] = {}
    duplicates = []
    for f in findings:
        fid = f.get("id")
        if isinstance(fid, str):
            if fid in ids:
                duplicates.append(f"{fid} in {ids[fid]} and {f['_file']}")
            ids[fid] = f["_file"]

    text_cache: dict[Path, list[str] | None] = {}

    def lines_of(p: Path):
        if p not in text_cache:
            t = C.read_text(p)
            text_cache[p] = t.splitlines() if t is not None else None
        return text_cache[p]

    results = {}
    totals = {"findings": len(findings), "ok": 0, "schema_error": 0, "evidence_error": 0, "relocated": 0,
              "wrong_language": 0}
    language = manifest.get("report_language", "")
    seen_ids: set[str] = set()
    for f in findings:
        errors, warnings = _schema(f)
        key = f.get("id") or f"{f['_file']}#{f['_line']}"
        if key in seen_ids:
            errors.append("duplicate id; this later occurrence is dropped from the digest")
            key = f"{key}#line{f['_line']}"
        seen_ids.add(key)
        ev_results = []
        for i, e in enumerate(f.get("evidence") or []):
            if not isinstance(e, dict):
                ev_results.append({"index": i, "status": "invalid", "detail": "evidence item is not an object"})
                continue
            repo_name = e.get("repo") or default_repo
            if "artifact" in e:
                ok = (workspace / str(e["artifact"])).exists()
                ev_results.append({"index": i, "status": "ok" if ok else "artifact_missing", "detail": e["artifact"]})
                continue
            if "search" in e:
                ev_results.append({"index": i, "status": "unchecked", "detail": "search evidence is taken as reported"})
                continue
            if repo_name not in repos:
                ev_results.append({"index": i, "status": "repo_unknown", "detail": f"repo {repo_name!r} not in manifest"})
                continue
            root = repos[repo_name]
            if "commit" in e:
                ok = bool(C.run_git(root, ["cat-file", "-t", str(e["commit"])]).strip() == "commit")
                ev_results.append({"index": i, "status": "ok" if ok else "commit_missing", "detail": e["commit"]})
                continue
            if "path" not in e:
                ev_results.append({"index": i, "status": "invalid", "detail": "needs path, commit, search or artifact"})
                continue
            rel = C.posix(str(e["path"]))
            if rel.startswith("./"):
                rel = rel[2:]
            rel = rel.lstrip("/")
            p = root / rel
            if not p.is_file() and rel.split("/")[0] == repo_name:
                alt = "/".join(rel.split("/")[1:])
                if (root / alt).is_file():
                    warnings.append(f"evidence {i}: path included the repo name; use {alt!r}")
                    rel, p = alt, root / alt
            if not p.is_file():
                ev_results.append({"index": i, "status": "file_missing", "detail": rel})
                continue
            content = lines_of(p)
            if content is None:
                ev_results.append({"index": i, "status": "ok", "detail": "binary or oversized file; lines not checked"})
                continue
            span = _parse_lines(e.get("lines")) if e.get("lines") is not None else None
            quote = e.get("quote")
            out_of_range = bool(span) and (span[0] < 1 or span[1] > len(content))
            range_detail = f"lines {e.get('lines')} but file has {len(content)} lines"
            if not quote:
                if out_of_range:
                    ev_results.append({"index": i, "status": "line_out_of_range", "detail": range_detail})
                    continue
                if f.get("certainty") == "fact":
                    warnings.append(f"evidence {i}: fact cited without a quote")
                ev_results.append({"index": i, "status": "no_quote", "detail": f"{rel}:{e.get('lines')}"})
                continue
            if span and not out_of_range:
                a, b = span
                window = "\n".join(content[max(0, a - 4): min(len(content), b + 3)])
                if _quote_in(window, str(quote)):
                    ev_results.append({"index": i, "status": "ok", "detail": f"{rel}:{e.get('lines')}"})
                    continue
            elif not span:
                warnings.append(f"evidence {i}: no line range given")
            head = GAP_RX.split(str(quote))[0].strip()
            first = _norm(head.splitlines()[0])[:40] if head else ""
            found = None
            if len(first) >= 3:
                for n, ln in enumerate(content, 1):
                    if first in _norm(ln) and _quote_in("\n".join(content[n - 1: n + 40]), str(quote)):
                        found = n
                        break
            if found:
                height = (span[1] - span[0]) if span else str(quote).count("\n")
                ev_results.append({"index": i, "status": "relocated", "detail": f"quote found at line {found}",
                                   "relocated_lines": f"{found}-{found + max(0, height)}"})
                continue
            ev_results.append({"index": i, "status": "line_out_of_range" if out_of_range else "quote_mismatch",
                               "detail": range_detail if out_of_range else f"quote not found in {rel}"})

        bad = [r for r in ev_results if r["status"] in ("invalid", "repo_unknown", "file_missing", "line_out_of_range",
                                                         "quote_mismatch", "commit_missing", "artifact_missing")]
        for ref in f.get("based_on") or []:
            if ref not in ids:
                errors.append(f"based_on references unknown finding {ref}")
        prose = " ".join(str(f.get(k) or "") for k in ("claim", "reasoning", "how_to_verify", "why_unknown"))
        if wrong_language(prose, language):
            warnings.append(f"written in another language than the report ({language})")
            totals["wrong_language"] += 1
        status = "schema_error" if errors else ("evidence_error" if bad else "ok")
        totals[status] += 1
        if any(r["status"] == "relocated" for r in ev_results):
            totals["relocated"] += 1
        results[key] = {
            "file": f["_file"], "line": f["_line"], "certainty": f.get("certainty"), "impact": f.get("impact"),
            "status": status, "errors": errors, "warnings": warnings, "evidence": ev_results,
        }
    report = {"generated_at": C.now_iso(), "totals": totals, "files": files, "duplicates": duplicates, "findings": results}
    C.write_json(workspace / "verification" / "mechanical.json", report)
    C.write_text(workspace / "verification" / "mechanical.md", to_markdown(report))
    return report


def to_markdown(r: dict) -> str:
    t = r["totals"]
    lines = ["# Mechanical evidence check", "",
             f"{t['findings']} findings: {t['ok']} ok, {t['evidence_error']} with evidence errors, "
             f"{t['schema_error']} with schema errors, {t['relocated']} with relocated quotes, "
             f"{t.get('wrong_language', 0)} not in the report language.", ""]
    rows = []
    for rel, rep in r["files"].items():
        per = [v for v in r["findings"].values() if v["file"] == rel]
        rows.append([f"`{rel}`", rep["findings"], sum(v["status"] == "ok" for v in per),
                     sum(v["status"] != "ok" for v in per), len(rep["parse_errors"])])
    lines += [C.md_table(["File", "Findings", "OK", "Problems", "Unparseable lines"], rows)]
    if r["duplicates"]:
        lines += ["", "## Duplicate IDs"] + [f"- {d}" for d in r["duplicates"]]
    parse = [(rel, e) for rel, rep in r["files"].items() for e in rep["parse_errors"]]
    if parse:
        lines += ["", "## Unparseable lines"] + [f"- `{rel}` {e}" for rel, e in parse[:40]]
    problems = [(fid, v) for fid, v in r["findings"].items() if v["status"] != "ok"]
    if problems:
        lines += ["", "## Findings with problems"]
        for fid, v in problems[:120]:
            detail = "; ".join(v["errors"][:2] + [f"evidence {e['index']}: {e['status']} ({e['detail']})"
                                                   for e in v["evidence"] if e["status"] not in ("ok", "no_quote", "unchecked", "relocated")][:2])
            lines.append(f"- **{fid}** ({v['certainty']}, {v['impact']}) {v['status']}: {detail}")
    return "\n".join(lines)
