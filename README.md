# Agent Signal crash test (GitHub Action)

We kill your agent mid-approval, restart it, and count how many times the tool ran. This action runs
[agentsignal-check](https://github.com/MounirMeziani/agentsignal-check) on every PR and keeps **one** PR comment up to date
with the failing detectors and a fix link for each.

```yaml
name: crash-test
on:
  push: {branches: [main]}
  pull_request:
  schedule:
    - cron: '0 6 * * 1'   # weekly (Mon 06:00 UTC): keeps your result fresh against new framework releases
permissions: {contents: read, pull-requests: write}
jobs:
  agentsignal:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: MounirMeziani/agentsignal-check-action@v1
        with:
          target: app.graph:build          # factory(checkpointer) -> compiled LangGraph graph
          effect: app.tools:charge         # side effect(s) to count, one per line
          input: '{"amount": 5}'
          # api-key: ${{ secrets.AGENTSIGNAL_API_KEY }}   # optional, Signal Pro
```

OpenAI Agents SDK: set `framework: openai-agents`, `target: app.agent:build` (factory() -> Agent) and optionally `context`.

## Inputs

| Input | Default | |
|---|---|---|
| `target` | (required) | `module:factory` |
| `effect` | (required) | `module:function`, one per line |
| `framework` | `langgraph` | or `openai-agents` |
| `input` / `context` | `{}` | JSON first input (LangGraph) / run context (OpenAI Agents) |
| `version` | `git+https://github.com/MounirMeziani/agentsignal-check@v0.3.2` | git URL, bare git ref (e.g. `master`), or a full pip spec starting with `agentsignal-check` |
| `extras` | the framework | pip extras |
| `api-key` | | Signal Pro key. Uploads the run to `api-url`; fix links then come from the server |
| `api-url` | `https://tryagentsignal.com/api/check/runs/` | |
| `comment` | `auto` | `auto`, `always` or `never` (see below). Legacy `true` = `auto`, `false` = `never` |
| `fail-on-fail` | `true` | fail the job if any detector fails |
| `working-directory`, `python-version`, `github-token` | `.`, `3.12`, `github.token` | |

Outputs: `result` (`pass`/`fail`), `report` (JSON path), `run-id`.

The upload sends `{report, repo, commit_sha, framework, version}` with `repo`/`commit_sha` from `GITHUB_REPOSITORY`/`GITHUB_SHA`. Upload errors (400, 401, 403, 413, 429, network) become warnings and never fail the job. The PR comment is also written to the job summary.

## PR comment

Only `pull_request` runs touch the PR. `push` and `schedule` runs (for example the weekly cron above) never post or edit a comment;
they still run the check, upload with `api-key`, and write the job summary.

On `pull_request` runs the action keeps **one** sticky comment, found by the hidden marker `<!-- agentsignal-check-action -->`.
It lists the failing detectors with a per-framework fix link (server links when `api-key` is set), plus links to the
[$79 Fix](https://tryagentsignal.com/fix/) and [Signal Pro](https://tryagentsignal.com/pro/). It is never deleted:
a PASS after a FAIL edits it to passing.

| `comment` | FAIL | PASS |
|---|---|---|
| `auto` (default) | with `api-key`: create or update. Without: job summary only (an existing comment is still updated) | update an existing comment; never create one |
| `always` | create or update | create or update |
| `never` | nothing | nothing |

Permissions: the comment uses `github-token` (default `github.token`) and needs only `pull-requests: write`
(plus `contents: read` for checkout). Without it, or on fork PRs with a read-only token, the comment step logs a warning and the job result is unchanged.

## Develop

```bash
python -m unittest discover -s tests -v    # renders comments from real `agentsignal check --json` output in tests/samples
```

`.github/workflows/test.yml` runs the action against `fixtures/naive_graph.py` (must fail) and `fixtures/idem_graph.py` (must pass).

MIT licensed. https://tryagentsignal.com
