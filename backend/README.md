# DevArchAI Backend - Production-Grade SaaS Architecture

AI-Powered DevOps Production Readiness Engine that analyzes GitHub repositories and evaluates DevOps production readiness.

## Architecture Overview

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       │   ├── auth.py          # Authentication & user management
│   │       │   ├── scans.py         # Scan management
│   │       │   ├── repositories.py  # Repository tracking
│   │       │   ├── reports.py       # Report generation
│   │       │   └── health.py        # Health checks
│   │       └── router.py            # API v1 aggregation
│   ├── core/
│   │   ├── config.py                # Application settings
│   │   ├── security.py              # JWT, password hashing, API keys
│   │   ├── logging.py               # Structured logging
│   │   └── exceptions.py            # Custom exceptions & handlers
│   ├── db/
│   │   ├── session.py               # Database session management
│   │   ├── base.py                  # SQLAlchemy base
│   │   └── migrations/              # Alembic migrations
│   ├── models/
│   │   ├── user.py                  # User model
│   │   ├── repository.py            # Repository model
│   │   ├── scan.py                  # Scan model
│   │   ├── finding.py               # Finding model
│   │   └── report.py                # Report model
│   ├── schemas/
│   │   ├── auth.py                  # Auth schemas
│   │   ├── scan.py                  # Scan schemas
│   │   ├── repository.py            # Repository schemas
│   │   ├── report.py                # Report schemas
│   │   ├── finding.py               # Finding schemas
│   │   └── common.py                # Common schemas
│   ├── services/
│   │   └── scan_service.py          # Scan orchestration
│   ├── rule_engine/
│   │   ├── base.py                  # Rule base classes & registry
│   │   ├── rule_runner.py           # Rule execution engine
│   │   └── rules/
│   │       ├── terraform_rules.py   # Terraform rules
│   │       ├── kubernetes_rules.py  # Kubernetes rules
│   │       ├── docker_rules.py      # Docker rules
│   │       └── cicd_rules.py        # CI/CD rules
│   ├── ai_engine/
│   │   ├── llm_client.py            # LLM provider abstraction
│   │   └── explanation_engine.py    # AI explanation generation
│   ├── scoring/
│   │   └── engine.py                # Score calculation
│   ├── workers/
│   │   └── scan_worker.py           # Background scan execution
│   ├── utils/
│   │   ├── file_loader.py           # File parsing utility
│   │   └── repo_downloader.py       # Repository cloning
│   ├── parsers/                     # File parsers (existing)
│   └── main.py                      # Application entry point
├── requirements.txt
├── Dockerfile
├── alembic.ini
└── .env.example
```

## Features

### Security-First Design
- JWT authentication with refresh tokens
- API key support for enterprise users
- Password hashing with bcrypt
- Rate limiting ready
- Input validation via Pydantic
- Secure file uploads
- GitHub URL validation
- CORS protection

### Modular AI Analysis Engine
- Rule-based detection (LLM used ONLY for explanations)
- Multi-provider LLM support (OpenAI, Anthropic, Mock)
- AI-generated executive summaries
- Risk analysis
- Prioritized recommendations

### Rule Engine
Rules organized by file type and category:

**Terraform Rules:**
- Missing state locking (SEC-001)
- Public security groups (SEC-002)
- Unencrypted storage (SEC-003)
- Missing backup strategy (REL-001)
- Missing multi-AZ (REL-002)
- Missing spot instances (COST-001)

**Kubernetes Rules:**
- Missing HPA (SCALE-001)
- Missing resource limits (SCALE-002)
- Missing health checks (REL-001)
- Missing network policies (SEC-001)
- Missing pod security context (SEC-002)
- Missing PDB (REL-002)
- Missing monitoring (OBS-001)

**Dockerfile Rules:**
- Running as root (SEC-001)
- Secrets in ENV (SEC-002)
- Using latest tag (SCALE-001)
- Missing healthcheck (REL-001)
- Large base images (COST-001)

**CI/CD Rules:**
- Missing security scanning (SEC-001)
- Missing container scanning (SEC-002)
- Missing OIDC (SEC-003)
- Missing caching (SCALE-001)
- Missing approval gates (REL-001)
- Missing testing (REL-002)

### Scoring Engine
Production readiness score (0-100) across 5 categories:
- **Security** (35% weight)
- **Scalability** (20% weight)
- **Reliability** (25% weight)
- **Cost Optimization** (10% weight)
- **Observability** (10% weight)

### Background Jobs
- Async scan execution
- Progress tracking
- Cancel support
- Worker pool ready for Celery integration

## Database Schema

```
users
├── id (PK)
├── email (unique)
├── username (unique)
├── hashed_password
├── api_key (unique, nullable)
├── role (user/admin/enterprise)
└── ...

