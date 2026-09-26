"""Integration signals per repository (exposed routes, outbound hosts, endpoint env vars,
messaging names, contracts, compose and Kubernetes descriptors) and candidate
cross-repository edges. Everything here is a lead for the integrations lens, not a fact."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from . import common as C

JS_FILES = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts")
ROUTE_PATTERNS = [
    ("express", JS_FILES, re.compile(r"""\b(?:app|router|server|api|routes?)\.(get|post|put|patch|delete|all)\(\s*['"`](/[^'"`]*)['"`]""")),
    ("nestjs", JS_FILES, re.compile(r"""@(Get|Post|Put|Patch|Delete|All)\(\s*(?:['"`]([^'"`]*)['"`])?\s*\)""")),
    ("spring", (".java", ".kt", ".kts", ".groovy", ".scala"),
     re.compile(r"""@(Get|Post|Put|Patch|Delete|Request)Mapping\(\s*(?:(?:value|path)\s*=\s*)?\{?\s*"([^"]*)\"""")),
    ("python-decorator", (".py",), re.compile(r"""@\w+\.(get|post|put|patch|delete|route|api_route|websocket)\(\s*['"]([^'"]+)['"]""")),
    ("django", (".py",), re.compile(r"""\b(?:re_)?path\(\s*r?['"]([^'"]*)['"]\s*,""")),
    ("aspnet-attribute", (".cs",), re.compile(r"""\[(Http(?:Get|Post|Put|Patch|Delete)|Route)\(\s*"([^"]*)"\s*\)\]""")),
    ("aspnet-minimal", (".cs",), re.compile(r"""\.Map(Get|Post|Put|Patch|Delete)\(\s*"([^"]+)\"""")),
    ("go-http", (".go",), re.compile(r"""\bHandleFunc\(\s*"([^"]+)\"""")),
    ("go-router", (".go",), re.compile(r"""\b\w+\.(GET|POST|PUT|PATCH|DELETE|Get|Post|Put|Patch|Delete)\(\s*"(/[^"]*)\"""")),
    ("rails", (".rb",), re.compile(r"""^\s*(get|post|put|patch|delete)\s+['"](/?[^'"]+)['"]""", re.M)),
]
NEST_CONTROLLER = re.compile(r"""@Controller\(\s*(?:['"`]([^'"`]*)['"`])?""")

MESSAGING_PATTERNS = [
    ("kafka", "consume", re.compile(r"""@KafkaListener\([^)]*?topics\s*=\s*\{?\s*"([^"]+)\"""")),
    ("kafka", "produce", re.compile(r"""[kK]afkaTemplate\.send\(\s*"([^"]+)\"""")),
    ("kafka", "produce", re.compile(r"""[pP]roducer\.send\(\s*\{\s*topic\s*:\s*['"`]([^'"`]+)['"`]""")),
    ("kafka", "produce", re.compile(r"""[pP]roducer\.(?:send|produce)\(\s*['"]([\w.\-]+)['"]""")),
    ("kafka", "consume", re.compile(r"""[cC]onsumer\.subscribe\(\s*\{\s*topics?\s*:\s*\[?\s*['"`]([^'"`]+)['"`]""")),
    ("kafka", "consume", re.compile(r"""KafkaConsumer\(\s*['"]([\w.\-]+)['"]""")),
    ("kafka", "unknown", re.compile(r"""\btopics?\s*[:=]\s*\[?\s*['"]([A-Za-z0-9][\w.\-]{2,})['"]""")),
    ("rabbitmq", "consume", re.compile(r"""@RabbitListener\([^)]*?queues\s*=\s*\{?\s*"([^"]+)\"""")),
    ("rabbitmq", "declare", re.compile(r"""queue_declare\([^)]*?queue\s*=\s*['"]([^'"]+)['"]""")),
    ("rabbitmq", "unknown", re.compile(r"""\b(?:exchange|routing_?[kK]ey|queue(?:Name)?)\s*[:=]\s*['"]([A-Za-z0-9][\w.\-:]{2,})['"]""")),
    ("sqs", "unknown", re.compile(r"""sqs[.\-][\w.\-]*amazonaws\.com/\d+/([\w\-]+)""")),
    ("sqs", "consume", re.compile(r"""@SqsListener\(\s*(?:value\s*=\s*)?\{?\s*"([^"]+)\"""")),
    ("sqs/sns", "declare", re.compile(r"""\b(?:QueueName|TopicName)\s*:\s*['"]?([\w\-]{3,})""")),
    ("sns", "unknown", re.compile(r"""arn:aws:sns:[\w\-]+:\d+:([\w\-]+)""")),
    ("pubsub", "unknown", re.compile(r"""projects/[\w\-]+/(?:topics|subscriptions)/([\w.\-]+)""")),
    ("nats", "unknown", re.compile(r"""\b(?:nc|nats|conn|js)\.(?:[Ss]ubscribe|[Pp]ublish|QueueSubscribe)\(\s*['"]([\w.>*\-]+)['"]""")),
    ("nestjs-microservices", "consume", re.compile(r"""@(?:EventPattern|MessagePattern)\(\s*['"]([^'"]+)['"]""")),
    ("eventbridge", "unknown", re.compile(r"""\bDetailType['"]?\s*[:=]\s*['"]([^'"]+)['"]""")),
]

