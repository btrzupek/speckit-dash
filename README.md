# speckit-dash

A local status page for [Spec Kit](https://github.com/github/spec-kit) repos. One page across all your repos shows:

- every task, with its status and dependencies;
- ideas that aren't specs yet;
- which specs and tasks went into each release;
- a **⧉ prompt** button on each open task and idea, which copies a prompt telling your coding agent to start on
  it.

Read only, local only, Python standard library only.

It's two things in one repo:

- **A command-line tool**, `speckit-dash`, which reads your repos and builds the page. This is where the work
  happens.
- **A Spec Kit extension** (`extension/`). It adds `/speckit-dash-open` and `/speckit-dash-init` to a repo, so your
  agent can register the repo and open the page, the Spec Kit way. It's optional; it calls the tool.

## Quick start: a brand-new repo, from zero

You need `git`, Python 3.9+, and [uv](https://docs.astral.sh/uv/). `gh` is optional; it adds issue and PR links.

**1. Install Spec Kit and speckit-dash** (once per machine)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # skip if you have uv
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
uv tool install git+https://github.com/btrzupek/speckit-dash
```

**2. Make the repo and set up Spec Kit in it**

```bash
mkdir my-app && cd my-app
git init
specify init --here --integration claude      # or copilot, gemini, codex … (`specify init --help`)
```

**3. Register it with the dashboard**

```bash
speckit-dash init
```

This writes `.specify/dash.json` (settings, all optional) and adds the repo to your list in
`~/.config/speckit-dash/repos.json`. Commit the file if you like.

**4. Write your first feature** in your coding agent:

```text
/speckit-specify  a photo album page where people can upload and sort pictures
/speckit-plan
/speckit-tasks
```

**5. Open the page**

```bash
speckit-dash open        # writes ~/.cache/speckit-dash/index.html and opens it
```

You'll see your tasks. Click **⧉ prompt** on the one you want, paste the prompt into your agent, and it starts on
that task. Tick tasks off in `tasks.md` as they're done, and commit with the task id first (`001-T003: …`). The page
then shows progress, links each task to its commits, and shows which release each one shipped in.

**6. (Optional) Add the Spec Kit extension**

```bash
git clone https://github.com/btrzupek/speckit-dash ~/src/speckit-dash
specify extension add --dev ~/src/speckit-dash/extension
```

Your agent now has `/speckit-dash-open` and `/speckit-dash-init`. The extension can also refresh the page after
`/speckit-tasks` and `/speckit-implement`; it asks first.

## Already have Spec Kit repos?

```bash
speckit-dash discover          # lists repos with .specify/ under ~/projects ~/work ~/code ~/src ~/dev ~/repos
speckit-dash discover --add    # registers all of them
speckit-dash init ~/code/one-repo --roadmap 'docs/ROADMAP.md#Next'   # or one at a time, with settings
speckit-dash open              # one page, with a repo picker and "All repos"
```

To keep a live page open instead, run `speckit-dash serve` and go to http://127.0.0.1:8787/. It rebuilds on every
reload. `speckit-dash list` shows what's registered, and `speckit-dash remove <name>` drops a repo.

No install? With the source checked out: `PYTHONPATH=src python3 -m speckit_dash open`.

## What it shows

**Tasks**: every checkbox in every `specs/NNN-*/tasks.md`, open ones by default, with a toggle for closed. Each task
shows:

- its summary, status and tags;
- its dependencies, each coloured by its own status (click one to jump to it);
- linked GitHub issues and PRs, and branches named after it;
- the first release that contains a commit naming it.

Expand a task for its notes, **Owns** and commits.

Status is derived, and the page always says from what:

| Status | Derived from |
|---|---|
| closed | `- [x]` |
| split | a `~~struck~~` id; its children are found in its notes (`split into T003a-T003c`) |
| in progress / queued | a build queue (the halo adapter, below), when configured |
| blocked | the task's tag or first line matches `waiting on`, `blocked`, `on hold`, … (a heuristic, labelled) |
| waiting | a dependency is still open (Dependencies section, `**Depends**:`, or `after T003a` in the tag) |
| in progress | a commit subject leads with the id (`039-T002: …`) while it's unchecked (a heuristic, labelled) |
| open | everything else |

**Ideas**: Spec Kit has no backlog of its own; an idea becomes a spec when `/speckit-specify` runs. So the page
gathers likely next specs from wherever they live:

- specs on branches not merged to main;
- specs with no `tasks.md` yet;
- Spec Kit's own `assess` extension (`.specify/assessments/<slug>/`, killed ones left out);
- list items under a roadmap heading you name;
- ideas docs you name, such as audits;
- open GitHub issues that name no task;
- TODO and FIXME in code.

**Releases**: git tags newest first, plus "Unreleased". For each one:

- the specs named in its release notes (`release_notes`, e.g. `docs/releases/{tag}.md` or a `CHANGELOG.md`) and in
  commit subjects;
- the tasks its commits name.

A commit counts for the first tag that contains it. Pre-release tags get their own ranges.

**Features**: one row per spec: state, progress, releases, and spec.md's Status line verbatim.

## The ⧉ prompt button

Every open task and every idea has one. It copies a ready-to-paste prompt for your coding agent:

- **A task:** "work on task X in this repo". It includes the task's summary, status, dependencies and what it owns,
  where to read its full entry, and to tick it and commit with its id when done.
- **A spec with no tasks:** plan and break it down (`/speckit-plan`, `/speckit-tasks`).
- **Any other idea:** turn it into a spec (`/speckit-specify`).

If the browser blocks the clipboard, the prompt opens in a box, already selected, so you can copy it by hand.

Make the prompts match your repo's workflow with templates in `.specify/dash.json`:

```json
{"prompts": {
  "task": "In {path}, do {id}: {title}. Deps: {deps}. Read {file}:{line} first; commit as \"{id}: …\".",
  "idea": "In {path}, spec this with /speckit-specify: {title} (from {where})"
}}
```

The placeholders:

- **Tasks:** `{path} {repo} {id} {feature} {title} {status} {detail} {deps} {owns} {file} {line} {tag} {notes}`.
- **Ideas:** `{path} {repo} {title} {where} {kind} {detail} {branches} {url}`.
- **A template for one kind of idea:** key it by that kind, e.g. `"spec, no tasks"` or `"unmerged spec"`.

## Settings: `.specify/dash.json`

Everything is optional. A stock Spec Kit repo needs no file at all.

```json
{
  "name": "my-app",
  "release_notes": "docs/releases/{tag}.md",
  "ideas": {"docs": [{"path": "docs/ROADMAP.md", "section": "Next"}, {"glob": "docs/*AUDIT*.md"}],
            "todos": true, "issues": true, "branches": true, "spec_only": true, "assessments": true},
  "blocked_patterns": ["\\bwaiting (?:on|for)\\b", "\\bblocked\\b"],
  "github": "owner/repo",
  "prompts": {"task": "…", "idea": "…"},
  "halo": {"project": "my-app", "ssh": "halo-agents"}
}
```

`speckit-dash init --no-config` keeps the settings in the registry instead, for repos you'd rather not add a file
to. Registry settings win over the repo's file.

`halo` is an adapter for a halo-agents build queue (local coding agents building Spec Kit tasks). It reads
`halo-agent status <project>` over ssh to show which tasks a local build agent is working on. Leave it out
otherwise.

## Read only, local only

- **GitHub:** only `gh issue list` and `gh pr list`, when the origin is on github.com and `gh` is signed in. Results
  are cached for ten minutes; `--fresh` or `?fresh=1` skips the cache. Nothing is ever written to GitHub.
- **The halo adapter:** runs `halo-agent status <project>` over ssh, read only, with a 15 s timeout, cached for a
  minute.
- **The page:** `serve` binds 127.0.0.1 and has no option to bind anything else. The page makes no network
  requests (a Content-Security-Policy forbids them), and all repo text is rendered as text.
- **Files it writes:** only the page and its cache (`~/.cache/speckit-dash/`), the registry, and
  `.specify/dash.json` (by `init`).

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

This repo is a Spec Kit project too: see `specs/`.

## License

MIT
