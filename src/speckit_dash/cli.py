"""speckit-dash: init, discover, list, remove, build, open, serve."""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

from . import __version__, config

SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "Library", ".Trash", ".cache", "dist", "build", "__pycache__"}
DEFAULT_ROOTS = ["~/projects", "~/work", "~/code", "~/src", "~/dev", "~/repos"]


def _entries(args):
    reg = config.load_registry()["repos"]
    if getattr(args, "repo", None):
        out = []
        for p in args.repo:
            path = str(Path(p).expanduser().resolve())
            out.append(next((r for r in reg if r["path"] == path), {"path": path}))
        return out
    if reg:
        return reg
    if config.is_speckit_repo(Path.cwd()):
        return [{"path": str(Path.cwd())}]
    sys.exit("No repos registered and this folder isn't a Spec Kit repo. Run `speckit-dash init` in a repo, "
             "or `speckit-dash discover`.")


def cmd_init(args):
    repo = Path(args.path).expanduser().resolve()
    if not config.is_speckit_repo(repo):
        sys.exit(f"{repo} has no .specify/ or specs/*/spec.md: run `specify init` there first.")
    cfg = {}
    p = config.dash_json(repo)
    if p.exists():
        try:
            cfg = json.loads(p.read_text())
        except ValueError as e:
            sys.exit(f"{p}: {e}")
    if args.name:
        cfg["name"] = args.name
    if "release_notes" not in cfg:
        if (repo / "docs" / "releases").is_dir():
            cfg["release_notes"] = "docs/releases/{tag}.md"
        elif (repo / "CHANGELOG.md").exists():
            cfg["release_notes"] = "CHANGELOG.md"
    if args.halo_project:
        cfg["halo"] = {"project": args.halo_project, "ssh": args.halo_ssh or "halo-agents"}
    docs = (cfg.get("ideas") or {}).get("docs", [])
    for r in args.roadmap or []:
        path, _, section = r.partition("#")
        item = {"path": path, "section": section} if section else {"path": path}
        if item not in docs:
            docs.append(item)
    for g in args.ideas_glob or []:
        if {"glob": g} not in docs:
            docs.append({"glob": g})
    if docs:
        cfg.setdefault("ideas", {})["docs"] = docs
    if args.no_config:
        config.register(repo, cfg)
        print(f"Registered {repo} (settings kept in {config.registry_path()}, nothing written to the repo).")
    else:
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2) + "\n")
        config.register(repo)
        print(f"Wrote {p.relative_to(repo)} and registered {repo} in {config.registry_path()}.")
    print("Next: `speckit-dash open` (a static page) or `speckit-dash serve` (live, 127.0.0.1).")


def find_repos(roots, depth):
    found = []
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            continue
        stack = [(root, 0)]
        while stack:
            d, lvl = stack.pop()
            if (d / ".specify").is_dir():
                if (d / ".git").is_file() or "/.claude/worktrees/" in str(d):
                    continue  # a worktree of a repo found elsewhere
                found.append(str(d.resolve()))
                continue
            if lvl >= depth:
                continue
            try:
                kids = sorted(p for p in d.iterdir() if p.is_dir() and not p.is_symlink())
            except OSError:
                continue
            stack += [(k, lvl + 1) for k in reversed(kids) if k.name not in SKIP_DIRS and not k.name.startswith(".")]
    return sorted(set(found))


def cmd_discover(args):
    roots = args.roots or DEFAULT_ROOTS
    registered = {r["path"] for r in config.load_registry()["repos"]}
    found = find_repos(roots, args.depth)
    if not found:
        print("No Spec Kit repos (folders with .specify/) under " + ", ".join(roots))
        return
    for path in found:
        mark = "registered" if path in registered else ("adding" if args.add else "")
        print(f"  {mark:<11} {path}")
        if args.add and path not in registered:
            config.register(path)
    if not args.add and any(p not in registered for p in found):
        print("\nAdd them all with `speckit-dash discover --add`, or one with `speckit-dash init <path>`.")


