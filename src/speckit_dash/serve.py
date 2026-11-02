"""Serve each repo's own page on 127.0.0.1 (/<repo>/), rebuilt on each load (GitHub and the build queue stay cached).
The root lists the repos."""

import http.server
import json
import threading
import time
from urllib.parse import unquote

from .page import build_data, entry_name, launcher_html, render, slug, summary

HOST = "127.0.0.1"  # local only, by design: there is no option to bind anything else


def make_server(entries_fn, port=8787, use_github=True, use_halo=True):
    lock = threading.Lock()
    built = {}  # slug -> (time, data)

    def entries():
        return {slug(entry_name(e)): e for e in entries_fn()}

    def current(key, entry, fresh=False):
        with lock:
            t, data = built.get(key, (0.0, None))
            if fresh or data is None or time.time() - t > 3:
                data = build_data([entry], use_github, use_halo, use_cache=not fresh, served=True)
                data["home"] = "/"
                built[key] = (time.time(), data)
            return data

    class Handler(http.server.BaseHTTPRequestHandler):
        def send(self, body, ctype, code=200, extra=()):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:")
            for k, v in extra:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path, _, query = self.path.partition("?")
            fresh = "fresh=1" in query
            parts = [unquote(p) for p in path.split("/") if p]
            repos = entries()
            if not parts:
                if len(repos) == 1:  # one repo: go straight to it
                    self.send(b"", "text/plain", 302, [("Location", "/" + next(iter(repos)) + "/")])
                    return
                rows = []
                for key, e in repos.items():
                    data = built.get(key, (0, None))[1]
                    rows.append((entry_name(e), e["path"], summary(data["repos"][0]) if data else None))
                body = launcher_html(rows, lambda n: "/" + slug(n) + "/", pending="open it to see its status")
                self.send(body.encode(), "text/html; charset=utf-8")
                return
            key = parts[0]
            if key not in repos or len(parts) > 2 or (len(parts) == 2 and parts[1] not in ("index.html", "data.json")):
                self.send_error(404)
                return
            if len(parts) == 1 and not path.endswith("/"):
                self.send(b"", "text/plain", 301, [("Location", f"/{key}/")])
                return
            data = current(key, repos[key], fresh)
            if len(parts) == 2 and parts[1] == "data.json":
                self.send(json.dumps(data).encode(), "application/json")
            else:
                self.send(render(data).encode(), "text/html; charset=utf-8")

        def log_message(self, fmt, *args):
            pass

    return http.server.ThreadingHTTPServer((HOST, port), Handler)


def serve(entries_fn, port=8787, use_github=True, use_halo=True):
    httpd = make_server(entries_fn, port, use_github, use_halo)
    print(f"speckit-dash on http://{HOST}:{port}/  (each repo at /<repo>/; Ctrl-C to stop; ?fresh=1 skips the cache)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
