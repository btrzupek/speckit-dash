"""One repo's model: features, tasks with derived statuses and links, releases, ideas."""

import re
from pathlib import Path

from . import config, gitdata, github, halo, ideas
from .tasks import feature_number, ids_in, parse_spec, parse_tasks

CLOSED = {"closed", "split"}
FEATURE_IN_TEXT = re.compile(r"(?<![\w-])(\d{3,})(?=-[a-z]|[:\s,]|$)")
SPEC_IN_NOTES = re.compile(r"(?:\bSpecs?\s+|specs/)(\d{3,})\b|(?<![\w-])(\d{3,})-[a-z][a-z0-9]*(?:-[a-z0-9]+)+")


def build_repo(path, overrides=None, use_github=True, use_halo=True, use_cache=True):
    repo = Path(path).expanduser().resolve()
    cfg = config.repo_config(repo, overrides)
    main = gitdata.main_branch(repo, cfg.get("main"))
    slug = None if cfg.get("github") is False else (cfg.get("github") or gitdata.github_slug(gitdata.origin_url(repo)))
    gh = github.fetch(slug, use_cache) if use_github and cfg.get("github") is not False \
        else {"status": "off", "issues": [], "prs": []}
    queue = halo.fetch(cfg.get("halo"), use_cache) if use_halo else {"status": "off", "tasks": {}}

    features, tasks, pairs = [], [], []
    for d in sorted(p for p in (repo / "specs").glob("*") if p.is_dir() and feature_number(p.name)):
        num = feature_number(d.name)
        spec = parse_spec((d / "spec.md").read_text(errors="replace")) if (d / "spec.md").exists() else \
            {"title": d.name, "status_text": "", "created": ""}
        f = {"id": d.name, "num": num, "title": spec["title"] or d.name, "status_text": spec["status_text"],
             "created": spec["created"], "artifacts": sorted(p.name for p in d.iterdir() if not p.name.startswith(".")),
             "has_tasks": (d / "tasks.md").exists()}
        if f["has_tasks"]:
            ts, ps = parse_tasks((d / "tasks.md").read_text(errors="replace"), num, cfg.get("blocked_patterns"))
            for t in ts:
                t["feature"] = d.name
                t["file"] = f"specs/{d.name}/tasks.md"
            tasks += ts
            pairs += ps
        features.append(f)

    by_id = {}
    for t in tasks:
        by_id.setdefault(t["id"], t)  # a duplicated id keeps its first line
    known = set(by_id)

    for t in tasks:
        t["split_into"] = []
        if t["struck"]:
            kids = [i for i in ids_in(t["notes"], feature_number(t["feature"])) if i in known and i != t["id"]]
            kids += [i for i in known if re.fullmatch(re.escape(t["id"]) + r"[a-z]", i)]
            t["split_into"] = sorted(set(kids))

    deps = {}
    for dep, pre in pairs:
        if dep in known and pre in known and dep != pre:
            targets = by_id[pre]["split_into"] or [pre]
            for p in targets:
                if p != dep:
                    deps.setdefault(dep, [])
                    if p not in deps[dep]:
                        deps[dep].append(p)

    # commits, releases
    commits = gitdata.commits(repo, main)
    tags, unreleased = gitdata.releases(repo, main)
    release_of, prerelease_of = {}, {}
    for t in tags:
        target = prerelease_of if t["prerelease"] else release_of
        for sha in t["shas"]:
            target.setdefault(sha, t["tag"])
    task_commits, feature_commits = {}, {}
    fnums = {f["num"]: f["id"] for f in features}
    for c in commits:
        c["release"] = release_of.get(c["sha"])
        c["prerelease"] = prerelease_of.get(c["sha"])
        for i in set(ids_in(c["subject"], "")):
            if i in known:
                task_commits.setdefault(i, []).append(c)
        for n in set(FEATURE_IN_TEXT.findall(c["subject"])):
            if n in fnums:
                feature_commits.setdefault(fnums[n], []).append(c)

    # links
    issues, prs = gh.get("issues", []), gh.get("prs", [])
    branch_names = gitdata.all_branch_names(repo)

    def links_for(t):
        raw = t["id"].split("-", 1)[-1]
        single = len(features) == 1
        pat = re.compile(r"(?<![\w-])" + re.escape(t["id"]) + r"(?![\w])")
        bare = re.compile(r"(?<![\w-])" + re.escape(raw) + r"(?![\w])")
        num = feature_number(t["feature"])
        out = []
        for i in issues:
            text = i["title"] + " " + " ".join(l.get("name", "") for l in i.get("labels", []))
            if pat.search(text) or (bare.search(i["title"]) and (single or num in text or t["feature"] in text)):
                out.append({"kind": "issue", "label": f"#{i['number']}", "state": i["state"].lower(), "url": i["url"],
                            "title": i["title"]})
        for p in prs:
            if pat.search(p["title"]) or pat.search(p.get("headRefName") or ""):
                out.append({"kind": "pr", "label": f"PR #{p['number']}", "state": p["state"].lower(), "url": p["url"],
                            "title": p["title"]})
        for b in branch_names:
            if pat.search(b):
                out.append({"kind": "branch", "label": b})
        return out

    commit_url = f"https://github.com/{slug}/commit/" if slug else None
    for t in tasks:
        cs = task_commits.get(t["id"], [])
        t["commits"] = [{"short": c["short"], "date": c["date"], "subject": c["subject"], "release": c["release"],
                         "work": t["id"] in ids_in(c["subject"].split(":", 1)[0], "") and ":" in c["subject"],
                         "url": commit_url + c["sha"] if commit_url else None} for c in cs]
        rels = [c["release"] for c in cs if c["release"]]
        t["release"] = _oldest(rels, tags)
        t["unreleased"] = bool(cs) and any(c["release"] is None for c in cs)
        t["links"] = links_for(t)
        t["deps"] = deps.get(t["id"], [])
        t["queue"] = queue["tasks"].get(t["id"])
        t["assignee"] = _assignee(t["tag"])

    # statuses: dependencies need their prerequisites' status first
    status = {}

    def derive(t, seen=()):
        if t["id"] in status:
            return status[t["id"]]
        q = (t["queue"] or {}).get("state")
        if t["struck"]:
            s = ("split", "tasks.md", f"split into {', '.join(t['split_into'])}" if t["split_into"] else "struck through")
        elif t["done"]:
            s = ("closed", "tasks.md", "checked")
        elif q in halo.ACTIVE:
            s = ("in progress", "build queue", q)
        elif q == "merged":
            s = ("in progress", "build queue", "merged on the build host, not checked off")
        elif q in halo.QUEUED:
            s = ("queued", "build queue", q)
        elif t["blocked_reason"]:
            s = ("blocked", "text match (heuristic)", t["blocked_reason"])
        else:
            open_deps = [d for d in t["deps"] if d not in seen and derive(by_id[d], seen + (t["id"],))[0] not in CLOSED]
            if open_deps:
                s = ("waiting", "Dependencies", "waiting on " + ", ".join(open_deps))
            elif any(c["work"] for c in t["commits"]):
                n = sum(c["work"] for c in t["commits"])
                s = ("in progress", "commits (heuristic)", f"{n} commit(s) lead with its id")
            else:
                s = ("open", "tasks.md", "")
        status[t["id"]] = s
        return s

    for t in tasks:
        t["status"], t["status_source"], t["status_detail"] = derive(t)
        t["dep_status"] = {d: derive(by_id[d])[0] for d in t["deps"]}

    # features: counts and releases
    notes_specs = _release_note_specs(repo, cfg, tags, set(fnums))
    for f in features:
        ft = [t for t in tasks if t["feature"] == f["id"]]
        counts = {"total": len(ft)}
        for t in ft:
            counts[t["status"]] = counts.get(t["status"], 0) + 1
        counts["closed"] = counts.get("closed", 0) + counts.get("split", 0)
        f["counts"] = counts
        rel = set(r for t in ft if t["release"] for r in [t["release"]])
        rel |= set(c["release"] for c in feature_commits.get(f["id"], []) if c["release"])
        rel |= {tag for tag, nums in notes_specs.items() if f["num"] in nums}
        f["releases"] = [t["tag"] for t in tags if t["tag"] in rel]
        f["commits"] = len(feature_commits.get(f["id"], []))
        f["last_commit"] = (feature_commits.get(f["id"]) or [{}])[0].get("date", "")
        if not f["has_tasks"]:
            f["state"] = "spec only"
        elif counts["total"] and counts["closed"] == counts["total"]:
            f["state"] = "done"
        elif counts["closed"]:
            f["state"] = "in progress"
        else:
            f["state"] = "not started"

    # releases, newest first, with "Unreleased" on top
    sha_tasks = {}
    for i, cs in task_commits.items():
        for c in cs:
            sha_tasks.setdefault(c["sha"], set()).add(i)
    sha_features = {}
    for fid, cs in feature_commits.items():
        for c in cs:
            sha_features.setdefault(c["sha"], set()).add(fid)
    rel_rows = []
    for t in [{"tag": None, "date": "", "prerelease": False, "shas": unreleased}] + list(reversed(tags)):
        ts = sorted(set().union(*[sha_tasks.get(s, set()) for s in t["shas"]]) if t["shas"] else set())
        fs = set().union(*[sha_features.get(s, set()) for s in t["shas"]]) if t["shas"] else set()
        fs |= {by_id[i]["feature"] for i in ts}
        from_notes = {fnums[n] for n in notes_specs.get(t["tag"], set())}
        rel_rows.append({"tag": t["tag"], "date": t["date"], "prerelease": t["prerelease"], "commits": len(t["shas"]),
                         "tasks": ts, "specs": sorted(fs | from_notes), "specs_in_notes": sorted(from_notes)})

    branches = gitdata.branches(repo, main, cfg.get("remote_branches", True)) \
        if (cfg.get("ideas") or {}).get("branches", True) else []
    idea_rows = ideas.gather(repo, cfg, main, features, known, issues, branches)

    for t in tasks:
        t.pop("indent", None)
    return {
        "name": cfg["name"], "path": str(repo), "main": main, "checkout": gitdata.current_branch(repo),
        "github": slug, "commit_url": commit_url, "prompts": cfg.get("prompts") or {},
        "sources": {"github": gh["status"], "halo": queue["status"], "config": cfg.get("_error") or "ok",
                    "queue_unmatched": sorted(set(queue["tasks"]) - known)[:50]},
        "features": features, "tasks": tasks, "releases": rel_rows, "ideas": idea_rows,
    }


