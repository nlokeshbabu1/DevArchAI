# DevArchAI - Product Engineering Document

> **Version:** 1.0.0  
> **Status:** Production-Ready  
> **Last Updated:** April 14, 2026  
> **Classification:** Internal Engineering Documentation

---

## 1. Product Overview

### Problem Statement
Modern DevOps teams struggle to maintain production readiness across complex infrastructure-as-code (IaC) repositories. Manual code reviews miss critical security vulnerabilities, scalability bottlenecks, and cost optimization opportunities. Teams lack automated, AI-powered guidance to fix issues before they reach production.

### Solution
DevArchAI is an AI-powered DevOps SaaS platform that automatically scans GitHub repositories, analyzes IaC configurations (Terraform, Kubernetes, Docker, CI/CD), applies 50+ production readiness rules, generates AI-driven remediation suggestions, and calculates a comprehensive production readiness score. It enables one-click automated Pull Requests with fixes directly to the user's repository.

### Target Users
- **DevOps Engineers**: Automate infrastructure reviews and catch misconfigurations early
- **Platform Engineers**: Standardize production readiness across multiple teams
- **CTOs/Engineering Managers**: Gain visibility into infrastructure health and compliance
- **Security Teams**: Identify and remediate security vulnerabilities in IaC before deployment

---

