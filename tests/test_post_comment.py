"""post_comment.py against a local mock GitHub API: first run creates, second updates the same comment."""
import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
from render_comment import render

class T(unittest.TestCase):
    def test_create_then_update(self):
        store, log = {}, []
        class H(BaseHTTPRequestHandler):
            def _send(self, o):
                b = json.dumps(o).encode(); self.send_response(200)
                self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            def _body(self): return json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            def do_GET(self):
                log.append("GET"); self._send(([{"id": 99, "body": "unrelated"}] + list(store.values())) if self.path.endswith("&page=1") else [])
            def do_POST(self):
                log.append("POST"); store[1] = {"id": 1, "body": self._body()["body"]}; self._send(store[1])
            def do_PATCH(self):
                log.append("PATCH:" + self.path.rsplit("/", 1)[1]); store[1]["body"] = self._body()["body"]; self._send(store[1])
            def log_message(self, *a): pass
        s = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=s.serve_forever, daemon=True).start()
        env = dict(os.environ, GITHUB_TOKEN="dummy", GITHUB_REPOSITORY="o/r", PR_NUMBER="7",
                   GITHUB_API_URL=f"http://127.0.0.1:{s.server_port}")
        try:
            for name in ("naive.json", "idem.json"):
                with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
                    f.write(render(json.load(open(os.path.join(HERE, "samples", name)))))
                subprocess.run([sys.executable, "post_comment.py", f.name], env=env, cwd=SCRIPTS, check=True, capture_output=True)
        finally:
            s.shutdown(); s.server_close()
        self.assertEqual(log, ["GET", "GET", "POST", "GET", "PATCH:1"])
        self.assertIn("PASS", store[1]["body"].splitlines()[1])

if __name__ == "__main__": unittest.main()
