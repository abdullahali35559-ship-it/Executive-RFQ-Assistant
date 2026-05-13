import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INDEX_PATH = os.path.join(ROOT, "analysis_index.json")
OUT_JSON = os.path.join(ROOT, "project_analysis.json")
OUT_README = os.path.join(ROOT, "README.md")


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def infer_summary(path, entry):
    rel = path.replace("\\", "/")
    base = os.path.basename(rel)
    name = os.path.splitext(base)[0]

    if entry.get("type") == "json":
        return entry.get("summary", "JSON data file")

    if base == "__init__.py":
        return "Package initializer."

    if rel == "auth/users.json":
        return "User data store (redacted)."
    if rel == "auth/sessions.json":
        return "Session data store (redacted)."

    if rel == "api/main.py":
        return "FastAPI app entry point, startup tasks, routing, and DB initialization."
    if rel.startswith("api/routes/"):
        return f"API route handlers for {name} features."
    if rel.startswith("api/") and base == "tasks.py":
        return "Background task helpers and async processing."
    if rel.startswith("auth/"):
        return f"Authentication and authorization utilities for {name}."
    if rel.startswith("config/"):
        return f"Configuration and settings for {name}."
    if rel.startswith("database/"):
        return f"Database models, migrations, and setup for {name}."
    if rel.startswith("agents/"):
        return f"Agent component for {name.replace('_', ' ')}."
    if rel.startswith("integrations/"):
        return f"Integration utilities for {name.replace('_', ' ')}."
    if rel.startswith("models/"):
        return f"Model or client implementation for {name.replace('_', ' ')}."
    if rel.startswith("scripts/"):
        return f"Utility script to {name.replace('_', ' ')}."
    if rel.startswith("tests/"):
        return f"Test cases for {name.replace('_', ' ')}."
    if rel.startswith("ui/") and rel.endswith(".html"):
        title = entry.get("title") or name
        return f"UI page: {title}."
    if rel.startswith("ui/") and rel.endswith(".js"):
        return f"Frontend logic for {name.replace('_', ' ')}."

    if name.startswith("check_"):
        return f"Diagnostic check for {name.replace('check_', '').replace('_', ' ')}."
    if name.startswith("verify_"):
        return f"Verification script for {name.replace('verify_', '').replace('_', ' ')}."
    if name.startswith("test_"):
        return f"Test script for {name.replace('test_', '').replace('_', ' ')}."
    if name.startswith("fix_"):
        return f"Fix or repair routine for {name.replace('fix_', '').replace('_', ' ')}."
    if name.startswith("reset_"):
        return f"Reset utility for {name.replace('reset_', '').replace('_', ' ')}."
    if name.startswith("list_"):
        return f"List or report utility for {name.replace('list_', '').replace('_', ' ')}."
    if name.startswith("get_"):
        return f"Fetch helper for {name.replace('get_', '').replace('_', ' ')}."
    if name.startswith("run_"):
        return f"Run utility for {name.replace('run_', '').replace('_', ' ')}."
    if name.startswith("init_"):
        return f"Initialization helper for {name.replace('init_', '').replace('_', ' ')}."
    if name.startswith("diagnose_"):
        return f"Diagnostics for {name.replace('diagnose_', '').replace('_', ' ')}."
    if name.startswith("simulate_"):
        return f"Simulation helper for {name.replace('simulate_', '').replace('_', ' ')}."
    if name.startswith("debug_"):
        return f"Debug helper for {name.replace('debug_', '').replace('_', ' ')}."
    if name.startswith("tmp_") or name.startswith("temp_"):
        return "Temporary or experimental helper."

    if entry.get("module_docstring"):
        return entry["module_docstring"].splitlines()[0].strip()

    if entry.get("summary"):
        return entry["summary"]

    return "No summary available."


def extract_route_prefix(path):
    source = read_text(os.path.join(ROOT, path))
    m = re.search(r"APIRouter\(.*?prefix\s*=\s*[\"']([^\"']+)[\"']", source, re.DOTALL)
    return m.group(1) if m else ""


