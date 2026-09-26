"""Report source (a Markdown subset plus component blocks) → language lint and a
self-contained HTML page. The component syntax is documented in REPORT-FORMAT.md."""
from __future__ import annotations

import html
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from . import common as C

ASSETS = Path(__file__).resolve().parents[2] / "assets"
DIRECTIVES = {"lead", "stats", "card", "risk", "callout", "flow", "compare", "timeline", "details", "diagram"}
TONES = {"risk", "warn", "ok", "info", "neutral"}
SEVERITY_TONE = {"alta": "risk", "alto": "risk", "high": "risk", "média": "warn", "media": "warn", "médio": "warn",
                 "medio": "warn", "medium": "warn", "baixa": "ok", "baixo": "ok", "low": "ok"}
LENS_LABELS = {"recon": "Reconhecimento", "domain": "Domínio", "data": "Dados", "integrations": "Integrações",
               "structure": "Estrutura", "infra": "Infraestrutura", "evolution": "Evolução", "runtime": "Execução",
               "flows": "Fluxos", "risk": "Riscos", "synthesis": "Síntese"}
CERT_LABELS = {"fact": "fato", "inference": "inferência", "hypothesis": "hipótese", "unknown": "desconhecido"}
AUDIENCE_LABELS = {"dev": "Dev entrando no projeto", "lead": "Tech lead / arquiteto", "non-technical": "Leitor não técnico"}

ID_RX = r"[A-Z]{1,3}\d{0,2}-\d{3}"
INLINE_CODE = re.compile(r"`([^`\n]+)`")
TERM_RX = re.compile(r"\[\[([^\]|\n]+?)(?:\|([^\]\n]+))?\]\]")
EVID_RX = re.compile(r"\^\[\s*(" + ID_RX + r"(?:[\s,;]+" + ID_RX + r")*)\s*\]")
LINK_RX = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+|#[^)\s]+)\)")
BOLD_RX = re.compile(r"\*\*(.+?)\*\*")
ITAL_RX = re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])")
CODE_REF_RX = re.compile(r"^(?:([\w.-]+):)?([^\s:]+?)(?::(\d+)(?:-(\d+))?)?$")
DIRECTIVE_OPEN = re.compile(r"^:::\s*([a-z-]+)\s*(.*)$")
ATTR_RX = re.compile(r"""([\w-]+)=(?:"([^"]*)"|'([^']*)'|(\S+))""")

