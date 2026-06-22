# DevArchAI - API Specification Document

> **Version:** 1.0.0  
> **Status:** Production-Ready  
> **Last Updated:** April 14, 2026  
> **Base URL:** `https://api.devarchai.com/api/v1`

---

## 1. Overview

This document defines the complete REST API specification for DevArchAI, including authentication, request/response formats, error handling, and rate limiting.

**API Style:** RESTful JSON  
**Authentication:** JWT Bearer tokens, API keys  
**Rate Limiting:** 100 requests/minute (free), 1000 requests/minute (paid)  
**Versioning:** URL-based (`/api/v1/`)

---

## 2. Authentication

### 2.1 JWT Token Format

**Access Token (30 min expiry):**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "type": "access",
  "exp": 1713097200,
  "iat": 1713095400
}
```

**Refresh Token (7 day expiry):**
```json
{
  "sub": "user-uuid",
  "type": "refresh",
  "exp": 1713700200,
  "iat": 1713095400
}
```

### 2.2 Authentication Methods

**Method 1: JWT Bearer Token**
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Method 2: API Key**
```http
X-API-Key: dck_abc123def456...
```

**Method 3: Session Cookie (Web UI only)**
```http
Cookie: session=eyJhbGciOiJIUzI1NiIs...
```

---

## 3. Request/Response Format

### 3.1 Standard Request Headers

```http
Content-Type: application/json
Authorization: Bearer {token}
X-Organization-ID: {org-uuid}  # Optional, for multi-tenant apps
User-Agent: DevArchAI-Web/1.0.0
```

### 3.2 Standard Response Format

**Success Response:**
```json
{
  "data": {
    "id": "scan-uuid",
    "status": "completed",
    "overall_score": 85.5
  },
  "meta": {
    "timestamp": "2026-04-14T10:30:00Z",
    "request_id": "req-abc123"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "SCAN_NOT_FOUND",
    "message": "Scan with ID 'abc123' not found",
    "details": {
      "scan_id": "abc123"
    },
    "timestamp": "2026-04-14T10:30:00Z",
    "request_id": "req-abc123"
  }
}
```

### 3.3 Pagination

**Request:**
```http
GET /api/v1/scans?page=1&page_size=20
```

**Response:**
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total_count": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 4. API Endpoints

### 4.1 Authentication Endpoints

#### POST `/auth/register`

Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecureP@ssw0rd!",
  "organization_name": "Acme Corp",
  "country": "US"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "role": "owner",
    "subscription_plan": "free",
    "created_at": "2026-04-14T10:30:00Z"
  }
}
```

**Errors:**
- `400 BAD_REQUEST` - Email already registered
- `400 BAD_REQUEST` - Username already taken
- `400 BAD_REQUEST` - Invalid email format
- `400 BAD_REQUEST` - Password too weak

---

#### POST `/auth/login`

Authenticate user and return JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd!"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**Errors:**
- `401 UNAUTHORIZED` - Invalid email or password
- `403 FORBIDDEN` - Account is disabled

---

#### POST `/auth/refresh`

Refresh access token using refresh token.

**Request:**
```http
Authorization: Bearer {refresh_token}
```

**Response (200 OK):**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**Errors:**
- `401 UNAUTHORIZED` - Invalid or expired refresh token
- `401 UNAUTHORIZED` - User not found or inactive

---

#### GET `/auth/me`

Get current user profile information.

**Headers:**
```http
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "avatar_url": "https://avatars.githubusercontent.com/u/123",
    "role": "owner",
    "is_active": true,
    "is_verified": true,
    "subscription_plan": "pro",
    "current_org_id": "org-uuid",
    "created_at": "2026-01-15T08:00:00Z",
    "last_login_at": "2026-04-14T10:30:00Z"
  }
}
```

**Errors:**
- `401 UNAUTHORIZED` - Invalid or missing token
- `404 NOT_FOUND` - User not found

---

#### GET `/auth/github/url`

Get GitHub OAuth authorization URL.

**Response (200 OK):**
```json
{
  "data": {
    "oauth_url": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=yyy&scope=user:email,read:user"
  }
}
```

---

#### POST `/auth/github/callback`

Handle GitHub OAuth callback and create/update user.

