# Agent Signal crash test (GitHub Action)

We kill your agent mid-approval, restart it, and count how many times the tool ran. This action runs
[agentsignal-check](https://github.com/MounirMeziani/agentsignal-check) on every PR and keeps **one** PR comment up to date
with the failing detectors and a fix link for each.

```yaml
name: crash-test
on: pull_request
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
| `version` | `master` | git ref of agentsignal-check, or a full pip spec starting with `agentsignal-check` |
| `extras` | the framework | pip extras |
| `api-key` | | Signal Pro key. Uploads the run to `api-url`; fix links then come from the server |
| `api-url` | `https://tryagentsignal.com/api/check/runs` | |
| `comment` | `true` | create/update the PR comment |
| `fail-on-fail` | `true` | fail the job if any detector fails |
| `working-directory`, `python-version`, `github-token` | `.`, `3.12`, `github.token` | |

Outputs: `result` (`pass`/`fail`), `report` (JSON path), `run-id`.

Upload errors (401, 413, 429, network) become warnings and never fail the job. The PR comment is also written to the job summary.

## Develop

```bash
python -m unittest discover -s tests -v    # renders comments from real `agentsignal check --json` output in tests/samples
```

`.github/workflows/test.yml` runs the action against `fixtures/naive_graph.py` (must fail) and `fixtures/idem_graph.py` (must pass).

MIT licensed. https://tryagentsignal.com