URL_RX = re.compile(r"""https?://([A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)*)(?::(\d{2,5}))?""")
ENV_ENDPOINT_RX = re.compile(
    r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:URL|URI|HOST|HOSTNAME|ENDPOINT|ADDR|ADDRESS|DSN|BROKERS?|BOOTSTRAP_SERVERS|QUEUE|QUEUE_URL|QUEUE_NAME|TOPIC|TOPIC_ARN|TOPIC_NAME|EXCHANGE|BUCKET))\b")
PATH_LITERAL_RX = re.compile(r"""['"`](/(?:api|v\d+|internal|public|rest)(?:/[\w{}:.\-$]+)+)/?['"`]""")
IGNORED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "example.com", "example.org", "example.net", "www.example.com",
    "www.w3.org", "w3.org", "json-schema.org", "schemas.xmlsoap.org", "www.apache.org", "apache.org",
    "opensource.org", "github.com", "raw.githubusercontent.com", "registry.npmjs.org", "www.npmjs.com",
    "maven.apache.org", "schemas.microsoft.com", "purl.org", "fonts.googleapis.com", "fonts.gstatic.com",
    "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com", "developer.mozilla.org", "stackoverflow.com",
    "semver.org", "keepachangelog.com", "yaml.org", "www.gnu.org", "spdx.org", "img.shields.io",
    "docs.github.com", "swagger.io", "spec.openapis.org", "tools.ietf.org", "datatracker.ietf.org",
    "www.rfc-editor.org", "en.wikipedia.org", "www.youtube.com", "aka.ms", "go.microsoft.com",
    "learn.microsoft.com", "docs.microsoft.com", "docs.aws.amazon.com", "pkg.go.dev", "golang.org",
    "pypi.org", "docs.python.org", "nodejs.org", "react.dev", "www.typescriptlang.org", "jestjs.io",
    "xmlns.jcp.org", "java.sun.com", "www.springframework.org", "json.schemastore.org", "schema.org",
}
LOCAL_HOST_RX = re.compile(r"^(localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|host\.docker\.internal|\[::1\])$")
INTERNAL_SUFFIXES = (".svc", ".svc.cluster.local", ".cluster.local", ".internal", ".local", ".consul", ".lan", ".corp")
GENERIC_TOKENS = {"service", "services", "svc", "api", "app", "server", "backend", "srv", "ms", "microservice",
                  "http", "https", "url", "uri", "host", "hostname", "endpoint", "base", "addr", "address", "grpc",
                  "internal", "public", "rest", "v1", "v2", "the", "prod", "dev", "staging", "local"}


# ---------------------------------------------------------------- mini YAML

def _scalar(raw: str):
    s = raw.strip()
    if " #" in s and not s.startswith(("'", '"')):
        s = s.split(" #", 1)[0].rstrip()
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(x) for x in s[1:-1].split(",") if x.strip()]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1]
    return s


