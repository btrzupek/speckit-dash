"""Build the data for a set of repos and render the single-file page."""

import datetime
import html
import json
import re
import traceback
from pathlib import Path

from . import __version__, config
from .model import build_repo

TEMPLATE = Path(__file__).with_name("page.html")


def build_data(entries, use_github=True, use_halo=True, use_cache=True, served=False):
    """entries: [{"path": ..., "config": {...}}] -> the page's data."""
    repos = []
    for e in entries:
        try:
            repos.append(build_repo(e["path"], e.get("config"), use_github, use_halo, use_cache))
        except Exception as ex:  # one broken repo must not take the page down
            repos.append({"name": Path(e["path"]).name, "path": e["path"], "error": f"{type(ex).__name__}: {ex}",
                          "trace": traceback.format_exc(limit=3), "sources": {"config": "error"},
                          "features": [], "tasks": [], "releases": [], "ideas": []})
    names = {}
    for r in repos:  # names must be unique: they key the picker and the row ids
        n = r["name"]
        names[n] = names.get(n, 0) + 1
        if names[n] > 1:
            r["name"] = f"{n} ({names[n]})"
    return {"version": __version__, "served": served, "home": None,
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "repos": repos}


def render(data):
    blob = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")  # no </script> or <!-- can end the block
    return TEMPLATE.read_text().replace("/*DATA*/", blob, 1)


def slug(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "repo"


def entry_name(entry):
    return config.repo_config(entry["path"], entry.get("config"))["name"]


def summary(repo):
    if repo.get("error"):
        return {"name": repo["name"], "path": repo["path"], "error": repo["error"]}
    counts = {}
    for t in repo["tasks"]:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    return {"name": repo["name"], "path": repo["path"], "features": len(repo["features"]), "tasks": len(repo["tasks"]),
            "counts": counts, "ideas": len(repo["ideas"]),
            "built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}


def build_one(entry, use_github=True, use_halo=True, use_cache=True, out=None):
    """One repo's own page at ~/.cache/speckit-dash/<repo>/index.html (or `out`), and its summary for the launcher."""
    data = build_data([entry], use_github, use_halo, use_cache)
    d = config.cache_dir() / "pages" / slug(entry_name(entry))
    d.mkdir(parents=True, exist_ok=True)
    data["home"] = None if out else "../../index.html"
    out = out or d / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data))
    (d / "summary.json").write_text(json.dumps(summary(data["repos"][0])))
    return out, data


def launcher_html(rows, link, pending=None):
    """A plain list of repos, each linking to its own dashboard. rows: [(entry name, path, summary or None)]."""
    e = html.escape
    items = []
    for name, path, s in rows:
        if s and not s.get("error"):
            c = s.get("counts", {})
            open_n = s["tasks"] - c.get("closed", 0) - c.get("split", 0)
            bits = [f"{open_n} open of {s['tasks']} tasks"] + [f"{c[k]} {k}" for k in ("in progress", "blocked", "waiting")
                                                                 if c.get(k)] + [f"{s['ideas']} ideas", f"built {s['built']}"]
            meta = " · ".join(bits)
        elif s:
            meta = "error: " + s["error"]
        else:
            meta = pending or ("not built yet: <code>speckit-dash open " + e(name) + "</code>")
        items.append(f'<li><a href="{e(link(name))}">{e(name)}</a><div class="m">{meta if not s else e(meta)}</div>'
                     f'<div class="p">{e(path)}</div></li>')
    body = "\n".join(items) or "<li>No repos registered. Run <code>speckit-dash init</code> in a repo.</li>"
    return LAUNCHER.replace("/*ITEMS*/", body)


def write_launcher():
    reg = config.load_registry()["repos"]
    rows = []
    for r in reg:
        name = entry_name(r)
        p = config.cache_dir() / "pages" / slug(name) / "summary.json"
        try:
            s = json.loads(p.read_text())
        except (OSError, ValueError):
            s = None
        rows.append((name, r["path"], s))
    out = config.cache_dir() / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(launcher_html(rows, lambda n: f"pages/{slug(n)}/index.html"))
    return out


LAUNCHER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Spec Kit repos</title>
<style>
:root { --bg: #f7f7f5; --panel: #fff; --ink: #1d1d1b; --muted: #6b6b66; --line: #e3e2dc; --accent: #2f5fd0;
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #161615; --panel: #1f1f1d; --ink: #ecebe6;
  --muted: #9a9a93; --line: #34342f; --accent: #7ea2ff; } }
body { margin: 0; background: var(--bg); color: var(--ink); }
main { max-width: 760px; margin: 0 auto; padding: 24px 16px; }
h1 { font-size: 18px; margin: 0 0 4px; } p { color: var(--muted); margin: 0 0 16px; }
ul { list-style: none; padding: 0; margin: 0; }
li { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }
a { color: var(--accent); font-weight: 600; font-size: 15px; text-decoration: none; } a:hover { text-decoration: underline; }
.m { font-size: 13px; margin-top: 2px; } .p { font: 12px ui-monospace, Menlo, monospace; color: var(--muted); margin-top: 2px; overflow-wrap: anywhere; }
code { font: 12px ui-monospace, Menlo, monospace; }
</style></head>
<body><main><h1>Spec Kit repos</h1><p>Each repo has its own dashboard.</p><ul>
/*ITEMS*/
</ul></main></body></html>
"""