## 2. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DevArchAI Cloud Platform                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   Web UI     │────▶│              API Gateway / Load Balancer         │  │
│  │ (React/Next) │     │                                                 │  │
│  └──────────────┘     │  ┌─────────────────────────────────────────────┐ │  │
│                       │  │              FastAPI Backend                 │ │  │
│  ┌──────────────┐     │  │  ┌───────────────────────────────────────┐  │ │  │
│  │  GitHub Repo │────▶│  │  │  Scan Orchestrator & Task Queue       │  │ │  │
│  │  (Webhook)   │     │  │  └───────────────────────────────────────┘  │ │  │
│  └──────────────┘     │  │                                             │ │  │
│                       │  │  ┌───────────────────────────────────────┐  │ │  │
│  ┌──────────────┐     │  │  │  Rule Engine & AI Suggestion Layer    │  │ │  │
│  │  Stripe/     │────▶│  │  │  (Gemini, OpenAI, Anthropic, Mistral) │  │ │  │
│  │  Razorpay    │     │  │  └───────────────────────────────────────┘  │ │  │
│  └──────────────┘     │  │                                             │ │  │
│                       │  │  ┌───────────────────────────────────────┐  │ │  │
│                       │  │  │  GitHub PR Automation & Webhooks      │  │ │  │
│                       │  │  └───────────────────────────────────────┘  │ │  │
│                       │  └─────────────────────────────────────────────┘ │  │
│                       │                                                 │  │
│  ┌──────────────┐     │  ┌─────────────────────────────────────────────┐ │  │
│  │  AWS S3      │◀────│  │  PostgreSQL + Redis Cache                   │ │  │
│  │  (Reports)   │     │  │  (User Data, Scans, Findings, Sessions)     │ │  │
│  └──────────────┘     │  └─────────────────────────────────────────────┘ │  │
│                       │                                                 │  │
└───────────────────────┴─────────────────────────────────────────────────┘  │
```

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React + TypeScript, Vite, Tailwind | User interface, real-time dashboards, scan management |
| **Backend API** | FastAPI (Python 3.11+) | REST API, WebSocket, authentication, orchestration |
| **Database** | PostgreSQL 15 + SQLAlchemy 2.0 | Persistent storage for users, scans, findings, subscriptions |
| **Cache/Queue** | Redis 7 + Celery | Session caching, task queue, rate limiting, real-time pub/sub |
| **AI Engine** | LangChain + Multi-LLM Router | AI explanations, fix generation, risk analysis |
| **Storage** | AWS S3 | Report exports, scan artifacts, backup storage |
| **GitHub Integration** | PyGitHub + OAuth | Repository cloning, branch detection, PR creation |
| **Payments** | Stripe + Razorpay | Subscription management, webhook handling, billing |

---

## 3. Feature Modules

### 3.1 Authentication & Authorization
- **GitHub OAuth 2.0**: Primary login method with seamless repository access
- **Email/Password**: Fallback authentication with JWT tokens
- **Role-Based Access Control (RBAC)**: Owner, Admin, Member, Viewer
- **Organization Management**: Multi-tenant support with team workspaces
- **API Key Generation**: Programmatic access for CI/CD integration

### 3.2 Repository Scanning Pipeline
1. **Repository Fetch**: Clone via GitHub API or webhook trigger
2. **Technology Detection**: Identify IaC tools (Docker, K8s, Terraform, CI/CD, Helm, Ansible)
3. **File Parsing**: Extract structured data from configuration files
4. **Rule Execution**: Apply 50+ production readiness checks
5. **AI Enrichment**: Generate explanations, impact analysis, and fix examples
6. **Score Calculation**: Compute production readiness score (0-100)
7. **Result Storage**: Persist findings and generate S3 report

### 3.3 Rule Engine
- **Categories**: Security, Scalability, Reliability, Cost, Observability
- **Severity Levels**: Critical, High, Medium, Low, Info
- **Dynamic Rule Loading**: Technology-specific rules activated based on detected stack
- **Extensible Framework**: Easy to add new rules without code changes

### 3.4 AI Suggestion System
- **Multi-Provider Support**: Gemini, OpenAI, Anthropic, Mistral (with automatic fallback)
- **Context-Aware Prompts**: File content + rule violation + best practices
- **Structured Output**: JSON-formatted explanations, fix code, before/after diffs
- **Confidence Scoring**: AI confidence level for each suggestion

### 3.5 Score Calculation System
- **Weighted Categories**: Security (30%), Scalability (20%), Reliability (20%), Cost (15%), Observability (15%)
- **Penalty Matrix**: Critical (-15), High (-10), Medium (-5), Low (-2), Info (-1)
- **Normalization**: Scores clamped to 0-100 range with grade mapping (A-F)

### 3.6 GitHub PR Automation
- **Branch Creation**: Auto-create `devarchai/fix-{rule-id}` branches
- **Commit Generation**: Apply AI-generated fixes with descriptive commit messages
- **Pull Request Creation**: Open PR with detailed description, diff, and score impact
- **Webhook Integration**: Listen for PR merge/close events to update scan status

### 3.7 Reporting System
- **JSON Export**: Machine-readable format for CI/CD integration
- **PDF Reports**: Executive summaries for management review
- **Excel/CSV**: Bulk analysis and compliance tracking
- **S3 Storage**: Long-term retention with configurable lifecycle policies

---

## 4. Data Flow

### End-to-End Scan Workflow

```
User Action → Backend Processing → AI Enrichment → Results → PR Creation
     │              │                   │              │          │
     ▼              ▼                   ▼              ▼          ▼
┌─────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ Enter   │  │ Clone Repo   │  │ LLM Analysis │  │ Store in │  │ Create   │
│ Repo URL│─▶│ Detect Stack │─▶│ Generate Fix │─▶│ DB + S3  │─▶│ GitHub PR│
│ + Branch│  │ Run Rules    │  │ Calc Score   │  │ Display  │  │ w/ Fixes │
└─────────┘  └──────────────┘  └──────────────┘  └──────────┘  └──────────┘
```

### Step-by-Step Flow

1. **User Initiates Scan**: Enters GitHub repository URL and selects branch
2. **Backend Clones Repository**: Fetches code to temporary isolated environment
3. **Technology Detection**: Scans file patterns to identify DevOps tools
4. **Rule Engine Execution**: Applies relevant rules based on detected stack
5. **AI Enrichment**: Sends violations to LLM for explanations and fix generation
6. **Score Calculation**: Computes weighted production readiness score
7. **Results Storage**: Saves findings to PostgreSQL, exports report to S3
8. **Real-Time Updates**: WebSocket pushes progress to frontend during scan
9. **User Reviews Results**: Views dashboard with scores, findings, and AI suggestions
10. **PR Creation (Optional)**: User clicks "Fix with PR" → Backend creates branch, commits fixes, opens PR

---

## 5. Database Design

### Entity Relationship Overview

```
users ────< organizations >──── repositories ────< scans >──── findings
  │                               │                    │
  └────< subscriptions             └────< pull_requests  └────< ai_suggestions