def cmd_list(args):
    reg = config.load_registry()["repos"]
    if not reg:
        print("No repos registered. `speckit-dash init` in a repo, or `speckit-dash discover`.")
    for r in reg:
        ok = "" if Path(r["path"]).is_dir() else "  (missing)"
        cfg = "  dash.json" if config.dash_json(r["path"]).exists() else ""
        print(f"{r['path']}{cfg}{'  +registry settings' if r.get('config') else ''}{ok}")


def cmd_remove(args):
    n = config.unregister(str(Path(args.key).expanduser().resolve()) if os.sep in args.key else args.key)
    print(f"Removed {n} repo(s)." if n else f"No registered repo matches {args.key}.")


def _build(args):
    from .page import build_data, render
    data = build_data(_entries(args), not args.no_github, not args.no_halo, use_cache=not args.fresh)
    out = Path(args.out).expanduser() if args.out else config.cache_dir() / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data))
    if args.json:
        Path(args.json).expanduser().write_text(json.dumps(data, indent=1))
    for r in data["repos"]:
        if r.get("error"):
            print(f"  {r['name']}: {r['error']}", file=sys.stderr)
        else:
            open_n = sum(t["status"] not in ("closed", "split") for t in r["tasks"])
            print(f"  {r['name']}: {len(r['features'])} features, {len(r['tasks'])} tasks ({open_n} open), "
                  f"{len(r['ideas'])} ideas · GitHub {r['sources']['github']} · build queue {r['sources']['halo']}")
    print(out)
    return out


def cmd_build(args):
    _build(args)


def cmd_open(args):
    out = _build(args)
    webbrowser.open(out.resolve().as_uri())


def cmd_serve(args):
    from .serve import serve
    serve(lambda: _entries(args), args.port, not args.no_github, not args.no_halo)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="speckit-dash", description="A status page for Spec Kit repos.")
    ap.add_argument("--version", action="version", version=f"speckit-dash {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="register a repo and write its .specify/dash.json")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--name")
    p.add_argument("--halo-project", help="read this project's halo-agents build queue for 'in progress'")
    p.add_argument("--halo-ssh", help="ssh host for the build queue (default halo-agents)")
    p.add_argument("--roadmap", action="append", metavar="PATH#SECTION", help="list items under a heading are ideas")
    p.add_argument("--ideas-glob", action="append", metavar="GLOB", help="docs matching this are ideas, e.g. docs/*AUDIT*.md")
    p.add_argument("--no-config", action="store_true", help="write nothing to the repo; keep settings in the registry")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("discover", help="find Spec Kit repos (folders with .specify/)")
    p.add_argument("roots", nargs="*", help="folders to search (default: " + " ".join(DEFAULT_ROOTS) + ")")
    p.add_argument("--depth", type=int, default=3)
    p.add_argument("--add", action="store_true", help="register every repo found")
    p.set_defaults(fn=cmd_discover)

    sub.add_parser("list", help="registered repos").set_defaults(fn=cmd_list)
    p = sub.add_parser("remove", help="unregister a repo (by path or folder name)")
    p.add_argument("key")
    p.set_defaults(fn=cmd_remove)

    for name, fn, help_ in (("build", cmd_build, "write the page"), ("open", cmd_open, "write the page and open it"),
                            ("serve", cmd_serve, "serve the page on 127.0.0.1, rebuilt on each load")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--repo", action="append", help="only this repo (repeatable); default: all registered")
        p.add_argument("--no-github", action="store_true")
        p.add_argument("--no-halo", action="store_true")
        if name == "serve":
            p.add_argument("--port", type=int, default=8787)
        else:
            p.add_argument("--out", help="the page (default: ~/.cache/speckit-dash/index.html)")
            p.add_argument("--json", help="also write the data as JSON here")
            p.add_argument("--fresh", action="store_true", help="skip the GitHub and build-queue cache")
        p.set_defaults(fn=fn)

    args = ap.parse_args(argv)
    args.fn(args)
    return 0
