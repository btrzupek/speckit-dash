"""Where things live: the registry of repos, each repo's .specify/dash.json, the cache."""

import json
import os
from pathlib import Path

DEFAULTS = {
    "name": None,              # display name; the folder name when unset
    "main": None,              # main branch; origin/HEAD, then main/master
    "github": None,            # "owner/repo"; from origin when unset; false turns GitHub off
    "release_notes": None,     # e.g. "docs/releases/{tag}.md", or "CHANGELOG.md" (sections per version)
    "blocked_patterns": None,  # regexes matched against a task's tag and first line; built-in list when unset
    "remote_branches": True,   # look for unmerged specs on remote branches too
    "ideas": {
        "docs": [],            # [{"path": "docs/ROADMAP.md", "section": "Next"}] or [{"glob": "docs/*AUDIT*.md"}]
        "branches": True,      # specs (and doc globs) added on branches not merged to main
        "spec_only": True,     # specs with no tasks.md yet
        "assessments": True,   # Spec Kit's assess extension: .specify/assessments/<slug>/
        "issues": True,        # open GitHub issues that name no task
        "todos": True,         # TODO / FIXME / XXX in code
    },
    "prompts": None,           # {"task": "...", "idea": "..."}: templates for the Copy prompt buttons (see README)
    "halo": None,              # {"project": "...", "ssh": "halo-agents", "agent": "~/halo-agents/bin/halo-agent"}
}


def config_dir():
    if os.environ.get("SPECKIT_DASH_CONFIG"):
        return Path(os.environ["SPECKIT_DASH_CONFIG"])
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "speckit-dash"


def cache_dir():
    if os.environ.get("SPECKIT_DASH_CACHE"):
        return Path(os.environ["SPECKIT_DASH_CACHE"])
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "speckit-dash"


def registry_path():
    return config_dir() / "repos.json"


def load_registry():
    try:
        data = json.loads(registry_path().read_text())
    except (OSError, ValueError):
        data = {}
    data.setdefault("repos", [])
    return data


def save_registry(data):
    p = registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(p)


def register(path, config=None):
    path = str(Path(path).expanduser().resolve())
    data = load_registry()
    entry = next((r for r in data["repos"] if r["path"] == path), None)
    if entry is None:
        entry = {"path": path}
        data["repos"].append(entry)
    if config:
        entry["config"] = merge(entry.get("config") or {}, config)
    save_registry(data)
    return entry


def unregister(key):
    data = load_registry()
    keep = [r for r in data["repos"] if key not in (r["path"], Path(r["path"]).name)]
    removed = len(data["repos"]) - len(keep)
    data["repos"] = keep
    save_registry(data)
    return removed


def dash_json(repo):
    return Path(repo) / ".specify" / "dash.json"


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def repo_config(repo, overrides=None):
    """DEFAULTS, then .specify/dash.json, then the registry entry's config."""
    cfg = merge(DEFAULTS, {})
    try:
        cfg = merge(cfg, json.loads(dash_json(repo).read_text()))
    except FileNotFoundError:
        pass
    except ValueError as e:
        cfg["_error"] = f".specify/dash.json: {e}"
    cfg = merge(cfg, overrides or {})
    cfg["name"] = cfg.get("name") or Path(repo).name
    return cfg


def is_speckit_repo(path):
    p = Path(path)
    return (p / ".specify").is_dir() or (p / "specs").is_dir() and any(p.glob("specs/*/spec.md"))


def read_cache(name, ttl):
    import time
    p = cache_dir() / name
    try:
        if time.time() - p.stat().st_mtime < ttl:
            return json.loads(p.read_text())
    except (OSError, ValueError):
        pass
    return None


def write_cache(name, data):
    p = cache_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))
