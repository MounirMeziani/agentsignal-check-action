#!/usr/bin/env python3
"""Create or update the single sticky agentsignal PR comment. Stdlib only.

env: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, GITHUB_API_URL (optional)
     AS_COMMENT  auto | always | never  (legacy: true -> auto, false -> never)
     AS_RESULT   pass | fail
     AS_PRO      non-empty when a Signal Pro api-key is set
usage: post_comment.py COMMENT.md

auto (default):
  FAIL + Pro key  -> create or update the comment
  FAIL, no key    -> no new comment (job summary only); an existing comment is updated
  PASS            -> update an existing comment to passing; never create one
always: create or update on FAIL and PASS, with or without a key.
never:  do nothing.
The comment is matched by MARKER and is never deleted.
"""
import json, os, sys, urllib.request
from render_comment import MARKER


def api(method, url, token, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "agentsignal-check-action"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def mode():
    m = (os.environ.get("AS_COMMENT") or "auto").strip().lower()
    return {"true": "auto", "false": "never", "": "auto"}.get(m, m if m in ("auto", "always", "never") else "auto")


def find(base, repo, pr, token):
    for page in range(1, 21):
        cs = api("GET", f"{base}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}", token)
        if not cs:
            return None
        hit = next((c for c in cs if MARKER in (c.get("body") or "")), None)
        if hit:
            return hit
    return None


def main(path):
    m = mode()
    if m == "never":
        print("agentsignal-action: comment=never; skipping PR comment")
        return 0
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event and event != "pull_request":
        print(f"agentsignal-action: {event} run; skipping PR comment")
        return 0
    token, repo, pr = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY"), os.environ.get("PR_NUMBER")
    if not (token and repo and pr):
        print("agentsignal-action: not a pull_request run or no token; skipping PR comment")
        return 0
    failed = (os.environ.get("AS_RESULT") or "").lower() == "fail"
    pro = bool(os.environ.get("AS_PRO"))
    may_create = m == "always" or (failed and pro)
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    body = open(path).read()
    existing = find(base, repo, pr, token)
    if existing:
        api("PATCH", f"{base}/repos/{repo}/issues/comments/{existing['id']}", token, {"body": body})
        print(f"agentsignal-action: updated comment {existing['id']}")
    elif may_create:
        c = api("POST", f"{base}/repos/{repo}/issues/{pr}/comments", token, {"body": body})
        print(f"agentsignal-action: created comment {c.get('id')}")
    else:
        why = "PASS with no earlier comment" if not failed else "no Signal Pro key (set comment: always to comment anyway)"
        print(f"agentsignal-action: no PR comment ({why}); see the job summary")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1]))
    except Exception as e:  # never fail the job over the comment
        print(f"::warning::agentsignal-action: could not post PR comment: {e}")
        sys.exit(0)