```

### Core Tables

#### `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique user identifier |
| email_encrypted | VARCHAR | UNIQUE, NOT NULL | Encrypted email address |
| email_hash | VARCHAR | UNIQUE, NOT NULL | Hashed email for lookups |
| username | VARCHAR | UNIQUE, NOT NULL | Display username |
| hashed_password | VARCHAR | NULL | Bcrypt hash (null for OAuth) |
| github_id | VARCHAR | NULL | GitHub user ID |
| github_access_token | VARCHAR | NULL | Encrypted GitHub token |
| role | ENUM | DEFAULT 'member' | user, admin, owner |
| subscription_plan | ENUM | DEFAULT 'free' | free, plus, pro, enterprise |
| created_at | TIMESTAMP | DEFAULT NOW() | Account creation time |

#### `repositories`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique repository identifier |
| user_id | UUID | FK → users.id | Owner user ID |
| name | VARCHAR | NOT NULL | Repository name |
| url | VARCHAR | UNIQUE, NOT NULL | Full GitHub URL |
| default_branch | VARCHAR | DEFAULT 'main' | Primary branch |
| is_private | BOOLEAN | DEFAULT false | Private repo flag |
| last_scanned_at | TIMESTAMP | NULL | Last successful scan |

#### `scans`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique scan identifier |
| repository_id | UUID | FK → repositories.id | Associated repository |
| user_id | UUID | FK → users.id, NULL | User who initiated scan (NULL for anonymous) |
| status | ENUM | NOT NULL | pending, processing, completed, failed, cancelled |
| progress | INT | DEFAULT 0 | 0-100 progress percentage |
| overall_score | FLOAT | NULL | 0-100 production readiness score |
| security_score | FLOAT | NULL | Security category score |
| scalability_score | FLOAT | NULL | Scalability category score |
| reliability_score | FLOAT | NULL | Reliability category score |
| cost_score | FLOAT | NULL | Cost optimization score |
| observability_score | FLOAT | NULL | Observability score |
| detected_stack | JSONB | NULL | Detected technologies and files |
| celery_task_id | VARCHAR | NULL | Background task ID |
| started_at | TIMESTAMP | NULL | Scan start time |
| completed_at | TIMESTAMP | NULL | Scan completion time |

#### `findings`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique finding identifier |
| scan_id | UUID | FK → scans.id | Associated scan |
| rule_id | VARCHAR | NOT NULL | Rule identifier (e.g., SEC-001) |
| severity | ENUM | NOT NULL | critical, high, medium, low, info |
| category | ENUM | NOT NULL | security, scalability, reliability, cost, observability |
| description | TEXT | NOT NULL | What was found |
| recommendation | TEXT | NOT NULL | How to fix |
| file_path | VARCHAR | NULL | File where issue was found |
| line_number | INT | NULL | Line number of issue |
| ai_explanation | TEXT | NULL | AI-generated explanation |
| fix_code | TEXT | NULL | AI-generated fix code |
| fix_example | TEXT | NULL | Before/after example |
| confidence_score | FLOAT | NULL | AI confidence (0-1) |
| created_at | TIMESTAMP | DEFAULT NOW() | Finding creation time |

