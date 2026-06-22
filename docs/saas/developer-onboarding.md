# DevArchAI - Developer Onboarding Guide

> **Version:** 1.0.0  
> **Last Updated:** April 14, 2026  
> **Audience:** New developers joining the team

---

## 1. Welcome to DevArchAI! 🎉

Welcome to the DevArchAI engineering team! This guide will help you get set up and productive quickly.

### 1.1 What is DevArchAI?

DevArchAI is an AI-powered DevOps SaaS platform that:
- Scans GitHub repositories for infrastructure-as-code (IaC)
- Analyzes Terraform, Kubernetes, Docker, and CI/CD configurations
- Applies 50+ production readiness rules
- Generates AI-powered fix suggestions
- Calculates production readiness scores (0-100)
- Creates automated GitHub Pull Requests with fixes

### 1.2 Tech Stack Overview

**Backend:**
- Python 3.11+
- FastAPI (async web framework)
- SQLAlchemy 2.0 (async ORM)
- PostgreSQL 15
- Redis 7 + Celery
- LangChain + Multi-LLM (Gemini, OpenAI, Anthropic, Mistral)

**Frontend:**
- React 18 + TypeScript
- Vite 6
- Zustand (state management)
- TanStack Query (data fetching)
- Tailwind CSS + Radix UI
- Axios (HTTP client)

**Infrastructure:**
- Docker + Docker Compose
- Kubernetes (production)
- AWS S3 (report storage)
- GitHub Actions (CI/CD)

---

## 2. First Day Setup

### 2.1 Access & Accounts

**You should receive:**
- [ ] GitHub repository access (ask team lead)
- [ ] AWS account access (if needed)
- [ ] Stripe test account credentials
- [ ] LLM API keys (Gemini, OpenAI, etc.)
- [ ] Slack workspace invitation
- [ ] Jira/Linear access

**Request access to:**
```
- GitHub: https://github.com/devarchai/platform
- AWS Console: https://console.aws.amazon.com
- Stripe Dashboard: https://dashboard.stripe.com
- Sentry (error tracking): https://sentry.io
- Grafana (monitoring): https://grafana.devarchai.com
```

### 2.2 Development Environment

**Required Software:**
```bash
# Core tools
- VS Code (or preferred IDE)
- Git 2.40+
- Docker 24.0+
- Docker Compose 2.20+
- Python 3.11+
- Node.js 18+
- PostgreSQL client (psql)

# Recommended VS Code Extensions
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- ESLint (dbaeumer.vscode-eslint)
- Tailwind CSS Intelliwind
- Docker (ms-azuretools.vscode-docker)
- GitLens
- REST Client (for API testing)
```

### 2.3 Clone & Setup

```bash
# Clone repository
git clone https://github.com/devarchai/platform.git
cd platform

# Create feature branch
git checkout -b feature/your-name-onboarding

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
# (Get API keys from team lead or 1Password)
```

### 2.4 Start Development Environment

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## 3. Project Structure

### 3.1 Backend Structure

```
backend/
├── app/
│   ├── api/v1/routes/          # API endpoints
│   │   ├── auth.py             # Authentication
│   │   ├── scans.py            # Scan management
│   │   ├── ai_suggestions.py   # AI fixes
│   │   ├── github.py           # GitHub integration
│   │   └── billing.py          # Payments
│   │
│   ├── ai/                     # AI engine
│   │   └── engine.py           # LLM providers
│   │
│   ├── parsers/                # File parsers
│   │   ├── terraform.py
│   │   ├── kubernetes.py
│   │   ├── dockerfile.py
│   │   └── cicd.py
│   │
│   ├── rules/                  # Rule engine
│   │   ├── base.py
│   │   ├── security.py
│   │   ├── scalability.py
│   │   └── reliability.py
│   │
│   ├── models/                 # Database models
│   │   ├── user.py
│   │   ├── scan.py
│   │   ├── finding.py
│   │   └── repository.py
│   │
│   ├── db/                     # Database
│   │   ├── session.py
│   │   └── migrations/         # Alembic migrations
│   │
│   ├── workers/                # Celery tasks
│   │   └── tasks/
│   │       └── scan_repository.py
│   │
│   ├── websockets/             # Real-time updates
│   │   └── scan_progress.py
│   │
│   ├── services/               # Business logic
│   │   ├── github.py
│   │   ├── storage.py
│   │   └── findings_enricher.py
│   │
│   ├── core/                   # Core utilities
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   │
│   └── main.py                 # FastAPI app
│
├── tests/                      # Backend tests
├── requirements.txt
└── Dockerfile
```