# Words that belong to the analysis method or to academic jargon, never to the report.
FORBIDDEN = [
    (r"\bfindings?\b", "Descreva o fato; a evidência vai no marcador ^[...]."),
    (r"\blentes?\b", "Não mencione o método de análise."),
    (r"\bonda [AB]\b|\bwaves?\b", "Não mencione o método de análise."),
    (r"\breflexion\b", "Diga 'a documentação diz X, o código faz Y'."),
    (r"\bdigest\b", "Não mencione o método de análise."),
    (r"\brecon\b", "Não mencione o método de análise."),
    (r"\bconvergências?\b", "Diga 'a documentação e o código concordam'."),
    (r"\bn[ãa]o[- ]riscos?\b|\bnon-risks?\b", "Diga 'o que está bem resolvido'."),
    (r"\bponto de sensibilidade\b|\bsensitivity points?\b", "Diga qual decisão controla qual comportamento."),
    (r"\butility tree\b|\bárvore de utilidade\b", "Liste os atributos de qualidade em linguagem direta."),
    (r"\bconnascence\b|\bconasc[eê]ncia\b", "Diga 'acoplamento' e explique qual."),
    (r"\bsubdom[ií]nios? (?:gen[ée]rico|de suporte|core)\b|\bcore domain\b",
     "Diga 'a parte central do negócio' ou 'função de apoio'."),
]
LONG_SENTENCE = 40
LONG_PARAGRAPH = 110


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFKD", re.sub(r"<[^>]+>|[`*\[\]^]", "", text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "secao"


def load_glossary() -> tuple[dict, dict]:
    data = json.loads((ASSETS / "glossary.json").read_text(encoding="utf-8"))
    index = {}
    for key, v in data.items():
        index[key.lower()] = key
        for a in v.get("aliases", []):
            index.setdefault(a.lower(), key)
    return data, index


class Ctx:
    def __init__(self, workspace: Path):
        self.ws = workspace
        self.manifest = C.read_json(workspace / "manifest.json")
        self.repos = {r["name"]: Path(r["path"]) for r in self.manifest["repos"]}
        self.glossary, self.gindex = load_glossary()
        digest = workspace / "synthesis" / "digest.json"
        self.findings = C.read_json(digest)["findings"] if digest.exists() else []
        extra = workspace / "synthesis" / "synthesis.findings.jsonl"
        if extra.exists():
            for line in extra.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    f = json.loads(line)
                except ValueError:
                    continue
                if isinstance(f, dict) and f.get("id") and f["id"] not in {x["id"] for x in self.findings}:
                    self.findings.append({**f, "verification": "síntese"})
        self.ids = {f["id"] for f in self.findings}
        self.terms_used: dict[str, str] = {}
        self.audience = self.manifest.get("audience", "dev")

    def resolve(self, repo: str | None, path: str) -> Path | None:
        path = path[2:] if path.startswith("./") else path
        roots = [self.repos[repo]] if repo in self.repos else list(self.repos.values())
        for root in roots:
            p = root / path
            if p.exists():
                return p
        return None


# ---------------------------------------------------------------- inline

def code_html(token: str, ctx: Ctx) -> str:
    m = CODE_REF_RX.match(token.strip())
    if m and ("/" in m.group(2) or "." in m.group(2)):
        repo, path, a, b = m.groups()
        if repo and repo not in ctx.repos:
            path, repo = f"{repo}:{path}", None
        target = ctx.resolve(repo, path)
        if target is not None:
            uri = "vscode://file/" + C.posix(target.resolve()) + (f":{a}" if a else "")
            return f'<a class="code-link" href="{esc(uri)}" title="Abrir no VS Code: {esc(C.posix(target))}"><code>{esc(token)}</code></a>'
    return f"<code>{esc(token)}</code>"


def term_html(term: str, definition: str | None, ctx: Ctx) -> str:
    key = ctx.gindex.get(term.strip().lower())
    d = (definition or "").strip() or (ctx.glossary[key]["def"] if key else "")
    label = key or term.strip()
    if d:
        ctx.terms_used.setdefault(label, d)
        return f'<span class="term" tabindex="0" data-term="{esc(label)}" data-def="{esc(d)}">{esc(term.strip())}</span>'
    return esc(term.strip())


def ev_html(ids_text: str) -> str:
    ids = re.findall(ID_RX, ids_text)
    title = "Evidências: " + ", ".join(ids)
    return f'<sup class="ev"><a href="#ev-{ids[0]}" title="{esc(title)}">{len(ids)}</a></sup>'


def inline(text: str, ctx: Ctx) -> str:
    keep: list[str] = []

    def hold(s: str) -> str:
        keep.append(s)
        return f"\x00{len(keep) - 1}\x00"

    text = INLINE_CODE.sub(lambda m: hold(code_html(m.group(1), ctx)), text)
    text = TERM_RX.sub(lambda m: hold(term_html(m.group(1), m.group(2), ctx)), text)
    text = EVID_RX.sub(lambda m: hold(ev_html(m.group(1))), text)
    text = LINK_RX.sub(lambda m: hold(f'<a href="{esc(m.group(2))}">{esc(m.group(1))}</a>'), text)
    text = esc(text)
    text = BOLD_RX.sub(r"<strong>\1</strong>", text)
    text = ITAL_RX.sub(r"<em>\1</em>", text)
    for _ in range(3):
        text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
    return text


# ---------------------------------------------------------------- blocks

def parse_attrs(s: str) -> dict:
    return {m.group(1): next(g for g in m.groups()[1:] if g is not None) for m in ATTR_RX.finditer(s)}


def parse(lines: list[str], start: int = 0) -> list[dict]:
    """Parse lines into block nodes. Each node keeps its first source line number."""
    nodes: list[dict] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        ln = start + i + 1
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        m = DIRECTIVE_OPEN.match(stripped)
        if m and stripped != ":::":
            depth, j = 1, i + 1
            while j < n:
                s = lines[j].strip()
                if s == ":::":
                    depth -= 1
                    if depth == 0:
                        break
                elif DIRECTIVE_OPEN.match(s):
                    depth += 1
                j += 1
            nodes.append({"t": "directive", "name": m.group(1), "attrs": parse_attrs(m.group(2)),
                          "body": lines[i + 1:j], "body_start": start + i + 1, "line": ln, "closed": j < n})
            i = j + 1
            continue
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            j = i + 1
            while j < n and not lines[j].strip().startswith("```"):
                j += 1
            nodes.append({"t": "code", "lang": lang, "text": "\n".join(lines[i + 1:j]), "line": ln})
            i = j + 1
            continue
        hm = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if hm:
            nodes.append({"t": "heading", "level": len(hm.group(1)), "text": hm.group(2).strip(), "line": ln})
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            nodes.append({"t": "hr", "line": ln})
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            rows = []
            j = i + 2
            while j < n and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            nodes.append({"t": "table", "head": split_row(line), "rows": rows, "line": ln})
            i = j
            continue
        if stripped.startswith(">"):
            j = i
            quote = []
            while j < n and lines[j].strip().startswith(">"):
                quote.append(lines[j].strip()[1:].strip())
                j += 1
            nodes.append({"t": "quote", "text": " ".join(quote), "line": ln})
            i = j
            continue
        lm = re.match(r"^(\s*)([-*]|\d+[.)])\s+(.*)$", line)
        if lm and len(lm.group(1)) == 0:
            ordered = lm.group(2)[0].isdigit()
            items: list[dict] = []
            j = i
            while j < n:
                cur = lines[j]
                im = re.match(r"^(\s*)([-*]|\d+[.)])\s+(.*)$", cur)
                if im and len(im.group(1)) == 0:
                    items.append({"text": im.group(3).strip(), "children": [], "line": start + j + 1})
                elif im and items:
                    items[-1]["children"].append(im.group(3).strip())
                elif cur.strip() and cur.startswith((" ", "\t")) and items:
                    if items[-1]["children"]:
                        items[-1]["children"][-1] += " " + cur.strip()
                    else:
                        items[-1]["text"] += " " + cur.strip()
                else:
                    break
                j += 1
            nodes.append({"t": "list", "ordered": ordered, "items": items, "line": ln})
            i = j
            continue
        j = i
        para = []
        while j < n and lines[j].strip() and not (DIRECTIVE_OPEN.match(lines[j].strip())
                                                  or lines[j].strip().startswith(("```", "#", "|", ">"))
                                                  or re.match(r"^([-*]|\d+[.)])\s+", lines[j])):
            para.append(lines[j].strip())
            j += 1
        if not para:
            para, j = [stripped], i + 1
        nodes.append({"t": "para", "text": " ".join(para), "line": ln})
        i = j
    return nodes


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def pipe_items(body: list[str]) -> list[tuple[str, str]]:
    out = []
    for line in body:
        m = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$", line)
        if not m:
            continue
        parts = re.split(r"\s+\|\s+", m.group(1), maxsplit=1)
        out.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""))
    return out


