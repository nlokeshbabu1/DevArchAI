# devsec — DevArchAI CLI

Production command-line client for [DevArchAI](https://www.devarchai.xyz/).
The CLI authenticates against the hosted SaaS backend, registers repositories,
starts scans, streams real-time progress, and returns findings. It does **not**
run a local scanning engine.

## Install

Requires Python 3.11+.

```bash
pip install devsec
```

Or install from this repository while developing:

```bash
pip install -e ./cli
```

Verify:

```bash
devsec --version
devsec --help
```

## Quick start

```bash
# Log in (opens https://www.devarchai.xyz/ settings)
devsec auth login

# Scan the current git repository (uses origin/upstream remote)
cd your-repo
devsec scan

# Scan a specific repository URL
devsec scan --repo https://github.com/org/repo

# CI / scripting
devsec scan --json --quiet --no-color --fail-on high
```

Production API and frontend URLs are the defaults — no local setup required:

| Setting | Default |
|---------|---------|
| API | `https://backend.devarchai.xyz` |
| Web app | `https://www.devarchai.xyz` |

Override for local development:

```bash
export DEVSEC_API_URL=http://localhost:8000
export DEVSEC_FRONTEND_URL=http://localhost:5174
# or
devsec config set api-url http://localhost:8000
```

## Authentication

```bash
devsec auth login          # paste API key from Settings → Security
devsec auth status         # show current user
devsec auth logout         # remove local credential
devsec auth logout --revoke  # also revoke key on server
```

API keys (`sk-...`) are stored in the OS keyring (or `~/.config/devsec/credentials.json`
with `0600` permissions as fallback). Keys are never logged or written to `config.toml`.

For CI, set `DEVSEC_API_KEY` in the environment.

## Projects

Projects map to repositories in the DevArchAI backend (single source of truth).

```bash
devsec project list
devsec project create https://github.com/org/repo
devsec project select <project-id>
devsec project current
devsec project show <project-id>
```

## Scan

```bash
# From inside a git repo (detects origin/upstream + branch)
devsec scan

# Explicit repository URL (auto-registers if needed)
devsec scan --repo https://github.com/org/repo

# Selected or explicit project
devsec project select <id>
devsec scan
devsec scan --project <id> --branch develop

# Inspect scans
devsec scan status <scan-id>
devsec scan results <scan-id>
```

### Scan lifecycle

Progress is **backend-driven** (WebSocket with polling fallback):

1. Connect to repository
2. Clone repository
3. Detect technologies (dynamic — Docker, Kubernetes, Helm, Terraform, CI/CD, …)
4. Scan infrastructure
5. Analyze findings
6. Scan completed
7. AI recommendations (when enabled)

### Results

After completion the CLI prints findings summary and a link to the web UI:

`https://www.devarchai.xyz/repositories/<id>/results`

Scans started from the CLI appear in the SaaS dashboard immediately.

## CI/CD

```bash
export DEVSEC_API_URL=https://backend.devarchai.xyz
export DEVSEC_API_KEY=sk-...
devsec scan --repo https://github.com/org/repo --json --quiet --fail-on high
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success / scan passed policy |
| 1 | Policy violation (findings above `--fail-on`) |
| 2 | Usage error |
| 3 | Authentication error |
| 4 | API error |
| 5 | Scan failure |

## Configuration

Precedence (highest wins):

1. Environment: `DEVSEC_API_URL`, `DEVSEC_FRONTEND_URL`, `DEVSEC_API_KEY`
2. `~/.config/devsec/config.toml` (non-secret values via `devsec config`)
3. Production defaults

```bash
devsec config show
devsec config set api-url https://backend.devarchai.xyz
devsec config set frontend-url https://www.devarchai.xyz
```

Non-local API URLs must use HTTPS unless `DEVSEC_ALLOW_HTTP=1`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Authentication required` | Run `devsec auth login` or set `DEVSEC_API_KEY` |
| `No Git remote found` | Add a remote or use `devsec scan --repo <url>` |
| `Unable to reach the API` | Check network and `DEVSEC_API_URL` |
| Scan stuck / WebSocket fails | CLI falls back to polling automatically |
| HTTPS error in production | Use `https://` API URL |

## Development

```bash
pip install -e "./cli[dev]"
cd cli
pytest -q
ruff check src tests
python -m build
```

## License

Apache-2.0