### 3.2 Frontend Structure

```
frontend/
├── src/
│   ├── pages/                  # Route pages
│   │   ├── Landing.tsx
│   │   ├── ScanPage.tsx
│   │   ├── ResultPage.tsx
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   └── dashboard/
│   │
│   ├── components/             # Reusable components
│   │   ├── ui/                 # UI primitives
│   │   └── layout/
│   │
│   ├── api/                    # API layer
│   │   ├── client.ts           # Axios config
│   │   └── endpoints/          # API endpoints
│   │       ├── auth.ts
│   │       ├── scans.ts
│   │       └── github.ts
│   │
│   ├── stores/                 # Zustand stores
│   │   └── auth-store.ts
│   │
│   ├── types/                  # TypeScript types
│   │   └── index.ts
│   │
│   ├── hooks/                  # Custom React hooks
│   ├── utils/                  # Utility functions
│   ├── App.tsx                 # Main app
│   └── main.tsx                # Entry point
│
├── tests/                      # Frontend tests
├── package.json
└── Dockerfile
```

---

## 4. Development Workflow

### 4.1 Making Changes

**1. Create Feature Branch:**
```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

**2. Make Changes:**
```bash
# Backend changes
cd backend
# Edit code...

# Frontend changes
cd frontend
# Edit code...
```

**3. Test Locally:**
```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Linting
cd backend && ruff check .
cd frontend && npm run lint
```

**4. Commit Changes:**
```bash
git add .
git commit -m "feat: add your feature description"

# Commit message format:
# feat: new feature
# fix: bug fix
# docs: documentation
# style: formatting
# refactor: code refactoring
# test: tests
# chore: maintenance
```

**5. Push & Create PR:**
```bash
git push origin feature/your-feature-name
# Go to GitHub, create Pull Request
```

### 4.2 Code Review Process

**Before submitting PR:**
- [ ] All tests passing
- [ ] Linting passes (no errors)
- [ ] Code follows project conventions
- [ ] Documentation updated
- [ ] Self-reviewed your changes

**PR Template:**
```markdown
## Description
What does this PR do?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] E2E tests added (if applicable)

## Screenshots (if applicable)
Add screenshots of UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests passing
```

### 4.3 Deployment Process

**Automatic Deployment:**
```
develop branch → Staging environment
main branch → Production environment
```

**Manual Deployment:**
```bash
# Deploy to staging
kubectl apply -f k8s/ -n devarchai-staging

# Deploy to production (requires approval)
kubectl apply -f k8s/ -n devarchai-production
```

---

## 5. Common Development Tasks

### 5.1 Adding a New API Endpoint

**1. Create route file:**
```python
# backend/app/api/v1/routes/my_feature.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("")
async def get_my_feature(
    current_user: User = Depends(get_current_user)
):
    return {"message": "Hello from my feature!"}
```

**2. Register router:**
```python
# backend/app/api/v1/router.py
from app.api.v1.routes import my_feature

api_router.include_router(my_feature.router)
```

**3. Add frontend API client:**
```typescript
// frontend/src/api/endpoints/my-feature.ts
import apiClient from '../client'

export const myFeatureApi = {
  getFeature: async () => {
    const response = await apiClient.get('/my-feature')
    return response.data
  }
}
```

**4. Use in component:**
```tsx
import { myFeatureApi } from '@/api/endpoints/my-feature'

