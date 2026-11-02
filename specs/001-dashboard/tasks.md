# Tasks: 001 A status dashboard for Spec Kit repos

**Input**: spec.md, plan.md

## Phase 1: Setup

- [x] 001-T001 *(architect)* spec.md, plan.md, constitution and this file (2026-11-02).
- [ ] 001-T002 Package skeleton: `pyproject.toml`, `src/speckit_dash/__init__.py`, `__main__.py`, README, LICENSE.
  **Owns**: `pyproject.toml`, `src/speckit_dash/__init__.py`, `src/speckit_dash/__main__.py`, `README.md`

## Phase 2: US1 Every task (P1)

- [ ] 001-T003 tasks.md and spec.md parser with the Dependencies section (FR-001), tests on halo-agents' formats.
  **Owns**: `src/speckit_dash/tasks.py`, `tests/test_tasks.py`
- [ ] 001-T004 git data: commits naming tasks, tags and releases, branches (FR-003, FR-004).
  **Owns**: `src/speckit_dash/gitdata.py`, `tests/test_gitdata.py`
- [ ] 001-T005 The model and statuses (FR-002, FR-005), the GitHub and halo adapters (FR-007, FR-008).
  **Owns**: `src/speckit_dash/model.py`, `github.py`, `halo.py`, `tests/test_model.py`
- [ ] 001-T006 The page (FR-009): tasks view with the closed toggle, features, filters.
  **Owns**: `src/speckit_dash/page.py`, `src/speckit_dash/page.html`

## Phase 3: US2 Ideas (P1)

- [ ] 001-T007 Idea sources (FR-006) and the Ideas view.
  **Owns**: `src/speckit_dash/ideas.py`, `tests/test_ideas.py`

## Phase 4: US3 Releases (P2)

- [ ] 001-T008 The Releases view from T004's data.

## Phase 5: US4 Every repo, US5 Live

- [ ] 001-T009 CLI and registry: init, discover, list, remove, build, serve, open (FR-010, FR-011).
  **Owns**: `src/speckit_dash/cli.py`, `config.py`, `serve.py`, `tests/test_cli.py`
- [ ] 001-T010 The Spec Kit extension: `extension/extension.yml`, `/speckit.dash` and `/speckit.dash.init`.
  **Owns**: `extension/`

## Phase 6: Live (architect)

- [ ] 001-T011 *(architect, live)* Register halo-agents with the halo adapter; check SC-001..SC-005 on it, SC-006
  on a fresh `specify init` repo.

## Dependencies

T003, T004 → T005 → T006 → T007, T008. T002 → T009 → T010. T006, T009 → T011.
