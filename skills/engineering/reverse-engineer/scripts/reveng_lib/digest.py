"""Merge findings with mechanical results and verifier verdicts into a compact digest,
the synthesizer's main input."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from . import common as C
from .evidence import load_findings

LENS_ORDER = ["recon", "domain", "data", "integrations", "structure", "infra", "evolution", "runtime", "flows",
              "risk", "synthesis"]
CERT_ORDER = {"fact": 0, "inference": 1, "hypothesis": 2, "unknown": 3}
IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}
DOWNGRADE = {"fact": "inference", "inference": "hypothesis", "hypothesis": "hypothesis", "unknown": "unknown"}


def _ev_label(e: dict) -> str:
    if not isinstance(e, dict):
        return "?"
    if "path" in e:
        lines = f":{e['lines']}" if e.get("lines") is not None else ""
        repo = f"{e['repo']}:" if e.get("repo") else ""
        return f"{repo}{e['path']}{lines}"
    if "commit" in e:
        return f"{e.get('repo', '')}@{str(e['commit'])[:10]}"
    if "artifact" in e:
        return f"artifact {e['artifact']}"
    if "search" in e:
        return f"search: {str(e['search'])[:60]}"
    return "?"


def build(workspace: str | Path) -> dict:
    workspace = Path(workspace).resolve()
    findings, _ = load_findings(workspace)
    mech_path = workspace / "verification" / "mechanical.json"
    mech = C.read_json(mech_path)["findings"] if mech_path.exists() else {}
    verdicts: dict[str, dict] = {}
    for path in sorted(workspace.glob("verification/*.verdicts.jsonl")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    v = json.loads(line)
                except ValueError:
                    continue
                if isinstance(v, dict) and v.get("id"):
                    verdicts[v["id"]] = v

    effective, refuted = [], []
    stats: Counter = Counter()
    seen: set[str] = set()
    for f in findings:
        fid = f.get("id")
        if not fid:
            continue
        if fid in seen:
            stats["duplicate-dropped"] += 1
            continue
        seen.add(fid)
        cert = f.get("certainty")
        note = None
        v = verdicts.get(fid)
        m = mech.get(fid, {})
        evidence = f.get("evidence") or []
        if v:
            verdict = v.get("verdict")
            status = verdict
            stats[verdict] += 1
            if verdict == "refuted":
                refuted.append({"id": fid, "claim": f.get("claim"), "reason": v.get("reason")})
                continue
            if verdict == "downgraded":
                cert = v.get("certainty") or DOWNGRADE.get(cert, cert)
                note = v.get("reason")
            elif verdict == "relocated" and isinstance(v.get("evidence"), list):
                evidence = v["evidence"]
            elif verdict == "unverifiable":
                cert = "hypothesis" if cert in ("fact", "inference") else cert
                note = v.get("reason")
        elif m.get("status") in ("evidence_error", "schema_error") and cert in ("fact", "inference"):
            cert = "hypothesis"
            note = "evidence failed the mechanical check"
            status = "auto-downgraded"
            stats["auto-downgraded"] += 1
        else:
            status = "unreviewed" if cert in ("fact", "inference") else "not-applicable"
            stats[status] += 1
            # Apply line corrections the mechanical check found.
            moved = {r["index"]: r["relocated_lines"] for r in m.get("evidence", []) if r.get("relocated_lines")}
            if moved:
                evidence = [dict(e, lines=moved[i]) if i in moved and isinstance(e, dict) else e
                            for i, e in enumerate(evidence)]
        effective.append({
            "id": fid, "lens": f.get("lens"), "kind": f.get("kind"), "certainty": cert,
            "original_certainty": f.get("certainty"), "impact": f.get("impact"), "claim": f.get("claim"),
            "evidence": evidence, "based_on": f.get("based_on") or [], "reasoning": f.get("reasoning"),
            "how_to_verify": f.get("how_to_verify"), "why_unknown": f.get("why_unknown"),
            "scope": f.get("scope"), "verification": status, "note": note, "source": f["_file"],
        })

    effective.sort(key=lambda x: (LENS_ORDER.index(x["lens"]) if x["lens"] in LENS_ORDER else 99, x["kind"] or "",
                                  IMPACT_ORDER.get(x["impact"], 3), CERT_ORDER.get(x["certainty"], 4), x["id"]))
    by_cert = Counter(x["certainty"] for x in effective)
    data = {"generated_at": C.now_iso(), "totals": {"findings": len(effective), "refuted": len(refuted),
                                                    "by_certainty": dict(by_cert), "verification": dict(stats)},
            "findings": effective, "refuted": refuted}
    C.write_json(workspace / "synthesis" / "digest.json", data)
    C.write_text(workspace / "synthesis" / "digest.md", to_markdown(data))
    return data


def _short(text, n=300) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def to_markdown(d: dict) -> str:
    t = d["totals"]
    bc = t["by_certainty"]
    lines = ["# Findings digest", "",
             f"{t['findings']} findings kept ({bc.get('fact', 0)} facts, {bc.get('inference', 0)} inferences, "
             f"{bc.get('hypothesis', 0)} hypotheses, {bc.get('unknown', 0)} unknowns); {t['refuted']} refuted and dropped.",
             "Verification: " + ", ".join(f"{k} {v}" for k, v in sorted(t["verification"].items())), "",
             "Format: `[ID] certainty·impact · claim — support`. Cite IDs exactly as written.", ""]
    groups: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for f in d["findings"]:
        groups[f["lens"] or "?"][f["kind"] or "?"].append(f)
    for lens in sorted(groups, key=lambda l: LENS_ORDER.index(l) if l in LENS_ORDER else 99):
        lines.append(f"## {lens}")
        for kind, items in groups[lens].items():
            lines.append(f"### {kind}")
            for f in items:
                ev = f["evidence"]
                if f["certainty"] == "unknown" and f["why_unknown"]:
                    support = f"why: {_short(f['why_unknown'], 160)}"
                elif f["certainty"] == "hypothesis" and f["how_to_verify"]:
                    support = f"verify: {_short(f['how_to_verify'], 160)}"
                elif f["certainty"] == "inference" and f["based_on"]:
                    support = f"from {', '.join(f['based_on'][:5])}"
                elif ev:
                    support = _ev_label(ev[0]) + (f" (+{len(ev) - 1})" if len(ev) > 1 else "")
                elif f["reasoning"]:
                    support = f"reasoning: {_short(f['reasoning'], 160)}"
                else:
                    support = "no support recorded"
                flag = ""
                if f["original_certainty"] != f["certainty"]:
                    flag = f" [was {f['original_certainty']}: {_short(f['note'], 80)}]"
                lines.append(f"- [{f['id']}] {f['certainty']}·{f['impact']} · {_short(f['claim'])} — {support}{flag}")
        lines.append("")
    if d["refuted"]:
        lines += ["## Refuted (dropped; do not reuse)"]
        lines += [f"- [{r['id']}] {_short(r['claim'], 160)} — {_short(r['reason'], 160)}" for r in d["refuted"]]
    return "\n".join(lines)
