# DevArchAI - Sequence Diagrams

> **Version:** 1.0.0  
> **Status:** Production-Ready  
> **Last Updated:** April 14, 2026

---

## 1. User Authentication Flow

### 1.1 Email/Password Login

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │PostgreSQL│
│  (Browser)          │ (React)  │          │(FastAPI) │          │   (DB)   │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │
     │  1. Enter email     │                     │                     │
     │     + password      │                     │                     │
     │────────────────────▶│                     │                     │
     │                     │                     │                     │
     │  2. Submit login    │                     │                     │
     │     form            │                     │                     │
     │────────────────────▶│                     │                     │
     │                     │                     │                     │
     │                     │  3. POST /auth/login│                     │
     │                     │  {email, password}  │                     │
     │                     │────────────────────▶│                     │
     │                     │                     │                     │
     │                     │                     │  4. Hash email      │
     │                     │                     │     lookup user     │
     │                     │                     │────────────────────▶│
     │                     │                     │                     │
     │                     │                     │  5. User record     │
     │                     │                     │◀────────────────────│
     │                     │                     │                     │
     │                     │                     │  6. Verify password │
     │                     │                     │     (bcrypt)        │
     │                     │                     │                     │
     │                     │                     │  7. Generate JWT    │
     │                     │                     │     tokens          │
     │                     │                     │                     │
     │                     │  8. {access_token,  │                     │
     │                     │     refresh_token}  │                     │
     │                     │◀────────────────────│                     │
     │                     │                     │                     │
     │                     │  9. Store tokens    │                     │
     │                     │     in localStorage │                     │
     │                     │                     │                     │
     │                     │  10. GET /auth/me   │                     │
     │                     │  Authorization:     │                     │
     │                     │  Bearer {token}     │                     │
     │                     │────────────────────▶│                     │
     │                     │                     │                     │
     │                     │                     │  11. Validate token │
     │                     │                     │     get user        │
     │                     │                     │────────────────────▶│
     │                     │                     │                     │
     │                     │                     │  12. User data      │
     │                     │                     │◀────────────────────│
     │                     │                     │                     │
     │                     │  13. User profile   │                     │
     │                     │     data            │                     │
     │                     │◀────────────────────│                     │
     │                     │                     │                     │
     │  14. Navigate to    │                     │                     │
     │      /dashboard     │                     │                     │
     │◀────────────────────│                     │                     │
     │                     │                     │                     │
```

### 1.2 GitHub OAuth Login

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  User    │   │ Frontend │   │ Backend  │   │  GitHub  │   │PostgreSQL│
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │              │
     │ 1. Click     │              │              │              │
     │ "Login with  │              │              │              │
     │  GitHub"     │              │              │              │
     │─────────────▶│              │              │              │
     │              │              │              │              │
     │              │ 2. GET       │              │              │
     │              │ /auth/github│              │              │
     │              │ /url         │              │              │
     │              │─────────────▶│              │              │
     │              │              │              │              │
     │              │ 3. OAuth URL │              │              │
     │              │◀─────────────│              │              │
     │              │              │              │              │
     │ 4. Redirect  │              │              │              │
     │ to GitHub    │              │              │              │
     │───────────────────────────────────────────▶│              │
     │              │              │              │              │
     │ 5. Authorize │              │              │              │
     │ app          │              │              │              │
     │───────────────────────────────────────────▶│              │
     │              │              │              │              │
     │ 6. Redirect  │              │              │              │
     │ with code    │              │              │              │
     │◀───────────────────────────────────────────│              │
     │              │              │              │              │
     │ 7. POST      │              │              │              │
     │ /auth/github │              │              │              │
     │ /callback    │              │              │              │
     │ {code}       │              │              │              │
     │─────────────▶│              │              │              │
     │              │              │              │              │
     │              │ 8. POST      │              │              │
     │              │ /auth/github │              │              │
     │              │ /callback    │              │              │
     │              │─────────────▶│              │              │
     │              │              │              │              │
     │              │              │ 9. Exchange  │              │
     │              │              │ code for     │              │
     │              │              │ token        │              │
     │              │              │─────────────▶│              │
     │              │              │              │              │
     │              │              │ 10. Access   │              │
     │              │              │ token        │              │
     │              │              │◀─────────────│              │
     │              │              │              │              │
     │              │              │ 11. GET      │              │
     │              │              │ /user        │              │
     │              │              │─────────────▶│              │
     │              │              │              │              │
     │              │              │ 12. User     │              │
     │              │              │ info         │              │
     │              │              │◀─────────────│              │
     │              │              │              │              │
     │              │              │ 13. Find or  │              │
     │              │              │ create user  │              │
     │              │              │────────────────────────────▶│
     │              │              │              │              │
     │              │              │ 14. Generate │              │
     │              │              │ JWT tokens   │              │
     │              │              │              │              │
     │              │ 15. Tokens + │              │              │
     │              │ user data    │              │              │
     │              │◀─────────────│              │              │
     │              │              │              │              │
     │ 16. Login    │              │              │              │
     │ successful   │              │              │              │
     │◀─────────────│              │              │              │
     │              │              │              │              │
```

