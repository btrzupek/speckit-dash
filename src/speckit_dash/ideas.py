"""Ideas that aren't specs yet (or are specs with no tasks): Spec Kit has no backlog store of its own, so ideas are
gathered from wherever they live, each naming its source."""

import re
from pathlib import Path

from . import gitdata
from .tasks import HEADING, parse_spec

BACKLOG_STATUS = re.compile(r"\b(backlog|draft|idea|proposed|someday|parked)\b", re.I)
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")


def _first_heading(text):
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def section_items(text, section):
    """Top-level list items under the heading whose text starts with `section` (case-insensitive)."""
    items, inside, level, cur = [], False, 0, None
    for line in text.splitlines():
        h = HEADING.match(line)
        if h:
            if inside and len(h.group(1)) <= level:
                break
            if not inside and h.group(2).lower().startswith(section.lower()):
                inside, level = True, len(h.group(1))
            continue
        if not inside:
            continue
        m = LIST_ITEM.match(line)
        if m and len(m.group(1)) == 0:
            cur = m.group(2).strip()
            items.append(cur)
        elif cur is not None and line.strip() and line.startswith((" ", "\t")):
            items[-1] += " " + line.strip()
    return items


def gather(repo, cfg, main, features, task_ids, issues, branches):
    icfg = cfg.get("ideas") or {}
    ideas = []
    main_specs = {f["id"] for f in features}

    if icfg.get("spec_only", True):
        for f in features:
            if not f["has_tasks"]:
                ideas.append({"kind": "spec, no tasks", "title": f["title"], "where": f"specs/{f['id']}/",
                              "detail": f["status_text"]})
            elif f["counts"]["total"] and f["counts"]["closed"] < f["counts"]["total"] \
                    and BACKLOG_STATUS.search(f["status_text"] or "") and not f["counts"]["closed"]:
                ideas.append({"kind": "backlog spec", "title": f["title"], "where": f"specs/{f['id']}/",
                              "detail": f["status_text"]})

    globs = [d["glob"] for d in icfg.get("docs", []) if d.get("glob")]
    if icfg.get("branches", True):
        found = {}
        for b in branches:
            for path in gitdata.added_files(repo, main, b["name"], ["specs/*/spec.md"] + globs):
                if path.startswith("specs/"):
                    sid = path.split("/")[1]
                    if sid in main_specs:
                        continue
                    key = ("spec", sid)
                else:
                    if (Path(repo) / path).exists():
                        continue
                    key = ("doc", path)
                if key not in found:
                    text = gitdata.show(repo, b["name"], path)
                    meta = parse_spec(text) if key[0] == "spec" else {"title": _first_heading(text), "status_text": ""}
                    found[key] = {"kind": "unmerged spec" if key[0] == "spec" else "doc on a branch",
                                  "title": f"{key[1]}: {meta['title']}" if key[0] == "spec" else meta["title"] or path,
                                  "where": path, "detail": meta["status_text"], "branches": []}
                found[key]["branches"].append(b["name"])
        ideas += found.values()

    if icfg.get("assessments", True):
        root = Path(repo) / ".specify" / "assessments"
        for d in sorted(p for p in root.glob("*") if p.is_dir()):
            mds = sorted(d.glob("*.md"))
            title = next((t for t in (_first_heading(m.read_text(errors="replace")) for m in mds) if t), d.name)
            verdict = ""
            if (d / "decide.md").exists():
                m = re.search(r"verdict\W{0,6}\s*(go|kill|needs[- ]clarification)", (d / "decide.md").read_text(errors="replace"), re.I)
                verdict = m.group(1).lower() if m else "decided"
            if verdict == "kill":
                continue
            stages = [m.stem for m in mds]
            ideas.append({"kind": "assessment", "title": title, "where": str(d.relative_to(repo)) + "/",
                          "detail": (f"verdict: {verdict}; " if verdict else "") + "stages: " + ", ".join(stages)})

    for d in icfg.get("docs", []):
        if d.get("path"):
            p = Path(repo) / d["path"]
            if not p.exists():
                continue
            text = p.read_text(errors="replace")
            if d.get("section"):
                for item in section_items(text, d["section"]):
                    ideas.append({"kind": "roadmap", "title": item, "where": f"{d['path']} › {d['section']}",
                                  "refs": [t for t in _refs(item) if t in task_ids]})
            else:
                ideas.append({"kind": "doc", "title": _first_heading(text) or d["path"], "where": d["path"]})
        elif d.get("glob"):
            for p in sorted(Path(repo).glob(d["glob"])):
                text = p.read_text(errors="replace")
                heads = [h.group(2) for h in map(HEADING.match, text.splitlines()) if h and len(h.group(1)) == 3]
                ideas.append({"kind": "doc", "title": _first_heading(text) or p.name, "where": str(p.relative_to(repo)),
                              "detail": "; ".join(heads[:8])})

    if icfg.get("issues", True):
        for i in issues:
            if i.get("state", "").upper() == "OPEN" and not any(t in task_ids for t in _refs(i["title"])):
                ideas.append({"kind": "issue", "title": f"#{i['number']} {i['title']}", "where": "GitHub",
                              "url": i.get("url"), "detail": ", ".join(l.get("name", "") for l in i.get("labels", []))})

    if icfg.get("todos", True):
        for t in gitdata.grep_todos(repo):
            ideas.append({"kind": "todo", "title": t["text"], "where": f"{t['path']}:{t['line']}"})
    return ideas


def _refs(text):
    from .tasks import ids_in
    return ids_in(text, "")
