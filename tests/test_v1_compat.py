"""v1 users who never set `comment`: same outputs and exit behaviour as v1.0.1 (0291206)."""
import os, re, subprocess, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")

def block(text, start, end):
    return text[text.index(start):text.index(end)]

class T(unittest.TestCase):
    def setUp(self):
        self.new = open(os.path.join(ROOT, "action.yml")).read()
        r = subprocess.run(["git", "show", "0291206:action.yml"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode: self.skipTest("v1.0.1 base commit not available")
        self.old = r.stdout

    def test_outputs_unchanged(self):
        self.assertEqual(block(self.old, "outputs:", "runs:"), block(self.new, "outputs:", "runs:"))

    def test_check_upload_result_steps_unchanged(self):
        for start, end in (("- name: Run agentsignal check", "- name: Upload run"),
                           ("- name: Upload run", "- name: Comment on PR"),
                           ("- name: Result", "\x00")):
            o = self.old[self.old.index(start):] if end == "\x00" else block(self.old, start, end)
            n = self.new[self.new.index(start):] if end == "\x00" else block(self.new, start, end)
            self.assertEqual(o, n, start)

    def test_comment_step_never_fails_job(self):
        # post_comment.py swallows every error -> exit 0, so the job exit code is decided only by the Result step
        src = open(os.path.join(ROOT, "scripts", "post_comment.py")).read()
        self.assertIn("sys.exit(0)", src)
        self.assertNotRegex(src, re.compile(r"sys\.exit\([1-9]"))

    def test_comment_step_gated_to_pull_request(self):
        step = block(self.new, "- name: Comment on PR", "- name: Result")
        self.assertIn("github.event_name == 'pull_request'", step)

if __name__ == "__main__": unittest.main()
