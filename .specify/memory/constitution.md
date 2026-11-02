# speckit-dash Constitution

## Core Principles

### I. Read-only
The dashboard reads repositories, GitHub and build queues; it never writes to them. GitHub access is `gh issue list`
and `gh pr list` only. The only files it writes are its own: the generated page, its cache, its registry, and a
repo's `.specify/dash.json` when the user runs `init` there.

### II. Local only
`serve` binds 127.0.0.1 and has no option to bind anything else. The page has no external requests: no CDN, no
fonts, no analytics. It works opened as a file.

### III. Honest status
Every derived status names its source (tasks.md, the Dependencies section, a commit, a build queue, a text match).
A heuristic is labelled as one. When a source is unavailable the page says so instead of guessing.

### IV. Plain Spec Kit first
Anything that works on a stock Spec Kit repo is on by default. Anything specific to one project's conventions (a
build queue, extra tags, a roadmap section) is an adapter, off unless `.specify/dash.json` turns it on.

### V. Stdlib only
Python 3.9+, standard library only, so `uvx speckit-dash` and a plain checkout both work with nothing to install.
Tests use `unittest` and build throwaway git repos in temp directories.

## Governance
Changes that break a principle need the owner's OK and an amendment here.

**Version**: 1.0.0 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