#### `pull_requests`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique PR identifier |
| scan_id | UUID | FK → scans.id | Associated scan |
| github_pr_number | INT | NOT NULL | GitHub PR number |
| github_pr_url | VARCHAR | NOT NULL | Full GitHub PR URL |
| branch_name | VARCHAR | NOT NULL | Created branch name |
| status | ENUM | DEFAULT 'open' | open, merged, closed |
| created_at | TIMESTAMP | DEFAULT NOW() | PR creation time |

#### `subscriptions`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique subscription identifier |
| user_id | UUID | FK → users.id | Subscriber user ID |
| provider | ENUM | NOT NULL | stripe, razorpay |
| provider_subscription_id | VARCHAR | UNIQUE, NOT NULL | External subscription ID |
| plan | ENUM | NOT NULL | plus, pro, enterprise |
| status | ENUM | DEFAULT 'active' | active, cancelled, past_due |
| current_period_start | TIMESTAMP | NOT NULL | Billing period start |
| current_period_end | TIMESTAMP | NOT NULL | Billing period end |
| cancel_at_period_end | BOOLEAN | DEFAULT false | Scheduled cancellation |

---

## 6. API Design

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/auth/register` | Create new user account | No |
| `POST` | `/api/v1/auth/login` | Authenticate user, return JWT tokens | No |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | Refresh Token |
| `GET` | `/api/v1/auth/me` | Get current user profile | Yes |
| `PUT` | `/api/v1/auth/me` | Update user profile | Yes |
| `GET` | `/api/v1/auth/github/url` | Get GitHub OAuth URL | No |
| `POST` | `/api/v1/auth/github/callback` | Handle GitHub OAuth callback | No |

### Scan Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/scan/start` | Start new scan (guest or authenticated) | Optional |
| `GET` | `/api/v1/scans` | List user scans with pagination | Yes |
| `GET` | `/api/v1/scans/{id}` | Get scan details and scores | Yes |
| `GET` | `/api/v1/scans/{id}/findings` | Get all findings for scan | Yes |
| `GET` | `/api/v1/scan/status/{id}` | Get real-time scan progress | Yes |
| `POST` | `/api/v1/scans/{id}/cancel` | Cancel running scan | Yes |
| `DELETE` | `/api/v1/scans/{id}` | Delete scan and findings | Yes |

### AI & PR Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/ai-suggestions/generate` | Generate AI suggestions for finding | Yes |
| `POST` | `/api/v1/ai-suggestions/generate-fix` | Generate AI fix code for finding | Yes |
| `POST` | `/api/v1/github/create-pr` | Create GitHub PR with fixes | Yes |
| `GET` | `/api/v1/github/branches` | Fetch repository branches | Yes |
| `POST` | `/api/v1/github/webhook` | Handle GitHub webhook events | Webhook Secret |

### Billing & Reports

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/billing/checkout` | Create payment checkout session | Yes |
| `POST` | `/api/v1/billing/webhook` | Handle payment provider webhooks | Webhook Secret |
| `GET` | `/api/v1/reports/{scan_id}/download` | Download scan report (JSON/PDF) | Yes |
| `GET` | `/api/v1/dashboard/metrics` | Get dashboard analytics | Yes |

---

## 7. Scoring System

### Calculation Methodology

The production readiness score is calculated using a **weighted penalty system**:

```python
def calculate_category_score(findings, category):
    base_score = 100
    penalties = {
        'critical': 15,
        'high': 10,
        'medium': 5,
        'low': 2,
        'info': 1
    }
    
    category_findings = [f for f in findings if f.category == category]
    total_penalty = sum(penalties[f.severity] for f in category_findings)
    
    return max(0, base_score - total_penalty)

def calculate_overall_score(category_scores):
    weights = {
        'security': 0.30,
        'scalability': 0.20,
        'reliability': 0.20,
        'cost': 0.15,
        'observability': 0.15
    }
    
    return sum(score * weights[category] 
               for category, score in category_scores.items())
