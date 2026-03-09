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

```
DevArchAI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration settings
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analysis.py     # Analysis endpoints
│   │   │   │   ├── reports.py      # Report endpoints
│   │   │   │   └── health.py       # Health check endpoints
│   │   │   └── deps.py             # Dependencies
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # Security utilities
│   │   │   └── exceptions.py       # Custom exceptions
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base parser interface
│   │   │   ├── terraform.py        # Terraform file parser
│   │   │   ├── kubernetes.py       # K8s YAML parser
│   │   │   ├── dockerfile.py       # Dockerfile parser
│   │   │   └── cicd.py             # CI/CD parser
│   │   ├── rules/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base rule interface
│   │   │   ├── registry.py         # Rule registry
│   │   │   ├── security.py         # Security rules
│   │   │   ├── scalability.py      # Scalability rules
│   │   │   ├── reliability.py      # Reliability rules
│   │   │   ├── cost.py             # Cost optimization rules
│   │   │   └── observability.py    # Observability rules
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # LLM integration
│   │   │   ├── prompts.py          # Prompt templates
│   │   │   └── models.py           # AI models
│   │   ├── scoring/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Scoring logic
│   │   │   └── weights.py          # Category weights
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py          # Pydantic schemas
│   │   │   └── entities.py         # Database entities
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py         # Analysis orchestration
│   │   │   ├── github.py           # GitHub integration
│   │   │   └── storage.py          # File storage
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── session.py          # Database session
│   │       └── crud.py             # CRUD operations
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
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
