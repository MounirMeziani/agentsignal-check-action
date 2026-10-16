import json, os, sys, unittest
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from render_comment import render, MARKER

def load(n): return json.load(open(os.path.join(HERE, "samples", n)))

class T(unittest.TestCase):
    def test_naive_lists_fails_with_fix_links(self):
        rep = load("naive.json"); md = render(rep, target="fixtures.naive_graph:build")
        fails = [r["detector"] for r in rep["results"] if r["status"] == "FAIL"]
        self.assertTrue(fails)
        self.assertTrue(md.startswith(MARKER)); self.assertIn("FAIL", md.splitlines()[1])
        for d in fails: self.assertIn(f"`{d}`", md)
        self.assertIn("/templates/langgraph-idempotent-approval/", md)
        self.assertIn("langgraph 1.2.15", md)
    def test_idem_pass_no_table(self):
        md = render(load("idem.json"))
        self.assertIn("PASS", md); self.assertNotIn("Failing detector", md)
    def test_server_fix_links_and_run_id_win(self):
        up = {"run_id": "run_x", "fix_links": [{"detector": "baseline", "url": "https://tryagentsignal.com/fix/abc"}]}
        md = render(load("naive.json"), up)
        self.assertIn("https://tryagentsignal.com/fix/abc", md); self.assertIn("`run_x`", md)
    def test_pipes_escaped(self):
        md = render({"framework": "langgraph", "results": [{"detector": "baseline", "status": "FAIL", "detail": "a|b"}]})
        self.assertIn("a/b", md)

if __name__ == "__main__": unittest.main()