```

### Score Interpretation

| Score Range | Grade | Status | Recommendation |
|-------------|-------|--------|----------------|
| 90-100 | A | Production Ready | Minor optimizations only |
| 80-89 | B | Mostly Ready | Address high-severity items |
| 70-79 | C | Needs Work | Critical issues present |
| 60-69 | D | Not Ready | Multiple critical gaps |
| 0-59 | F | High Risk | Do not deploy to production |

### Confidence Scoring

AI-generated suggestions include a confidence score (0.0-1.0):
- **0.9-1.0**: High confidence - Fix is well-tested and widely applicable
- **0.7-0.89**: Medium confidence - Fix is reasonable but may need context adjustment
- **0.5-0.69**: Low confidence - Suggestion is generic, manual review required
- **<0.5**: Very low confidence - Fallback explanation, not AI-generated

---

## 8. Security

### Token & Credential Management
- **JWT Tokens**: Short-lived access tokens (30 min), refresh tokens (7 days)
- **Password Hashing**: bcrypt with 12 salt rounds
- **Email Encryption**: AES-256 encryption at rest, hash-based lookups
- **GitHub Tokens**: Encrypted storage, scoped to minimal required permissions
- **API Keys**: Hashed before database storage, prefix shown to user for identification

### OAuth Security
- **State Parameter**: CSRF protection on all OAuth flows
- **PKCE**: Proof Key for Code Exchange for public clients
- **Scope Minimization**: Request only `repo` and `user:email` scopes
- **Token Rotation**: Refresh tokens rotated on each use

### Payment Security
- **PCI Compliance**: No card data stored; all payment processing via Stripe/Razorpay hosted fields
- **Webhook Verification**: Signature validation on all payment webhooks
- **Idempotency Keys**: Prevent duplicate charges on retry
- **Audit Logging**: All billing events logged with timestamps and user IDs

### S3 Access Control
- **IAM Roles**: Least-privilege access to S3 buckets
- **Presigned URLs**: Time-limited download URLs for reports (15 min expiry)
- **Bucket Policies**: Block public access, enforce encryption in transit (TLS)
- **Lifecycle Rules**: Auto-delete temporary scan artifacts after 7 days

---

## 9. Scalability

### Background Workers
- **Celery Task Queue**: Async processing for scans, AI enrichment, report generation
- **Horizontal Scaling**: Workers auto-scale based on queue depth
- **Task Prioritization**: Critical scans (paid users) get higher priority queue
- **Retry Logic**: Exponential backoff with dead-letter queue for failed tasks

### Real-Time Communication
- **WebSockets**: Live scan progress updates to frontend
- **Redis Pub/Sub**: Broadcast scan status changes to multiple frontend instances
- **Connection Pooling**: WebSocket manager with heartbeat keepalive

### Caching Strategy
- **Redis Cache**: 
  - User sessions and JWT blacklists
  - Scan result caching (5 min TTL)
  - Rate limiting counters (100 req/min per user)
  - GitHub API response caching (1 hour TTL)
- **CDN**: Static assets and report downloads via CloudFront

### Horizontal Scaling
- **Stateless Backend**: No local state; all data in PostgreSQL/Redis/S3
- **Load Balancer**: Round-robin distribution across API instances
- **Database Connection Pooling**: AsyncPG with configurable pool size (default: 10)
- **Read Replicas**: PostgreSQL read replicas for dashboard queries

---

## 10. Deployment

### Docker Configuration

```yaml
# docker-compose.yml (Development)
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/devarchai
      - REDIS_URL=redis://redis:6379/0
    depends_on: [postgres, redis]

  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [backend]

  postgres:
    image: postgres:15-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    volumes: [redis_data:/data]

  celery-worker:
    build: ./backend
    command: celery -A app.workers.celery_config worker --loglevel=info
    depends_on: [postgres, redis]
```

### Kubernetes (Production)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devarchai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devarchai-backend
  template:
    spec:
      containers:
      - name: backend
        image: devarchai/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: devarchai-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Backend Tests
        run: cd backend && pytest --cov=app --cov-report=xml
      - name: Run Frontend Tests
        run: cd frontend && npm test -- --coverage
      - name: Security Scan
        run: pip-audit && npm audit

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: kubectl apply -f k8s/
      - name: Run Database Migrations
        run: kubectl exec -it backend-pod -- alembic upgrade head
```

