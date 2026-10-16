"""post_comment.py against a local mock GitHub API: create, update, PASS-after-FAIL, free path, never."""
import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
from render_comment import render, MARKER


class MockGitHub:
    def __init__(self, preexisting=None):
        self.store, self.log = dict(preexisting or {}), []
        me = self
        class H(BaseHTTPRequestHandler):
            def _send(self, o, code=200):
                b = json.dumps(o).encode(); self.send_response(code)
                self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            def _body(self): return json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            def do_GET(self):
                me.log.append("GET")
                self._send(([{"id": 99, "body": "unrelated"}] + list(me.store.values())) if self.path.endswith("&page=1") else [])
            def do_POST(self):
                me.log.append("POST"); assert self.path == "/repos/o/r/issues/7/comments"
                assert self.headers["Authorization"] == "Bearer dummy"
                me.store[1] = {"id": 1, "body": self._body()["body"]}; self._send(me.store[1], 201)
            def do_PATCH(self):
                cid = int(self.path.rsplit("/", 1)[1]); me.log.append(f"PATCH:{cid}")
                me.store[cid]["body"] = self._body()["body"]; self._send(me.store[cid])
            def do_DELETE(self):
                me.log.append("DELETE"); self._send({})
            def log_message(self, *a): pass
        self.s = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.s.serve_forever, daemon=True).start()

    def run(self, sample, result, mode="auto", pro=True):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(render(json.load(open(os.path.join(HERE, "samples", sample)))))
        env = dict(os.environ, GITHUB_TOKEN="dummy", GITHUB_REPOSITORY="o/r", PR_NUMBER="7",
                   GITHUB_API_URL=f"http://127.0.0.1:{self.s.server_port}", AS_COMMENT=mode, AS_RESULT=result,
                   AS_PRO="1" if pro else "")
        return subprocess.run([sys.executable, "post_comment.py", f.name], env=env, cwd=SCRIPTS,
                              check=True, capture_output=True, text=True).stdout

    def close(self): self.s.shutdown(); self.s.server_close()


class T(unittest.TestCase):
    def setUp(self): self.gh = MockGitHub()
    def tearDown(self): self.gh.close()

    def test_fail_pro_creates(self):
        self.gh.run("naive.json", "fail")
        self.assertEqual(self.gh.log, ["GET", "GET", "POST"])
        b = self.gh.store[1]["body"]
        self.assertTrue(b.startswith(MARKER)); self.assertIn("FAIL", b)
        self.assertIn("https://tryagentsignal.com/pro/", b); self.assertIn("[$79 Fix](https://tryagentsignal.com/fix/)", b)

    def test_second_fail_updates_same_comment(self):
        self.gh.run("naive.json", "fail"); self.gh.run("naive.json", "fail")
        self.assertEqual(self.gh.log, ["GET", "GET", "POST", "GET", "PATCH:1"])
        self.assertEqual(len([c for c in self.gh.store.values() if MARKER in c["body"]]), 1)

    def test_pass_after_fail_updates_not_deletes(self):
        self.gh.run("naive.json", "fail"); self.gh.run("idem.json", "pass")
        self.assertEqual(self.gh.log, ["GET", "GET", "POST", "GET", "PATCH:1"])
        self.assertNotIn("DELETE", self.gh.log)
        self.assertIn("PASS", self.gh.store[1]["body"].splitlines()[1])

    def test_pass_without_earlier_comment_is_silent(self):
        self.gh.run("idem.json", "pass")
        self.assertNotIn("POST", self.gh.log); self.assertEqual(self.gh.store, {})

    def test_free_fail_auto_is_silent(self):
        out = self.gh.run("naive.json", "fail", pro=False)
        self.assertNotIn("POST", self.gh.log); self.assertIn("no Signal Pro key", out)

    def test_free_fail_always_comments(self):
        self.gh.run("naive.json", "fail", mode="always", pro=False)
        self.assertEqual(self.gh.log[-1], "POST")

    def test_free_updates_existing(self):
        self.gh.store[5] = {"id": 5, "body": MARKER + "\nold"}
        self.gh.run("idem.json", "pass", pro=False)
        self.assertEqual(self.gh.log, ["GET", "PATCH:5"])

    def test_never_and_legacy_false(self):
        for m in ("never", "false"):
            self.gh.run("naive.json", "fail", mode=m)
        self.assertEqual(self.gh.log, [])

    def test_legacy_true_is_auto(self):
        self.gh.run("naive.json", "fail", mode="true", pro=False)
        self.assertNotIn("POST", self.gh.log)


class Render(unittest.TestCase):
    def test_openai_agents_links(self):
        rep = {"framework": "openai-agents", "results": [{"detector": "approval.lost_on_restart", "status": "FAIL", "detail": "x"}]}
        self.assertIn("/templates/openai-agents-approval-resume/", render(rep))

    def test_server_links_win(self):
        rep = json.load(open(os.path.join(HERE, "samples", "naive.json")))
        b = render(rep, {"run_id": "r1", "fix_links": [{"detector": "baseline", "url": "https://tryagentsignal.com/x/"}]})
        self.assertIn("[fix](https://tryagentsignal.com/x/)", b)


if __name__ == "__main__": unittest.main()