---

## 2. Repository Scan Flow

### 2.1 Complete Scan Pipeline

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │ Frontend │  │ Backend  │  │  GitHub  │  │   LLM    │  │PostgreSQL│
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │             │
     │ 1. Enter    │             │             │             │             │
     │ repo URL    │             │             │             │             │
     │ + branch    │             │             │             │             │
     │────────────▶│             │             │             │             │
     │             │             │             │             │             │
     │             │ 2. POST     │             │             │             │
     │             │ /scan/start │             │             │             │
     │             │────────────▶│             │             │             │
     │             │             │             │             │             │
     │             │             │ 3. Create   │             │             │
     │             │             │ Scan record │             │             │
     │             │             │ (pending)   │             │             │
     │             │             │────────────────────────────────────────▶│
     │             │             │             │             │             │
     │             │             │ 4. Scan ID  │             │             │
     │             │             │◀────────────────────────────────────────│
     │             │             │             │             │             │
     │             │ 5. Scan ID  │             │             │             │
     │             │ returned    │             │             │             │
     │             │◀────────────│             │             │             │
     │             │             │             │             │             │
     │             │ 6. Connect  │             │             │             │
     │             │ WebSocket   │             │             │             │
     │             │ /ws/scan/{id}             │             │             │
     │             │────────────▶│             │             │             │
     │             │             │             │             │             │
     │             │             │ 7. Clone    │             │             │
     │             │             │ repository  │             │             │
     │             │             │────────────▶│             │             │
     │             │             │             │             │             │
     │             │             │ 8. Repo     │             │             │
     │             │             │ files       │             │             │
     │             │             │◀────────────│             │             │
     │             │             │             │             │             │
     │             │             │ 9. Detect   │             │             │
     │             │             │ technologies│             │             │
     │             │             │ (Docker,K8s,│             │             │
     │             │             │ Terraform)  │             │             │
     │             │             │             │             │             │
     │             │ 10. WS:   │             │             │             │
     │             │ stack     │             │             │             │
     │             │ detected  │             │             │             │
     │             │◀────────────│             │             │             │
     │             │             │             │             │             │
     │             │             │ 11. Parse   │             │             │
     │             │             │ files       │             │             │
     │             │             │             │             │             │
     │             │             │ 12. Run     │             │             │
     │             │             │ rule engine │             │             │
     │             │             │ (50+ rules) │             │             │
     │             │             │             │             │             │
     │             │ 13. WS:   │             │             │             │
     │             │ progress  │             │             │             │
     │             │ update    │             │             │             │
     │             │◀────────────│             │             │             │
     │             │             │             │             │             │
     │             │             │ 14. AI      │             │             │
     │             │             │ enrichment  │             │             │
     │             │             │────────────────────────▶│             │
     │             │             │             │             │             │
     │             │             │ 15. AI      │             │             │
     │             │             │ explanations│             │             │
     │             │             │◀────────────────────────│             │
     │             │             │             │             │             │
     │             │             │ 16. Calculate           │             │
     │             │             │ scores      │             │             │
     │             │             │             │             │             │
     │             │             │ 17. Save    │             │             │
     │             │             │ findings    │             │             │
     │             │             │────────────────────────────────────────▶│
     │             │             │             │             │             │
     │             │             │ 18. Update  │             │             │
     │             │             │ scan status │             │             │
     │             │             │ (completed) │             │             │
     │             │             │────────────────────────────────────────▶│
     │             │             │             │             │             │
     │             │ 19. WS:   │             │             │             │
     │             │ scan      │             │             │             │
     │             │ complete  │             │             │             │
     │             │◀────────────│             │             │             │
     │             │             │             │             │             │
     │             │ 20. GET   │             │             │             │
     │             │ /scan/    │             │             │             │
     │             │ results/{id}            │             │             │
     │             │────────────▶│             │             │             │
     │             │             │             │             │             │
     │             │             │ 21. Fetch   │             │             │
     │             │             │ scan +     │             │             │
     │             │             │ findings   │             │             │
     │             │             │────────────────────────────────────────▶│
     │             │             │             │             │             │
     │             │             │ 22. Results │             │             │
     │             │             │◀────────────────────────────────────────│
     │             │             │             │             │             │
     │             │ 23. Scan  │             │             │             │
     │             │ results   │             │             │             │
     │             │◀────────────│             │             │             │
     │             │             │             │             │             │
     │ 24. Display │             │             │             │             │
     │ results     │             │             │             │             │
     │◀────────────│             │             │             │             │
     │             │             │             │             │             │
