# Feature Specification: 001 A status dashboard for Spec Kit repos

**Feature Branch**: `001-dashboard`
**Created**: 2026-11-02
**Status**: Building (owner, 2026-11-02: "Static + optional --serve"; "I want this reusable by anyone"; "Hybrid,
but make the new repo now")
**Input**: the owner wants one page that shows where every Spec Kit repo stands: every task, ideas that aren't specs
yet, and which specs and tasks went into each release. First used on halo-agents (features 001-042).

## Why

Spec Kit keeps a feature's state in `specs/NNN-*/tasks.md`, but there is no view across features, let alone across
repos. With 40 features in one repo the owner reads NORTH-STAR and greps tasks.md files to know what's open, what's
blocked and what shipped. Spec Kit has no ideas store either, so ideas sit in roadmap docs, audit docs, unmerged
spec branches and issues.

## User Scenarios

### US1 (P1) Every task, open by default
The owner opens the page and sees every open task across features, grouped by feature, each with its summary, its
status, its dependencies (and their status), its tags, and linked issues, PRs and branches. A toggle shows closed
and split tasks. Expanding a task shows its notes, what it owns, and the commits that name it.

**Acceptance**: on halo-agents, 039-T004 shows as open (or waiting on dependencies, none of which are open, so
open); 004-T011 shows as blocked with "waiting on the second box" as the reason; 039-T003 shows as split into
T003a-T003c; 039-T002 shows closed with its commits and the release that contains them (none yet: unreleased).

### US2 (P1) Ideas that aren't specs yet
A second view lists likely next specs, each with where it lives: specs on branches not merged to main (041, 042
today), specs on main with no tasks.md or a backlog/draft status (038), Spec Kit `assess` ideas under
`.specify/assessments/`, items from configured roadmap sections (NORTH-STAR's "Open work"), configured docs
(audit docs), open GitHub issues that name no task, and TODO/FIXME lines in code.

### US3 (P2) Releases
A third view lists releases newest first (git tags, plus "Unreleased" since the last tag): the specs each one
shipped (from its release notes when present, and from commits) and the tasks whose commits it contains.

### US4 (P2) Every repo
`speckit-dash init` in a repo registers it (in `~/.config/speckit-dash/repos.json`) and writes `.specify/dash.json`
with its settings. `speckit-dash discover` finds Spec Kit repos under given folders and offers to add them. The page
has a repo picker with "All repos". A Spec Kit extension (`specify extension add`) gives the same `init` and a
`/speckit.dash` command, the Spec Kit way.

### US5 (P3) Live
`speckit-dash serve` serves the page on 127.0.0.1 and rebuilds it on reload, so it is always current. A static build
(`speckit-dash build`) writes one self-contained HTML file.

## Requirements

- **FR-001** Parse every `specs/NNN-*/tasks.md`: checkbox lines with or without a feature prefix (`T001`,
  `039-T002`, `E003`, `T003a`), `~~struck~~` ids, `[P]` and `[USn]` markers, the first `*( … )*` tag, `**Owns**`,
  indented notes, the phase heading, and the Dependencies section (arrow chains `A, B → C`, and sentences
  "X needs Y", "X after Y", "X depends on Y", "X waits for Y"), plus inline "after T003a".
- **FR-002** Status per task, first match wins, with its source shown: split (struck), closed (`[x]`), in progress
  or queued (a configured build queue says so), blocked (text match against configurable patterns such as
  "waiting on", "blocked", "on hold"; labelled a heuristic), waiting (a dependency is open), in progress (a commit
  names the task while it is unchecked; labelled), open.
- **FR-003** Links per task: GitHub issues and PRs whose title or branch names the task id; local branches whose
  name contains the id.
- **FR-004** Releases from tags reachable from the main branch; the first tag containing each commit; specs per
  release from release notes (`release_notes` path pattern, "Spec NNN" or `NNN-slug`) and from commit ids.
- **FR-005** Features: title (spec.md H1), the Status line verbatim, which artifacts exist, task counts, releases.
- **FR-006** Ideas from the sources in US2; each names its source and location.
- **FR-007** GitHub only through `gh` read commands, only when the origin is on github.com and `gh` is signed in;
  cached 10 minutes; a failure is shown, never fatal.
- **FR-008** The `halo` adapter: when `dash.json` has `"halo": {"project": …, "ssh": …}`, read the build queue with
  `ssh <host> ~/halo-agents/bin/halo-agent status <project>` (read only, 15 s timeout, cached 60 s).
- **FR-009** One self-contained HTML file, no network requests, light and dark, usable at phone width; all repo text
  rendered as text, never as HTML.
- **FR-010** `serve` binds 127.0.0.1 only.
- **FR-011** Nothing written to any repo except `.specify/dash.json` by `init`.
- **FR-012** (owner, 2026-11-02: "a copy button where I can grab a prompt to tell the agent to begin work on whatever
  item I clicked on") Every open task and every idea has a copy-prompt button. A task's prompt names the repo, the
  id, summary, status, dependencies with their status, Owns, and where its full entry is, and says to tick it and
  commit with its id. A spec with no tasks gets "plan and break it down"; other ideas get "/speckit-specify". Templates
  per repo in `dash.json` `prompts`. When the clipboard is blocked, the prompt opens selected in a dialog.

## Success Criteria

- **SC-001** On halo-agents, every checkbox line in every tasks.md appears exactly once on the page.
- **SC-002** The US1 acceptance cases hold.
- **SC-003** 041 and 042 appear as ideas from their branches; 038 appears as a spec with no tasks.
- **SC-004** v0.17.0 lists 033-T009 and 037-T002 among its tasks, and its specs from docs/releases/v0.17.0.md.
- **SC-005** A build of halo-agents takes under 10 s with GitHub and halo cached.
- **SC-006** A stock `specify init` repo with one feature builds with no dash.json.