repositories
├── id (PK)
├── user_id (FK → users)
├── name
├── url
└── ...

scans
├── id (PK)
├── user_id (FK → users)
├── repository_id (FK → repositories)
├── status (pending/processing/completed/failed)
├── overall_score
└── ...

findings
├── id (PK)
├── scan_id (FK → scans)
├── rule_id
├── severity (critical/high/medium/low/info)
├── category (security/scalability/reliability/cost/observability)
├── ai_explanation
└── ...

reports
├── id (PK)
├── scan_id (FK → scans, unique)
├── overall_score
├── executive_summary
├── risk_analysis
└── ...
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `GET /api/v1/auth/me` - Get current user
- `PUT /api/v1/auth/me` - Update user profile
- `POST /api/v1/auth/api-key` - Generate API key
- `DELETE /api/v1/auth/api-key` - Revoke API key
- `POST /api/v1/auth/refresh` - Refresh access token

### Repositories
- `POST /api/v1/repositories` - Add repository
- `GET /api/v1/repositories` - List repositories
- `GET /api/v1/repositories/{id}` - Get repository
- `PUT /api/v1/repositories/{id}` - Update repository
- `DELETE /api/v1/repositories/{id}` - Delete repository
- `POST /api/v1/repositories/{id}/scan` - Trigger scan

### Scans
- `POST /api/v1/scans` - Create scan
- `GET /api/v1/scans` - List scans
- `GET /api/v1/scans/{id}` - Get scan
- `GET /api/v1/scans/{id}/progress` - Get progress
- `POST /api/v1/scans/{id}/cancel` - Cancel scan
- `DELETE /api/v1/scans/{id}` - Delete scan
- `GET /api/v1/scans/{id}/findings` - Get findings

### Reports
- `GET /api/v1/reports` - List reports
- `GET /api/v1/reports/{id}` - Get report
- `GET /api/v1/reports/{id}/download` - Download (JSON/CSV)
- `GET /api/v1/reports/{id}/summary` - Get summary
- `DELETE /api/v1/reports/{id}` - Delete report
- `GET /api/v1/reports/scan/{id}/latest` - Latest for scan

### Health
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

## Scan Workflow

```
User submits GitHub repo
         ↓
Repo downloaded (temp)
         ↓
Parsers extract files (.tf, .yaml, Dockerfile, .github/workflows)
         ↓
Rule engine analyzes resources
         ↓
Issues detected with severity & category
         ↓
AI generates explanations (optional)
         ↓
Scores calculated (0-100 per category)
         ↓
Report stored in database
         ↓
Temp files cleaned up
```

## Quick Start

### Development

```bash
# Clone repository
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Update .env with your settings
# Set LLM_PROVIDER=mock for development

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access API docs
open http://localhost:8000/docs
```

### Docker

```bash
# Development
docker build --target development -t devarchai-backend:dev .
docker run -p 8000:8000 --env-file .env devarchai-backend:dev

# Production
docker build --target production -t devarchai-backend:latest .
docker run -p 8000:8000 --env-file .env devarchai-backend:latest
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql+asyncpg://... | Database connection |
| `SECRET_KEY` | change-me | JWT signing key |
| `LLM_PROVIDER` | mock | openai/anthropic/mock |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `GITHUB_TOKEN` | - | GitHub auth token |
| `ENVIRONMENT` | development | development/production |

## Production Deployment

### Security Checklist
- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `CORS_ORIGINS` for your domain
- [ ] Set `ALLOWED_HOSTS` to your domains
- [ ] Use production database (PostgreSQL)
- [ ] Enable SSL/TLS
- [ ] Configure rate limiting
- [ ] Set up monitoring/logging

### Recommended Infrastructure
- **Container**: Kubernetes or ECS
- **Database**: PostgreSQL 15+ (RDS/Cloud SQL)
- **Cache**: Redis (ElastiCache/Memorystore)
- **Load Balancer**: ALB/Nginx
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or CloudWatch

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## Code Quality

```bash
# Linting
ruff check app/

# Type checking
mypy app/

# Format code
ruff format app/
```

## License

MIT License - See LICENSE file for details.