```

### 2.2 Technology Detection Process

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Technology Detection Pipeline                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Scan Repository Files                                           │
│     └── Iterate through all files in cloned repository              │
│                                                                      │
│  2. Pattern Matching                                                │
│     ├── Docker: Dockerfile*, *.dockerfile, docker-compose*.yml      │
│     ├── Kubernetes: deployment.yaml, service.yaml, *-k8s.yaml       │
│     ├── Terraform: *.tf, *.tfvars                                   │
│     ├── Helm: Chart.yaml, values.yaml                               │
│     ├── GitHub Actions: .github/workflows/*.yml                     │
│     ├── Jenkins: Jenkinsfile                                        │
│     ├── GitLab CI: .gitlab-ci.yml                                   │
│     ├── Ansible: *.yml (in roles/, playbooks/)                      │
│     └── Monitoring: prometheus.yml, grafana dashboards              │
│                                                                      │
│  3. Build DetectedTechnologyStack Object                            │
│     └── {                                                           │
│           has_docker: true,                                         │
│           docker_files: ["Dockerfile", "docker-compose.yml"],       │
│           has_terraform: true,                                      │
│           terraform_files: ["main.tf", "variables.tf"],             │
│           has_kubernetes: true,                                     │
│           kubernetes_files: ["deployment.yaml", "service.yaml"],    │
│           ...                                                       │
│         }                                                           │
│                                                                      │
│  4. Send WebSocket Event                                            │
│     └── { type: "stack_detected", data: { technologies: [...] } }   │
│                                                                      │
│  5. Load Appropriate Rules                                          │
│     ├── Docker rules (if has_docker)                                │
│     ├── Terraform rules (if has_terraform)                          │
│     ├── Kubernetes rules (if has_kubernetes)                        │
│     └── CI/CD rules (if has_github_actions || has_jenkins)          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. AI Suggestion Generation Flow

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │ Frontend │  │ Backend  │  │  Redis   │  │   LLM    │
│          │  │          │  │          │  │  Cache   │  │  (Gemini)│
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │
     │ 1. Click    │             │             │             │
     │ "Generate   │             │             │             │
     │ AI Fix"     │             │             │             │
     │────────────▶│             │             │             │
     │             │             │             │             │
     │             │ 2. POST     │             │             │
     │             │ /ai-sugges- │             │             │
     │             │ tions/      │             │             │
     │             │ generate-fix│             │             │
     │             │ {finding_id}│             │             │
     │             │────────────▶│             │             │
     │             │             │             │             │
     │             │             │ 3. Check    │             │
     │             │             │ cache       │             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 4. Cache    │             │
     │             │             │ hit?        │             │
     │             │             │◀────────────│             │
     │             │             │             │             │
     │             │             │             │             │
     │             │             │ [If cache miss]           │
     │             │             │             │             │
     │             │             │ 5. Get      │             │
     │             │             │ finding +   │             │
     │             │             │ file content│             │
     │             │             │             │             │
     │             │             │ 6. Build    │             │
     │             │             │ prompt      │             │
     │             │             │             │             │
     │             │             │ 7. Call LLM │             │
     │             │             │ API         │             │
     │             │             │──────────────────────────▶│
     │             │             │             │             │
     │             │             │             │             │
     │             │             │ 8. AI       │             │
     │             │             │ response    │             │
     │             │             │ (JSON)      │             │
     │             │             │◀──────────────────────────│
     │             │             │             │             │
     │             │             │ 9. Parse    │             │
     │             │             │ response    │             │
     │             │             │             │             │
     │             │             │ 10. Cache   │             │
     │             │             │ result      │             │
     │             │             │ (30 days)   │             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 11. Update  │             │
     │             │             │ finding in  │             │
     │             │             │ database    │             │
     │             │             │             │             │
     │             │ 12. AI fix│             │             │
     │             │ data      │             │             │
     │             │◀────────────│             │             │
     │             │             │             │             │
     │ 13. Display │             │             │             │
     │ AI fix with │             │             │             │
     │ code diff   │             │             │             │
     │◀────────────│             │             │             │
     │             │             │             │             │
```

