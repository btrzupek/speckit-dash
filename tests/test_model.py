"""End to end on throwaway git repos: statuses, commits, releases, ideas, the page, init, discover, serve."""

import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

from speckit_dash import cli, config, serve
from speckit_dash.model import build_repo
from speckit_dash.page import build_data, render

TASKS = """# Tasks: 001 Albums

## Phase 1

- [x] 001-T001 *(architect)* spec and plan.
- [ ] 001-T002 *(agent: web)* the album page.
- [ ] 001-T003 the album API.
- [ ] 001-T004 *(waiting on the designer)* the album art.
- [ ] ~~001-T005~~ *(split)*: too big; split into T005a-T005b.
- [x] 001-T005a first half.
- [ ] 001-T005b second half.
- [ ] 001-T006 photo sharing.

## Dependencies

T003 needs T002. T006 needs T005.
"""


def sh(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_AUTHOR_DATE="2026-01-01T00:00:00", GIT_COMMITTER_DATE="2026-01-01T00:00:00")
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, env=env)


def commit(repo, msg):
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "--allow-empty", "-m", msg)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = {k: os.environ.get(k) for k in ("SPECKIT_DASH_CONFIG", "SPECKIT_DASH_CACHE")}
        os.environ["SPECKIT_DASH_CONFIG"] = str(root / "cfg")
        os.environ["SPECKIT_DASH_CACHE"] = str(root / "cache")
        self.repo = root / "projects" / "albums"
        r = self.repo
        (r / ".specify").mkdir(parents=True)
        (r / "specs/001-albums").mkdir(parents=True)
        (r / "specs/001-albums/spec.md").write_text("# Feature Specification: Albums\n\n**Status**: Building\n")
        (r / "specs/001-albums/tasks.md").write_text(TASKS)
        (r / "specs/002-tags").mkdir()
        (r / "specs/002-tags/spec.md").write_text("# Feature Specification: Tags\n\n**Status**: Draft\n")
        (r / "docs/releases").mkdir(parents=True)
        (r / "docs/ROADMAP.md").write_text("# Roadmap\n\n## Next\n\n- Search across albums\n- Fix 001-T002\n\n## Later\n\n- Video\n")
        (r / "app.py").write_text("x = 1  # TODO: config file\n")
        sh(r, "git", "init", "-q", "-b", "main")
        commit(r, "001: spec and plan")
        commit(r, "001-T005a: first half")
        (r / "docs/releases/v0.1.0.md").write_text("# 0.1.0\n\n- **Spec 001:** albums\n")
        commit(r, "release notes")
        sh(r, "git", "tag", "-a", "v0.1.0", "-m", "0.1.0")
        commit(r, "001-T002: the album page, first cut")
        commit(r, "Notes: 001-T003 still to do")
        sh(r, "git", "checkout", "-q", "-b", "idea/003")
        (r / "specs/003-sharing").mkdir()
        (r / "specs/003-sharing/spec.md").write_text("# Feature Specification: Sharing\n\n**Status**: Draft\n")
        commit(r, "003: spec")
        sh(r, "git", "checkout", "-q", "main")
        sh(r, "git", "branch", "agent/001-T003")
        (r / ".specify/assessments/offline").mkdir(parents=True)
        (r / ".specify/assessments/offline/intake.md").write_text("# Offline albums\n")
        (r / ".specify/assessments/dead").mkdir(parents=True)
        (r / ".specify/assessments/dead/intake.md").write_text("# Dead idea\n")
        (r / ".specify/assessments/dead/decide.md").write_text("**Verdict**: kill\n")

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def build(self, **cfg):
        cfg.setdefault("ideas", {"docs": [{"path": "docs/ROADMAP.md", "section": "Next"}]})
        return build_repo(self.repo, cfg, use_github=False, use_halo=False)


