# devsec - DevArchAI CLI

A production-grade command-line interface for the
[DevArchAI](https://github.com/nlokeshbabu1/DevArchAI) DevSecOps platform.
The CLI is a thin client: it authenticates against the SaaS backend and drives
the same repositories / scans / findings APIs the web app uses. It never runs
its own scanning engine.

## Install

Requires Python 3.11+.

```bash
pip install -e ./cli
```

## Quick start

```bash
# Point at your backend (or the public SaaS) and log in once
devsec config set api-url https://api.devarchai.example
devsec auth login

# Register a repository as a project to track
devsec project create https://github.com/acme/infrastructure
devsec project select <project-id>

# Run a scan (waits for completion, streams progress via WebSocket or polling)
devsec scan
devsec scan --json --quiet    # CI-friendly output

# Inspect a scan
devsec scan status <scan-id>
devsec scan results <scan-id>
```

## Configuration

Precedence (highest wins):

1. Environment variables - `DEVSEC_API_URL`, `DEVSEC_API_KEY`
   (`DEVSEC_API_KEY` is the recommended CI/CD flow; the legacy
   `DEVSEC_API_TOKEN` name is also accepted)
2. `~/.config/devsec/config.toml` (non-secret values, `devsec config set`)
3. Built-in defaults (`http://localhost:8000`)

Tokens are stored in the OS keyring; on hosts without a keyring backend they
fall back to `~/.config/devsec/credentials.json` with `0600` permissions.
Tokens are never written to the config TOML and never logged.

Non-local API URLs must use HTTPS unless `DEVSEC_ALLOW_HTTP=1` is set.

## Authentication

`devsec auth login` opens the web app's Settings page; paste the generated
`sk-...` API key. Keys are validated against `GET /api/v1/auth/me` before
storage. `devsec auth status` and `devsec auth logout [--revoke]` manage the
session.

## Scan workflow

`devsec scan`:

1. Authenticates (API key or bearer token)
2. Uses the selected project (`devsec project select`) or `--project`
3. Calls `POST /api/v1/scan/start`
4. Streams progress over `/ws/scan/{scan_id}` when using JWT bearer tokens
5. Falls back to polling `GET /api/v1/scan/status/{scan_id}` for API keys or
   when WebSocket is unavailable
6. Fetches results from `GET /api/v1/scan/results/{scan_id}`
7. Exits with code `1` when findings meet `--fail-on` (default: `high`)

## CI usage

```bash
export DEVSEC_API_URL=https://api.example.com
export DEVSEC_API_KEY=sk-...
devsec scan --json --quiet --no-color --fail-on high
```

The CLI detects CI environments (`CI`, `GITHUB_ACTIONS`, `GITLAB_CI`,
`JENKINS_URL`, etc.) and avoids interactive prompts automatically.

## Exit codes

| Code | Meaning                                |
| ---- | -------------------------------------- |
| 0    | Success / scan passed                  |
| 1    | Policy violation (findings above threshold) |
| 2    | CLI usage error                        |
| 3    | Authentication error                   |
| 4    | API error                              |
| 5    | Scan failure                           |

## Development

```bash
pip install -e "./cli[dev]"
cd cli
ruff check src tests && ruff format --check src tests
mypy src/devsec
pytest
```
