# DevArchAI - AI-Powered DevOps Production Readiness Engine

## Overview

DevArchAI is a production-grade SaaS platform that analyzes GitHub repositories containing infrastructure-as-code (IaC) and generates comprehensive production readiness reports. The system evaluates Terraform configurations, Kubernetes manifests, Dockerfiles, and CI/CD pipelines to provide actionable insights on security, scalability, reliability, cost, and observability.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DevArchAI Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   React UI   │────▶│              FastAPI Backend                      │  │
│  │   (Frontend) │     │                                                 │  │
│  └──────────────┘     │  ┌─────────────────────────────────────────────┐ │  │
│                       │  │              API Layer                       │ │  │
│  ┌──────────────┐     │  └─────────────────────────────────────────────┘ │  │
│  │  GitHub Repo │────▶│                                                 │  │
│  │    Upload    │     │  ┌─────────────────────────────────────────────┐ │  │
│  └──────────────┘     │  │           File Parser Layer                  │ │  │
│                       │  │  ┌─────────┬─────────┬─────────┬──────────┐  │ │  │
│                       │  │  │Terraform│  K8s    │ Docker  │ CI/CD    │  │ │  │
│                       │  │  │ Parser  │ Parser  │ Parser  │ Parser   │  │ │  │
│                       │  │  └─────────┴─────────┴─────────┴──────────┘  │ │  │
│                       │  └─────────────────────────────────────────────┘ │  │
│                       │                                                 │  │
│                       │  ┌─────────────────────────────────────────────┐ │  │
│                       │  │            Rule Engine Layer                 │ │  │
│                       │  │  ┌──────────────────────────────────────┐   │ │  │
│                       │  │  │  Security │ Scalability │ Reliability │   │ │  │
│                       │  │  │  Cost     │ Observability            │   │ │  │
│                       │  │  └──────────────────────────────────────┘   │ │  │
│                       │  └─────────────────────────────────────────────┘ │  │
│                       │                                                 │  │
│                       │  ┌─────────────────────────────────────────────┐ │  │
│                       │  │           AI Explanation Layer               │ │  │
│                       │  │         (LLM Integration)                    │ │  │
│                       │  └─────────────────────────────────────────────┘ │  │
│                       │                                                 │  │
│                       │  ┌─────────────────────────────────────────────┐ │  │
│                       │  │            Scoring Engine                    │ │  │
│                       │  │         (0-100 Score)                        │ │  │
│                       │  └─────────────────────────────────────────────┘ │  │
│                       │                                                 │  │
│                       └─────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │ JSON Report  │◀────│              PostgreSQL / S3                     │  │
│  │  Download    │     │           (Results Storage)                      │  │
│  └──────────────┘     └──────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-Format Parsing**: Terraform (.tf), Kubernetes YAML, Dockerfile, CI/CD configs
- **Rule-Based Analysis**: 50+ production readiness checks
- **AI-Powered Explanations**: Human-readable insights and recommendations
- **Scoring System**: 0-100 production readiness score
- **Categorized Findings**: Security, Scalability, Reliability, Cost, Observability
- **Downloadable Reports**: JSON and PDF report generation

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- OpenAI API Key (or compatible LLM)

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/devarchai.git
cd devarchai

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Project Structure
# DevArchAI

