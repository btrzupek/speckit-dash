"""GitHub issues and PRs through `gh`, read only (`gh issue list`, `gh pr list`), cached ten minutes."""

import json
import shutil
import subprocess

from . import config

TTL = 600


def _gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) else "gh failed")
    return json.loads(r.stdout or "[]")


def fetch(slug, use_cache=True):
    """{"status": "ok" | "skipped: ..." | "error: ...", "issues": [...], "prs": [...]}"""
    if not slug:
        return {"status": "skipped: no github.com origin", "issues": [], "prs": []}
    if not shutil.which("gh"):
        return {"status": "skipped: gh not installed", "issues": [], "prs": []}
    key = "gh-" + slug.replace("/", "__") + ".json"
    if use_cache:
        cached = config.read_cache(key, TTL)
        if cached:
            return cached
    try:
        issues = _gh("issue", "list", "-R", slug, "--state", "all", "--limit", "1000",
                     "--json", "number,title,state,url,labels,updatedAt")
        prs = _gh("pr", "list", "-R", slug, "--state", "all", "--limit", "500",
                  "--json", "number,title,state,url,headRefName,mergedAt")
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        return {"status": f"error: {e}", "issues": [], "prs": []}
    data = {"status": "ok", "issues": issues, "prs": prs}
    config.write_cache(key, data)
    return data