---

## 11. UI/UX Principles

### Design Philosophy
- **Clean & Minimal**: Remove clutter; focus on actionable insights
- **Progressive Disclosure**: Show summary first, details on demand
- **Real-Time Feedback**: Live progress indicators, no black-box operations
- **Consistent Visual Language**: Unified color scheme for severity levels

### Key UI Patterns

| Pattern | Implementation |
|---------|----------------|
| **Score Visualization** | Circular progress rings with color-coded grades |
| **Finding Cards** | Expandable cards with severity badges and AI fix previews |
| **Scan Progress** | Step-by-step progress bar with live log streaming |
| **Dashboard** | Grid layout with score trends, recent scans, top issues |
| **Code Diff Viewer** | Side-by-side before/after with syntax highlighting |

### Accessibility
- **WCAG 2.1 AA Compliance**: Color contrast, keyboard navigation, screen reader support
- **Responsive Design**: Mobile-first approach, works on tablets and phones
- **Dark/Light Mode**: User preference detection with manual override

---

## 12. Roadmap

### Q2 2026 - Immediate Priorities
- [ ] **Multi-Repository Scans**: Scan entire organization at once
- [ ] **Custom Rule Engine**: Allow users to define organization-specific rules
- [ ] **Slack Integration**: Send scan summaries and critical alerts to Slack channels
- [ ] **Trend Analysis**: Track score improvements over time with charts

### Q3 2026 - Advanced Features
- [ ] **Policy as Code**: Define production readiness policies in YAML/Rego
- [ ] **Compliance Frameworks**: SOC2, HIPAA, PCI-DSS rule packs
- [ ] **Team Collaboration**: Comment on findings, assign fixes to team members
- [ ] **API Rate Limiting Tiers**: Different limits for free vs paid plans

### Q4 2026 - Enterprise Features
- [ ] **Self-Hosted Deployment**: On-premise installation for enterprise clients
- [ ] **SSO Integration**: SAML/OIDC support for enterprise authentication
- [ ] **Audit Logs**: Immutable log of all user actions and scan results
- [ ] **Custom AI Models**: Fine-tune LLMs on organization's historical data

### 2027 - Future Vision
- [ ] **Predictive Analytics**: ML models to predict production incidents from IaC patterns
- [ ] **Auto-Remediation**: Automatically merge safe fixes without manual PR review
- [ ] **Multi-Cloud Support**: AWS, Azure, GCP native configuration scanning
- [ ] **Developer IDE Plugin**: Real-time IaC linting in VS Code/JetBrains

---

## Appendix

### A. Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `REDIS_URL` | Redis connection string | Yes | - |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Yes | - |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | Yes | - |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret | Yes | - |
| `GEMINI_API_KEY` | Google Gemini API key | No | - |
| `OPENAI_API_KEY` | OpenAI API key | No | - |
| `STRIPE_SECRET_KEY` | Stripe secret key | No | - |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 | No | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 | No | - |

### B. Error Response Format

```json
{
  "error": {
    "code": "SCAN_NOT_FOUND",
    "message": "Scan with ID 'abc123' not found",
    "details": {
      "scan_id": "abc123",
      "timestamp": "2026-04-14T10:30:00Z"
    }
  }
}
```

### C. Support & Contact

- **Engineering Lead**: [engineering@devarchai.com](mailto:engineering@devarchai.com)
- **Documentation**: [docs.devarchai.com](https://docs.devarchai.com)
- **Status Page**: [status.devarchai.com](https://status.devarchai.com)
- **GitHub Repository**: [github.com/devarchai/platform](https://github.com/devarchai/platform)

---

*This document is maintained by the DevArchAI engineering team. Last reviewed: April 14, 2026.*
