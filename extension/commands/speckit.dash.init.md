---
description: "Register this repo with speckit-dash and write .specify/dash.json"
---

# Register this repo

Add this repo to the user's speckit-dash registry (`~/.config/speckit-dash/repos.json`) and write
`.specify/dash.json`, its settings for the status page.

## User Input

```text
$ARGUMENTS
```

## Steps

1. Find the runner as in `__SPECKIT_COMMAND_DASH_OPEN__` step 1.
2. Look for idea sources the page should read, and ask the user before adding any:
   - a roadmap or backlog doc with a list under a heading (e.g. `docs/ROADMAP.md` "Next"): `--roadmap 'PATH#Heading'`;
   - audit or ideas docs: `--ideas-glob 'docs/*AUDIT*.md'`.
   Specs on unmerged branches, specs without tasks, `.specify/assessments/`, open issues and TODOs are read by
   default and need nothing here.
3. Run `<runner> init . [--name NAME] [--roadmap ...] [--ideas-glob ...]`. Pass `--no-config` if the user doesn't
   want a file in the repo; the settings then live in the registry.
4. Show the user the resulting `.specify/dash.json` and suggest committing it, then offer `__SPECKIT_COMMAND_DASH_OPEN__`.
