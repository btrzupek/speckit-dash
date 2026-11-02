# Implementation Plan: 001 A status dashboard for Spec Kit repos

**Branch**: `001-dashboard` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

## Summary

A stdlib Python package, `speckit_dash`, with a CLI (`speckit-dash`) that reads registered repos into one JSON
model and writes it into a single self-contained HTML page. `serve` rebuilds per request on 127.0.0.1. A thin Spec
Kit extension in `extension/` registers a repo and runs the CLI from the agent.

## Technical Context

- Python 3.9+, stdlib only; `git` required, `gh` and `ssh` optional.
- Packaging: `pyproject.toml` (setuptools), console script `speckit-dash`; runnable as `python -m speckit_dash`.
- Tests: `unittest`, throwaway git repos in temp dirs; `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` pointed at temp dirs.
- Performance: one `git log` per repo, one `git for-each-ref`, one `git ls-tree` per local branch; gh and the build
  queue cached on disk.

## Layout

```
src/speckit_dash/
  cli.py        init, discover, list, remove, build, serve, open
  config.py     registry (~/.config/speckit-dash/repos.json), .specify/dash.json, defaults
  tasks.py      tasks.md and spec.md parsing, the Dependencies section
  gitdata.py    commits, tags, releases, branches, specs on unmerged branches
  github.py     gh issue/pr list, cached
  halo.py       the halo build-queue adapter
  ideas.py      idea sources
  model.py      one repo's model: features, tasks, statuses, links, releases, ideas
  page.py       the HTML page (template + embedded JSON)
  serve.py      127.0.0.1 server
  page.html     the page template (vanilla JS, inline CSS)
extension/      extension.yml, commands/, README.md
tests/
```

## Data model (data.json)

```
{generated, version, repos: [{name, path, main, github, sources: {github: ok|skipped|error: …, halo: …},
  features: [{id, slug, title, status_text, location, artifacts, counts, releases}],
  tasks: [{id, feature, title, notes, done, struck, split_into, tag, owns, deps, phase, status, status_source,
           status_detail, queue, commits, release, links, file, line}],
  releases: [{tag, date, specs, tasks, commits}], ideas: [{title, source, where, detail, url}]}]}
```

## Decisions

- Data embedded in the HTML as `<script type="application/json">` so a file:// page works without fetch.
- Statuses: `open`, `in progress`, `queued`, `waiting`, `blocked`, `closed`, `split`. Closed and split are hidden by
  default.
- Task ids are normalised to `NNN-Xn` with the feature's number when tasks.md omits the prefix.
- Commit matching uses the main branch's history only; release = the oldest tag (by creation date) containing a
  commit, computed from consecutive tag ranges.
- Unmerged specs: for each local branch, `git ls-tree` of `specs/`; a spec directory absent on main is an idea, read
  with `git show branch:specs/NNN-x/spec.md`.
- `dash.json` is JSON (stdlib); the Spec Kit extension's command runs `speckit-dash init`, which writes it.
