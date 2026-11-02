"""Serve the page on 127.0.0.1, rebuilt on each load (GitHub and the build queue stay cached)."""

import http.server
import json
import threading
import time

from .page import build_data, render

HOST = "127.0.0.1"  # local only, by design: there is no option to bind anything else


def make_server(entries_fn, port=8787, use_github=True, use_halo=True):
    lock = threading.Lock()
    last = {"t": 0.0, "data": None}

    def current(fresh=False):
        with lock:
            if fresh or last["data"] is None or time.time() - last["t"] > 3:
                last["data"] = build_data(entries_fn(), use_github, use_halo, use_cache=not fresh, served=True)
                last["t"] = time.time()
            return last["data"]

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path, _, query = self.path.partition("?")
            fresh = "fresh=1" in query
            if path in ("/", "/index.html"):
                body, ctype = render(current(fresh)).encode(), "text/html; charset=utf-8"
            elif path == "/data.json":
                body, ctype = json.dumps(current(fresh)).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    return http.server.ThreadingHTTPServer((HOST, port), Handler)


def serve(entries_fn, port=8787, use_github=True, use_halo=True):
    httpd = make_server(entries_fn, port, use_github, use_halo)
    print(f"speckit-dash on http://{HOST}:{port}/  (Ctrl-C to stop; add ?fresh=1 to skip the GitHub cache)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