const response = await myFeatureApi.getFeature()
console.log(response.message)
```

### 5.2 Adding a Database Model

**1. Create model:**
```python
# backend/app/models/my_model.py
from sqlalchemy import Column, String, DateTime
from app.db.base import Base
import uuid
from datetime import datetime

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**2. Create migration:**
```bash
cd backend
alembic revision --autogenerate -m "add my_model table"
```

**3. Apply migration:**
```bash
alembic upgrade head
```

### 5.3 Adding a Celery Task

```python
# backend/app/workers/tasks/my_task.py
from app.workers.celery_config import celery_app
import structlog

logger = structlog.get_logger(__name__)

@celery_app.task(bind=True)
def my_background_task(self, param1: str, param2: int):
    """Description of what this task does."""
    logger.info("Starting task", param1=param1, param2=param2)
    
    try:
        # Do work here
        result = do_something(param1, param2)
        
        logger.info("Task completed", result=result)
        return result
    except Exception as e:
        logger.error("Task failed", error=str(e))
        raise self.retry(exc=e, countdown=60, max_retries=3)
```

**Call task:**
```python
from app.workers.tasks.my_task import my_background_task

# Async execution
my_background_task.delay("value1", 42)
```

### 5.4 Adding a New Rule

```python
# backend/app/rules/security/my_rule.py
from app.rules.base import BaseRule, RuleFinding, Severity, Category

class MySecurityRule(BaseRule):
    rule_id = "SEC-XXX"
    rule_name = "My Security Rule"
    severity = Severity.HIGH
    category = Category.SECURITY
    description = "Description of the issue"
    recommendation = "How to fix it"
    
    def evaluate(self, parsed_file) -> list[RuleFinding]:
        findings = []
        
        # Check for issue
        if self.detect_issue(parsed_file):
            findings.append(RuleFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=self.severity,
                category=self.category,
                description=self.description,
                recommendation=self.recommendation,
                file_path=parsed_file.file_path,
                line_number=self.get_line_number(parsed_file)
            ))
        
        return findings
    
    def detect_issue(self, parsed_file) -> bool:
        # Logic to detect issue
        return True
    
    def get_line_number(self, parsed_file) -> int:
        # Return line number
        return 1
```

---

## 6. Testing Guide

### 6.1 Backend Testing

```python
# backend/tests/test_my_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_feature(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        "/api/v1/my-feature",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Hello from my feature!"

@pytest.mark.asyncio
async def test_my_feature_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/my-feature")
    assert response.status_code == 401
```

**Run tests:**
```bash
cd backend
pytest tests/ -v
pytest tests/test_my_feature.py -v  # Single file
pytest tests/ -k "my_feature" -v    # By name
pytest tests/ --cov=app             # With coverage
```

### 6.2 Frontend Testing

```typescript
// frontend/src/pages/__tests__/MyPage.test.tsx
import { render, screen } from '@testing-library/react'
import { MyPage } from '../MyPage'

test('renders my page', () => {
  render(<MyPage />)
  expect(screen.getByText('My Page')).toBeInTheDocument()
})
```

**Run tests:**
```bash
cd frontend
npm test
npm test -- MyPage.test.tsx  # Single file
npm test -- --coverage       # With coverage
```

---

## 7. Debugging Tips

### 7.1 Backend Debugging

**Enable debug logging:**
```bash
# .env
LOG_LEVEL=DEBUG
DEBUG=true
```

**Debug with pdb:**
```python
import pdb; pdb.set_trace()  # Breakpoint
```

**View logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

**Database queries:**
```python
# Enable SQL logging
# .env
DATABASE_URL=postgresql+asyncpg://...?echo=true
```

### 7.2 Frontend Debugging

**React DevTools:**
- Install React DevTools browser extension
- Inspect component tree
- View state and props

**Network tab:**
- Check API requests/responses
- Verify headers and auth tokens

