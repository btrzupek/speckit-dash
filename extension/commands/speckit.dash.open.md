---
description: "Build the status page for this repo (or every registered repo) and open it"
---

# Status page

Build the speckit-dash page and open it. The tool is read-only: it reads `specs/*/tasks.md`, `spec.md`, git
history and tags, and (when signed in) `gh issue list` / `gh pr list`. It never writes to GitHub or the repo.

## User Input

```text
$ARGUMENTS
```

Arguments may be `serve` (a live page on 127.0.0.1), `all` (every registered repo, the default once more than one is
registered) or `here` (only this repo).

## Steps

1. Find the runner, first match wins:
   - `speckit-dash` on PATH;
   - `uvx --from git+https://github.com/btrzupek/speckit-dash speckit-dash` when `uv` is installed;
   - otherwise tell the user to install it (`pipx install speckit-dash` or the `uvx` line above) and stop.
2. If `.specify/dash.json` does not exist, run `__SPECKIT_COMMAND_DASH_INIT__` first (or `<runner> init .`).
3. Run, from the repo root:
   - `here`: `<runner> open --repo .`
   - `serve`: `<runner> serve` in the background, then give the user `http://127.0.0.1:8787/`
   - otherwise: `<runner> open`
4. Report the one-line summary per repo that the command prints (features, tasks, open tasks, ideas, and whether
   GitHub and any build queue were read). Do not paste the page's content.
