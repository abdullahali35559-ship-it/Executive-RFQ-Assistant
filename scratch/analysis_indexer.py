import ast
import json
import os
import re
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
}

TEXT_FILE_EXTS = {".py", ".js", ".html", ".md", ".json"}

EXCLUDE_FILES = {
    "analysis_index.json",
    ".gmail_oauth_token.json",
    ".outlook_oauth_token.json",
}


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name in EXCLUDE_FILES:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_FILE_EXTS:
                yield os.path.join(dirpath, name)


def summarize_python(source):
    summary = {
        "module_docstring": "",
        "functions": [],
        "classes": [],
        "imports": [],
    }
    try:
        tree = ast.parse(source)
    except Exception:
        return summary

    summary["module_docstring"] = (ast.get_docstring(tree) or "").strip()

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for n in node.names:
                    summary["imports"].append(n.name)
            else:
                module = node.module or ""
                for n in node.names:
                    if module:
                        summary["imports"].append(f"{module}.{n.name}")
                    else:
                        summary["imports"].append(n.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            summary["functions"].append({
                "name": node.name,
                "args": [a.arg for a in node.args.args],
                "doc": (ast.get_docstring(node) or "").strip(),
                "line": node.lineno,
                "async": isinstance(node, ast.AsyncFunctionDef),
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": item.name,
                        "args": [a.arg for a in item.args.args],
                        "doc": (ast.get_docstring(item) or "").strip(),
                        "line": item.lineno,
                        "async": isinstance(item, ast.AsyncFunctionDef),
                    })
            summary["classes"].append({
                "name": node.name,
                "doc": (ast.get_docstring(node) or "").strip(),
                "line": node.lineno,
                "methods": methods,
            })

    return summary


def summarize_js(source):
    functions = []
    classes = []
    # Basic regex-based extraction
    for match in re.finditer(r"\bfunction\s+([A-Za-z0-9_]+)\s*\(", source):
        functions.append({"name": match.group(1)})
    for match in re.finditer(r"\bclass\s+([A-Za-z0-9_]+)\b", source):
        classes.append({"name": match.group(1)})
    for match in re.finditer(r"\bconst\s+([A-Za-z0-9_]+)\s*=\s*\([^)]*\)\s*=>", source):
        functions.append({"name": match.group(1)})
    first_comment = ""
    for line in source.splitlines():
        if line.strip().startswith("//"):
            first_comment = line.strip().lstrip("//").strip()
            break
    return {
        "summary": first_comment,
        "functions": functions,
        "classes": classes,
    }


def summarize_html(source):
    title = ""
    scripts = []
    styles = []
    m = re.search(r"<title>(.*?)</title>", source, flags=re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
    for m in re.finditer(r"<script[^>]*src=[\"']([^\"']+)[\"']", source, flags=re.IGNORECASE):
        scripts.append(m.group(1))
    for m in re.finditer(r"<link[^>]*rel=[\"']stylesheet[\"'][^>]*href=[\"']([^\"']+)[\"']", source, flags=re.IGNORECASE):
        styles.append(m.group(1))
    return {"title": title, "scripts": scripts, "styles": styles}


def summarize_json(path, source):
    base = os.path.basename(path).lower()
    if base.startswith(".") or "token" in base or "secret" in base:
        return "Sensitive JSON (redacted)"
    if os.path.normpath(path).lower().endswith(os.path.normpath("auth\\users.json")):
        return "User data store (redacted)"
    if os.path.normpath(path).lower().endswith(os.path.normpath("auth\\sessions.json")):
        return "Session data store (redacted)"
    try:
        data = json.loads(source)
        if isinstance(data, dict):
            keys = list(data.keys())[:20]
            return f"JSON object keys: {', '.join(keys)}" if keys else "Empty JSON object"
        if isinstance(data, list):
            return f"JSON list ({len(data)} items)"
    except Exception:
        pass
    return "JSON data file"


def main():
    data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "root": ROOT,
        "files": [],
    }

    for path in iter_files(ROOT):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        ext = os.path.splitext(path)[1].lower()
        source = read_text(path)
        file_entry = {"path": rel, "type": ext.lstrip(".")}

        if ext == ".py":
            py = summarize_python(source)
            file_entry.update({
                "module_docstring": py["module_docstring"],
                "functions": py["functions"],
                "classes": py["classes"],
                "imports": py["imports"],
            })
        elif ext == ".js":
            js = summarize_js(source)
            file_entry.update(js)
        elif ext == ".html":
            html = summarize_html(source)
            file_entry.update(html)
        else:
            # Minimal summary for md/json
            if ext == ".json":
                file_entry["summary"] = summarize_json(path, source)
            else:
                first_line = source.splitlines()[0].strip() if source else ""
                file_entry["summary"] = first_line

        data["files"].append(file_entry)

    out_path = os.path.join(ROOT, "analysis_index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
