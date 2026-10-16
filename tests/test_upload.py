"""scripts/upload.py against a contract-validating mock of POST /api/check/runs/."""
import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, HERE); sys.path.insert(0, SCRIPTS)
import contract
from upload import build_body
KEY = "as_live_" + "T" * 43  # shape-valid dummy


def serve(forced=None):
    seen = []
    class H(BaseHTTPRequestHandler):
        def reply(self, code, obj, extra=None):
            b = json.dumps(obj).encode(); self.send_response(code)
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"])); body = json.loads(raw)
            errs = contract.validate_run(body)
            seen.append({"path": self.path, "body": body, "errors": errs})
            if forced: return self.reply(*forced)
            if not contract.bearer_key(self.headers.get("Authorization")): return self.reply(401, {"error": "invalid_key"})
            if errs: return self.reply(400, {"error": "invalid_body", "errors": errs})
            self.reply(201, {"run_id": "run_42", "fix_links": contract.fix_links(body["report"])})
        def log_message(self, *a): pass
    s = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_port}/api/check/runs/", seen


def run(url, key=KEY, sample="naive.json"):
    out = tempfile.mktemp(suffix=".json"); go = tempfile.mktemp()
    env = dict(os.environ, AGENTSIGNAL_API_KEY=key, AS_URL=url, GITHUB_REPOSITORY="acme/agent",
               GITHUB_SHA="0123456789abcdef0123456789abcdef01234567", GITHUB_OUTPUT=go)
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "upload.py"), os.path.join(HERE, "samples", sample), out],
                       env=env, capture_output=True, text=True)
    return p, out, (open(go).read() if os.path.exists(go) else "")


class T(unittest.TestCase):
    def test_real_samples_validate(self):
        for n in ("naive.json", "idem.json"):
            b = build_body(json.load(open(os.path.join(HERE, "samples", n))), "acme/agent", "abcdef1")
            self.assertEqual(contract.validate_run(b), [], n)
            self.assertEqual(b["version"], "1.2.15")

    def test_success(self):
        s, url, seen = serve()
        try: p, out, go = run(url)
        finally: s.shutdown(); s.server_close()
        self.assertEqual(p.returncode, 0); self.assertEqual(seen[0]["errors"], [])
        self.assertEqual(seen[0]["path"], "/api/check/runs/")
        b = seen[0]["body"]
        self.assertEqual((b["repo"], b["commit_sha"]), ("acme/agent", "0123456789abcdef0123456789abcdef01234567"))
        self.assertIn("baseline  FAIL  https://tryagentsignal.com/templates/langgraph-idempotent-approval/", p.stdout)
        self.assertIn("run_id=run_42", go)
        self.assertEqual(json.load(open(out))["fix_links"][0]["status"], "FAIL")
        self.assertNotIn(KEY, p.stdout + p.stderr)

    def test_errors_are_warnings(self):
        cases = [((401, {"error": "invalid_key"}), "invalid_key"), ((403, {"error": "pro_required"}), "pro_required"),
                 ((413, {"error": "payload_too_large"}), "payload_too_large"),
                 ((429, {"error": "rate_limited"}, {"Retry-After": "60"}), "retry after 60s"),
                 ((400, {"error": "invalid_body", "errors": ["repo must be \"owner/name\""]}), "invalid_body: repo")]
        for forced, needle in cases:
            s, url, _ = serve(forced)
            try: p, _, go = run(url)
            finally: s.shutdown(); s.server_close()
            self.assertEqual(p.returncode, 0); self.assertIn("::warning::", p.stdout); self.assertIn(needle, p.stdout)
            self.assertNotIn("run_id=", go)

    def test_bad_key_shape_401_and_network(self):
        s, url, _ = serve()
        try: p, _, _ = run(url, key="nope")
        finally: s.shutdown(); s.server_close()
        self.assertIn("invalid_key", p.stdout)
        p, _, _ = run("http://127.0.0.1:9/api/check/runs/")
        self.assertEqual(p.returncode, 0); self.assertIn("network error", p.stdout)

if __name__ == "__main__": unittest.main()
