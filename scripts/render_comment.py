#!/usr/bin/env python3
"""Render the PR comment markdown from `agentsignal check --json` output.

usage: render_comment.py REPORT.json [UPLOAD_RESPONSE.json] [--target module:factory]
Stdlib only. The first line is a hidden marker used to find and update the comment.
"""
import json, sys

MARKER = "<!-- agentsignal-check-action -->"
SITE = "https://tryagentsignal.com"
FIX = {  # same mapping as agentsignal_check.report.FIX
    "baseline": f"{SITE}/templates/langgraph-idempotent-approval/",
    "double_execution.kill_resume": f"{SITE}/templates/langgraph-idempotent-approval/",
    "double_execution.kill_before_checkpoint": f"{SITE}/templates/langgraph-idempotent-approval/",
    "approval.lost_on_restart": f"{SITE}/templates/langgraph-human-in-the-loop/",
    "approval.replay": f"{SITE}/templates/langgraph-approval-ui/",
}


def _md(s):
    return str(s).replace("|", "/").replace("\n", " ")


def server_links(upload):
    """fix_links from POST /api/check/runs: list of str or {detector, url}."""
    out = {}
    for l in (upload or {}).get("fix_links") or []:
        if isinstance(l, dict) and l.get("url"):  # {detector, status, url}
            out.setdefault(l.get("detector", ""), l["url"])
        elif isinstance(l, str):
            out.setdefault("", l)
    return out


def render(report, upload=None, target=None):
    rs = report.get("results", [])
    fails = [r for r in rs if r.get("status") == "FAIL"]
    passed = sum(1 for r in rs if r.get("status") == "PASS")
    links = server_links(upload)
    head = "❌ **Agent Signal crash test: FAIL**" if fails else "✅ **Agent Signal crash test: PASS**"
    out = [MARKER, f"{head} ({passed}/{len(rs)} crash tests survived, framework `{report.get('framework', '?')}`)"]
    if target:
        out.append(f"\nTarget: `{target}`")
    if fails:
        out += ["", "| Failing detector | Detail | Fix |", "|---|---|---|"]
        for r in fails:
            d = r.get("detector", "")
            url = links.get(d) or FIX.get(d) or f"{SITE}/fix/"
            out.append(f"| `{_md(d)}` | {_md(r.get('detail', ''))} | [fix]({url}) |")
        if "" in links:
            out.append(f"\nMore fixes: {links['']}")
        out.append(f"\nWant it fixed for you? [$79 Fix]({SITE}/fix/)")
    else:
        out.append("\nNo double execution or lost approvals detected.")
    if upload and upload.get("run_id"):
        out.append(f"\nUploaded run: `{_md(upload['run_id'])}`")
    env = report.get("env") or {}
    pkgs = env.get("packages") if isinstance(env.get("packages"), dict) else {}
    if pkgs:
        out.append("\n<sub>" + ", ".join(f"{k} {v}" for k, v in pkgs.items()) + "</sub>")
    out.append(f"\n<sub>[agentsignal-check](https://github.com/MounirMeziani/agentsignal-check) · {SITE}</sub>")
    return "\n".join(out) + "\n"


def main(argv):
    target = None
    if "--target" in argv:
        i = argv.index("--target"); target = argv[i + 1]; del argv[i:i + 2]
    report = json.load(open(argv[0]))
    upload = None
    if len(argv) > 1:
        try:
            upload = json.load(open(argv[1]))
        except (OSError, ValueError):
            upload = None
    sys.stdout.write(render(report, upload, target))


if __name__ == "__main__":
    main(sys.argv[1:])
