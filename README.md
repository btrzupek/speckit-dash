# speckit-dash

A local status page for [Spec Kit](https://github.com/github/spec-kit) repos: every task with its status and
dependencies, ideas that aren't specs yet, and which specs and tasks went into each release. One page across all
your repos. Read only, local only, Python standard library only.

```bash
uv tool install --editable .          # or: pipx install .   (or run with: python -m speckit_dash, src on PYTHONPATH)
speckit-dash init ~/projects/my-repo  # register a repo, write its .specify/dash.json
speckit-dash discover                 # find Spec Kit repos under ~/projects, ~/work, ~/code …; --add registers them
speckit-dash open                     # build the page and open it (a single self-contained HTML file)
speckit-dash serve                    # or: a live page on http://127.0.0.1:8787/, rebuilt on each load
```

## What it shows

**Tasks**: every checkbox in every `specs/NNN-*/tasks.md`, open ones by default, with a toggle for closed. Each task
shows its summary, status, dependencies (each coloured by its own status; click to jump), tags, linked GitHub
issues and PRs, branches named after it, and the first release that contains a commit naming it. Expand a task for
its notes, **Owns**, and commits.

Status is derived, and the page always says from what:

| Status | Derived from |
|---|---|
| closed | `- [x]` |
| split | a `~~struck~~` id; its children are found in its notes (`split into T003a-T003c`) |
| in progress / queued | a build queue (the halo adapter), when configured |
| blocked | the task's tag or first line matches `waiting on`, `blocked`, `on hold`, … (a heuristic, labelled) |
| waiting | a dependency is still open (Dependencies section, `**Depends**:`, or `after T003a` in the tag) |
| in progress | a commit subject leads with the id (`039-T002: …`) while it's unchecked (a heuristic, labelled) |
| open | everything else |

**Ideas**: Spec Kit has no backlog store of its own, so the page gathers likely next specs from wherever they live:
specs on branches not merged to main, specs with no `tasks.md`, Spec Kit's `assess` extension
(`.specify/assessments/<slug>/`, killed ones left out), list items under a roadmap heading you name, ideas docs you
name (audits), open GitHub issues that name no task, and TODO/FIXME in code.

**Releases**: git tags newest first, plus "Unreleased": the specs named in each release's notes
(`release_notes`, e.g. `docs/releases/{tag}.md` or a `CHANGELOG.md`) and in commit subjects, and the tasks whose
commits each release contains. A commit counts for the first tag that contains it; pre-release tags get their own
ranges.

**Features**: one row per spec: state, progress, releases, and spec.md's Status line verbatim.

## Settings: `.specify/dash.json`

Everything is optional; a stock Spec Kit repo needs no file at all.

```json
{
  "name": "halo-agents",
  "release_notes": "docs/releases/{tag}.md",
  "ideas": {"docs": [{"path": "docs/NORTH-STAR.md", "section": "Open work"}, {"glob": "docs/*AUDIT*.md"}],
            "todos": true, "issues": true, "branches": true, "spec_only": true, "assessments": true},
  "blocked_patterns": ["\\bwaiting (?:on|for)\\b", "\\bblocked\\b"],
  "github": "owner/repo",
  "halo": {"project": "halo-agents", "ssh": "halo-agents"}
}
```

`speckit-dash init --no-config` keeps the settings in the registry (`~/.config/speckit-dash/repos.json`) instead,
for repos you'd rather not add a file to. Registry settings win over the repo's file.

## The Spec Kit extension

`extension/` installs `/speckit.dash.open` and `/speckit.dash.init` into a repo, the Spec Kit way, with optional
hooks that refresh the page after `/speckit-tasks` and `/speckit-implement`:

```bash
specify extension add --dev /path/to/speckit-dash/extension
```

## Read only, local only

- GitHub: `gh issue list` and `gh pr list` only, when the origin is on github.com and `gh` is signed in; cached ten
  minutes (`--fresh` or `?fresh=1` skips the cache). Nothing is ever written to GitHub.
- The halo adapter runs `halo-agent status <project>` over ssh (read only, 15 s timeout, cached a minute).
- `serve` binds 127.0.0.1 and has no option to bind anything else. The page makes no network requests (a CSP
  forbids them) and renders all repo text as text.
- The only files written: the page and cache (`~/.cache/speckit-dash/`), the registry, and `.specify/dash.json` by
  `init`.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Specs live in `specs/` (this repo is a Spec Kit project too).