def render_nodes(nodes: list[dict], ctx: Ctx, toc: list | None = None) -> str:
    out: list[str] = []
    cards: list[str] = []

    def flush() -> None:
        if cards:
            out.append('<div class="grid">' + "".join(cards) + "</div>")
            cards.clear()

    for node in nodes:
        t = node["t"]
        if t == "directive" and node["name"] == "card":
            cards.append(render_directive(node, ctx))
            continue
        flush()
        if t == "heading":
            if node["level"] == 1:
                continue
            hid = slugify(node["text"])
            if toc is not None and node["level"] in (2, 3):
                toc.append((node["level"], hid, inline(node["text"], ctx)))
            out.append(f'<h{node["level"]} id="{hid}">{inline(node["text"], ctx)}</h{node["level"]}>')
        elif t == "para":
            out.append(f"<p>{inline(node['text'], ctx)}</p>")
        elif t == "list":
            tag = "ol" if node["ordered"] else "ul"
            items = []
            for it in node["items"]:
                sub = "".join(f"<li>{inline(c, ctx)}</li>" for c in it["children"])
                items.append(f"<li>{inline(it['text'], ctx)}" + (f"<ul>{sub}</ul>" if sub else "") + "</li>")
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
        elif t == "table":
            head = "".join(f"<th>{inline(c, ctx)}</th>" for c in node["head"])
            rows = "".join("<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>" for r in node["rows"])
            out.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')
        elif t == "code":
            if node["lang"] == "mermaid":
                out.append(f'<div class="diagram"><pre class="mermaid">{esc(node["text"])}</pre></div>')
            else:
                out.append(f"<pre><code>{esc(node['text'])}</code></pre>")
        elif t == "quote":
            out.append(f"<blockquote>{inline(node['text'], ctx)}</blockquote>")
        elif t == "hr":
            out.append("<hr>")
        elif t == "directive":
            out.append(render_directive(node, ctx))
    flush()
    return "\n".join(out)


