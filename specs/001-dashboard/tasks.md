# Tasks: 001 A status dashboard for Spec Kit repos

**Input**: spec.md, plan.md

## Phase 1: Setup

- [x] 001-T001 *(architect)* spec.md, plan.md, constitution and this file (2026-11-02).
- [x] 001-T002 Package skeleton: `pyproject.toml`, `src/speckit_dash/__init__.py`, `__main__.py`, README, LICENSE.
  **Owns**: `pyproject.toml`, `src/speckit_dash/__init__.py`, `src/speckit_dash/__main__.py`, `README.md`

## Phase 2: US1 Every task (P1)

- [x] 001-T003 tasks.md and spec.md parser with the Dependencies section (FR-001), tests on halo-agents' formats.
  **Owns**: `src/speckit_dash/tasks.py`, `tests/test_tasks.py`
- [x] 001-T004 git data: commits naming tasks, tags and releases, branches (FR-003, FR-004).
  **Owns**: `src/speckit_dash/gitdata.py`, `tests/test_gitdata.py`
- [x] 001-T005 The model and statuses (FR-002, FR-005), the GitHub and halo adapters (FR-007, FR-008).
  **Owns**: `src/speckit_dash/model.py`, `github.py`, `halo.py`, `tests/test_model.py`
- [x] 001-T006 The page (FR-009): tasks view with the closed toggle, features, filters.
  **Owns**: `src/speckit_dash/page.py`, `src/speckit_dash/page.html`

## Phase 3: US2 Ideas (P1)

- [x] 001-T007 Idea sources (FR-006) and the Ideas view.
  **Owns**: `src/speckit_dash/ideas.py`, `tests/test_ideas.py`

## Phase 4: US3 Releases (P2)

- [x] 001-T008 The Releases view from T004's data.

## Phase 5: US4 Every repo, US5 Live

- [x] 001-T009 CLI and registry: init, discover, list, remove, build, serve, open (FR-010, FR-011).
  **Owns**: `src/speckit_dash/cli.py`, `config.py`, `serve.py`, `tests/test_cli.py`
- [x] 001-T010 The Spec Kit extension: `extension/extension.yml`, `/speckit.dash` and `/speckit.dash.init`.
  **Owns**: `extension/`

## Phase 6: Live (architect)

- [x] 001-T011 *(architect, live)* Register halo-agents with the halo adapter; check SC-001..SC-005 on it, SC-006
  on a fresh `specify init` repo.
  *2026-11-02:* halo-agents registered (settings in the registry until its `.specify/dash.json` merges).
  SC-001: 434 checkbox lines, 434 unique tasks on the page. SC-002: 039-T004 open (T002, T005, T006 closed),
  004-T011 blocked ("waiting on the second box, 026-T035"), 039-T003 split into T003a-T003c, 039-T002 closed and
  unreleased with 4 commits. SC-003: 041 and 042 were merged to main during the build, so they show as "spec, no
  tasks" with 038 (the branch path is covered by tests). SC-004: v0.17.0 has 033-T009 and 037-T002, 037 from its
  notes. SC-005: about 2.5 s with GitHub and the build queue cached. SC-006: a fresh `specify init` repo builds with
  no dash.json, and `specify extension add --dev extension` installs `/speckit-dash-open` and `/speckit-dash-init`.
  Also built once each against six other local Spec Kit repos (up to 1683 tasks each); every count matched its
  checkbox count.

## Phase 7: Follow-ups (owner, 2026-11-02)

- [x] 001-T012 FR-012: the copy-prompt button on tasks and ideas, `prompts` templates, the dialog fallback.
  **Owns**: `src/speckit_dash/page.html`, `model.py` (the `prompts` field), `tests/test_model.py`
- [x] 001-T013 README: what the tool and the extension each are, and a from-zero walkthrough for a new repo.
- [x] 001-T014 *(architect)* Review for anything work-related before publishing (none found; other local repo names
  dropped from T011's notes), then publish to github.com/btrzupek/speckit-dash (public, owner's OK).

## Dependencies

T003, T004 → T005 → T006 → T007, T008. T002 → T009 → T010. T006, T009 → T011.