[![React](https://img.shields.io/badge/Frontend-React-blue?logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Deploy-Docker-blue?logo=docker)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes-blue?logo=kubernetes)](https://kubernetes.io/)
[![AWS](https://img.shields.io/badge/Cloud-AWS-orange?logo=amazon-aws)](https://aws.amazon.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Cache-Redis-red?logo=redis)](https://redis.io/)

---

## Overview

**DevArchAI** is an enterprise SaaS platform for AI-powered DevOps, Cloud, and Security production readiness. It analyzes infrastructure-as-code, CI/CD, and cloud configurations using advanced AI models, providing actionable insights, risk assessments, and compliance reports. DevArchAI integrates with GitHub, supports multi-cloud, and delivers a unified dashboard for continuous improvement.

---

## Features

- **AI-Powered Analysis:** Integrates OpenAI, Anthropic, Gemini, and Mistral for deep code/config understanding.
- **Comprehensive Scanning:** Supports Terraform, Kubernetes, Docker, and CI/CD.
- **Security & Compliance:** Detects secrets, misconfigurations, and enforces best practices.
- **Scalability & Reliability:** Evaluates HPA, resource limits, backups, and more.
- **Cost Optimization:** Identifies unused resources and cost-saving opportunities.
- **Observability:** Checks for logging, monitoring, and alerting.
- **Automated Reporting:** Generates downloadable reports (JSON/PDF) with presigned S3 URLs.
- **GitHub OAuth:** Secure SSO for teams.
- **Real-Time Scan Progress:** Live status and notifications.
- **RBAC:** Role-based access control.
- **API-First:** Full REST API for automation and integrations.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Frontend
        A[React + Vite + Tailwind]
    end
    subgraph Backend
        B[FastAPI]
        C[Redis]
        D[PostgreSQL]
        E[AWS S3]
        F[AI Providers]
        G[Worker]
    end
    subgraph Infra
        H[Nginx]
        I[Docker/Kubernetes]
    end
    subgraph Auth
        J[GitHub OAuth]
    end

    A --REST/API--> B
    B --DB--> D
    B --Cache/Queue--> C
    B --Storage--> E
    B --AI--> F
    B --OAuth--> J
    B --Queue--> G
    G --AI--> F
    G --Storage--> E
    H --SPA Routing--> A
    I --Orchestrates--> B
    I --Orchestrates--> H
    I --Orchestrates--> G
```

---

## Folder Structure

```
DevArchAI/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry
│   │   ├── config.py               # Settings
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── analysis.py     # Analysis endpoints
│   │   │   │   ├── reports.py      # Report endpoints
│   │   │   │   └── health.py
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   ├── parsers/
│   │   │   ├── terraform.py
│   │   │   ├── kubernetes.py
│   │   │   ├── dockerfile.py
│   │   │   └── cicd.py
│   │   ├── rules/
│   │   │   ├── security.py
│   │   │   ├── scalability.py
│   │   │   ├── reliability.py
│   │   │   ├── cost.py
│   │   │   └── observability.py
│   │   ├── ai/
│   │   │   ├── engine.py
│   │   │   ├── prompts.py
│   │   │   └── models.py
│   │   ├── scoring/
│   │   │   ├── engine.py
│   │   │   └── weights.py
│   │   ├── models/
│   │   │   ├── schemas.py
│   │   │   └── entities.py
│   │   ├── services/
│   │   │   ├── analysis.py
│   │   │   ├── github.py
│   │   │   └── storage.py
│   │   └── db/
│   │       ├── session.py
│   │       └── crud.py
│   ├── tests/
│   │   ├── test_parsers.py
│   │   ├── test_rules.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Upload/
│   │   │   ├── Dashboard/
│   │   │   ├── Report/
│   │   │   └── common/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── kubernetes/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
└── README.md
```

---

## Frontend Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
- Runs at [http://localhost:5174](http://localhost:5174)

---

## Backend Setup

```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- Runs at [http://localhost:8000](http://localhost:8000)
- API docs at `/docs`

---

## Environment Variables

### Frontend `.env.example`

```env
VITE_API_URL=http://localhost:8000
VITE_GITHUB_CLIENT_ID=your_github_client_id
VITE_APP_ENV=development
```

### Backend `.env.example`

```env
APP_NAME=DevArchAI
ENVIRONMENT=development
DEBUG=true

HOST=0.0.0.0
PORT=8000

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/devarchai
REDIS_URL=redis://localhost:6379/0

AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=devarchai-reports

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
MISTRAL_API_KEY=
LLM_PROVIDER=openai

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:5174/auth/github/callback

SECRET_KEY=your_secret
```

---

## Docker Setup

```bash
docker-compose up --build
```
- Brings up frontend, backend, PostgreSQL, Redis, and Nginx for SPA routing.

---

## Kubernetes Deployment

- Manifests in `infrastructure/kubernetes/`
- Example:
  ```bash
  kubectl apply -f infrastructure/kubernetes/
  ```

---

## Nginx SPA Routing

React Router is a client-side router. For deep links (e.g., `/dashboard`), Nginx must serve `index.html` for all non-API routes.  
**Config:**
```nginx
location / {
    try_files $uri /index.html;
}
```
**Why?**  
Without `try_files`, direct navigation to a route would result in a 404. React Router then takes over and renders the correct view.

---

## GitHub OAuth Flow

```mermaid
flowchart LR
    A[User] -- "Login with GitHub" --> B[Frontend]
    B -- Redirect --> C[GitHub OAuth]
    C -- Callback (code) --> B
    B -- code --> D[Backend]
    D -- Exchange code --> C
    C -- Access Token --> D
    D -- JWT Session --> B
    B -- Authenticated --> A
```
- Secure SSO for teams.
- Backend validates and stores session.

---

## AI Provider Configuration

- Set API keys in backend `.env`.
- Choose provider with `LLM_PROVIDER`.
- Backend abstracts provider differences.

---

## Scan Workflow

```mermaid
flowchart TD
    U[User] --> F[Frontend]
    F -->|Start Scan| B[Backend API]
    B -->|Enqueue| Q[Redis Queue]
    Q --> W[Worker]
    W -->|Parse & Analyze| P[Parsers & Rules]
    W -->|AI Enrichment| AI[AI Providers]
    W -->|Score| S[Scoring Engine]
    W -->|Generate Report| R[Report Service]
    R -->|Upload| S3[AWS S3]
    S3 -->|Presigned URL| B
    B --> F
    F --> U
```

---

## Report Generation Flow

- Worker parses repo, applies rules, and invokes AI for explanations.
- Scores are calculated per category.
- Report is generated (JSON/PDF).
- Report is uploaded to S3.
- Backend generates a presigned URL for secure download.
- Frontend displays download link to user.

---

## S3 + Presigned URL Flow

- Reports are uploaded to S3 via backend service.
- Presigned URLs are generated for secure, time-limited access.
- Users download reports without exposing S3 credentials.

---

## Security Features

- **OAuth 2.0:** Secure authentication via GitHub.
- **RBAC:** Role-based access control.
- **Secret Scanning:** Detects hardcoded secrets.
- **Data Isolation:** Logical separation per user/org.
- **Presigned URLs:** Secure, expiring access to reports.
- **HTTPS:** Enforced in production via Nginx/Cloud.

---

## API Overview

| Method | Endpoint                        | Description                |
|--------|---------------------------------|----------------------------|
| POST   | `/api/v1/auth/login`            | GitHub OAuth login         |
| POST   | `/api/v1/scan`                  | Start a new scan           |
| GET    | `/api/v1/scan/{id}/status`      | Get scan status            |
| GET    | `/api/v1/scan/{id}/report`      | Download report (presigned)|
| GET    | `/api/v1/user`                  | Get current user info      |

### Example: Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "code": "<github_oauth_code>"
}
```

### Example: Start Scan

```http
POST /api/v1/scan
Authorization: Bearer <token>
Content-Type: application/json

{
  "repo_url": "https://github.com/org/repo"
}
```

### Example: Get Scan Status

```http
GET /api/v1/scan/123/status
Authorization: Bearer <token>
```

### Example: Download Report

```http
GET /api/v1/scan/123/report
Authorization: Bearer <token>
```

---

## Production Deployment

- Use Docker Compose or Kubernetes for orchestration.
- Configure Nginx for HTTPS and SPA routing.
- Set environment variables securely (never commit secrets).
- Use AWS S3 for report storage.
- Use managed PostgreSQL and Redis.
- Integrate with GitHub Actions for CI/CD.

---

## Troubleshooting

- **Frontend 404s:** Ensure Nginx is using `try_files` for SPA routing.
- **OAuth Issues:** Check GitHub app credentials and redirect URIs.
- **AI Provider Errors:** Verify API keys and provider status.
- **S3 Access Denied:** Check IAM permissions and bucket policy.
- **Database/Redis:** Ensure services are running and accessible.
- **Scan Stuck:** Check worker logs and Redis queue.

---

## Future Roadmap

- Multi-cloud support (Azure, GCP)
- Custom rule authoring and marketplace
- Advanced compliance frameworks (CIS, SOC2, PCI)
- Slack/MS Teams integrations
- Webhooks and API triggers
- Enterprise SSO (SAML, OIDC)
- Usage analytics and billing
- Automated remediation suggestions

---

## License

MIT License – See [LICENSE](LICENSE) for details.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze` | Analyze a GitHub repository |
| GET | `/api/v1/reports/{id}` | Get analysis report |
| GET | `/api/v1/reports/{id}/download` | Download report |
| GET | `/api/v1/health` | Health check |

## Rule Categories

### Security
- State locking configuration
- Public security groups
- Secret management
- Network policies

### Scalability
- Horizontal Pod Autoscaler
- Resource limits
- Load balancing

### Reliability
- Backup strategies
- Health checks
- Pod disruption budgets

### Cost
- Right-sizing recommendations
- Spot instance usage
- Storage optimization

### Observability
- Monitoring stack
- Logging configuration
- Alerting rules

## License

MIT License - See LICENSE file for details
