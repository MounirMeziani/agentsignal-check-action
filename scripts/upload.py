#!/usr/bin/env python3
"""Upload an `agentsignal check --json` report to POST /api/check/runs/ (Signal Pro). Stdlib only.

env: AGENTSIGNAL_API_KEY, AS_URL, GITHUB_REPOSITORY, GITHUB_SHA, GITHUB_OUTPUT
usage: upload.py REPORT.json RESPONSE_OUT.json
Never fails the job: problems become ::warning:: lines. Exit 0 always.
"""
import json, os, re, sys, urllib.error, urllib.request

DEFAULT_URL = "https://tryagentsignal.com/api/check/runs/"
MAX_BYTES = 262144
STATUSES = ("PASS", "FAIL", "ERROR", "SKIP")


def map_status(s):
    s = str(s or "").upper()
    return s if s in STATUSES else ("FAIL" if s == "WARN" else "ERROR")


def build_body(report, repo=None, sha=None):
    results = []
    for r in report.get("results", [])[:100]:
        item = {"detector": str(r.get("detector", ""))[:100], "status": map_status(r.get("status"))}
        if r.get("detail") is not None:
            item["detail"] = str(r["detail"])
        results.append(item)
    fw = report.get("framework")
    rep = {"results": results}
    if fw:
        rep["framework"] = str(fw)[:64]
    if report.get("env") is not None:
        rep["env"] = report["env"]
    body = {"report": rep}
    if fw:
        body["framework"] = str(fw)[:64]
        pkgs = (report.get("env") or {}).get("packages") or {}
        ver = pkgs.get(fw) if isinstance(pkgs, dict) else None
        if isinstance(ver, str) and ver:
            body["version"] = ver[:64]
    repo = (repo or "").strip()
    sha = (sha or "").strip().lower()
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo) and len(repo) <= 200:
        body["repo"] = repo
    if re.match(r"^[0-9a-f]{7,40}$", sha):
        body["commit_sha"] = sha
    return body


def warn(msg):
    print(f"::warning::Agent Signal upload failed: {msg}")


def main(report_path, out_path):
    key = os.environ.get("AGENTSIGNAL_API_KEY", "").strip()
    if not key:
        print("agentsignal-action: no api-key; skipping upload"); return
    url = os.environ.get("AS_URL", "").strip() or DEFAULT_URL
    body = json.dumps(build_body(json.load(open(report_path)), os.environ.get("GITHUB_REPOSITORY"),
                                 os.environ.get("GITHUB_SHA"))).encode()
    if len(body) > MAX_BYTES:
        return warn(f"report is {len(body)} bytes, limit is {MAX_BYTES}")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "agentsignal-check-action"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read() or b"{}")
        except ValueError:
            err = {}
        name = err.get("error", "") if isinstance(err, dict) else ""
        msg = {401: "invalid or revoked API key (401 invalid_key)",
               403: "no active Signal Pro plan (403 pro_required)",
               413: f"report too large (413 payload_too_large, limit {MAX_BYTES})",
               429: "rate limited (429 rate_limited, 60/h per key)"}.get(e.code, f"HTTP {e.code} {name}".strip())
        if e.code == 429 and e.headers.get("Retry-After"):
            msg += f", retry after {e.headers['Retry-After']}s"
        if e.code == 400:
            errs = err.get("errors") if isinstance(err, dict) else None
            msg = f"400 {name or 'bad request'}" + ((": " + "; ".join(map(str, errs[:5]))) if errs else "")
        return warn(msg)
    except (urllib.error.URLError, OSError) as e:
        return warn(f"network error: {getattr(e, 'reason', e)}")
    except ValueError:
        return warn("response was not JSON")
    json.dump(data, open(out_path, "w"))
    print(f"agentsignal-action: uploaded run {data.get('run_id', '?')}")
    for l in data.get("fix_links") or []:
        if isinstance(l, dict):
            print(f"  {l.get('detector', '?')}  {l.get('status', '?')}  {l.get('url', '')}")
    go = os.environ.get("GITHUB_OUTPUT")
    if go:
        with open(go, "a") as f:
            f.write(f"run_id={data.get('run_id', '')}\nupload={out_path}\n")


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:  # never fail the job over the upload
        warn(str(e))
    sys.exit(0)
