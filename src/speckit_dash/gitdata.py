"""Read-only git queries: the main branch's commits, tags and their ranges, branches, files added on branches."""

import fnmatch
import re
import subprocess

TODO = re.compile(r"\b(TODO|FIXME|XXX)\b[:( ]")
PRERELEASE = re.compile(r"(rc|alpha|beta|pre|dev)\.?\d*$", re.I)


def git(repo, *args, check=False, timeout=60):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])}: {r.stderr.strip()[-500:]}")
    return r.stdout if r.returncode == 0 else ""


def main_branch(repo, configured=None):
    if configured:
        return configured
    head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    if head:
        local = head.split("/", 1)[-1]
        return local if git(repo, "rev-parse", "--verify", "-q", local) else head
    for name in ("main", "master", "trunk"):
        if git(repo, "rev-parse", "--verify", "-q", name):
            return name
    return "HEAD"


def current_branch(repo):
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def commits(repo, ref):
    out = git(repo, "log", ref, "--format=%H%x1f%h%x1f%ad%x1f%s", "--date=short")
    rows = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            rows.append({"sha": parts[0], "short": parts[1], "date": parts[2], "subject": parts[3]})
    return rows


def releases(repo, ref):
    """Tags reachable from ref, oldest first, each with the commits it added: a final release since the previous
    final one, a pre-release since the previous tag of any kind. Plus "unreleased" commits since the last tag."""
    out = git(repo, "tag", "--merged", ref, "--sort=creatordate", "--format=%(refname:short)%1f%(creatordate:short)")
    tags = [dict(zip(("tag", "date"), l.split("\x1f"))) for l in out.splitlines() if "\x1f" in l]
    prev_final = prev_any = None
    for t in tags:
        t["prerelease"] = bool(PRERELEASE.search(t["tag"]))
        base = prev_any if t["prerelease"] else prev_final
        rng = f"{base}..{t['tag']}" if base else t["tag"]
        t["shas"] = git(repo, "rev-list", rng).split()
        prev_any = t["tag"]
        if not t["prerelease"]:
            prev_final = t["tag"]
    last = tags[-1]["tag"] if tags else None
    unreleased = git(repo, "rev-list", f"{last}..{ref}" if last else ref).split()
    return tags, unreleased


def branches(repo, main, remotes=True):
    """Branches not merged into main: [{name, date, sha}]. Remote branches that have a local twin are dropped."""
    refs = ["refs/heads"] + (["refs/remotes"] if remotes else [])
    out = git(repo, "for-each-ref", "--no-merged", main,
              "--format=%(refname:short)%1f%(committerdate:short)%1f%(objectname:short)", *refs)
    rows, seen = [], set()
    for line in out.splitlines():
        name, date, sha = line.split("\x1f")
        if name.endswith("/HEAD"):
            continue
        short = name.split("/", 1)[1] if name.startswith(tuple(r + "/" for r in remote_names(repo))) else name
        if short in seen:
            continue
        seen.add(short)
        rows.append({"name": name, "date": date, "sha": sha})
    return rows


def all_branch_names(repo):
    return git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()


_remotes = {}


def remote_names(repo):
    key = str(repo)
    if key not in _remotes:
        _remotes[key] = git(repo, "remote").split()
    return _remotes[key]


def added_files(repo, main, branch, patterns):
    """Files added on branch since it left main, matching any glob in patterns."""
    out = git(repo, "diff", "--name-only", "--diff-filter=A", f"{main}...{branch}")
    return [f for f in out.splitlines() if any(fnmatch.fnmatch(f, p) for p in patterns)]


def show(repo, ref, path):
    return git(repo, "show", f"{ref}:{path}")


def tracked_dirs(repo, ref, path):
    return [l.rsplit("/", 1)[-1] for l in git(repo, "ls-tree", "-d", "--name-only", ref, f"{path}/").splitlines()]


def origin_url(repo):
    return git(repo, "remote", "get-url", "origin").strip()


def github_slug(url):
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else None


def grep_todos(repo, limit=100):
    out = git(repo, "grep", "-n", "-I", "-w", "-E", "TODO|FIXME|XXX", "--", ".",
              ":!specs", ":!.specify", ":!.claude", ":!*.md", ":!*.lock", ":!*.min.js")
    rows = []
    for line in out.splitlines():
        path, _, rest = line.partition(":")
        num, _, text = rest.partition(":")
        if not TODO.search(text):
            continue
        if len(rows) >= limit:
            break
        rows.append({"path": path, "line": int(num) if num.isdigit() else 0, "text": text.strip()[:200]})
    return rows
