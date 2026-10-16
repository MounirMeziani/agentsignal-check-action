#!/usr/bin/env python3
"""Create or update the single agentsignal PR comment. Stdlib only.

env: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, GITHUB_API_URL (optional)
usage: post_comment.py COMMENT.md
"""
import json, os, sys, urllib.request
from render_comment import MARKER


def api(method, url, token, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "agentsignal-check-action"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def main(path):
    token, repo, pr = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY"), os.environ.get("PR_NUMBER")
    if not (token and repo and pr):
        print("agentsignal-action: not a pull_request run or no token; skipping PR comment")
        return 0
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    body = open(path).read()
    existing, page = None, 1
    while existing is None and page <= 20:
        cs = api("GET", f"{base}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}", token)
        if not cs:
            break
        existing = next((c for c in cs if MARKER in (c.get("body") or "")), None)
        page += 1
    if existing:
        api("PATCH", f"{base}/repos/{repo}/issues/comments/{existing['id']}", token, {"body": body})
        print(f"agentsignal-action: updated comment {existing['id']}")
    else:
        c = api("POST", f"{base}/repos/{repo}/issues/{pr}/comments", token, {"body": body})
        print(f"agentsignal-action: created comment {c.get('id')}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1]))
    except Exception as e:  # never fail the job over the comment
        print(f"::warning::agentsignal-action: could not post PR comment: {e}")
        sys.exit(0)
