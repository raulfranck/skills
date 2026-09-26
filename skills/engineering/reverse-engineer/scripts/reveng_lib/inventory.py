"""Repository inventory: languages, sizes, modules, manifests, entry points, IaC, CI,
contracts, data, docs, config and technology hints."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from . import common as C

try:  # Python 3.11+
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover
    tomllib = None

LIMIT = 30  # rows per markdown section

# ---------------------------------------------------------------- technology hints
# (category, technology, pattern). Patterns use only non-capturing groups.
TECH_HINTS = [
    ("web", "Express", r"require\(['\"]express['\"]\)|from ['\"]express['\"]"),
    ("web", "NestJS", r"@nestjs/"),
    ("web", "Fastify", r"['\"]fastify['\"]"),
    ("web", "Next.js", r"from ['\"]next/"),
    ("web", "Spring", r"org\.springframework"),
    ("web", "Django", r"from django\b|import django\b"),
    ("web", "Flask", r"from flask import|import flask\b"),
    ("web", "FastAPI", r"from fastapi\b|import fastapi\b"),
    ("web", "ASP.NET Core", r"Microsoft\.AspNetCore"),
    ("web", "Gin", r"github\.com/gin-gonic/gin"),
    ("web", "Echo", r"github\.com/labstack/echo"),
    ("web", "Fiber", r"github\.com/gofiber/fiber"),
    ("web", "Rails", r"Rails\.application|ActionController::"),
    ("web", "Laravel", r"Illuminate\\"),
    ("orm", "TypeORM", r"['\"]typeorm['\"]"),
    ("orm", "Prisma", r"@prisma/client"),
    ("orm", "Sequelize", r"['\"]sequelize['\"]"),
    ("orm", "Mongoose", r"['\"]mongoose['\"]"),
    ("orm", "Drizzle", r"drizzle-orm"),
    ("orm", "SQLAlchemy", r"\bsqlalchemy\b"),
    ("orm", "Django ORM", r"from django\.db import models"),
    ("orm", "JPA/Hibernate", r"javax\.persistence|jakarta\.persistence|org\.hibernate"),
    ("orm", "Entity Framework", r"Microsoft\.EntityFrameworkCore"),
    ("orm", "GORM", r"gorm\.io/gorm"),
    ("orm", "ActiveRecord", r"ActiveRecord::"),
    ("datastore", "PostgreSQL", r"postgres(?:ql)?:/|psycopg|npgsql|\bpg\.Pool\b|org\.postgresql|jackc/pgx"),
    ("datastore", "MySQL", r"mysql:/|pymysql|mysql2|com\.mysql"),
    ("datastore", "MongoDB", r"mongodb(?:\+srv)?:/|MongoClient|pymongo"),
    ("datastore", "Redis", r"\bioredis\b|['\"]redis['\"]|StackExchange\.Redis|redis://|go-redis|\bjedis\b|lettuce"),
    ("datastore", "DynamoDB", r"(?i:dynamodb)"),
    ("datastore", "Elasticsearch/OpenSearch", r"(?i:elasticsearch|opensearch)"),
    ("datastore", "Cassandra", r"(?i:cassandra)"),
    ("datastore", "S3/Blob storage", r"(?i:client-s3|s3client|boto3\.client\(['\"]s3|BlobServiceClient|google\.cloud\.storage)"),
    ("messaging", "Kafka", r"(?i:kafka)"),
    ("messaging", "RabbitMQ/AMQP", r"(?i:rabbitmq|amqplib|\bamqp\b|pika\b)"),
    ("messaging", "AWS SQS", r"(?i:client-sqs|SQSClient|boto3\.client\(['\"]sqs|@SqsListener|amazonaws\.com/\d+/)"),
    ("messaging", "AWS SNS", r"(?i:client-sns|SNSClient|arn:aws:sns)"),
    ("messaging", "Google Pub/Sub", r"(?i:pubsub)"),
    ("messaging", "NATS", r"(?i:nats\.go|['\"]nats['\"]|nats://)"),
    ("messaging", "Azure Service Bus", r"ServiceBusClient|Azure\.Messaging\.ServiceBus"),
    ("messaging", "AWS EventBridge", r"(?i:eventbridge)"),
    ("messaging", "Celery", r"\bcelery\b|shared_task"),
    ("messaging", "Sidekiq", r"(?i:sidekiq)"),
    ("messaging", "BullMQ/Bull", r"['\"]bullmq?['\"]"),
    ("cloud", "AWS SDK", r"aws-sdk|@aws-sdk/|\bboto3\b|software\.amazon\.awssdk|aws/aws-sdk-go"),
    ("cloud", "Google Cloud SDK", r"@google-cloud/|google\.cloud\b|cloud\.google\.com/go"),
    ("cloud", "Azure SDK", r"@azure/|Azure\.Identity|azure\.identity"),
    ("observability", "OpenTelemetry", r"(?i:opentelemetry)"),
    ("observability", "Prometheus/Micrometer", r"(?i:prom-client|prometheus_client|micrometer|prometheus/client_golang)"),
    ("observability", "Datadog", r"(?i:dd-trace|ddtrace|datadog)"),
    ("observability", "New Relic", r"(?i:newrelic)"),
    ("observability", "Sentry", r"(?i:@sentry/|sentry_sdk|sentry-go|io\.sentry)"),
    ("observability", "Structured logging", r"(?i:\bwinston\b|\bpino\b|logback|log4j|serilog|structlog|zerolog|\bzap\b|logrus)"),
    ("auth", "OAuth/OIDC", r"(?i:oauth2?|openid|\boidc\b)"),
    ("auth", "JWT", r"(?i:jsonwebtoken|\bjwt\b|pyjwt|\bjose\b)"),
    ("auth", "Keycloak", r"(?i:keycloak)"),
    ("auth", "Auth0", r"(?i:auth0)"),
    ("auth", "Cognito", r"(?i:cognito)"),
    ("auth", "Passport", r"['\"]passport['\"]"),
    ("feature-flags", "LaunchDarkly", r"(?i:launchdarkly)"),
    ("feature-flags", "Unleash", r"(?i:unleash)"),
    ("feature-flags", "GrowthBook", r"(?i:growthbook)"),
    ("feature-flags", "Flagsmith", r"(?i:flagsmith)"),
    ("http-client", "axios", r"['\"]axios['\"]"),
    ("http-client", "fetch", r"\bfetch\("),
    ("http-client", "requests/httpx/aiohttp", r"import requests\b|\bhttpx\b|\baiohttp\b"),
    ("http-client", "RestTemplate/WebClient/Feign", r"RestTemplate|WebClient\.|@FeignClient"),
    ("http-client", ".NET HttpClient", r"IHttpClientFactory|new HttpClient\("),
    ("http-client", "Go net/http client", r"http\.(?:Get|Post|NewRequest)\("),
    ("rpc", "gRPC", r"(?i:grpc)"),
    ("rpc", "GraphQL", r"(?i:graphql|apollo)"),
    ("resilience", "Retry/circuit breaker", r"(?i:resilience4j|\bpolly\b|tenacity|opossum|hystrix|p-retry|async-retry|backoff|circuit.?breaker)"),
    ("scheduling", "Schedulers/cron", r"@Scheduled|node-cron|cron\.schedule|APScheduler|CronJob|@nestjs/schedule|robfig/cron"),
    ("testing", "Jest/Vitest/Mocha", r"from ['\"](?:vitest|@jest/globals)['\"]|\bjest\.fn\(|\bdescribe\(['\"]"),
    ("testing", "pytest/unittest", r"\bimport pytest\b|\bimport unittest\b"),
    ("testing", "JUnit/TestNG", r"org\.junit|org\.testng"),
    ("testing", "xUnit/NUnit/MSTest", r"\bXunit\b|NUnit\.Framework|Microsoft\.VisualStudio\.TestTools"),
    ("testing", "Go testing", r"\"testing\""),
    ("testing", "Playwright/Cypress/Selenium", r"(?i:@playwright/test|cypress|selenium)"),
    ("testing", "Testcontainers", r"(?i:testcontainers)"),
]
_HINT_RX = re.compile("|".join(f"(?P<h{i}>{p})" for i, (_, _, p) in enumerate(TECH_HINTS)))

ENTRY_MARKERS = [
    ("spring-boot-app", re.compile(r"@SpringBootApplication")),
    ("python-main", re.compile(r"if __name__ == ['\"]__main__['\"]")),
    ("fastapi-app", re.compile(r"=\s*FastAPI\(")),
    ("flask-app", re.compile(r"=\s*Flask\(__name__")),
    ("http-listen", re.compile(r"\.listen\(\s*(?:process\.env\.\w+|\d{2,5}|port|PORT)")),
    ("nest-bootstrap", re.compile(r"NestFactory\.create")),
    ("go-main", re.compile(r"^func main\(\)", re.M)),
    ("dotnet-host", re.compile(r"WebApplication\.CreateBuilder|Host\.CreateDefaultBuilder|static (?:async )?(?:void|Task|int|Task<int>) Main\(")),
    ("java-main", re.compile(r"public static void main\s*\(\s*String")),
    ("serverless-handler", re.compile(r"exports\.handler\s*=|export (?:const|async function|function) handler\b|def (?:lambda_)?handler\(\s*event\s*,\s*context")),
    ("cli", re.compile(r"argparse\.ArgumentParser|@click\.command|new Command\(|yargs\(|cobra\.Command")),
    ("message-consumer", re.compile(r"@KafkaListener|@RabbitListener|@SqsListener|@EventPattern|@MessagePattern|\.consume\(\s*['\"]|consumer\.run\(|@app\.task|@shared_task")),
    ("scheduled-job", re.compile(r"@Scheduled\(|cron\.schedule\(|@Cron\(|BackgroundService\b")),
]

MANIFEST_NAMES = {
    "package.json": "npm", "pyproject.toml": "python", "setup.py": "python", "setup.cfg": "python",
    "pipfile": "python", "go.mod": "go", "cargo.toml": "rust", "pom.xml": "maven",
    "build.gradle": "gradle", "build.gradle.kts": "gradle", "settings.gradle": "gradle-settings",
    "settings.gradle.kts": "gradle-settings", "composer.json": "php", "gemfile": "ruby",
    "mix.exs": "elixir", "pubspec.yaml": "dart", "package.swift": "swift", "deno.json": "deno",
    "go.work": "go-workspace", "pnpm-workspace.yaml": "pnpm-workspace", "lerna.json": "lerna",
    "nx.json": "nx", "turbo.json": "turbo",
}
PACKAGE_MANIFESTS = {"package.json", "pyproject.toml", "setup.py", "go.mod", "cargo.toml", "pom.xml",
                     "build.gradle", "build.gradle.kts", "composer.json", "pubspec.yaml", "mix.exs"}
NON_MODULE_SEGMENTS = {"examples", "example", "samples", "sample", "fixtures", "testdata", "docs",
                       "test", "tests", "e2e", "benchmarks", "bench"}


def _section_for(rel: str, lower_name: str, lang: str | None, head: str) -> list[tuple[str, str]]:
    """Classify special files into inventory sections as (section, kind)."""
    out: list[tuple[str, str]] = []
    low = rel.lower()
    suffix = PurePosixPath(lower_name).suffix
    segs = low.split("/")

    # IaC and containers
    if suffix == ".tf":
        out.append(("iac", "terraform"))
    elif lower_name == "chart.yaml":
        out.append(("iac", "helm"))
    elif lower_name in ("kustomization.yaml", "kustomization.yml"):
        out.append(("iac", "kustomize"))
    elif re.match(r"(docker-)?compose(\.[\w-]+)?\.ya?ml$", lower_name):
        out.append(("iac", "docker-compose"))
    elif lower_name.startswith("dockerfile") or lower_name.endswith(".dockerfile"):
        out.append(("iac", "dockerfile"))
    elif re.match(r"serverless(\.[\w-]+)?\.ya?ml$", lower_name):
        out.append(("iac", "serverless"))
    elif lower_name == "cdk.json":
        out.append(("iac", "aws-cdk"))
    elif lower_name in ("pulumi.yaml", "pulumi.yml"):
        out.append(("iac", "pulumi"))
    elif lower_name in ("skaffold.yaml", "helmfile.yaml", "tiltfile"):
        out.append(("iac", lower_name.split(".")[0]))
    elif suffix in (".yaml", ".yml", ".json") and ("AWSTemplateFormatVersion" in head or "AWS::Serverless" in head):
        out.append(("iac", "cloudformation"))
    elif suffix in (".yaml", ".yml") and re.search(r"^apiVersion:", head, re.M) and re.search(r"^kind:", head, re.M):
        out.append(("iac", "kubernetes"))

    # CI/CD
    if low.startswith(".github/workflows/") and suffix in (".yml", ".yaml"):
        out.append(("ci", "github-actions"))
    elif lower_name == ".gitlab-ci.yml":
        out.append(("ci", "gitlab-ci"))
    elif lower_name == "jenkinsfile":
        out.append(("ci", "jenkins"))
    elif lower_name in ("azure-pipelines.yml", "azure-pipelines.yaml"):
        out.append(("ci", "azure-pipelines"))
    elif low.startswith(".circleci/"):
        out.append(("ci", "circleci"))
    elif lower_name == "bitbucket-pipelines.yml":
        out.append(("ci", "bitbucket-pipelines"))
    elif lower_name in ("buildspec.yml", "buildspec.yaml"):
        out.append(("ci", "aws-codebuild"))
    elif lower_name in ("cloudbuild.yaml", "cloudbuild.yml"):
        out.append(("ci", "google-cloud-build"))
    elif lower_name == ".travis.yml":
        out.append(("ci", "travis"))

    # Contracts
    if suffix == ".proto":
        out.append(("contracts", "protobuf"))
    elif suffix in (".graphql", ".gql"):
        out.append(("contracts", "graphql"))
    elif suffix == ".avsc":
        out.append(("contracts", "avro"))
    elif suffix == ".wsdl":
        out.append(("contracts", "wsdl"))
    elif suffix in (".yaml", ".yml", ".json"):
        if re.search(r"^\s*['\"]?openapi['\"]?\s*:|^\s*['\"]?swagger['\"]?\s*:", head, re.M):
            out.append(("contracts", "openapi"))
        elif re.search(r"^\s*['\"]?asyncapi['\"]?\s*:", head, re.M):
            out.append(("contracts", "asyncapi"))

    # Data
    if any(s in ("migrations", "migration", "migrate", "alembic", "flyway", "liquibase", "changelogs") for s in segs[:-1]):
        out.append(("data", "migration"))
    elif suffix == ".sql":
        out.append(("data", "sql"))
    if lower_name == "schema.prisma" or suffix == ".prisma":
        out.append(("data", "prisma-schema"))
    elif suffix == ".dbml":
        out.append(("data", "dbml"))

    # Docs
    if lower_name.startswith("readme"):
        out.append(("docs", "readme"))
    elif any(s in ("adr", "adrs", "decisions", "architecture-decisions") for s in segs[:-1]) and lang == "Markdown":
        out.append(("docs", "adr"))
    elif lower_name.startswith("architecture"):
        out.append(("docs", "architecture"))
    elif lower_name.startswith("contributing"):
        out.append(("docs", "contributing"))
    elif lower_name.startswith("changelog") or lower_name.startswith("history.md"):
        out.append(("docs", "changelog"))
    elif any(s in ("runbook", "runbooks", "playbooks") for s in segs[:-1]):
        out.append(("docs", "runbook"))
    elif segs[0] in ("docs", "doc", "documentation") and lang in ("Markdown", "reStructuredText"):
        out.append(("docs", "docs"))

    # Config
    if re.match(r"\.env\.(example|sample|template|dist|defaults)$|.*\.env\.(example|sample|template)$", lower_name):
        out.append(("config", "env-template"))
    elif re.match(r"application(-[\w]+)?\.(ya?ml|properties)$", lower_name):
        out.append(("config", "spring-config"))
    elif re.match(r"appsettings(\.[\w]+)?\.json$", lower_name):
        out.append(("config", "dotnet-config"))
    elif lower_name == "settings.py" and "django" in head.lower():
        out.append(("config", "django-settings"))
    elif segs[0] in ("config", "configs", "conf") and lang in ("YAML", "JSON", "TOML", "INI", "Properties"):
        out.append(("config", "config"))

    # Ownership
    if lower_name == "codeowners":
        out.append(("ownership", "codeowners"))

    # Observability as code
    if suffix in (".yaml", ".yml") and re.search(r"^\s*-?\s*alert:\s", head, re.M):
        out.append(("observability", "alert-rules"))
    elif suffix == ".json" and '"panels"' in head and '"dashboard' in head.lower():
        out.append(("observability", "dashboard"))
    elif re.search(r"(^|[._-])slos?([._-]|$)", lower_name) and suffix in (".yaml", ".yml", ".json"):
        out.append(("observability", "slo"))
    elif re.match(r"otel.*\.ya?ml$", lower_name):
        out.append(("observability", "otel-collector"))
    return out


# ---------------------------------------------------------------- manifest parsing

def _toml(text: str) -> dict:
    if tomllib is None:
        return {}
    try:
        return tomllib.loads(text)
    except Exception:
        return {}


def _xml_strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def parse_manifest(rel: str, lower_name: str, text: str) -> dict:
    kind = MANIFEST_NAMES.get(lower_name)
    if kind is None:
        if lower_name.endswith((".csproj", ".fsproj", ".vbproj")):
            kind = "dotnet-project"
        elif lower_name.endswith(".sln"):
            kind = "dotnet-solution"
        elif re.match(r"requirements.*\.txt$", lower_name):
            kind = "python-requirements"
    info: dict = {"path": rel, "type": kind}
    try:
        if lower_name == "package.json":
            data = json.loads(text)
            deps = sorted(set(data.get("dependencies", {}) or {}) | set(data.get("peerDependencies", {}) or {}))
            info.update({
                "name": data.get("name"),
                "main": data.get("main") or data.get("module"),
                "bin": data.get("bin"),
                "scripts": data.get("scripts", {}) or {},
                "dependencies": deps,
                "dev_dependencies": sorted(data.get("devDependencies", {}) or {}),
                "workspaces": data.get("workspaces"),
            })
        elif lower_name == "pyproject.toml":
            data = _toml(text)
            proj = data.get("project", {})
            poetry = data.get("tool", {}).get("poetry", {})
            deps = [re.split(r"[<>=!~\[; ]", d, 1)[0] for d in proj.get("dependencies", []) or []]
            deps += [d for d in (poetry.get("dependencies", {}) or {}) if d.lower() != "python"]
            info.update({"name": proj.get("name") or poetry.get("name"), "dependencies": sorted(set(deps)),
                         "scripts": proj.get("scripts") or poetry.get("scripts") or {}})
        elif kind == "python-requirements":
            deps = []
            for line in text.splitlines():
                line = line.split("#", 1)[0].strip()
                if line and not line.startswith(("-", "git+", "http")):
                    deps.append(re.split(r"[<>=!~\[; ]", line, 1)[0])
            info["dependencies"] = sorted(set(deps))
        elif lower_name == "go.mod":
            m = re.search(r"^module\s+(\S+)", text, re.M)
            reqs = re.findall(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-]+/[^\s]+)\s+v[\w.\-+]+", text, re.M)
            info.update({"name": m.group(1) if m else None, "dependencies": sorted(set(reqs))})
        elif lower_name == "go.work":
            info["members"] = re.findall(r"^\s*(?:use\s+)?(\./[^\s)]+)", text, re.M)
        elif lower_name == "cargo.toml":
            data = _toml(text)
            info.update({"name": data.get("package", {}).get("name"),
                         "dependencies": sorted(data.get("dependencies", {}) or {}),
                         "members": data.get("workspace", {}).get("members", [])})
        elif lower_name == "pom.xml":
            root = _xml_strip_ns(ET.fromstring(text))
            gid = root.findtext("groupId") or root.findtext("parent/groupId")
            aid = root.findtext("artifactId")
            deps = [f"{d.findtext('groupId')}:{d.findtext('artifactId')}" for d in root.findall("dependencies/dependency")]
            info.update({"name": f"{gid}:{aid}" if gid and aid else aid,
                         "dependencies": sorted(set(deps)),
                         "members": [m.text for m in root.findall("modules/module") if m.text]})
        elif kind == "gradle":
            deps = re.findall(r"""(?:implementation|api|compile|runtimeOnly|compileOnly)\s*\(?\s*['"]([\w.\-]+:[\w.\-]+)(?::[^'"]*)?['"]""", text)
            projects = re.findall(r"""project\(\s*['"](:[\w\-:]+)['"]\s*\)""", text)
            info.update({"dependencies": sorted(set(deps)), "project_dependencies": sorted(set(projects))})
        elif kind == "gradle-settings":
            info["members"] = re.findall(r"""['"](:[\w\-:]+)['"]""", text)
        elif kind == "dotnet-project":
            info.update({
                "name": (re.search(r"<(?:PackageId|AssemblyName)>([^<]+)<", text) or [None, PurePosixPath(rel).stem])[1],
                "dependencies": sorted(set(re.findall(r"<PackageReference\s+Include=\"([^\"]+)\"", text))),
                "project_references": [C.posix(p) for p in re.findall(r"<ProjectReference\s+Include=\"([^\"]+)\"", text)],
            })
        elif lower_name == "composer.json":
            data = json.loads(text)
            info.update({"name": data.get("name"), "dependencies": sorted(data.get("require", {}) or {})})
        elif lower_name == "gemfile":
            info["dependencies"] = sorted(set(re.findall(r"""^\s*gem\s+['"]([^'"]+)['"]""", text, re.M)))
        elif lower_name == "pubspec.yaml":
            m = re.search(r"^name:\s*(\S+)", text, re.M)
            info["name"] = m.group(1) if m else None
        elif lower_name == "pnpm-workspace.yaml":
            info["members"] = re.findall(r"^\s*-\s*['\"]?([^'\"\n]+)['\"]?", text, re.M)
    except Exception as exc:  # malformed manifests are reported, never fatal
        info["parse_error"] = str(exc)[:200]
    return info


# ---------------------------------------------------------------- main

def build(repo_name: str, repo_path: str | Path, exclude_abs=()) -> dict:
    repo = Path(repo_path).resolve()
    files = C.list_files(repo, exclude_abs)
    sections: dict[str, list[dict]] = defaultdict(list)
    manifests: list[dict] = []
    entrypoints: list[dict] = []
    lang_files: Counter = Counter()
    lang_loc: Counter = Counter()
    per_file: dict[str, dict] = {}
    hint_files: dict[int, list[str]] = defaultdict(list)
    tests = 0
    generated = 0
    categories: Counter = Counter()

    for rel in files:
        name = PurePosixPath(rel).name
        lower = name.lower()
        lang = C.language_of(rel)
        cat = C.category_of(lang)
        gen = C.is_generated(rel)
        tst = C.is_test(rel)
        categories[cat] += 1
        if gen:
            generated += 1
        text = None
        if cat in ("code", "config", "docs", "markup") or lower in MANIFEST_NAMES or lower.endswith((".csproj", ".sln")):
            text = C.read_text(repo / rel)
        head = text[:4096] if text else ""

        for section, kind in _section_for(rel, lower, lang, head):
            sections[section].append({"path": rel, "kind": kind})

        if not gen and (lower in MANIFEST_NAMES or lower.endswith((".csproj", ".fsproj", ".vbproj", ".sln"))
                        or re.match(r"requirements.*\.txt$", lower)) and text is not None:
            manifests.append(parse_manifest(rel, lower, text))

        if text is None or gen:
            continue
        if cat == "code":
            loc, cx, max_ind = C.text_stats(text)
            if tst:
                tests += 1
            else:
                lang_files[lang] += 1
                lang_loc[lang] += loc
            per_file[rel] = {"loc": loc, "complexity": cx, "max_indent": max_ind, "test": tst, "language": lang}
            scan = text[:200_000]
            if not tst:
                for kind, rx in ENTRY_MARKERS:
                    m = rx.search(scan)
                    if m:
                        entrypoints.append({"path": rel, "kind": kind, "line": C.LineIndex(scan).line(m.start()),
                                            "snippet": C.snippet(scan, m.start())})
        if cat in ("code", "config"):
            seen = set()
            for m in _HINT_RX.finditer(text[:200_000]):
                seen.add(int(m.lastgroup[1:]))
            for idx in seen:
                hint_files[idx].append(rel)
        if lower.startswith("dockerfile") or lower.endswith(".dockerfile"):
            for m in re.finditer(r"^\s*(CMD|ENTRYPOINT)\s+(.+)$", text, re.M):
                entrypoints.append({"path": rel, "kind": "container-" + m.group(1).lower(),
                                    "line": C.LineIndex(text).line(m.start()), "snippet": m.group(2).strip()[:120]})
        if lower == "procfile":
            for m in re.finditer(r"^([\w-]+):\s*(.+)$", text, re.M):
                entrypoints.append({"path": rel, "kind": "procfile-" + m.group(1),
                                    "line": C.LineIndex(text).line(m.start()), "snippet": m.group(2).strip()[:120]})
        if re.match(r"serverless(\.[\w-]+)?\.ya?ml$", lower):
            for m in re.finditer(r"^\s*handler:\s*(\S+)", text, re.M):
                entrypoints.append({"path": rel, "kind": "serverless-function",
                                    "line": C.LineIndex(text).line(m.start()), "snippet": m.group(1)[:120]})

    for man in manifests:
        if man.get("type") == "npm":
            for key in ("main",):
                if man.get(key):
                    entrypoints.append({"path": man["path"], "kind": "npm-main", "line": None, "snippet": str(man[key])[:120]})
            if man.get("bin"):
                entrypoints.append({"path": man["path"], "kind": "npm-bin", "line": None, "snippet": json.dumps(man["bin"])[:120]})
            for script in ("start", "serve", "dev", "worker"):
                if script in man.get("scripts", {}):
                    entrypoints.append({"path": man["path"], "kind": f"npm-script:{script}", "line": None,
                                        "snippet": str(man["scripts"][script])[:120]})

    # Monorepo packages: directories holding their own package manifest.
    package_roots = []
    for man in manifests:
        p = PurePosixPath(man["path"])
        if p.name.lower() in PACKAGE_MANIFESTS or man.get("type") == "dotnet-project":
            d = str(p.parent)
            if d != "." and not (set(d.lower().split("/")) & NON_MODULE_SEGMENTS):
                package_roots.append(d)
    package_roots = sorted(set(package_roots))
    workspace_markers = [m["path"] for m in manifests if m.get("workspaces") or m.get("members")
                         or m.get("type") in ("pnpm-workspace", "lerna", "nx", "turbo", "go-workspace", "gradle-settings", "dotnet-solution")]
    monorepo = len(package_roots) >= 2 or bool(workspace_markers)

    source_files = [r for r, f in per_file.items() if not f["test"]]
    prefixes = C.compute_module_prefixes(source_files, package_roots if monorepo else [])
    modules: dict[str, dict] = {}
    for rel, f in per_file.items():
        mod = C.module_of(rel, prefixes)
        m = modules.setdefault(mod, {"module": mod, "files": 0, "loc": 0, "test_files": 0, "languages": Counter()})
        if f["test"]:
            m["test_files"] += 1
        else:
            m["files"] += 1
            m["loc"] += f["loc"]
            m["languages"][f["language"]] += f["loc"]
    module_rows = []
    for m in sorted(modules.values(), key=lambda x: -x["loc"]):
        m["languages"] = [k for k, _ in m["languages"].most_common(3)]
        module_rows.append(m)

    top_level: dict[str, dict] = {}
    for rel in files:
        top = rel.split("/")[0] if "/" in rel else "(root files)"
        t = top_level.setdefault(top, {"path": top, "files": 0, "source_loc": 0})
        t["files"] += 1
        if rel in per_file and not per_file[rel]["test"]:
            t["source_loc"] += per_file[rel]["loc"]

    tech = []
    for idx, paths in hint_files.items():
        cat, techname, _ = TECH_HINTS[idx]
        tech.append({"category": cat, "technology": techname, "files": len(paths), "samples": paths[:3]})
    tech.sort(key=lambda t: (t["category"], -t["files"]))

    largest = sorted(((r, f) for r, f in per_file.items() if not f["test"]), key=lambda x: -x[1]["loc"])[:25]

    source_loc = sum(f["loc"] for f in per_file.values() if not f["test"])
    return {
        "repo": repo_name,
        "path": C.posix(repo),
        "head": C.git_head(repo) if C.is_git_repo(repo) else None,
        "generated_at": C.now_iso(),
        "totals": {
            "files": len(files), "code_files": len(per_file), "source_files": len(source_files),
            "source_loc": source_loc, "test_files": tests, "generated_or_vendored_files": generated,
            "by_category": dict(categories),
        },
        "languages": [{"language": l, "files": lang_files[l], "loc": lang_loc[l]} for l, _ in lang_loc.most_common()],
        "monorepo": {"detected": monorepo, "package_roots": package_roots, "workspace_markers": workspace_markers},
        "module_prefixes": prefixes,
        "modules": module_rows,
        "top_level": sorted(top_level.values(), key=lambda t: -t["files"]),
        "manifests": manifests,
        "entrypoints": entrypoints[:200],
        "sections": {k: v for k, v in sorted(sections.items())},
        "tech_hints": tech,
        "largest_files": [{"path": r, **f} for r, f in largest],
    }


def to_markdown(inv: dict) -> str:
    t = inv["totals"]
    lines = [f"# Inventory: {inv['repo']}", ""]
    lines.append(f"HEAD `{(inv.get('head') or 'n/a')[:12]}` · {t['files']} files · {t['source_files']} source files · "
                 f"{t['source_loc']} source LOC · {t['test_files']} test files · {t['generated_or_vendored_files']} generated/vendored")
    lines += ["", "## Languages (non-test code)", C.md_table(["Language", "Files", "LOC"],
                                                     [[l["language"], l["files"], l["loc"]] for l in inv["languages"]], 12)]
    mono = inv["monorepo"]
    if mono["detected"]:
        lines += ["", f"## Monorepo: {len(mono['package_roots'])} packages",
                  ", ".join(f"`{p}`" for p in mono["package_roots"][:40]) or "(markers only)",
                  f"Workspace markers: {', '.join(mono['workspace_markers']) or 'none'}"]
    lines += ["", "## Modules (derived from layout; tests excluded from LOC)",
              C.md_table(["Module", "Files", "LOC", "Tests", "Languages"],
                         [[f"`{m['module']}`", m["files"], m["loc"], m["test_files"], ", ".join(m["languages"])] for m in inv["modules"]], LIMIT)]
    lines += ["", "## Manifests", C.md_table(["Path", "Type", "Name", "Deps"],
                                             [[f"`{m['path']}`", m.get("type"), m.get("name") or "", len(m.get("dependencies") or [])]
                                              for m in inv["manifests"]], LIMIT)]
    lines += ["", "## Entry point candidates", C.md_table(["Path", "Kind", "Line", "Snippet"],
                                                          [[f"`{e['path']}`", e["kind"], e.get("line") or "", e.get("snippet", "")]
                                                           for e in inv["entrypoints"]], LIMIT)]
    titles = {"iac": "Infrastructure as code", "ci": "CI/CD", "contracts": "Contracts", "data": "Data (schema, migrations)",
              "docs": "Documentation", "config": "Configuration", "ownership": "Ownership", "observability": "Observability as code"}
    for key, title in titles.items():
        items = inv["sections"].get(key, [])
        lines += ["", f"## {title} ({len(items)})"]
        if not items:
            lines.append("None found.")
            continue
        by_kind: dict[str, list[str]] = defaultdict(list)
        for it in items:
            by_kind[it["kind"]].append(it["path"])
        for kind, paths in sorted(by_kind.items()):
            shown = ", ".join(f"`{p}`" for p in paths[:12])
            more = f" (+{len(paths) - 12} more)" if len(paths) > 12 else ""
            lines.append(f"- **{kind}** ({len(paths)}): {shown}{more}")
    lines += ["", "## Technology hints (files mentioning each; hints, not facts)",
              C.md_table(["Category", "Technology", "Files", "Samples"],
                         [[h["category"], h["technology"], h["files"], ", ".join(f"`{s}`" for s in h["samples"])] for h in inv["tech_hints"]], 60)]
    lines += ["", "## Largest source files", C.md_table(["Path", "LOC", "Indentation complexity", "Max indent"],
                                                        [[f"`{f['path']}`", f["loc"], f["complexity"], f["max_indent"]] for f in inv["largest_files"]], 15)]
    return "\n".join(lines)