### 3.1 AI Prompt Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Prompt Template                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  System: You are a DevOps expert specializing in                 │
│  infrastructure-as-code security and best practices.            │
│                                                                  │
│  User: Analyze the following finding and generate a fix:        │
│                                                                  │
│  Finding Details:                                               │
│  - Rule ID: SEC-001                                             │
│  - Rule Name: Missing State Locking                             │
│  - Severity: critical                                           │
│  - Category: security                                           │
│  - Description: Terraform state backend does not have           │
│    locking enabled                                              │
│  - Recommendation: Enable state locking using DynamoDB          │
│  - File: terraform/backend.tf                                   │
│  - Line: 5                                                      │
│                                                                  │
│  Current Code:                                                  │
│  ```hcl                                                         │
│  backend "s3" {                                                 │
│    bucket = "my-terraform-state"                                │
│  }                                                              │
│  ```                                                            │
│                                                                  │
│  Please provide:                                                │
│  1. Detailed explanation of the issue                           │
│  2. Impact analysis (what could go wrong)                       │
│  3. Fixed code with proper configuration                        │
│  4. Before/after example                                        │
│  5. Best practices (array of 3-5 items)                         │
│                                                                  │
│  Respond ONLY with valid JSON in this format:                   │
│  {                                                              │
│    "explanation": "...",                                        │
│    "impact_analysis": "...",                                    │
│    "fix_code": "...",                                           │
│    "fix_example": "...",                                        │
│    "best_practices": ["...", "..."]                             │
│  }                                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. GitHub PR Creation Flow

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │ Frontend │  │ Backend  │  │  GitHub  │  │PostgreSQL│
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │
     │ 1. Click    │             │             │             │
     │ "Fix with   │             │             │             │
     │ PR"         │             │             │             │
     │────────────▶│             │             │             │
     │             │             │             │             │
     │             │ 2. POST     │             │             │
     │             │ /github/    │             │             │
     │             │ create-pr   │             │             │
     │             │ {scan_id,   │             │             │
     │             │  findings}  │             │             │
     │             │────────────▶│             │             │
     │             │             │             │             │
     │             │             │ 3. Get scan │             │
     │             │             │ + findings  │             │
     │             │             │──────────────────────────▶│
     │             │             │             │             │
     │             │             │ 4. Scan data│             │
     │             │             │◀──────────────────────────│
     │             │             │             │             │
     │             │             │ 5. Get user │             │
     │             │             │ GitHub token│             │
     │             │             │──────────────────────────▶│
     │             │             │             │             │
     │             │             │ 6. GitHub   │             │
     │             │             │ token       │             │
     │             │             │◀──────────────────────────│
     │             │             │             │             │
     │             │             │ 7. Create   │             │
     │             │             │ new branch  │             │
     │             │             │ devarchai/  │             │
     │             │             │ fix-security│             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 8. Branch   │             │
     │             │             │ created     │             │
     │             │             │◀────────────│             │
     │             │             │             │             │
     │             │             │ 9. Apply    │             │
     │             │             │ fixes to    │             │
     │             │             │ files       │             │
     │             │             │             │             │
     │             │             │ 10. Commit  │             │
     │             │             │ changes     │             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 11. Commit  │             │
     │             │             │ created     │             │
     │             │             │◀────────────│             │
     │             │             │             │             │
     │             │             │ 12. Create  │             │
     │             │             │ Pull Request│             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 13. PR      │             │
     │             │             │ created     │             │
     │             │             │ (PR #42)    │             │
     │             │             │◀────────────│             │
     │             │             │             │             │
     │             │             │ 14. Save PR │             │
     │             │             │ to database │             │
     │             │             │──────────────────────────▶│
     │             │             │             │             │
     │             │ 15. PR    │             │             │
     │             │ details   │             │             │
     │             │◀────────────│             │             │
     │             │             │             │             │
     │ 16. Show PR │             │             │             │
     │ URL +       │             │             │             │
     │ status      │             │             │             │
     │◀────────────│             │             │             │
     │             │             │             │             │
```

### 4.1 PR Description Template

```markdown
## 🔒 DevArchAI Security Fix

This Pull Request was automatically generated by DevArchAI to address critical security issues detected in your infrastructure code.

### Scan Summary
- **Scan ID**: scan-uuid
- **Overall Score**: 65.0 → 85.0 (after fixes)
- **Findings Fixed**: 3
- **Severity**: Critical, High

### Issues Fixed

#### 1. SEC-001: Missing State Locking (Critical)
**File**: `terraform/backend.tf`
**Issue**: Terraform state backend does not have locking enabled
**Fix**: Added DynamoDB table for state locking

#### 2. SEC-002: Public Security Group (High)
**File**: `terraform/security.tf`
**Issue**: Security group allows ingress from 0.0.0.0/0
**Fix**: Restricted ingress to specific CIDR blocks

#### 3. K8S-005: Missing Resource Limits (High)
**File**: `k8s/deployment.yaml`
**Issue**: Container does not have resource limits
**Fix**: Added CPU and memory limits

### Changes Made
- Modified: `terraform/backend.tf`
- Modified: `terraform/security.tf`
- Modified: `k8s/deployment.yaml`

### Review Checklist
- [ ] Review all changes before merging
- [ ] Test in staging environment
- [ ] Verify Terraform plan output
- [ ] Confirm Kubernetes deployments work as expected

### View Full Report
[View DevArchAI Scan Report](https://app.devarchai.com/scans/scan-uuid)

---

*Generated by DevArchAI on 2026-04-14*
```

---

## 5. Payment & Subscription Flow

### 5.1 Upgrade to Paid Plan

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │ Frontend │  │ Backend  │  │  Stripe  │  │PostgreSQL│
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │
     │ 1. Click    │             │             │             │
     │ "Upgrade to │             │             │             │
     │ Pro"        │             │             │             │
     │────────────▶│             │             │             │
     │             │             │             │             │
     │             │ 2. Check    │             │             │
     │             │ auth        │             │             │
     │             │             │             │             │
     │             │  [If not    │             │             │
     │             │   logged in]│             │             │
     │             │             │             │             │
     │             │ 3. Redirect │             │             │
     │             │ to /login   │             │             │
     │             │             │             │             │
     │             │             │             │             │
     │             │  [If logged │             │             │
     │             │    in]      │             │             │
     │             │             │             │             │
     │             │ 4. POST     │             │             │
     │             │ /billing/   │             │             │
     │             │ checkout    │             │             │
     │             │ {plan:pro}  │             │             │
     │             │────────────▶│             │             │
     │             │             │             │             │
     │             │             │ 5. Create   │             │
     │             │             │ Stripe      │             │
     │             │             │ checkout    │             │
     │             │             │ session     │             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 6. Checkout │             │
     │             │             │ URL         │             │
     │             │             │◀────────────│             │
     │             │             │             │             │
     │             │ 7. Checkout │             │             │
     │             │ URL         │             │             │
     │             │◀────────────│             │             │
     │             │             │             │             │
     │ 8. Redirect │             │             │             │
     │ to Stripe   │             │             │             │
     │ Checkout    │             │             │             │
     │────────────────────────────────────────▶│             │
     │             │             │             │             │
     │ 9. Enter    │             │             │             │
     │ payment     │             │             │             │
     │ details     │             │             │             │
     │             │             │             │             │
     │ 10. Payment │             │             │             │
     │ successful  │             │             │             │
     │             │             │             │             │
     │ 11. Stripe  │             │             │             │
     │ sends       │             │             │             │
     │ webhook     │             │             │             │
     │──────────────────────────────────────────────────────▶│
     │             │             │             │             │
     │             │             │ 12. Webhook │             │
     │             │             │ received    │             │
     │             │             │────────────▶│             │
     │             │             │             │             │
     │             │             │ 13. Verify  │             │
     │             │             │ signature   │             │
     │             │             │             │             │
     │             │             │ 14. Update  │             │
     │             │             │ subscription│             │
     │             │             │──────────────────────────▶│
     │             │             │             │             │
     │             │             │ 15. Send    │             │
     │             │             │ receipt     │             │
     │             │             │ email       │             │
     │             │             │             │             │
     │ 16. Redirect│             │             │             │
     │ back to     │             │             │             │
     │ /dashboard  │             │             │             │
     │◀─────────────────────────────────────────────────────│
     │             │             │             │             │
     │ 17. Show    │             │             │             │
     │ success     │             │             │             │
     │ message     │             │             │             │
     │             │             │             │             │
```

---

## 6. WebSocket Real-Time Updates

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │ Frontend │  │ Backend  │  │  Redis   │
│  (Browser)          │  │(FastAPI) │  │  Pub/Sub │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     │ 1. Connect  │             │             │
     │ WebSocket   │             │             │
     │ /ws/scan/{id}             │             │
     │────────────▶│             │             │
     │             │             │             │
     │             │ 2. Accept   │             │
     │             │ connection  │             │
     │             │             │             │
     │             │ 3. Subscribe│             │
     │             │ to Redis    │             │
     │             │ channel:    │             │
     │             │ scan:{id}   │             │
     │             │────────────▶│             │
     │             │             │             │
     │             │             │  [Scan runs │
     │             │             │   in background]
     │             │             │             │
     │             │             │ 4. Publish  │
     │             │             │ progress    │
     │             │             │ update      │
     │             │             │────────────▶│
     │             │             │             │
     │             │ 5. Receive  │             │
     │             │ message     │             │
     │             │◀────────────│             │
     │             │             │             │
     │ 6. Update   │             │             │
     │ progress bar│             │             │
     │◀────────────│             │             │
     │             │             │             │
     │             │             │ 7. Publish  │             │
     │             │             │ log message │             │
     │             │             │────────────▶│             │
     │             │             │             │
     │             │ 8. Receive  │             │
     │             │ log         │             │
     │             │◀────────────│             │
     │             │             │             │
     │ 9. Append   │             │             │
     │ to log      │             │             │
     │ display     │             │             │
     │◀────────────│             │             │
     │             │             │             │
     │             │             │ 10. Publish │
     │             │             │ scan        │
     │             │             │ complete    │
     │             │             │────────────▶│
     │             │             │             │
     │             │ 11. Receive │             │
     │             │ complete    │             │
     │             │◀────────────│             │
     │             │             │             │
     │ 12. Fetch   │             │             │
     │ final       │             │             │
     │ results     │             │             │
     │────────────▶│             │             │
     │             │             │             │
     │ 13. Display │             │             │
     │ results     │             │             │
     │◀────────────│             │             │
     │             │             │             │
```

---

*This document is maintained by the DevArchAI engineering team. Last reviewed: April 14, 2026.*
