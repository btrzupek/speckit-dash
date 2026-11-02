# Feature Specification: 002 Each repo has its own dashboard

**Feature Branch**: `002-per-repo-dashboards`
**Created**: 2026-11-02
**Status**: Done (owner, 2026-11-02: "does that repo get its own dashboard … I do not want it all in a single
dashboard")

## Why

001 put every registered repo on one page behind a repo picker. The owner wants one dashboard per repo.

## Requirements

- **FR-001** `build`/`open` take a repo (name, folder name or path). With none: the repo the current folder is in;
  outside any repo, every registered repo. Each repo is built to its own page,
  `~/.cache/speckit-dash/pages/<name>/index.html`, with only that repo's data.
- **FR-002** A launcher page, `~/.cache/speckit-dash/index.html`, lists every registered repo with its counts
  (open, in progress, blocked, waiting, ideas, when it was built) and links to each page. It holds no tasks.
- **FR-003** `serve` serves each repo at `/<name>/` (and `/<name>/data.json`); `/` is the launcher, or redirects to
  the only repo. Still 127.0.0.1 only.
- **FR-004** Each page links back to the launcher ("← repos"), except a page written with `--out`.

## Success Criteria

- **SC-001** With two repos registered, each page holds only its own repo's tasks (tests).
- **SC-002** Inside a repo, `speckit-dash open` builds that repo only (tests).