def mini_yaml(text: str) -> list:
    """Parse the block-style YAML subset used by compose files and Kubernetes manifests.

    Supports mappings, sequences (including sequences of mappings), plain and quoted
    scalars and shallow flow lists. Multiline scalars are skipped. Returns one object per
    YAML document; unparseable documents yield None.
    """
    docs = []
    for doc in re.split(r"^---[^\n]*$", text, flags=re.M):
        lines = []
        for ln in doc.splitlines():
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            lines.append((len(ln) - len(ln.lstrip(" ")), ln.strip()))
        try:
            node, _ = _parse(lines, 0, lines[0][0]) if lines else (None, 0)
        except (IndexError, ValueError, RecursionError):
            node = None
        docs.append(node)
    return docs


_KEY_RX = re.compile(r"""^("[^"]*"|'[^']*'|[^\s:'"#][^:#]*?)\s*:(?:\s+(.*))?$""")


def _parse(lines, i, indent):
    if i >= len(lines):
        return None, i
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        return _parse_seq(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_seq(lines, i, indent):
    out = []
    while i < len(lines) and lines[i][0] == indent and (lines[i][1].startswith("- ") or lines[i][1] == "-"):
        rest = lines[i][1][1:].strip()
        if not rest:
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                node, i = _parse(lines, i + 1, lines[i + 1][0])
            else:
                node, i = None, i + 1
        elif _KEY_RX.match(rest) and not rest.startswith(("'", '"', "[", "{")):
            virtual = indent + 2
            lines = lines[:i] + [(virtual, rest)] + lines[i + 1:]
            node, i = _parse_map(lines, i, virtual)
        else:
            node, i = _scalar(rest), i + 1
        out.append(node)
    return out, i


def _parse_map(lines, i, indent):
    out = {}
    while i < len(lines) and lines[i][0] == indent:
        m = _KEY_RX.match(lines[i][1])
        if not m:
            i += 1
            continue
        key = m.group(1).strip().strip("'\"")
        rest = (m.group(2) or "").strip()
        i += 1
        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            while i < len(lines) and lines[i][0] > indent:
                i += 1
            out[key] = "(multiline)"
        elif rest and not rest.startswith(("&", "!")):
            out[key] = _scalar(rest)
        elif i < len(lines) and (lines[i][0] > indent or (lines[i][0] == indent and lines[i][1].startswith("- "))):
            out[key], i = _parse(lines, i, lines[i][0])
        else:
            out[key] = None
    return out, i


# ---------------------------------------------------------------- helpers

def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def core_name(text: str) -> str:
    toks = [t for t in _tokens(text) if t not in GENERIC_TOKENS]
    return "-".join(toks)


def classify_host(host: str) -> str:
    h = host.lower()
    if LOCAL_HOST_RX.match(h):
        return "local"
    if "." not in h or h.endswith(INTERNAL_SUFFIXES):
        return "internal"
    return "external"


def _norm_path(p: str) -> str:
    p = re.sub(r"\{[^}]*\}|:\w+|\$\{[^}]*\}|<[^>]*>", "{}", p.rstrip("/"))
    return p.lower()


def _env_list(env) -> list[str]:
    if isinstance(env, dict):
        return sorted(env)
    if isinstance(env, list):
        out = []
        for e in env:
            if isinstance(e, str):
                out.append(e.split("=", 1)[0])
            elif isinstance(e, dict) and e.get("name"):
                out.append(str(e["name"]))
        return sorted(out)
    return []


# ---------------------------------------------------------------- per repo

def build_repo(repo_name: str, repo_path: str | Path, inventory: dict) -> dict:
    repo = Path(repo_path).resolve()
    files = C.list_files(repo)
    routes, messaging = [], []
    hosts: dict[str, dict] = {}
    env_vars: dict[str, dict] = {}
    path_literals: dict[str, dict] = {}
    proto_services, proto_packages, openapi, asyncapi_channels = [], [], [], []
    compose, kubernetes = [], []

    sections = inventory.get("sections", {})
    compose_files = {x["path"] for x in sections.get("iac", []) if x["kind"] == "docker-compose"}
    k8s_files = {x["path"] for x in sections.get("iac", []) if x["kind"] in ("kubernetes", "helm")}
    openapi_files = {x["path"] for x in sections.get("contracts", []) if x["kind"] == "openapi"}
    asyncapi_files = {x["path"] for x in sections.get("contracts", []) if x["kind"] == "asyncapi"}

    for rel in files:
        lang = C.language_of(rel)
        cat = C.category_of(lang)
        if cat not in ("code", "config") or C.is_generated(rel) or C.is_test(rel):
            continue
        text = C.read_text(repo / rel)
        if text is None:
            continue
        idx = C.LineIndex(text)

        if cat == "code":
            prefix = ""
            if rel.endswith((".ts", ".js")):
                cm = NEST_CONTROLLER.search(text)
                prefix = ("/" + cm.group(1).strip("/")) if cm and cm.group(1) else ""
            for fw, exts, rx in ROUTE_PATTERNS:
                if not rel.endswith(exts):
                    continue
                for m in rx.finditer(text):
                    if fw in ("django", "go-http"):
                        method, path = "ANY", m.group(1)
                    else:
                        method, path = m.group(1).upper(), m.group(2) or ""
                    if fw == "nestjs":
                        path = prefix + ("/" + path.strip("/") if path else "")
                    if fw == "django" and not path.startswith("/"):
                        path = "/" + path
                    routes.append({"method": method, "path": path or "/", "framework": fw,
                                   "file": rel, "line": idx.line(m.start())})
            for m in PATH_LITERAL_RX.finditer(text):
                p = path_literals.setdefault(m.group(1), {"path": m.group(1), "count": 0, "samples": []})
                p["count"] += 1
                if len(p["samples"]) < 3:
                    p["samples"].append(f"{rel}:{idx.line(m.start())}")

        hits: dict[tuple[str, int], dict] = {}
        for tech, role, rx in MESSAGING_PATTERNS:
            for m in rx.finditer(text):
                key = (m.group(1), idx.line(m.start()))
                # One hit per name and line; a specific role beats "unknown".
                if key not in hits or hits[key]["role"] == "unknown":
                    hits[key] = {"tech": tech, "name": m.group(1), "role": role, "file": rel, "line": key[1]}
        messaging.extend(hits.values())

        for m in URL_RX.finditer(text):
            host = m.group(1).lower()
            if host in IGNORED_HOSTS or host.endswith((".w3.org", ".apache.org")):
                continue
            h = hosts.setdefault(host, {"host": host, "class": classify_host(host), "count": 0, "samples": []})
            h["count"] += 1
            if len(h["samples"]) < 3:
                h["samples"].append(f"{rel}:{idx.line(m.start())}")

        for m in ENV_ENDPOINT_RX.finditer(text):
            e = env_vars.setdefault(m.group(1), {"name": m.group(1), "count": 0, "samples": []})
            e["count"] += 1
            if len(e["samples"]) < 3:
                e["samples"].append(f"{rel}:{idx.line(m.start())}")

        if rel.endswith(".proto"):
            pm = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.M)
            if pm:
                proto_packages.append(pm.group(1))
            for sm in re.finditer(r"^\s*service\s+(\w+)\s*\{", text, re.M):
                rpcs = re.findall(r"rpc\s+(\w+)\s*\(", text[sm.end(): sm.end() + 5000])
                proto_services.append({"service": sm.group(1), "rpcs": rpcs[:30], "file": rel})
        if rel in openapi_files:
            title = re.search(r"""^\s*['"]?title['"]?\s*:\s*['"]?([^'"\n,]+)""", text, re.M)
            paths = re.findall(r"""^\s{2}['"]?(/[^\s'":]*)['"]?\s*:\s*$""", text, re.M)
            openapi.append({"file": rel, "title": title.group(1).strip() if title else None, "paths": paths[:200]})
        if rel in asyncapi_files:
            asyncapi_channels += re.findall(r"""^\s{2}['"]?([\w.\-/{}]+)['"]?\s*:\s*$""", text, re.M)[:100]
        if rel in compose_files:
            for doc in mini_yaml(text):
                if isinstance(doc, dict) and isinstance(doc.get("services"), dict):
                    svcs = []
                    for name, svc in doc["services"].items():
                        svc = svc if isinstance(svc, dict) else {}
                        dep = svc.get("depends_on")
                        svcs.append({"name": name, "image": svc.get("image"),
                                     "build": svc.get("build") if isinstance(svc.get("build"), str) else (svc.get("build") or {}).get("context") if isinstance(svc.get("build"), dict) else None,
                                     "depends_on": sorted(dep) if isinstance(dep, dict) else (dep or []),
                                     "environment": _env_list(svc.get("environment")),
                                     "ports": svc.get("ports") or []})
                    compose.append({"file": rel, "services": svcs})
        if rel in k8s_files:
            for doc in mini_yaml(text):
                if not isinstance(doc, dict) or not doc.get("kind"):
                    continue
                meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
                spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
                item = {"file": rel, "kind": doc.get("kind"), "name": meta.get("name"), "images": [], "env": [],
                        "hosts": [], "backends": []}
                tmpl = spec.get("template") if isinstance(spec.get("template"), dict) else {}
                if doc.get("kind") == "CronJob":
                    item["schedule"] = spec.get("schedule")
                    jt = spec.get("jobTemplate", {}) if isinstance(spec.get("jobTemplate"), dict) else {}
                    tmpl = (jt.get("spec") or {}).get("template", {}) if isinstance(jt.get("spec"), dict) else {}
                pod = tmpl.get("spec") if isinstance(tmpl, dict) and isinstance(tmpl.get("spec"), dict) else {}
                for cont in pod.get("containers", []) or []:
                    if isinstance(cont, dict):
                        if cont.get("image"):
                            item["images"].append(cont["image"])
                        item["env"] += _env_list(cont.get("env"))
                for rule in spec.get("rules", []) or []:
                    if isinstance(rule, dict):
                        if rule.get("host"):
                            item["hosts"].append(rule["host"])
                        http = rule.get("http") if isinstance(rule.get("http"), dict) else {}
                        for p in http.get("paths", []) or []:
                            if isinstance(p, dict):
                                be = p.get("backend") or {}
                                svc = be.get("service") if isinstance(be, dict) else None
                                name = (svc or {}).get("name") if isinstance(svc, dict) else be.get("serviceName") if isinstance(be, dict) else None
                                if name:
                                    item["backends"].append(name)
                kubernetes.append(item)

    identities = sorted({m["name"] for m in inventory.get("manifests", []) if m.get("name")})
    dependencies = sorted({d for m in inventory.get("manifests", []) for d in (m.get("dependencies") or [])})
    return {
        "repo": repo_name,
        "routes": routes[:400],
        "routes_total": len(routes),
        "outbound_hosts": sorted(hosts.values(), key=lambda h: (h["class"], -h["count"])),
        "endpoint_env_vars": sorted(env_vars.values(), key=lambda e: -e["count"]),
        "path_literals": sorted(path_literals.values(), key=lambda p: -p["count"])[:200],
        "messaging": messaging[:400],
        "contracts": {"proto_packages": sorted(set(proto_packages)), "proto_services": proto_services,
                      "openapi": openapi, "asyncapi_channels": sorted(set(asyncapi_channels))},
        "compose": compose,
        "kubernetes": kubernetes,
        "package_identities": identities,
        "dependencies": dependencies,
    }


