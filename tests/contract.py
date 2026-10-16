"""Python port of the server's POST /api/check/runs/ contract (site lib/apikeys.js: bearerKey, validateRun, fixLinks)."""
import re
KEY_RE = re.compile(r"^as_live_[A-Za-z0-9_-]{43}$")
STATUSES = ["PASS", "FAIL", "ERROR", "SKIP"]
MAX_BODY = 262144
SITE = "https://tryagentsignal.com"
FIX = {"baseline": f"{SITE}/templates/langgraph-idempotent-approval/",
       "double_execution.kill_resume": f"{SITE}/templates/langgraph-idempotent-approval/",
       "double_execution.kill_before_checkpoint": f"{SITE}/templates/langgraph-idempotent-approval/",
       "approval.lost_on_restart": f"{SITE}/templates/langgraph-human-in-the-loop/",
       "approval.replay": f"{SITE}/templates/langgraph-approval-ui/"}

def bearer_key(h):
    m = re.match(r"^Bearer\s+(\S+)$", (h or "").strip())
    return m.group(1) if m and KEY_RE.match(m.group(1)) else None

def _str(v, mx, rx=None):
    return v is None or (isinstance(v, str) and 0 < len(v) <= mx and (rx is None or re.search(rx, v)))

def validate_run(b):
    e = []
    if not isinstance(b, dict):
        return ["body must be a JSON object"]
    r = b.get("report")
    if not isinstance(r, dict):
        e.append("report must be an object")
    else:
        res = r.get("results")
        if not isinstance(res, list) or not 1 <= len(res) <= 100:
            e.append("report.results must be an array of 1-100 items")
        else:
            for i, x in enumerate(res):
                if not isinstance(x, dict) or not isinstance(x.get("detector"), str) or not x["detector"] or len(x["detector"]) > 100:
                    e.append(f"report.results[{i}].detector required")
                if not isinstance(x, dict) or x.get("status") not in STATUSES:
                    e.append(f"report.results[{i}].status must be one of PASS|FAIL|ERROR|SKIP")
        if r.get("framework") is not None and not _str(r["framework"], 64):
            e.append("report.framework must be a string")
    if not _str(b.get("repo"), 200, r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"): e.append('repo must be "owner/name"')
    if not _str(b.get("commit_sha"), 40, r"^[0-9a-f]{7,40}$"): e.append("commit_sha must be 7-40 lowercase hex")
    if not _str(b.get("framework"), 64): e.append("framework must be a string ≤64")
    if not _str(b.get("version"), 64): e.append("version must be a string ≤64")
    return e

def fix_links(report):
    seen, out = set(), []
    for x in report["results"]:
        if x["status"] in ("PASS", "SKIP"): continue
        url = FIX.get(x["detector"])
        if url and x["detector"] not in seen:
            seen.add(x["detector"]); out.append({"detector": x["detector"], "status": x["status"], "url": url})
    return out
