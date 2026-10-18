#!/usr/bin/env python3
"""Render the PR comment markdown from `agentsignal check --json` output.

usage: render_comment.py REPORT.json [UPLOAD_RESPONSE.json] [--target module:factory]
Stdlib only. The first line is a hidden marker used to find and update the comment.
"""
import json, sys

MARKER = "<!-- agentsignal-check-action -->"
SITE = "https://tryagentsignal.com"
T = f"{SITE}/templates"
PRO = f"{SITE}/pro/"
FIX79 = f"{SITE}/fix/"
G = f"{SITE}/guides"
# Every FAIL links to a FREE page (never a Pro template). The double-execution fixes point at the
# free guides that show the bug and the idempotency-key fix in full.
FIX_URLS = {
    "langgraph": {
        "baseline": f"{G}/langgraph-interrupt-resume-twice/",
        "double_execution.kill_resume": f"{G}/langgraph-interrupt-resume-twice/",
        "double_execution.kill_before_checkpoint": f"{G}/langgraph-interrupt-resume-twice/",
        "approval.lost_on_restart": f"{T}/langgraph-human-in-the-loop/",
        "approval.replay": f"{T}/langgraph-approval-ui/",
    },
    "openai-agents": {
        "baseline": f"{G}/duplicate-tool-calls-after-resume/",
        "double_execution.kill_resume": f"{G}/duplicate-tool-calls-after-resume/",
        "double_execution.kill_before_checkpoint": f"{G}/duplicate-tool-calls-after-resume/",
        "approval.lost_on_restart": f"{T}/openai-agents-approval-resume/",
        "approval.replay": f"{G}/duplicate-tool-calls-after-resume/",
    },
}
# Pro-only template pages. A fix URL from the CLI report (v0.3.2) or the server that points at one
# of these is replaced with the free page for that detector.
PRO_PATHS = ("/templates/langgraph-idempotent-approval/", "/templates/openai-agents-idempotent-approval/")
FIX = FIX_URLS["langgraph"]


def fix_url(detector, framework=None):
    return FIX_URLS.get(framework, FIX).get(detector, f"{T}/")


def is_pro(url):
    return isinstance(url, str) and any(p in url for p in PRO_PATHS)


def free_url(url, detector, framework=None):
    """url if it is set and not a Pro page, else the free page for this detector."""
    return url if url and not is_pro(url) else fix_url(detector, framework)


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


def badge_footer(upload):
    """Footer from the upload response's additive badge{enabled,markdown,enable_url}.
    No upload / no badge / malformed -> no footer."""
    b = (upload or {}).get("badge") if isinstance(upload, dict) else None
    if not isinstance(b, dict):
        return None
    if b.get("enabled") is True:
        md = b.get("markdown")
        if isinstance(md, str) and md.strip():
            return " ".join(md.split())
        return None
    if b.get("enabled") is False:
        url = b.get("enable_url")
        if isinstance(url, str) and url.startswith("https://") and not any(c in url for c in " ()\n"):
            return f"<sub>[Show a live badge in your README]({url})</sub>"
    return None


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
            url = free_url(links.get(d) or r.get("fix_url"), d, report.get("framework"))
            out.append(f"| `{_md(d)}` | {_md(r.get('detail', ''))} | [fix]({url}) |")
        if "" in links and not is_pro(links[""]):
            out.append(f"\nMore fixes: {links['']}")
        out.append(f"\nWant it fixed for you? [$79 Fix]({FIX79}) · Run history: [Signal Pro]({PRO})")
    else:
        out.append("\nNo double execution or lost approvals detected.")
        out.append(f"\n<sub>Run history: [Signal Pro]({PRO})</sub>")
    if upload and upload.get("run_id"):
        out.append(f"\nUploaded run: `{_md(upload['run_id'])}`")
    env = report.get("env") or {}
    pkgs = env.get("packages") if isinstance(env.get("packages"), dict) else {}
    if pkgs:
        out.append("\n<sub>" + ", ".join(f"{k} {v}" for k, v in pkgs.items()) + "</sub>")
    foot = badge_footer(upload)
    if foot:
        out.append("\n" + foot)
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