**Request:**
```json
{
  "code": "authorization_code_from_github"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "id": "user-uuid",
      "email": "user@example.com",
      "username": "johndoe",
      "avatar_url": "https://avatars.githubusercontent.com/u/123"
    }
  }
}
```

---

### 4.2 Scan Endpoints

#### POST `/scan/start`

Start a new repository scan (works for both authenticated and anonymous users).

**Request:**
```json
{
  "repository_url": "https://github.com/example/infrastructure",
  "branch": "main",
  "commit_hash": "abc123def456"  // Optional
}
```

**Response (202 Accepted):**
```json
{
  "data": {
    "scan_id": "scan-uuid",
    "status": "pending",
    "progress": 0,
    "repository_url": "https://github.com/example/infrastructure",
    "branch": "main",
    "created_at": "2026-04-14T10:30:00Z",
    "session_token": "st_abc123"  // For anonymous users
  }
}
```

**Errors:**
- `400 BAD_REQUEST` - Invalid repository URL
- `400 BAD_REQUEST` - Repository not found
- `403 FORBIDDEN` - Private repository without access
- `429 TOO_MANY_REQUESTS` - Rate limit exceeded

---

#### GET `/scans`

List all scans for the current user with pagination and filtering.

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 20, max: 100) - Items per page
- `status_filter` (string, optional) - Filter by status: `pending`, `processing`, `completed`, `failed`

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "scan-uuid-1",
      "repository_url": "https://github.com/example/infra",
      "branch": "main",
      "status": "completed",
      "progress": 100,
      "overall_score": 85.5,
      "security_score": 90.0,
      "scalability_score": 80.0,
      "reliability_score": 85.0,
      "cost_score": 75.0,
      "observability_score": 95.0,
      "findings_count": 12,
      "created_at": "2026-04-14T10:30:00Z",
      "completed_at": "2026-04-14T10:32:00Z",
      "analysis_duration_seconds": 120.5
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total_count": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

#### GET `/scans/{scan_id}`

Get detailed information about a specific scan.

**Path Parameters:**
- `scan_id` (UUID) - The scan identifier

**Response (200 OK):**
```json
{
  "data": {
    "id": "scan-uuid",
    "user_id": "user-uuid",
    "repository_id": "repo-uuid",
    "repository_url": "https://github.com/example/infrastructure",
    "repository_name": "example/infrastructure",
    "branch": "main",
    "commit_hash": "abc123def456",
    "status": "completed",
    "progress": 100,
    "status_message": "Scan completed successfully",
    "error_message": null,
    "overall_score": 85.5,
    "security_score": 90.0,
    "scalability_score": 80.0,
    "reliability_score": 85.0,
    "cost_score": 75.0,
    "observability_score": 95.0,
    "detected_stack": {
      "has_docker": true,
      "docker_files": ["Dockerfile", "docker-compose.yml"],
      "has_terraform": true,
      "terraform_files": ["main.tf", "variables.tf"],
      "has_kubernetes": true,
      "kubernetes_files": ["deployment.yaml", "service.yaml"]
    },
    "detected_technologies": ["Docker", "Terraform", "Kubernetes"],
    "files_analyzed": 15,
    "findings_count": 12,
    "started_at": "2026-04-14T10:30:00Z",
    "completed_at": "2026-04-14T10:32:00Z",
    "analysis_duration_seconds": 120.5,
    "created_at": "2026-04-14T10:30:00Z",
    "updated_at": "2026-04-14T10:32:00Z"
  }
}
```

**Errors:**
- `404 NOT_FOUND` - Scan not found
- `403 FORBIDDEN` - Access denied (not owner)

---

#### GET `/scans/{scan_id}/findings`

Get all findings for a specific scan with filtering and pagination.

**Path Parameters:**
- `scan_id` (UUID) - The scan identifier