def render_directive(node: dict, ctx: Ctx) -> str:
    name, a, body = node["name"], node["attrs"], node["body"]
    title = a.get("title", "")
    inner = lambda: render_nodes(parse(body, node["body_start"]), ctx)
    tone = a.get("tone", "neutral") if a.get("tone", "neutral") in TONES else "neutral"
    if name == "lead":
        return f'<div class="lead">{inner()}</div>'
    if name == "stats":
        tiles = "".join(f'<div class="stat"><div class="value">{inline(v, ctx)}</div><div class="label">{inline(l, ctx)}</div></div>'
                        for v, l in pipe_items(body))
        return f'<div class="stats">{tiles}</div>'
    if name == "card":
        head = f"<h4>{inline(title, ctx)}</h4>" if title else ""
        return f'<div class="card tone-{tone}">{head}{inner()}</div>'
    if name == "risk":
        sev = a.get("severity", "").strip()
        tone = SEVERITY_TONE.get(sev.lower(), "warn")
        badges = f'<span class="badge sev-{slugify(sev)}">impacto {esc(sev)}</span>' if sev else ""
        if a.get("likelihood"):
            lk = a["likelihood"]
            badges += f' <span class="badge sev-{slugify(lk)}">probabilidade {esc(lk)}</span>'
        return f'<div class="card tone-{tone} risk"><h4>{inline(title, ctx)} {badges}</h4>{inner()}</div>'
    if name == "callout":
        head = f'<div class="callout-title">{inline(title, ctx)}</div>' if title else ""
        return f'<div class="callout tone-{tone}">{head}{inner()}</div>'
    if name == "flow":
        steps = "".join(f'<li><span class="step-title">{inline(s, ctx)}</span><span class="step-desc">{inline(d, ctx)}</span></li>'
                        for s, d in pipe_items(body))
        head = f'<div class="flow-title">{inline(title, ctx)}</div>' if title else ""
        return f'<div class="flow">{head}<ol>{steps}</ol></div>'
    if name == "compare":
        rows = [f'<div class="compare-row compare-head"><div>{inline(a.get("left", "Antes"), ctx)}</div><div>{inline(a.get("right", "Depois"), ctx)}</div></div>']
        rows += [f'<div class="compare-row"><div>{inline(l, ctx)}</div><div>{inline(r, ctx)}</div></div>' for l, r in pipe_items(body)]
        head = f'<div class="compare-title">{inline(title, ctx)}</div>' if title else ""
        return f'<div class="compare">{head}{"".join(rows)}</div>'
    if name == "timeline":
        items = "".join(f'<li><span class="when">{inline(w, ctx)}</span>{inline(e, ctx)}</li>' for w, e in pipe_items(body))
        return f'<ul class="timeline">{items}</ul>'
    if name == "details":
        return f'<details class="block"><summary>{inline(title or "Detalhes", ctx)}</summary><div class="details-body">{inner()}</div></details>'
    if name == "diagram":
        head = f'<div class="diagram-title">{inline(title, ctx)}</div>' if title else ""
        return f'<div class="diagram">{head}<pre class="mermaid">{esc(chr(10).join(body))}</pre></div>'
    return f'<div class="callout tone-warn"><div class="callout-title">Componente desconhecido: {esc(name)}</div>{inner()}</div>'


# ---------------------------------------------------------------- lint