**Console logging:**
```typescript
console.log('Debug:', data)
console.error('Error:', error)
console.warn('Warning:', warning)
```

**Zustand DevTools:**
```bash
# In browser console
window.__ZUSTAND_DEVTOOLS__ = true
```

### 7.3 Common Issues

**Issue: CORS errors**
```bash
# Check CORS_ORIGINS in .env
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

**Issue: Database connection failed**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/devarchai
```

**Issue: Redis connection failed**
```bash
# Check Redis is running
docker-compose ps redis
redis-cli ping  # Should return PONG
```

---

## 8. Best Practices

### 8.1 Backend Best Practices

**Code Style:**
- Use type hints everywhere
- Follow PEP 8
- Use ruff for linting
- Write docstrings for public functions

**Error Handling:**
```python
from fastapi import HTTPException
import structlog

logger = structlog.get_logger(__name__)

try:
    result = do_something()
except ValueError as e:
    logger.error("Invalid input", error=str(e))
    raise HTTPException(400, f"Invalid input: {e}")
except Exception as e:
    logger.exception("Unexpected error")
    raise HTTPException(500, "Internal server error")
```

**Database:**
- Use async queries
- Avoid N+1 queries
- Use indexes appropriately
- Never use raw SQL (use SQLAlchemy ORM)

**Security:**
- Never log sensitive data
- Validate all inputs (Pydantic)
- Use parameterized queries
- Hash passwords with bcrypt

### 8.2 Frontend Best Practices

**Code Style:**
- Use TypeScript strictly
- Follow ESLint rules
- Use Prettier for formatting
- Write meaningful component names

**State Management:**
- Use Zustand for global state
- Use TanStack Query for server state
- Keep state as close to usage as possible

**Performance:**
- Use React.memo for expensive components
- Lazy load routes
- Debounce search inputs
- Virtualize long lists

**Accessibility:**
- Use semantic HTML
- Add aria labels
- Support keyboard navigation
- Test with screen readers

---

## 9. Resources

### 9.1 Documentation

- **Product Architecture:** `/docs/product-architecture.md`
- **API Specification:** `/docs/api-specification.md`
- **Database Design:** `/docs/database-design.md`
- **Security Architecture:** `/docs/security-architecture.md`
- **Deployment Guide:** `/docs/deployment-guide.md`
- **Sequence Diagrams:** `/docs/sequence-diagrams.md`

### 9.2 External Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **React Docs:** https://react.dev/
- **TypeScript Docs:** https://www.typescriptlang.org/
- **Tailwind CSS:** https://tailwindcss.com/

### 9.3 Team Contacts

- **Tech Lead:** [Name] - Slack: @techlead
- **Backend Lead:** [Name] - Slack: @backend-lead
- **Frontend Lead:** [Name] - Slack: @frontend-lead
- **DevOps:** [Name] - Slack: @devops

---

## 10. First Week Checklist

- [ ] Complete development environment setup
- [ ] Run application locally
- [ ] Read product architecture document
- [ ] Review API specification
- [ ] Understand database schema
- [ ] Complete first bug fix or small feature
- [ ] Attend team standup meetings
- [ ] Join relevant Slack channels
- [ ] Set up 1Password for secrets
- [ ] Review CI/CD pipeline
- [ ] Deploy to staging environment
- [ ] Schedule 1-on-1 with team members

---

## 11. First Month Goals

**Week 1-2: Learning**
- Understand codebase architecture
- Complete 2-3 small bug fixes
- Participate in code reviews
- Learn deployment process

**Week 3-4: Contributing**
- Take ownership of a feature
- Write comprehensive tests
- Document your work
- Suggest improvements

**End of Month:**
- Comfortable with codebase
- Can deploy to staging independently
- Contributing to architecture discussions
- Mentoring new team members (if applicable)

---

**Welcome aboard! 🚀**

*If you have any questions, don't hesitate to ask in Slack or during standup.*
