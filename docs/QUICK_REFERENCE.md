# DevArchAI - Quick Reference Card

## 🚀 Quick Start

### Start Services
```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Celery Worker
celery -A app.workers.celery_config worker --loglevel=info --concurrency=2

# Celery Beat (scheduled tasks)
celery -A app.workers.celery_config beat --loglevel=info

# Frontend
cd frontend
npm run dev
```

### Access URLs
| Service | URL |
|---------|-----|
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| Health | http://localhost:8000/api/v1/health |

---

## 📁 Project Structure

```
backend/app/
├── api/                    # API Layer
│   ├── v1/
│   │   ├── router.py
│   │   └── routes/        # Endpoint handlers
│   └── routes/
│
├── parsers/               # File Parsers
│   ├── base.py
│   ├── dockerfile.py
│   ├── terraform.py
│   ├── kubernetes.py
│   └── cicd.py
│
├── rules/                 # Rule Engine
│   ├── base.py           # Rule base classes
│   ├── security.py       # 8 security rules
│   ├── scalability.py    # 6 scalability rules
│   ├── reliability.py    # 6 reliability rules
│   ├── cost.py           # 5 cost rules
│   └── observability.py  # 6 observability rules
│
├── scoring/              # Score Calculation
│   └── engine.py
│
├── ai_engine/            # AI Explanations
│   ├── llm_client.py
│   └── explanation_engine.py
│
├── services/             # Business Logic
│   ├── scan_service.py
│   └── analysis.py
│
├── workers/              # Background Tasks
│   ├── celery_config.py
│   └── tasks/
│       └── scan_repository.py
│
├── utils/                # Utilities
│   ├── repository_scanner.py
│   ├── file_loader.py
│   └── repo_downloader.py
│
├── models/               # SQLAlchemy Models
├── schemas/              # Pydantic Schemas
└── db/                   # Database Layer
```

---

## 🔧 API Endpoints

### Authentication
```http
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/refresh
```

### Scans
```http
POST /api/v1/scans/analyze          # Start scan
GET  /api/v1/scans/{id}             # Get scan status
GET  /api/v1/scans/{id}/findings    # Get findings
POST /api/v1/scans/{id}/cancel      # Cancel scan
DELETE /api/v1/scans/{id}           # Delete scan
```

### Reports
```http
GET /api/v1/reports/{id}            # Get report
GET /api/v1/reports/{id}/download   # Download report
```

### Repositories
```http
GET    /api/v1/repositories         # List repos
POST   /api/v1/repositories         # Add repo
GET    /api/v1/repositories/{id}    # Get repo
POST   /api/v1/repositories/{id}/sync  # Sync repo
DELETE /api/v1/repositories/{id}    # Delete repo
```

---

## 📊 Rule Categories

| Category | Rules | Weight |
|----------|-------|--------|
| Security | 8 | 35% |
| Reliability | 6 | 25% |
| Scalability | 6 | 20% |
| Cost | 5 | 10% |
| Observability | 6 | 10% |

**Total: 31 Rules**

---

## 🎯 Scoring System

```
Start: 100 points

Deductions:
  Critical: -25 points
  High:     -15 points
  Medium:   -8 points
  Low:      -3 points
  Info:     0 points

Grades:
  A: 90-100 (Excellent)
  B: 80-89  (Good)
  C: 70-79  (Fair)
  D: 60-69  (Poor)
  F: 0-59   (Critical)
```

---

## 🧪 Testing

### Run Tests
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=app --cov-report=html
```

### Test Scan
```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/scans/analyze \
  -H "Content-Type: application/json" \
  -d '{"repository_url": "https://github.com/hashicorp/terraform"}'

# Using Python
from app.workers.tasks.scan_repository import scan_repository_task
result = scan_repository_task.delay(scan_id=1, repository_url="...")
```

---

## 🛠️ Configuration (.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/devarchai

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub
GITHUB_TOKEN=ghp_xxx

# LLM
LLM_PROVIDER=openai  # or anthropic, mock
OPENAI_API_KEY=sk-xxx

# Limits
MAX_REPO_SIZE_MB=100
ANALYSIS_TIMEOUT_SECONDS=300
```

---

## 📝 Code Examples

### Start a Scan
```python
from app.services.scan_service import ScanService
from app.utils.repository_scanner import RepositoryScanner

# Clone repo
scanner = RepositoryScanner()
repo_path, result = scanner.clone_repository(
    "https://github.com/org/repo"
)

# Parse files
from app.parsers.base import ParserRegistry
from app.parsers.terraform import TerraformParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.cicd import CICDParser

registry = ParserRegistry()
registry.register(TerraformParser())
registry.register(KubernetesParser())
registry.register(DockerfileParser())
registry.register(CICDParser())

# Run rules
from app.rules.base import RuleRegistry
from app.rules import security, scalability, reliability, cost, observability

registry = RuleRegistry()
findings = registry.evaluate_all(resources, file_path)

# Calculate score
from app.scoring.engine import ScoringEngine
engine = ScoringEngine()
scores = engine.calculate_scores(findings)
```

### Create Custom Rule
```python
from app.rules.base import BaseRule, Rule, RuleFinding, Severity, Category

class MyCustomRule(BaseRule):
    @property
    def rule(self) -> Rule:
        return Rule(
            id="CUSTOM-001",
            name="My Custom Rule",
            description="Description of what this rule checks",
            recommendation="How to fix the issue",
            severity=Severity.HIGH,
            category=Category.SECURITY,
        )

    def evaluate(self, resources, file_path):
        findings = []
        for resource in resources:
            if self.violation_found(resource):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))
        return findings
```

---

## 🔍 Debugging

### Check Celery Workers
```bash
celery -A app.workers.celery_config inspect active
celery -A app.workers.celery_config inspect registered
celery -A app.workers.celery_config stats
```

### View Scan Logs
```bash
# Worker logs
tail -f /var/log/celery/worker.log

# API logs
tail -f /var/log/devarchai/api.log
```

### Database Queries
```bash
# Connect to PostgreSQL
psql -U postgres -d devarchai

# Recent scans
SELECT id, status, overall_score, created_at 
FROM scans 
ORDER BY created_at DESC 
LIMIT 10;

# Findings by severity
SELECT severity, COUNT(*) 
FROM findings 
GROUP BY severity;
```

---

## 📈 Monitoring

### Key Metrics
- Scans per hour
- Average scan duration
- Findings per category
- Score distribution
- Worker queue depth

### Health Checks
```bash
# API health
curl http://localhost:8000/api/v1/health

# Worker health
celery -A app.workers.celery_config inspect ping
```

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Scan timeout | Increase `ANALYSIS_TIMEOUT_SECONDS` |
| Memory error | Reduce worker concurrency |
| Git clone fails | Check `GITHUB_TOKEN` |
| Celery not starting | Verify `REDIS_URL` |
| DB connection error | Check `DATABASE_URL` |

---

## 📚 Documentation

| Doc | Location |
|-----|----------|
| Architecture | `docs/ARCHITECTURE_REDESIGN.md` |
| Migration Plan | `docs/MIGRATION_PLAN.md` |
| Implementation | `docs/IMPLEMENTATION_SUMMARY.md` |
| API Docs | `http://localhost:8000/docs` |

---

**Version:** 1.0.0  
**Last Updated:** March 6, 2026