def _prose(source: str) -> list[tuple[int, str]]:
    """(line number, text) for lines that carry prose: not code, diagrams, tables or directive markers."""
    out = []
    in_code = in_diagram = False
    for n, line in enumerate(source.splitlines(), 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if re.match(r"^:::\s*diagram\b", s):
            in_diagram = True
            continue
        if in_diagram and s == ":::":
            in_diagram = False
            continue
        if in_code or in_diagram or not s or s.startswith(":::") or re.match(r"^\|?\s*:?-{2,}", s):
            continue
        out.append((n, line))
    return out


def lint(source: str, ctx: Ctx) -> list[dict]:
    issues: list[dict] = []

    def add(level, line, rule, msg, excerpt=""):
        issues.append({"level": level, "line": line, "rule": rule, "message": msg, "excerpt": excerpt[:160]})

    nodes = parse(source.splitlines())
    h2 = 0

    def walk(ns):
        nonlocal h2
        for nd in ns:
            if nd["t"] == "heading" and nd["level"] == 2:
                h2 += 1
            if nd["t"] == "directive":
                if nd["name"] not in DIRECTIVES:
                    add("error", nd["line"], "unknown-component", f"Componente '{nd['name']}' não existe (ver REPORT-FORMAT.md).")
                if not nd["closed"]:
                    add("error", nd["line"], "unclosed-component", f"Bloco '::: {nd['name']}' sem ':::' de fechamento.")
                if nd["name"] in ("risk",) and not nd["attrs"].get("severity"):
                    add("warning", nd["line"], "risk-severity", "Bloco risk sem severity.")
                if nd["name"] not in ("diagram",):
                    walk(parse(nd["body"], nd["body_start"]))
    walk(nodes)
    if h2 < 4:
        add("error", 1, "structure", f"Só {h2} seções de nível 2; o formato pede as seções de REPORT-FORMAT.md.")

    explain_all = ctx.audience == "non-technical"
    seen_terms: set[str] = set()
    for n, line in _prose(source):
        bare = INLINE_CODE.sub(" ", line)
        for m in EVID_RX.finditer(bare):
            for fid in re.findall(ID_RX, m.group(1)):
                if ctx.ids and fid not in ctx.ids:
                    add("error", n, "unknown-evidence", f"{fid} não existe entre as evidências da análise.", line)
        no_ev = EVID_RX.sub(" ", bare)
        for fid in re.findall(r"\b" + ID_RX + r"\b", no_ev):
            add("error", n, "bare-id", f"ID {fid} no meio do texto; use o marcador ^[{fid}] no fim da frase ou do bloco.", line)
        for m in TERM_RX.finditer(bare):
            key = ctx.gindex.get(m.group(1).strip().lower())
            if key:
                seen_terms.add(key)
            elif not m.group(2):
                add("error", n, "undefined-term", f"[[{m.group(1)}]] não está no glossário; use [[termo|definição curta]].", line)
        text = TERM_RX.sub(" ", no_ev)
        for rx, hint in FORBIDDEN:
            for m in re.finditer(rx, text, re.I):
                add("error", n, "forbidden-term", f"'{m.group(0)}': {hint}", line)
        low = text.lower()
        for key, v in ctx.glossary.items():
            if key in seen_terms or not (explain_all or v.get("level") == "advanced"):
                continue
            names = [key] + [a for a in v.get("aliases", []) if len(a) >= 6 or " " in a]
            for name in names:
                if re.search(r"(?<![\w-])" + re.escape(name.lower()) + r"(?![\w-])", low):
                    add("warning", n, "unexplained-term",
                        f"Primeiro uso de '{name}' sem explicação; escreva [[{name}]] para ganhar o tooltip.", line)
                    seen_terms.add(key)
                    break
        for m in INLINE_CODE.finditer(line):
            tok = m.group(1).strip()
            cm = CODE_REF_RX.match(tok)
            if cm and "/" in cm.group(2) and re.search(r"\.\w{1,5}$", cm.group(2)):
                repo = cm.group(1) if cm.group(1) in ctx.repos else None
                path = cm.group(2) if repo or not cm.group(1) else f"{cm.group(1)}:{cm.group(2)}"
                if ctx.resolve(repo, path) is None:
                    add("warning", n, "missing-file", f"`{tok}` não foi encontrado no repositório; o link não será criado.", line)

    for node in nodes_with_prose(nodes):
        words = len(re.sub(r"`[^`]*`|\^\[[^\]]*\]", " ", node["text"]).split())
        if words > LONG_PARAGRAPH:
            add("warning", node["line"], "long-paragraph", f"Parágrafo com {words} palavras; divida ou use componentes.", node["text"])
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ`*\[])", node["text"]):
            wc = len(re.sub(r"`[^`]*`|\^\[[^\]]*\]", " ", sent).split())
            if wc > LONG_SENTENCE:
                add("warning", node["line"], "long-sentence", f"Frase com {wc} palavras; o limite é {LONG_SENTENCE}.", sent)
    issues.sort(key=lambda x: (x["level"] != "error", x["line"]))
    return issues


def nodes_with_prose(nodes: list[dict]):
    for nd in nodes:
        if nd["t"] == "para":
            yield nd
        elif nd["t"] == "list":
            for it in nd["items"]:
                yield {"text": it["text"], "line": it["line"]}
        elif nd["t"] == "directive" and nd["name"] not in ("diagram", "stats", "flow", "compare", "timeline"):
            yield from nodes_with_prose(parse(nd["body"], nd["body_start"]))


def lint_markdown(issues: list[dict], source_name: str) -> str:
    errors = [i for i in issues if i["level"] == "error"]
    warns = [i for i in issues if i["level"] == "warning"]
    lines = [f"# Revisão de linguagem: {source_name}", "", f"{len(errors)} erros, {len(warns)} avisos.", ""]
    for title, group in (("Erros (corrigir todos)", errors), ("Avisos (corrigir quando fizer sentido)", warns)):
        if group:
            lines.append(f"## {title}")
            for i in group:
                ex = f" — «{i['excerpt'].strip()}»" if i["excerpt"] else ""
                lines.append(f"- linha {i['line']} · `{i['rule']}` · {i['message']}{ex}")
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- page

def appendix_html(ctx: Ctx) -> str:
    if not ctx.findings:
        return ""
    groups: dict[str, list[dict]] = {}
    for f in ctx.findings:
        groups.setdefault(f.get("lens") or "outros", []).append(f)
    parts = ['<h2 id="evidencias">Evidências</h2>',
             '<p class="note">Cada marcador numerado no texto leva a uma evidência abaixo. As afirmações ficam no idioma '
             'interno da análise, com o grau de certeza e o trecho de código que as sustenta.</p>',
             '<div class="appendix">']
    for lens in sorted(groups, key=lambda l: list(LENS_LABELS).index(l) if l in LENS_LABELS else 99):
        items = []
        for f in sorted(groups[lens], key=lambda x: x["id"]):
            cert = f.get("certainty", "")
            evs = []
            for e in f.get("evidence") or []:
                if isinstance(e, dict) and e.get("path"):
                    ref = f"{e['path']}:{e['lines']}" if e.get("lines") else e["path"]
                    if e.get("repo") and len(ctx.repos) > 1:
                        ref = f"{e['repo']}:{ref}"
                    evs.append(code_html(ref, ctx))
                elif isinstance(e, dict) and e.get("commit"):
                    evs.append(f"<code>commit {esc(str(e['commit'])[:10])}</code>")
                elif isinstance(e, dict) and e.get("search"):
                    evs.append(f"busca: <code>{esc(str(e['search'])[:80])}</code>")
            extra = f.get("why_unknown") or f.get("how_to_verify") or ""
            items.append(
                f'<div class="finding" id="ev-{esc(f["id"])}"><span class="fid">{esc(f["id"])}</span>'
                f'<span class="badge cert-{esc(cert)}">{esc(CERT_LABELS.get(cert, cert))}</span> {esc(f.get("claim", ""))}'
                + (f'<div class="evs">{" · ".join(evs)}</div>' if evs else "")
                + (f'<div class="evs">{esc(extra)}</div>' if extra and not evs else "") + "</div>")
        parts.append(f'<details class="block"><summary>{esc(LENS_LABELS.get(lens, lens))} ({len(items)})</summary>'
                     f'<div class="details-body">{"".join(items)}</div></details>')
    parts.append("</div>")
    return "\n".join(parts)


def glossary_html(ctx: Ctx) -> str:
    if not ctx.terms_used:
        return ""
    rows = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in sorted(ctx.terms_used.items(), key=lambda kv: kv[0].lower()))
    return f'<h2 id="termos">Termos usados</h2><div class="glossary"><dl>{rows}</dl></div>'