class TestModel(Base):
    def test_statuses(self):
        r = self.build()
        by = {t["id"]: t for t in r["tasks"]}
        self.assertEqual(by["001-T001"]["status"], "closed")
        self.assertEqual(by["001-T002"]["status"], "in progress")      # a commit leads with its id
        self.assertEqual(by["001-T002"]["status_source"], "commits (heuristic)")
        self.assertEqual(by["001-T003"]["status"], "waiting")          # needs T002; a mention isn't work
        self.assertEqual(by["001-T004"]["status"], "blocked")
        self.assertEqual(by["001-T004"]["status_source"], "text match (heuristic)")
        self.assertEqual(by["001-T005"]["status"], "split")
        self.assertEqual(by["001-T005"]["split_into"], ["001-T005a", "001-T005b"])
        self.assertEqual(by["001-T006"]["deps"], ["001-T005a", "001-T005b"])  # a split parent means its children
        self.assertEqual(by["001-T006"]["status_detail"], "waiting on 001-T005b")
        self.assertEqual(by["001-T002"]["assignee"], "agent: web")
        self.assertEqual([l["label"] for l in by["001-T003"]["links"]], ["agent/001-T003"])

    def test_queue_wins_for_open_tasks(self):
        from speckit_dash import halo
        orig = halo.fetch
        halo.fetch = lambda cfg, use_cache=True: {"status": "ok", "tasks": {
            "001-T006": {"state": "running", "attempt": 1}, "001-T001": {"state": "running"}}}
        try:
            r = build_repo(self.repo, {"halo": {"project": "albums"}}, use_github=False, use_halo=True)
        finally:
            halo.fetch = orig
        by = {t["id"]: t for t in r["tasks"]}
        self.assertEqual((by["001-T006"]["status"], by["001-T006"]["status_source"]), ("in progress", "build queue"))
        self.assertEqual(by["001-T001"]["status"], "closed")  # tasks.md's tick wins

    def test_releases(self):
        r = self.build()
        rel = {x["tag"]: x for x in r["releases"]}
        self.assertEqual(rel["v0.1.0"]["tasks"], ["001-T005a"])
        self.assertEqual(rel["v0.1.0"]["specs_in_notes"], ["001-albums"])
        self.assertEqual(rel[None]["tasks"], ["001-T002", "001-T003"])
        by = {t["id"]: t for t in r["tasks"]}
        self.assertEqual(by["001-T005a"]["release"], "v0.1.0")
        self.assertTrue(by["001-T002"]["unreleased"])
        self.assertEqual(r["features"][0]["releases"], ["v0.1.0"])

    def test_ideas(self):
        r = self.build()
        got = {(i["kind"], i["title"]) for i in r["ideas"]}
        self.assertIn(("spec, no tasks", "Tags"), got)
        self.assertIn(("unmerged spec", "003-sharing: Sharing"), got)
        self.assertIn(("assessment", "Offline albums"), got)
        self.assertNotIn(("assessment", "Dead idea"), got)  # killed at decide
        self.assertIn(("roadmap", "Search across albums"), got)
        self.assertNotIn(("roadmap", "Video"), got)
        self.assertIn(("todo", "x = 1  # TODO: config file"), got)
        fix = next(i for i in r["ideas"] if i["title"] == "Fix 001-T002")
        self.assertEqual(fix["refs"], ["001-T002"])

    def test_stock_repo_without_config(self):
        r = build_repo(self.repo, use_github=False, use_halo=False)
        self.assertEqual(r["name"], "albums")
        self.assertEqual(r["sources"]["github"], "off")
        self.assertEqual(len(r["tasks"]), 8)

    def test_prompt_templates_reach_the_page(self):
        r = self.build(prompts={"task": "do {id}"})
        self.assertEqual(r["prompts"], {"task": "do {id}"})
        html = render(build_data([{"path": str(self.repo)}], use_github=False, use_halo=False))
        self.assertIn("function taskPrompt", html)
        self.assertIn("function showPrompt", html)

    def test_page_escapes(self):
        (self.repo / "specs/001-albums/tasks.md").write_text(TASKS.replace(
            "## Dependencies", "- [ ] 001-T009 </script><img src=x onerror=alert(1)>\n\n## Dependencies"))
        html = render(build_data([{"path": str(self.repo)}], use_github=False, use_halo=False))
        body = html.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("<", body)
        self.assertIn("\\u003c/script>", body)


class TestCli(Base):
    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            cli.main(list(argv))
        return out.getvalue()

    def test_init_writes_dash_json_and_registers(self):
        self.run_cli("init", str(self.repo), "--roadmap", "docs/ROADMAP.md#Next", "--halo-project", "albums")
        cfg = json.loads((self.repo / ".specify/dash.json").read_text())
        self.assertEqual(cfg["release_notes"], "docs/releases/{tag}.md")
        self.assertEqual(cfg["halo"], {"project": "albums", "ssh": "halo-agents"})
        self.assertEqual(cfg["ideas"]["docs"], [{"path": "docs/ROADMAP.md", "section": "Next"}])
        self.assertEqual([r["path"] for r in config.load_registry()["repos"]], [str(self.repo.resolve())])
        self.run_cli("init", str(self.repo), "--roadmap", "docs/ROADMAP.md#Next")  # idempotent
        self.assertEqual(len(json.loads((self.repo / ".specify/dash.json").read_text())["ideas"]["docs"]), 1)

    def test_init_no_config_writes_nothing(self):
        self.run_cli("init", str(self.repo), "--no-config", "--name", "Albums")
        self.assertFalse((self.repo / ".specify/dash.json").exists())
        self.assertEqual(config.load_registry()["repos"][0]["config"]["name"], "Albums")

    def test_discover_skips_worktrees(self):
        wt = self.repo.parent / "albums-wt"
        sh(self.repo, "git", "worktree", "add", "-q", str(wt), "idea/003")
        found = cli.find_repos([str(self.repo.parent)], 3)
        self.assertEqual(found, [str(self.repo.resolve())])
        self.run_cli("discover", str(self.repo.parent), "--add")
        self.assertEqual(len(config.load_registry()["repos"]), 1)

    def test_build_writes_page(self):
        self.run_cli("init", str(self.repo))
        out = Path(self.tmp.name) / "page.html"
        text = self.run_cli("build", "--out", str(out), "--no-github", "--no-halo")
        self.assertIn("albums: 2 features, 8 tasks", text)
        self.assertIn('id="data"', out.read_text())

    def test_serve_is_local_only(self):
        self.assertEqual(serve.HOST, "127.0.0.1")
        httpd = serve.make_server(lambda: [{"path": str(self.repo)}], 0, use_github=False, use_halo=False)
        self.assertEqual(httpd.server_address[0], "127.0.0.1")
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            port = httpd.server_address[1]
            data = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/data.json").read())
            self.assertTrue(data["served"])
            page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
            self.assertIn("Spec Kit status", page)
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