# ---------------------------------------------------------------- cross repo

def cross_repo(signals: dict[str, dict]) -> list[dict]:
    """Candidate edges between repositories, each with evidence and a confidence label."""
    names = list(signals)
    edges: list[dict] = []
    if len(names) < 2:
        return edges

    identity: dict[str, set[str]] = {}
    for r, s in signals.items():
        toks = {core_name(r)}
        for pid in s["package_identities"]:
            toks.add(core_name(pid.split("/")[-1].split(":")[-1]))
        identity[r] = {t for t in toks if t}
    # Deployment descriptors name services; map each service name to the repo whose identity it matches.
    service_to_repo: dict[str, str] = {}
    for s in signals.values():
        svc_names = [svc["name"] for c in s["compose"] for svc in c["services"]]
        svc_names += [k["name"] for k in s["kubernetes"] if k.get("name") and k.get("kind") in ("Service", "Deployment")]
        for n in svc_names:
            core = core_name(n)
            for r, toks in identity.items():
                if core and core in toks:
                    service_to_repo[core] = r

    def target_for(token: str) -> str | None:
        core = core_name(token)
        if not core:
            return None
        for r, toks in identity.items():
            if core in toks:
                return r
        return service_to_repo.get(core)

    seen = set()

    def add(src, dst, kind, confidence, evidence, via):
        key = (src, dst, kind, via)
        if src == dst or key in seen:
            return
        seen.add(key)
        edges.append({"from": src, "to": dst, "kind": kind, "confidence": confidence, "via": via, "evidence": evidence})

    # 1. Library dependencies on another repo's published package.
    for a, s in signals.items():
        deps = set(s["dependencies"])
        for b, t in signals.items():
            for pid in t["package_identities"]:
                if pid in deps:
                    add(a, b, "library", "strong", [f"{a} depends on {pid}"], pid)
    # 2. Outbound hosts and endpoint env vars naming another repo or its service.
    for a, s in signals.items():
        for h in s["outbound_hosts"]:
            if h["class"] in ("internal", "local"):
                dst = target_for(h["host"].split(".")[0])
                if dst:
                    add(a, dst, "sync-call", "medium", h["samples"], h["host"])
        for e in s["endpoint_env_vars"]:
            base = re.sub(r"_(URL|URI|HOST|HOSTNAME|ENDPOINT|ADDR|ADDRESS|DSN|BASE)+$", "", e["name"])
            dst = target_for(base)
            if dst:
                add(a, dst, "sync-call", "weak", e["samples"], e["name"])
    # 3. Messaging names shared across repos.
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r, s in signals.items():
        for m in s["messaging"]:
            by_name[m["name"].lower()].append({**m, "repo": r})
    for name, uses in by_name.items():
        repos = {u["repo"] for u in uses}
        if len(repos) < 2:
            continue
        roles: dict[str, set[str]] = defaultdict(set)
        for u in uses:
            roles[u["repo"]].add(u["role"])
        ordered = sorted(repos)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                ev = [f"{u['repo']}:{u['file']}:{u['line']} ({u['role']})" for u in uses if u["repo"] in (a, b)][:4]
                if "produce" in roles[a] and "consume" in roles[b]:
                    add(a, b, "async-message", "strong", ev, name)
                if "produce" in roles[b] and "consume" in roles[a]:
                    add(b, a, "async-message", "strong", ev, name)
                known_a = roles[a] - {"unknown", "declare"}
                known_b = roles[b] - {"unknown", "declare"}
                if known_a and known_a == known_b and len(known_a) == 1:
                    continue  # two consumers (or two producers) of the same name do not talk to each other
                if not ("produce" in roles[a] and "consume" in roles[b]) and not ("produce" in roles[b] and "consume" in roles[a]):
                    add(a, b, "async-message (direction unknown)", "medium", ev, name)
    # 4. Shared contracts (same proto package/service or OpenAPI title in several repos).
    contract_keys: dict[str, set[str]] = defaultdict(set)
    for r, s in signals.items():
        for p in s["contracts"]["proto_packages"]:
            contract_keys["proto:" + p].add(r)
        for o in s["contracts"]["openapi"]:
            if o["title"]:
                contract_keys["openapi:" + o["title"].lower()].add(r)
    for key, repos in contract_keys.items():
        rs = sorted(repos)
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                add(a, b, "shared-contract", "medium", [key], key)
    # 5. Path literals in one repo matching routes exposed by another.
    route_index: dict[str, set[str]] = defaultdict(set)
    for r, s in signals.items():
        for rt in s["routes"]:
            route_index[_norm_path(rt["path"])].add(r)
    for a, s in signals.items():
        for p in s["path_literals"]:
            for b in route_index.get(_norm_path(p["path"]), set()):
                add(a, b, "sync-call", "medium", p["samples"], p["path"])
    return edges


