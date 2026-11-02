"""Build the data for a set of repos and render the single-file page."""

import datetime
import json
import traceback
from pathlib import Path

from . import __version__
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
    return {"version": __version__, "served": served,
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "repos": repos}


def render(data):
    blob = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")  # no </script> or <!-- can end the block
    return TEMPLATE.read_text().replace("/*DATA*/", blob, 1)
