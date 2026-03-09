# DevArchAI Architecture Documentation

## High-Level System Design

### Architecture Principles

1. **Modularity**: Each component is independently testable and replaceable
2. **Scalability**: Stateless design for horizontal scaling
3. **Security**: Defense in depth with input validation and secure defaults
4. **Observability**: Comprehensive logging, metrics, and tracing

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AWS Cloud Environment                          │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        Application Load Balancer                 │    │
│  │                         (ALB - Port 443)                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│                    ┌──────────────┴──────────────┐                       │
│                    │                             │                       │
│                    ▼                             ▼                       │
│  ┌─────────────────────────┐     ┌─────────────────────────┐            │
│  │   ECS Fargate Service   │     │   ECS Fargate Service   │            │
│  │   (Backend API)         │     │   (Frontend - Nginx)    │            │
│  │   - FastAPI             │     │   - React SPA           │            │
│  │   - 2-10 containers     │     │   - Static serving      │            │
│  │   - Auto-scaling        │     │                         │            │
│  └─────────────────────────┘     └─────────────────────────┘            │
│                    │                             │                       │
│                    │         ┌───────────────────┘                       │
│                    │         │                                           │
│                    ▼         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Amazon ECR                                  │    │
│  │              (Container Image Registry)                          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────┐     ┌─────────────────────────┐            │
│  │   Amazon RDS            │     │   Amazon S3             │            │
│  │   (PostgreSQL)          │     │   (Report Storage)      │            │
│  │   - Analysis results    │     │   - JSON reports        │            │
│  │   - User data           │     │   - PDF exports         │            │
│  └─────────────────────────┘     └─────────────────────────┘            │
│                                                                          │
│  ┌─────────────────────────┐     ┌─────────────────────────┐            │
│  │   Amazon ElastiCache    │     │   AWS Secrets Manager   │            │
│  │   (Redis)               │     │   - API Keys            │            │
│  │   - Session cache       │     │   - DB credentials      │            │
│  │   - Rate limiting       │     │   - LLM keys            │            │
│  └─────────────────────────┘     └─────────────────────────┘            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Analysis Request Flow

```
1. User uploads GitHub URL
         │
         ▼
2. Frontend → POST /api/v1/analyze
         │
         ▼
3. Backend validates input & creates analysis job
         │
         ▼
4. GitHub Service clones repository (temp storage)
         │
         ▼
5. File Parser Layer processes files:
   ├── Terraform Parser → AST extraction
   ├── Kubernetes Parser → Resource extraction
   ├── Dockerfile Parser → Instruction extraction
   └── CI/CD Parser → Pipeline extraction
         │
         ▼
6. Rule Engine evaluates parsed data:
   ├── Security Rules (20 rules)
   ├── Scalability Rules (10 rules)
   ├── Reliability Rules (10 rules)
   ├── Cost Rules (8 rules)
   └── Observability Rules (7 rules)
         │
         ▼
7. AI Layer generates explanations (async)
         │
         ▼
8. Scoring Engine calculates final score
         │
         ▼
9. Report stored in S3, metadata in PostgreSQL
         │
         ▼
10. Response returned to user
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Validation**: Pydantic v2
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Task Queue**: Celery + Redis
- **LLM**: OpenAI API / Anthropic / Local models

### Frontend
- **Framework**: React 18 + TypeScript
- **State**: React Query + Zustand
- **UI**: TailwindCSS + shadcn/ui
- **Charts**: Recharts
- **Build**: Vite

### Infrastructure
- **Container**: Docker
- **Orchestration**: ECS Fargate / EKS
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch + Prometheus
- **Logging**: ELK Stack

## Security Architecture

### Authentication Flow
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────▶│   ALB    │────▶│  API     │────▶│  Cognito │
│          │     │          │     │  Gateway │     │  / Auth0 │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                                                        │
     │◀─────────────────── JWT Token ─────────────────────────│
```

### Data Protection
- All data encrypted at rest (AES-256)
- TLS 1.3 for data in transit
- Secrets managed via AWS Secrets Manager
- Repository data deleted after analysis (configurable retention)

## Scalability Design

### Horizontal Scaling Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                     Auto Scaling Groups                      │
│                                                              │
│  Backend API: min=2, max=10                                 │
│  - Scale on: CPU > 70%, Request Count > 1000/min            │
│                                                              │
│  Worker Nodes: min=1, max=20                                │
│  - Scale on: Queue Depth > 100                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Caching Strategy
- **L1 Cache**: In-memory (API responses)
- **L2 Cache**: Redis (analysis results, rate limiting)
- **CDN**: CloudFront (static assets, reports)

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    Observability Stack                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Metrics    │  │   Logging   │  │   Tracing   │          │
│  │  Prometheus │  │     ELK     │  │  Jaeger     │          │
│  │  CloudWatch │  │  CloudWatch │  │  X-Ray      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                          ▼                                   │
│                 ┌─────────────────┐                          │
│                 │   Grafana       │                          │
│                 │   Dashboards    │                          │
│                 └─────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Metrics
- Request latency (p50, p95, p99)
- Error rate by endpoint
- Analysis job duration
- Queue depth
- Cache hit ratio
- LLM API latency

## Cost Optimization

### Infrastructure Cost Estimates (Monthly)

| Component | Small | Medium | Large |
|-----------|-------|--------|-------|
| ECS Fargate | $50 | $200 | $500 |
| RDS PostgreSQL | $25 | $100 | $300 |
| S3 Storage | $5 | $25 | $100 |
| ElastiCache | $15 | $50 | $150 |
| Data Transfer | $10 | $50 | $200 |
| **Total** | **$105** | **$425** | **$1,250** |

### Optimization Strategies
- Spot instances for worker nodes
- S3 Intelligent Tiering for reports
- Reserved capacity for RDS
- CloudFront for report delivery