def _oldest(rels, tags):
    order = {t["tag"]: i for i, t in enumerate(tags)}
    return min(rels, key=lambda r: order.get(r, 1 << 30)) if rels else None


def _assignee(tag):
    t = tag.lower()
    for who in ("owner", "architect", "design"):
        if t.startswith(who):
            return who
    m = re.match(r"agent:\s*([\w-]+)", t)
    return f"agent: {m.group(1)}" if m else ""


def _release_note_specs(repo, cfg, tags, fnums):
    """{tag: {feature numbers}} named in each release's notes."""
    pattern = cfg.get("release_notes")
    if not pattern and (repo / "docs" / "releases").is_dir():
        pattern = "docs/releases/{tag}.md"
    if not pattern and (repo / "CHANGELOG.md").exists():
        pattern = "CHANGELOG.md"
    if not pattern:
        return {}
    out = {}
    if "{tag}" in pattern:
        for t in tags:
            p = repo / pattern.format(tag=t["tag"])
            text = p.read_text(errors="replace") if p.exists() else gitdata.show(repo, t["tag"], pattern.format(tag=t["tag"]))
            out[t["tag"]] = _spec_nums(text, fnums)
    else:
        p = repo / pattern
        text = p.read_text(errors="replace") if p.exists() else ""
        sections = re.split(r"^##\s+", text, flags=re.M)
        for t in tags:
            v = t["tag"].lstrip("v")
            sec = next((s for s in sections if re.match(r"\[?v?" + re.escape(v) + r"\b", s)), "")
            out[t["tag"]] = _spec_nums(sec, fnums)
    return out


def _spec_nums(text, fnums):
    nums = set()
    for m in SPEC_IN_NOTES.finditer(text):
        n = m.group(1) or m.group(2)
        if n in fnums:
            nums.add(n)
    return nums