def make_markdown(data):
    files = data["files"]

    groups = {
        "agents": [],
        "api": [],
        "auth": [],
        "config": [],
        "database": [],
        "integrations": [],
        "models": [],
        "scripts": [],
        "tests": [],
        "ui": [],
        "root": [],
    }

    for f in files:
        path = f["path"].replace("\\", "/")
        added = False
        for key in ["agents", "api", "auth", "config", "database", "integrations", "models", "scripts", "tests", "ui"]:
            if path.startswith(f"{key}/"):
                groups[key].append(f)
                added = True
                break
        if not added:
            groups["root"].append(f)

    md = []
    md.append("# Project Deep Analysis")
    md.append("")
    md.append("Yeh README poore repo ka deep analysis hai: har page ka kaam, har Python/JS file ke functions aur classes, aur system flow ka overview.")
    md.append("")

    md.append("## System Overview")
    md.append("- Multi-agent RFQ pipeline: emails/documents ingest -> data extraction -> draft generation")
    md.append("- FastAPI backend (API routes, auth, background tasks)")
    md.append("- UI dashboard (HTML pages + JS clients)")
    md.append("- PostgreSQL models + migrations")
    md.append("")

    md.append("## Entry Points")
    md.append("- api/main.py - FastAPI app boot + routes + DB init")
    md.append("- scripts/run_rfq_agent.py - background agent runner")
    md.append("")

    md.append("## UI Pages")
    for f in sorted([x for x in groups["ui"] if x["path"].endswith(".html")], key=lambda x: x["path"]):
        title = f.get("title") or os.path.splitext(os.path.basename(f["path"]))[0]
        summary = infer_summary(f["path"], f)
        out_path = f["path"].replace("\\", "/")
        md.append(f"- {out_path} - {title} - {summary}")
    md.append("")

    md.append("## API Routes")
    api_routes = [x for x in groups["api"] if x["path"].replace("\\", "/").startswith("api/routes/")]
    for f in sorted(api_routes, key=lambda x: x["path"]):
        prefix = extract_route_prefix(f["path"].replace("\\", "/"))
        summary = infer_summary(f["path"], f)
        extra = f" (prefix: {prefix})" if prefix else ""
        out_path = f["path"].replace("\\", "/")
        md.append(f"- {out_path} - {summary}{extra}")
    md.append("")

    md.append("## Folder Responsibilities")
    folder_desc = {
        "agents": "AI agents (research, analysis, drafting).",
        "api": "Backend routes and async tasks.",
        "auth": "Authentication, sessions, audit logging.",
        "config": "App settings, OAuth, DB config.",
        "database": "SQLAlchemy models and migrations.",
        "integrations": "External integrations (email/file).",
        "models": "LLM / model clients.",
        "scripts": "Maintenance utilities and one-off tools.",
        "tests": "Test suite and validation scripts.",
        "ui": "Frontend HTML/JS/CSS.",
        "root": "Root utilities and docs.",
    }
    for key in ["agents", "api", "auth", "config", "database", "integrations", "models", "scripts", "tests", "ui", "root"]:
        md.append(f"- {key}/ - {folder_desc[key]}")
    md.append("")

    md.append("## File-by-File Summary")
    for key in ["root", "agents", "api", "auth", "config", "database", "integrations", "models", "scripts", "tests", "ui"]:
        md.append("")
        md.append(f"### {key}/")
        for f in sorted(groups[key], key=lambda x: x["path"]):
            summary = infer_summary(f["path"], f)
            out_path = f["path"].replace("\\", "/")
            md.append(f"- {out_path} - {summary}")

    md.append("")
    md.append("## Functions and Classes Index")
    for f in sorted([x for x in files if x["type"] == "py"], key=lambda x: x["path"]):
        path = f["path"].replace("\\", "/")
        md.append("")
        md.append(f"### {path}")
        if f.get("functions"):
            md.append("Functions:")
            for fn in f["functions"]:
                doc = fn.get("doc") or ""
                doc = doc.replace("\n", " ").strip()
                suffix = f" - {doc}" if doc else ""
                md.append(f"- {fn['name']}({', '.join(fn.get('args', []))}){suffix}")
        else:
            md.append("Functions: none")

        if f.get("classes"):
            md.append("Classes:")
            for cls in f["classes"]:
                doc = cls.get("doc") or ""
                doc = doc.replace("\n", " ").strip()
                suffix = f" - {doc}" if doc else ""
                md.append(f"- {cls['name']}{suffix}")
                if cls.get("methods"):
                    method_names = []
                    for m in cls["methods"]:
                        mdoc = m.get("doc") or ""
                        mdoc = mdoc.replace("\n", " ").strip()
                        msuffix = f" - {mdoc}" if mdoc else ""
                        method_names.append(f"{m['name']}({', '.join(m.get('args', []))}){msuffix}")
                    if method_names:
                        md.append(f"Methods: {', '.join(method_names)}")
        else:
            md.append("Classes: none")

    md.append("")
    md.append("## Frontend JS Index")
    for f in sorted([x for x in files if x["type"] == "js"], key=lambda x: x["path"]):
        md.append("")
        out_path = f["path"].replace("\\", "/")
        md.append(f"### {out_path}")
        if f.get("functions"):
            names = [x["name"] for x in f["functions"]]
            md.append(f"Functions: {', '.join(names)}")
        else:
            md.append("Functions: none")
        if f.get("classes"):
            names = [x["name"] for x in f["classes"]]
            md.append(f"Classes: {', '.join(names)}")
        else:
            md.append("Classes: none")

    return "\n".join(md) + "\n"


def main():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for f in data["files"]:
        f["summary"] = infer_summary(f["path"], f)
        if f["path"].startswith("api/routes/"):
            prefix = extract_route_prefix(f["path"])
            if prefix:
                f["route_prefix"] = prefix

    out = {
        "generated_at": data["generated_at"],
        "root": data["root"],
        "overview": {
            "entry_points": ["api/main.py", "scripts/run_rfq_agent.py"],
            "folders": [
                "agents/",
                "api/",
                "auth/",
                "config/",
                "database/",
                "integrations/",
                "models/",
                "scripts/",
                "tests/",
                "ui/",
            ],
        },
        "files": data["files"],
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    md = make_markdown(data)
    with open(OUT_README, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