**Query Parameters:**
- `severity` (string, optional) - Filter by severity: `critical`, `high`, `medium`, `low`, `info`
- `category` (string, optional) - Filter by category: `security`, `scalability`, `reliability`, `cost`, `observability`
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 50, max: 200) - Items per page

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "finding-uuid",
      "scan_id": "scan-uuid",
      "rule_id": "SEC-001",
      "rule_name": "Missing State Locking",
      "severity": "critical",
      "category": "security",
      "description": "Terraform state backend does not have locking enabled",
      "recommendation": "Enable state locking using DynamoDB or similar service",
      "file_path": "terraform/backend.tf",
      "line_number": 5,
      "resource_name": "aws_s3_bucket.terraform_state",
      "ai_explanation": "Without state locking, concurrent Terraform operations can lead to state corruption...",
      "ai_generated": true,
      "fix_code": "backend \"s3\" {\n  bucket         = \"my-terraform-state\"\n  key            = \"prod/terraform.tfstate\"\n  region         = \"us-east-1\"\n  dynamodb_table = \"terraform-lock\"\n}",
      "fix_example": "Before: backend \"s3\" { bucket = \"my-terraform-state\" }\nAfter: backend \"s3\" { ... dynamodb_table = \"terraform-lock\" }",
      "best_practices": [
        "Always enable state locking for production environments",
        "Use DynamoDB for locking with S3 backend",
        "Ensure DynamoDB table has appropriate IAM permissions"
      ],
      "confidence_score": 0.95,
      "documentation_url": "https://www.terraform.io/language/settings/backends/s3",
      "created_at": "2026-04-14T10:31:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total_count": 12,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false,
    "severity_counts": {
      "critical": 1,
      "high": 3,
      "medium": 5,
      "low": 2,
      "info": 1
    }
  }
}
```

---

#### GET `/scan/status/{scan_id}`

Get real-time scan progress (for polling when WebSocket is not available).

**Path Parameters:**
- `scan_id` (UUID) - The scan identifier

**Response (200 OK):**
```json
{
  "data": {
    "id": "scan-uuid",
    "status": "processing",
    "progress": 65,
    "current_step": "Running security rules",
    "status_message": "Analyzing Kubernetes configurations...",
    "error_message": null,
    "detected_technologies": ["Docker", "Terraform", "Kubernetes"],
    "files_scanned": 12,
    "created_at": "2026-04-14T10:30:00Z",
    "estimated_completion": "2026-04-14T10:32:00Z"
  }
}
```

---

#### POST `/scans/{scan_id}/cancel`

Cancel a running scan.

**Path Parameters:**
- `scan_id` (UUID) - The scan identifier

**Response (200 OK):**
```json
{
  "data": {
    "id": "scan-uuid",
    "status": "cancelled",
    "message": "Scan cancelled successfully",
    "error_message": "Scan cancelled by user"
  }
}
```

**Errors:**
- `400 BAD_REQUEST` - Scan already completed or failed
- `404 NOT_FOUND` - Scan not found
- `403 FORBIDDEN` - Access denied

---

#### DELETE `/scans/{scan_id}`

Delete a scan and all associated findings.

**Path Parameters:**
- `scan_id` (UUID) - The scan identifier

**Response (200 OK):**
```json
{
  "data": {
    "message": "Scan deleted successfully",
    "deleted_findings_count": 12
  }
}
```

**Errors:**
- `404 NOT_FOUND` - Scan not found
- `403 FORBIDDEN` - Access denied

---

### 4.3 AI Suggestion Endpoints

#### POST `/ai-suggestions/generate`

Generate AI suggestions for a specific finding.

**Request:**
```json
{
  "finding_id": "finding-uuid",
  "include_fix": true,
  "include_examples": true
}
```

**Response (200 OK):**
```json
{
  "data": {
    "finding_id": "finding-uuid",
    "explanation": "Without state locking, concurrent Terraform operations can lead to state corruption and inconsistent infrastructure...",
    "impact_analysis": "This issue poses a critical risk to production environments where multiple team members or CI/CD pipelines may run Terraform simultaneously...",
    "fix_code": "backend \"s3\" {\n  bucket         = \"my-terraform-state\"\n  key            = \"prod/terraform.tfstate\"\n  region         = \"us-east-1\"\n  dynamodb_table = \"terraform-lock\"\n}",
    "fix_example": "Before: backend \"s3\" { bucket = \"my-terraform-state\" }\nAfter: backend \"s3\" { ... dynamodb_table = \"terraform-lock\" }",
    "best_practices": [
      "Always enable state locking for production environments",
      "Use DynamoDB for locking with S3 backend",
      "Ensure DynamoDB table has appropriate IAM permissions"
    ],
    "confidence_score": 0.95,
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "tokens_used": 450,
    "generated_at": "2026-04-14T10:31:00Z"
  }
}
```

**Errors:**
- `404 NOT_FOUND` - Finding not found
- `503 SERVICE_UNAVAILABLE` - AI service unavailable

---

#### POST `/ai-suggestions/generate-fix`

Generate AI fix code for a specific finding with before/after diff.

**Request:**
```json
{
  "finding_id": "finding-uuid",
  "file_content": "backend \"s3\" {\n  bucket = \"my-terraform-state\"\n}",
  "include_full_example": true
}
```

**Response (200 OK):**
```json
{
  "data": {
    "finding_id": "finding-uuid",
    "before_code": "backend \"s3\" {\n  bucket = \"my-terraform-state\"\n}",
    "after_code": "backend \"s3\" {\n  bucket         = \"my-terraform-state\"\n  key            = \"prod/terraform.tfstate\"\n  region         = \"us-east-1\"\n  dynamodb_table = \"terraform-lock\"\n  encrypt        = true\n}",
    "unified_diff": "--- a/terraform/backend.tf\n+++ b/terraform/backend.tf\n@@ -1,3 +1,7 @@\n backend \"s3\" {\n-  bucket = \"my-terraform-state\"\n+  bucket         = \"my-terraform-state\"\n+  key            = \"prod/terraform.tfstate\"\n+  region         = \"us-east-1\"\n+  dynamodb_table = \"terraform-lock\"\n+  encrypt        = true\n }",
    "explanation": "Added DynamoDB table for state locking, encryption, and proper key structure...",
    "confidence_score": 0.92,
    "generated_at": "2026-04-14T10:31:00Z"
  }
}
```

---

### 4.4 GitHub Integration Endpoints

#### GET `/github/branches`

Fetch available branches for a GitHub repository.

**Query Parameters:**
- `repo_url` (string, required) - Full GitHub repository URL

**Response (200 OK):**
```json
{
  "data": {
    "repository_url": "https://github.com/example/infrastructure",
    "default_branch": "main",
    "branches": [
      {
        "name": "main",
        "protected": true,
        "commit_sha": "abc123def456"
      },
      {
        "name": "develop",
        "protected": false,
        "commit_sha": "def456ghi789"
      },
      {
        "name": "feature/new-infra",
        "protected": false,
        "commit_sha": "ghi789jkl012"
      }
    ]
  }
}
```

**Errors:**
- `400 BAD_REQUEST` - Invalid repository URL
- `404 NOT_FOUND` - Repository not found
- `403 FORBIDDEN` - Private repository without access

---

#### POST `/github/create-pr`

Create a GitHub Pull Request with AI-generated fixes.

**Request:**
```json
{
  "scan_id": "scan-uuid",
  "finding_ids": ["finding-uuid-1", "finding-uuid-2"],
  "branch_name": "devarchai/fix-security-issues",
  "commit_message": "Fix critical security issues detected by DevArchAI",
  "pr_title": "🔒 Fix critical security issues (DevArchAI)",
  "pr_description": "This PR addresses critical security issues identified by DevArchAI scan..."
}
```

**Response (201 Created):**
```json
{
  "data": {
    "pr_id": "pr-uuid",
    "scan_id": "scan-uuid",
    "github_pr_number": 42,
    "github_pr_url": "https://github.com/example/infrastructure/pull/42",
    "branch_name": "devarchai/fix-security-issues",
    "title": "🔒 Fix critical security issues (DevArchAI)",
    "status": "open",
    "findings_fixed": ["finding-uuid-1", "finding-uuid-2"],
    "score_before": 65.0,
    "score_after": 85.0,
    "created_at": "2026-04-14T10:35:00Z"
  }
}
```

**Errors:**
- `400 BAD_REQUEST` - Invalid scan or findings
- `403 FORBIDDEN` - GitHub token not connected
- `409 CONFLICT` - Branch already exists

---

#### POST `/github/webhook`

Handle GitHub webhook events (PR merged, closed, etc.).

**Headers:**
```http
X-Hub-Signature-256: sha256=abc123...
X-GitHub-Event: pull_request
Content-Type: application/json
```

**Request (PR Merged):**
```json
{
  "action": "closed",
  "pull_request": {
    "number": 42,
    "merged": true,
    "head": {
      "ref": "devarchai/fix-security-issues"
    }
  },
  "repository": {
    "full_name": "example/infrastructure"
  }
}
```

**Response (200 OK):**
```json
{
  "data": {
    "message": "Webhook processed successfully",
    "pr_number": 42,
    "status": "merged"
  }
}
```

---

### 4.5 Billing Endpoints

#### POST `/billing/checkout`

Create a payment checkout session for subscription upgrade.

**Request:**
```json
{
  "plan": "pro",
  "billing": "monthly"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "checkout_url": "https://checkout.stripe.com/pay/cs_test_abc123...",
    "session_id": "cs_test_abc123",
    "plan": "pro",
    "amount": 9900,
    "currency": "usd",
    "expires_at": "2026-04-14T11:00:00Z"
  }
}
```

---

#### POST `/billing/webhook`

Handle payment provider webhooks (Stripe, Razorpay).

**Headers:**
```http
Stripe-Signature: t=1234567890,v1=abc123...
Content-Type: application/json
```

**Request (Stripe):**
```json
{
  "id": "evt_abc123",
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_test_abc123",
      "customer": "cus_abc123",
      "subscription": "sub_abc123",
      "metadata": {
        "user_id": "user-uuid",
        "plan": "pro"
      }
    }
  }
}
```

**Response (200 OK):**
```json
{
  "data": {
    "message": "Webhook processed successfully",
    "event_type": "checkout.session.completed",
    "subscription_id": "sub-uuid"
  }
}
```

---

### 4.6 Report Endpoints

#### GET `/reports/{scan_id}/download`

Download scan report in various formats.

**Path Parameters:**
- `scan_id` (UUID) - The scan identifier

**Query Parameters:**
- `format` (string, default: `json`) - Report format: `json`, `pdf`, `excel`, `csv`

**Response (200 OK):**
```json
{
  "data": {
    "download_url": "https://s3.amazonaws.com/devarchai-reports/scan-uuid.pdf?X-Amz-Algorithm=...",
    "format": "pdf",
    "expires_at": "2026-04-14T10:45:00Z",
    "file_size_bytes": 245678
  }
}
```

**Errors:**
- `404 NOT_FOUND` - Scan not found
- `400 BAD_REQUEST` - Invalid format

---

### 4.7 Dashboard Endpoints

#### GET `/dashboard/metrics`

Get dashboard analytics and metrics for the current user.

**Response (200 OK):**
```json
{
  "data": {
    "total_scans": 150,
    "completed_scans": 142,
    "failed_scans": 8,
    "average_score": 78.5,
    "score_trend": [
      {"date": "2026-04-01", "score": 72.0},
      {"date": "2026-04-07", "score": 75.5},
      {"date": "2026-04-14", "score": 78.5}
    ],
    "severity_distribution": {
      "critical": 5,
      "high": 18,
      "medium": 42,
      "low": 25,
      "info": 12
    },
    "category_scores": {
      "security": 82.0,
      "scalability": 75.0,
      "reliability": 80.0,
      "cost": 70.0,
      "observability": 85.0
    },
    "recent_scans": [
      {
        "id": "scan-uuid",
        "repository_name": "example/infrastructure",
        "status": "completed",
        "overall_score": 85.5,
        "created_at": "2026-04-14T10:30:00Z"
      }
    ],
    "top_issues": [
      {
        "rule_id": "SEC-001",
        "rule_name": "Missing State Locking",
        "occurrences": 12,
        "severity": "critical"
      }
    ]
  }
}
```

---

## 5. Error Codes

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | Authentication required |
| `INVALID_TOKEN` | 401 | Invalid or expired token |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Scan-Specific Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SCAN_NOT_FOUND` | 404 | Scan ID does not exist |
| `SCAN_ALREADY_COMPLETED` | 400 | Scan already finished |
| `SCAN_TIMEOUT` | 504 | Scan exceeded time limit |
| `REPOSITORY_NOT_FOUND` | 404 | GitHub repository not found |
| `REPOSITORY_ACCESS_DENIED` | 403 | No access to private repository |
| `INVALID_BRANCH` | 400 | Branch does not exist |