def to_markdown(signals: dict[str, dict], edges: list[dict]) -> str:
    lines = ["# Integration signals", "", "Leads for the integrations lens. Each item is a regex hit, not a verified fact.", ""]
    if len(signals) > 1:
        lines += [f"## Candidate cross-repository edges ({len(edges)})",
                  C.md_table(["From", "To", "Kind", "Confidence", "Via", "Evidence"],
                             [[e["from"], e["to"], e["kind"], e["confidence"], f"`{e['via']}`", "; ".join(e["evidence"][:2])]
                              for e in sorted(edges, key=lambda e: (e["confidence"] != "strong", e["confidence"] != "medium"))], 60), ""]
    for r, s in signals.items():
        lines += [f"## {r}", ""]
        by_fw = Counter(rt["framework"] for rt in s["routes"])
        lines.append(f"- Exposed routes: {s['routes_total']} ({', '.join(f'{k} {v}' for k, v in by_fw.items()) or 'none'})")
        for rt in s["routes"][:25]:
            lines.append(f"  - `{rt['method']} {rt['path']}` · `{rt['file']}:{rt['line']}`")
        if s["routes_total"] > 25:
            lines.append(f"  - (+{s['routes_total'] - 25} more in signals.json)")
        ext = [h for h in s["outbound_hosts"] if h["class"] == "external"]
        internal = [h for h in s["outbound_hosts"] if h["class"] != "external"]
        lines.append(f"- Outbound hosts: {len(ext)} external, {len(internal)} internal/local")
        for h in (internal + ext)[:25]:
            lines.append(f"  - `{h['host']}` ({h['class']}, {h['count']}×) · {', '.join(f'`{x}`' for x in h['samples'][:2])}")
        env_names = ", ".join("`" + e["name"] + "`" for e in s["endpoint_env_vars"][:30]) or "none"
        lines.append(f"- Endpoint env vars: {env_names}")
        msg = Counter((m["tech"], m["name"], m["role"]) for m in s["messaging"])
        lines.append(f"- Messaging names: {len(msg)}")
        for (tech, name, role), n in msg.most_common(25):
            lines.append(f"  - {tech} `{name}` ({role}, {n}×)")
        c = s["contracts"]
        lines.append(f"- Contracts: proto packages {c['proto_packages'] or 'none'}; proto services "
                     f"{[p['service'] for p in c['proto_services']] or 'none'}; OpenAPI "
                     f"{[(o['file'], o['title'], len(o['paths'])) for o in c['openapi']] or 'none'}; "
                     f"AsyncAPI channels {c['asyncapi_channels'][:10] or 'none'}")
        for comp in s["compose"]:
            lines.append(f"- Compose `{comp['file']}`: " + "; ".join(
                f"{svc['name']} (image {svc['image'] or 'build'}; depends_on {svc['depends_on'] or '-'})" for svc in comp["services"][:20]))
        if s["kubernetes"]:
            kinds = Counter(k["kind"] for k in s["kubernetes"])
            lines.append(f"- Kubernetes objects: {dict(kinds)}")
            for k in s["kubernetes"][:25]:
                extra = []
                if k.get("hosts"):
                    extra.append(f"hosts {k['hosts']}")
                if k.get("backends"):
                    extra.append(f"backends {k['backends']}")
                if k.get("schedule"):
                    extra.append(f"schedule {k['schedule']}")
                lines.append(f"  - {k['kind']} `{k.get('name')}` · `{k['file']}` {' · '.join(extra)}")
        lines.append(f"- Package identities: {', '.join(f'`{p}`' for p in s['package_identities']) or 'none'}")
        lines.append("")
    return "\n".join(lines)