def build(workspace: str | Path, source: str | Path | None = None) -> dict:
    ws = Path(workspace).resolve()
    ctx = Ctx(ws)
    src_path = Path(source) if source else ws / "synthesis" / "report.md"
    if not src_path.is_absolute():
        src_path = ws / src_path
    text = src_path.read_text(encoding="utf-8")
    issues = lint(text, ctx)
    C.write_json(ws / "synthesis" / "lint.json", {"source": C.posix(src_path), "issues": issues})
    C.write_text(ws / "synthesis" / "lint.md", lint_markdown(issues, src_path.name))

    ctx.terms_used = {}
    nodes = parse(text.splitlines())
    title = next((n["text"] for n in nodes if n["t"] == "heading" and n["level"] == 1), ws.name)
    toc: list = []
    body = render_nodes(nodes, ctx, toc)
    body += "\n" + glossary_html(ctx)
    if ctx.terms_used:
        toc.append((2, "termos", "Termos usados"))
    app = appendix_html(ctx)
    if app:
        body += "\n" + app
        toc.append((2, "evidencias", "Evidências"))

    toc_html = ['<nav class="toc"><div class="toc-title">Nesta página</div><ol>']
    open_sub = False
    for level, hid, label in toc:
        if level == 2:
            if open_sub:
                toc_html.append("</ol></li>")
                open_sub = False
            toc_html.append(f'<li><a href="#{hid}">{label}</a>')
            toc_html.append("<ol>")
            open_sub = True
        else:
            toc_html.append(f'<li><a href="#{hid}">{label}</a></li>')
    if open_sub:
        toc_html.append("</ol></li>")
    toc_html.append("</ol></nav>")
    toc_str = "".join(toc_html).replace("<ol></ol>", "")

    m = ctx.manifest
    by_cert: dict[str, int] = {}
    for f in ctx.findings:
        by_cert[f.get("certainty", "")] = by_cert.get(f.get("certainty", ""), 0) + 1
    meta = [f"<span>{esc(', '.join(ctx.repos))}</span>", f"<span>{date.today().isoformat()}</span>",
            f"<span>Leitor: {esc(AUDIENCE_LABELS.get(ctx.audience, ctx.audience))}</span>"]
    if ctx.findings:
        meta.append(f"<span>{len(ctx.findings)} evidências verificadas</span>")
    page = f"""<!doctype html>
<html lang="{esc(m.get('report_language', 'pt-BR'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(re.sub(r'[`*]', '', title))}</title>
<style>{(ASSETS / 'report.css').read_text(encoding='utf-8')}</style>
</head>
<body>
<div class="layout">
{toc_str}
<main>
<header class="report-header"><div class="eyebrow">Análise de sistema</div><h1>{inline(title, ctx)}</h1>
<div class="meta">{''.join(meta)}</div></header>
{body}
<footer class="report-footer">Execução {esc(m.get('run_id', ''))}. Links de código abrem o arquivo no VS Code.</footer>
</main>
</div>
<script>{(ASSETS / 'report.js').read_text(encoding='utf-8')}</script>
</body>
</html>
"""
    out = ws / "report.html"
    C.write_text(out, page)
    errors = sum(1 for i in issues if i["level"] == "error")
    return {"html": C.posix(out), "errors": errors, "warnings": len(issues) - errors, "terms": len(ctx.terms_used)}


def lint_only(workspace: str | Path, source: str | Path | None = None) -> dict:
    ws = Path(workspace).resolve()
    ctx = Ctx(ws)
    src_path = Path(source) if source else ws / "synthesis" / "report.md"
    if not src_path.is_absolute():
        src_path = ws / src_path
    issues = lint(src_path.read_text(encoding="utf-8"), ctx)
    C.write_json(ws / "synthesis" / "lint.json", {"source": C.posix(src_path), "issues": issues})
    C.write_text(ws / "synthesis" / "lint.md", lint_markdown(issues, src_path.name))
    errors = sum(1 for i in issues if i["level"] == "error")
    return {"errors": errors, "warnings": len(issues) - errors, "report": "synthesis/lint.md"}