---

## 6. Rate Limiting

### Rate Limits by Plan

| Plan | Requests/Minute | Scans/Hour | Concurrent Scans |
|------|-----------------|------------|------------------|
| Free | 100 | 10 | 1 |
| Plus | 500 | 50 | 3 |
| Pro | 1000 | 200 | 10 |
| Enterprise | 5000 | Unlimited | 50 |

### Rate Limit Headers

**Response Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1713097260
Retry-After: 60  # Only when rate limit exceeded
```

### Rate Limit Exceeded Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "limit": 100,
      "remaining": 0,
      "reset_at": "2026-04-14T10:31:00Z",
      "retry_after_seconds": 60
    },
    "timestamp": "2026-04-14T10:30:00Z"
  }
}
```

---

## 7. WebSocket API

### Endpoint: `/ws/scan/{scan_id}`

Real-time scan progress updates via WebSocket.

### Connection

```javascript
const ws = new WebSocket(`wss://api.devarchai.com/ws/scan/${scanId}`);
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message);
};
```

### Message Types

**progress_update:**
```json
{
  "type": "progress_update",
  "data": {
    "progress": 65,
    "current_step": "Running security rules",
    "detected_stack": ["Docker", "Terraform", "Kubernetes"],
    "files_list": ["Dockerfile", "main.tf", "deployment.yaml"],
    "logs": [
      "[10:30:15] Cloning repository...",
      "[10:30:20] Detected Docker configuration",
      "[10:30:25] Parsing Terraform files..."
    ]
  }
}
```

**log_message:**
```json
{
  "type": "log_message",
  "data": {
    "message": "Running SEC-001: Missing State Locking check...",
    "timestamp": "2026-04-14T10:31:00Z",
    "level": "info"
  }
}
```

**stack_detected:**
```json
{
  "type": "stack_detected",
  "data": {
    "technology": "Kubernetes",
    "files": ["deployment.yaml", "service.yaml", "ingress.yaml"]
  }
}
```

**scan_complete:**
```json
{
  "type": "scan_complete",
  "data": {
    "scan_id": "scan-uuid",
    "overall_score": 85.5,
    "findings_count": 12,
    "completed_at": "2026-04-14T10:32:00Z"
  }
}
```

**scan_failed:**
```json
{
  "type": "scan_failed",
  "data": {
    "error": "Repository not found",
    "error_code": "REPOSITORY_NOT_FOUND"
  }
}
```

---

## 8. SDK Examples

### Python SDK

```python
from devarchai import DevArchAIClient

