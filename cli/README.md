# devsec - DevArchAI CLI

A production-grade command-line interface for the
[DevArchAI](https://github.com/nlokeshbabu1/DevArchAI) DevSecOps platform.
The CLI authenticates against the SaaS backend and drives the same
repositories / scans / findings APIs the web app uses - it never runs its own
scanning and never uploads repository content in Phase 1.

> **Phase 1 scope**: project registration & discovery, local technology
> detection, authentication, and configuration. Scan submission, live
> progress, findings, CI exit codes, and JSON reporting land in later phases.

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

# See what the CLI detects in a local repo (never uploads anything)
devsec project detect .
devsec project detect . --register

# List your projects
devsec project list
devsec project list --json
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

## Authentication

`devsec auth login` opens the web app's Settings page; paste the generated
`dk_...` API key. Keys are validated against `GET /api/v1/auth/me` before
storage. `devsec auth status` and `devsec auth logout [--revoke]` manage the
session.

## Local detection

`devsec project detect` walks the working tree (honouring `.devsecignore`,
default exclusions, and symlink/path-traversal protection) and reports a
best-effort technology stack: Docker, Docker Compose, Terraform, Kubernetes,
Helm, Ansible, GitHub Actions, GitLab CI, Jenkins, CircleCI, Azure DevOps,
Travis, Drone, Prometheus, Grafana, plus dominant languages.

Never uploaded:

- `.env*`, `*.pem`, `*.key`, `id_rsa*`, `.aws/`, `.ssh/`, and other secrets
  (these are *hard* exclusions and cannot be re-included)
- `.git/`, `node_modules/`, virtualenvs, build output
- Anything matched by your project's `.devsecignore`

## Exit codes

Exit codes are a CI-facing contract and never change without a coordinated
release:

| Code | Meaning                                |
| ---- | -------------------------------------- |
| 0    | Success / no policy violation          |
| 1    | Policy violation (future phases)       |
| 2    | CLI usage error                        |
| 3    | Authentication error                   |
| 4    | API error                              |
| 5    | Scan failure (future phases)           |

## `--json` mode

Commands supporting `--json` emit a single machine-readable JSON document on
stdout; all diagnostics go to stderr. The payload shape is stable and can be
parsed by CI pipelines.

## Development

```bash
pip install -e "./cli[dev]"
cd cli
ruff check src tests && ruff format --check src tests
mypy src/devsec
pytest
```
