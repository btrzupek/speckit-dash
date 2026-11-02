"""Parse a feature's tasks.md and spec.md.

Handles stock Spec Kit (`- [ ] T001 [P] [US1] Description`) and the common variants: ids with the feature's number
(`039-T002`), other letters (`E003`), suffixes (`T003a`), `~~struck~~` split tasks, a `*( ... )*` tag, `**Owns**`,
indented notes, and a Dependencies section written as arrow chains or sentences.
"""

import re

CHECK = re.compile(r"^(\s*)[-*] \[([ xX])\]\s+(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
LEAD_ID = re.compile(r"^(~~)?((?:\d{3,}-)?[A-Z]{1,3}\d+[a-z]?)(~~)?(?=[\s:*.,)~]|$)")
ID = re.compile(r"(?<![\w-])(?:(\d{3,})-)?([A-Z]{1,3}\d+[a-z]?)(?![\w])")
RANGE = re.compile(
    r"(?<![\w-])((?:\d{3,}-)?)([A-Z]{1,3})(\d+)([a-z]?)\s*(?:-|–|\.\.)\s*(?:\d{3,}-)?\2?(\d+)([a-z]?)(?![\w])")
TAG = re.compile(r"\*\(([^)]*)\)\*")
MARKER = re.compile(r"\[(P|US\d+|[a-z][a-z-]{1,15})\]\s*")
OWNS = re.compile(r"\*\*Owns\*\*:?\s*(.+?)(?=\*\*|\n\s*\n|\n\s*[-*] \[|\n\s*\*\d{4}-|\Z)", re.S)
DEPENDS = re.compile(r"\*\*Depends\*\*:?\s*(.+?)(?=\*\*|\n\s*\n|\Z)", re.S)
BACKTICK = re.compile(r"`([^`]+)`")
DEP_WORDS = re.compile(r"\b(needs?|after|depends? on|waits? for|requires?|blocked by|follows)\b", re.I)
BEFORE = re.compile(r"\bbefore\b", re.I)

CONT_STOP = re.compile(r"^\s*(?:[-*+] |\d+[.)] |\*\*|\*\d{4}-|\(|>|```|\|)")
SUMMARY_MAX = 280

DEFAULT_BLOCKED = [r"\bwaiting (?:on|for)\b", r"\bwaits (?:on|for)\b", r"\bblocked\b", r"\bon hold\b",
                   r"\bparked\b"]


def feature_number(dirname):
    m = re.match(r"^(\d{3,})-", dirname)
    return m.group(1) if m else ""


def norm(raw_id, num):
    """`T001` in feature 039 -> `039-T001`; ids that carry a number keep it."""
    if re.match(r"^\d{3,}-", raw_id):
        return raw_id
    return f"{num}-{raw_id}" if num else raw_id


def expand_ranges(text):
    """`T003a-T003d` -> `T003a T003b T003c T003d`; `T004-T007` -> `T004 T005 T006 T007`."""
    def rep(m):
        pfx, letters, n1, s1, n2, s2 = m.groups()
        a, b = int(n1), int(n2)
        width = len(n1)
        if s1 and s2 and a == b and s1 < s2 and ord(s2) - ord(s1) < 26:
            return " ".join(f"{pfx}{letters}{n1}{chr(c)}" for c in range(ord(s1), ord(s2) + 1))
        if not s1 and not s2 and a < b <= a + 50:
            return " ".join(f"{pfx}{letters}{str(i).zfill(width)}" for i in range(a, b + 1))
        return m.group(0)
    return RANGE.sub(rep, text)


def ids_in(text, num):
    return [norm((f"{m.group(1)}-" if m.group(1) else "") + m.group(2), num)
            for m in ID.finditer(expand_ranges(text))]


def summarize(para):
    """(summary, was it cut): the paragraph, or its leading sentences up to SUMMARY_MAX characters."""
    if len(para) <= SUMMARY_MAX:
        return para, False
    head = para[:SUMMARY_MAX]
    stop = max(head.rfind(". "), head.rfind("; "), head.rfind(": "))
    return (head[:stop + 1] if stop > 60 else head.rsplit(" ", 1)[0]) + " …", True


def parse_tasks(text, num, blocked_patterns=None):
    """Return (tasks, dependency pairs) for one tasks.md. Pairs are (task, prerequisite), unfiltered:
    the caller keeps only ids that exist."""
    blocked = [re.compile(p, re.I) for p in (blocked_patterns or DEFAULT_BLOCKED)]
    lines = text.splitlines()
    tasks, phase, cur, in_deps, dep_lines = [], "", None, False, []

    def finish():
        if cur is not None:
            notes = cur.pop("_notes")
            while notes and not notes[-1].strip():
                notes.pop()
            # the summary is the first line plus its wrapped continuation, up to a blank line or a new block
            k = 0
            while k < len(notes) and notes[k].strip() and not CONT_STOP.match(notes[k]):
                k += 1
            para = " ".join([cur["title"]] + [n.strip() for n in notes[:k]])
            cur["title"], cut = summarize(para)
            rest = notes[k:] if not cut else [para, ""] + notes[k:]
            cur["notes"] = "\n".join(rest).strip("\n")
            full = para + "\n" + cur["notes"]
            m = OWNS.search(full)
            if m:
                body = m.group(1)
                ticks = BACKTICK.findall(body)
                cur["owns"] = ticks or [s.strip() for s in body.split(",") if s.strip()]
            m = DEPENDS.search(full)
            if m:
                cur["inline_deps"] += ids_in(m.group(1), num)
            tasks.append(cur)

    for i, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            finish()
            cur = None
            level, title = len(h.group(1)), h.group(2)
            if re.match(r"dependenc", title, re.I):
                in_deps = True
            elif level <= 2:
                in_deps = False
                phase = title
            continue
        if in_deps:
            dep_lines.append(line)
            continue
        c = CHECK.match(line)
        if c:
            finish()
            indent, box, rest = c.groups()
            m = LEAD_ID.match(rest)
            struck = False
            if m:
                raw, rest = m.group(2), rest[m.end():]
                struck = bool(m.group(1) and m.group(3))
                tid = norm(raw, num)
            else:
                tid = f"{num}-L{i}" if num else f"L{i}"
            tag_m = TAG.search(rest)
            tag = tag_m.group(1).strip() if tag_m else ""
            title = rest
            if tag_m:
                title = title[:tag_m.start()] + title[tag_m.end():]
            markers = MARKER.findall(title)
            title = MARKER.sub("", title).strip().lstrip(":—–- ").strip()
            first = (tag + " " + rest)
            reason = ""
            for p in blocked:
                bm = p.search(first)
                if bm:
                    part = next((x for x in tag.split(";") if p.search(x)), "") if p.search(tag) else ""
                    reason = part.strip() or first[max(0, bm.start() - 20):bm.end() + 60].strip()
                    break
            after = re.search(r"\bafter ([^;)]*)", tag)
            cur = {
                "id": tid, "has_id": bool(m), "done": box in "xX", "struck": struck, "title": title,
                "tag": tag, "parallel": "P" in markers, "story": next((x for x in markers if x.startswith("US")), ""),
                "labels": [x for x in markers if x != "P" and not x.startswith("US")],
                "phase": phase, "line": i, "owns": [], "blocked_reason": reason,
                "inline_deps": ids_in(after.group(1), num) if after else [], "_notes": [], "indent": len(indent),
            }
            continue
        if cur is not None:
            if line.strip() == "" or line.startswith((" ", "\t")):
                cur["_notes"].append(line[2:] if line.startswith("  ") else line)
            else:
                finish()
                cur = None
    finish()
    pairs = parse_dependencies("\n".join(dep_lines), num)
    for t in tasks:
        pairs += [(t["id"], d) for d in t.pop("inline_deps")]
    return tasks, pairs


def parse_dependencies(text, num):
    """(dependent, prerequisite) pairs from a Dependencies section."""
    pairs = []
    for line in text.splitlines():
        line = re.sub(r"^\s*[-*]\s+", "", line)
        for clause in re.split(r";|(?<=[a-z0-9)])\.\s", line):
            if "→" in clause or "->" in clause:
                parts = re.split(r"→|->", clause)
                for a, b in zip(parts, parts[1:]):
                    for dep in ids_in(b, num):
                        pairs += [(dep, pre) for pre in ids_in(a, num)]
                continue
            m = DEP_WORDS.search(clause)
            if m:
                left, right = clause[:m.start()], clause[m.end():]
                for dep in ids_in(left, num):
                    pairs += [(dep, pre) for pre in ids_in(right, num)]
                continue
            m = BEFORE.search(clause)
            if m:
                left, right = clause[:m.start()], clause[m.end():]
                for pre in ids_in(left, num):
                    pairs += [(dep, pre) for dep in ids_in(right, num)]
    return pairs


def parse_spec(text):
    """Title (H1 without the template's prefix) and the Status line, verbatim."""
    title, status, created = "", "", ""
    for line in text.splitlines()[:40]:
        if not title and line.startswith("# "):
            title = re.sub(r"^#\s*(Feature Specification:\s*)?", "", line).strip()
        m = re.match(r"^\*\*Status\*?\*?:?\*?\*?\s*(.*)", line)
        if m and not status:
            status = m.group(1).strip()
        m = re.match(r"^\*\*Created\*\*:?\s*(.*)", line)
        if m and not created:
            created = m.group(1).strip()
    return {"title": title, "status_text": status, "created": created}