client = DevArchAIClient(api_key="dck_abc123...")

# Start a scan
scan = client.scans.start(
    repository_url="https://github.com/example/infrastructure",
    branch="main"
)
print(f"Scan started: {scan.id}")

# Wait for completion
scan.wait_for_completion()

# Get findings
findings = scan.get_findings(severity="critical")
for finding in findings:
    print(f"{finding.rule_id}: {finding.description}")

# Generate AI fix
fix = finding.generate_fix()
print(f"Fix: {fix.after_code}")

# Create PR
pr = scan.create_pr(
    findings=findings,
    branch_name="devarchai/fix-security",
    pr_title="Fix security issues"
)
print(f"PR created: {pr.github_pr_url}")
```

### JavaScript SDK

```javascript
import { DevArchAIClient } from '@devarchai/sdk';

const client = new DevArchAIClient({ apiKey: 'dck_abc123...' });

// Start a scan
const scan = await client.scans.start({
  repositoryUrl: 'https://github.com/example/infrastructure',
  branch: 'main'
});
console.log(`Scan started: ${scan.id}`);

// Wait for completion
await scan.waitForCompletion();

// Get findings
const findings = await scan.getFindings({ severity: 'critical' });
findings.forEach(finding => {
  console.log(`${finding.rule_id}: ${finding.description}`);
});

// Generate AI fix
const fix = await findings[0].generateFix();
console.log(`Fix: ${fix.afterCode}`);

// Create PR
const pr = await scan.createPR({
  findings: findings,
  branchName: 'devarchai/fix-security',
  prTitle: 'Fix security issues'
});
console.log(`PR created: ${pr.githubPrUrl}`);
```

---

## 9. Changelog

### v1.0.0 (April 14, 2026)
- Initial release
- Authentication endpoints
- Scan management endpoints
- AI suggestion endpoints
- GitHub integration endpoints
- Billing endpoints
- WebSocket real-time updates
- Rate limiting support

---

*This document is maintained by the DevArchAI engineering team. Last reviewed: April 14, 2026.*
