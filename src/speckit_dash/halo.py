"""The halo adapter: a halo-agents build queue, read with `halo-agent status <project>` over ssh. Read only."""

import json
import shlex
import subprocess

from . import config
from .tasks import feature_number, norm

TTL = 60
ACTIVE = {"running", "verifying", "reviewing", "ready_to_merge", "integrating"}
QUEUED = {"pending", "blocked", "waiting", "queued"}


def fetch(cfg, use_cache=True):
    """{"status": ..., "tasks": {task id: {state, attempt, minutes, title, error}}}"""
    if not cfg or not cfg.get("project"):
        return {"status": "off", "tasks": {}}
    host = cfg.get("ssh") or "halo-agents"
    agent = cfg.get("agent") or "~/halo-agents/bin/halo-agent"
    key = f"halo-{host}-{cfg['project']}.json"
    if use_cache:
        cached = config.read_cache(key, TTL)
        if cached:
            return cached
    cmd = f"{agent} status {shlex.quote(cfg['project'])}"
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, cmd],
                           capture_output=True, text=True, timeout=15)
        if r.returncode:
            raise RuntimeError((r.stderr or r.stdout).strip()[-200:] or f"exit {r.returncode}")
        raw = json.loads(r.stdout)
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        return {"status": f"error: {e}", "tasks": {}}
    tasks = {}
    for t in raw.get("tasks", []):
        tid = norm(t.get("id", ""), feature_number(t.get("feature", "")))
        tasks[tid] = {k: t.get(k) for k in ("state", "attempt", "minutes", "title", "error")}
    data = {"status": "ok", "tasks": tasks}
    config.write_cache(key, data)
    return data
