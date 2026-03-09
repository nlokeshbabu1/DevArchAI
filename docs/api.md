# DevArchAI API Documentation

## Base URL

- Development: `http://localhost:8000`
- Production: `https://api.devarchai.com`

## Authentication

Currently, the API does not require authentication for the MVP. In production, JWT-based authentication will be implemented.

## Endpoints

### Health Check

#### GET `/api/v1/health`

Check the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "api": "up",
    "database": "up",
    "cache": "up"
  }
}
```

---

### Analysis

#### POST `/api/v1/analyze`

Start analysis of a GitHub repository.

**Request Body:**
```json
{
  "repository_url": "https://github.com/example/infrastructure",
  "branch": "main",
  "commit_hash": null,
  "include_ai_explanations": true
}
```

**Response (202 Accepted):**
```json
{
  "id": "job_abc123",
  "repository_url": "https://github.com/example/infrastructure",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": null,
  "error_message": null,
  "report_id": null
}
```

---

#### GET `/api/v1/analysis/{job_id}`

Get the status of an analysis job.

**Path Parameters:**
- `job_id` - The job ID returned from the analyze endpoint

**Response:**
```json
{
  "id": "job_abc123",
  "repository_url": "https://github.com/example/infrastructure",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:00Z",
  "error_message": null,
  "report_id": "rpt_xyz789"
}
```

**Status Values:**
- `pending` - Job is queued
- `processing` - Job is being processed
- `completed` - Job completed successfully
- `failed` - Job failed

---

#### GET `/api/v1/analysis/{job_id}/report`

Get the analysis report for a completed job.

**Response:**
```json
{
  "id": "rpt_xyz789",
  "repository_url": "https://github.com/example/infrastructure",
  "repository_name": "infrastructure",
  "commit_hash": "abc123def",
  "created_at": "2024-01-15T10:32:00Z",
  "analysis_duration_seconds": 45.2,
  "overall_score": 72.5,
  "category_scores": [
    {
      "category": "security",
      "score": 65.0,
      "findings_count": 5,
      "critical_count": 1,
      "high_count": 2,
      "medium_count": 1,
      "low_count": 1
    },
    {
      "category": "scalability",
      "score": 80.0,
      "findings_count": 2,
      "critical_count": 0,
      "high_count": 1,
      "medium_count": 1,
      "low_count": 0
    }
  ],
  "findings": [
    {
      "rule_id": "SEC-001",
      "rule_name": "Missing State Locking",
      "severity": "critical",
      "category": "security",
      "description": "Terraform state backend does not have locking enabled",
      "recommendation": "Enable state locking using DynamoDB",
      "file_path": "terraform/backend.tf",
      "line_number": null,
      "ai_explanation": "Without state locking, concurrent runs can corrupt...",
      "impact_analysis": "This can lead to infrastructure drift and...",
      "confidence_score": 0.95
    }
  ],
  "summary": {
    "critical": 1,
    "high": 3,
    "medium": 5,
    "low": 4,
    "info": 2
  },
  "executive_summary": "The infrastructure shows moderate production readiness...",
  "risk_analysis": "Immediate risks include state corruption potential...",
  "prioritized_recommendations": [
    "Enable Terraform state locking immediately",
    "Configure resource limits for all containers",
    "Implement Horizontal Pod Autoscaler"
  ],
  "files_analyzed": [
    "terraform/main.tf",
    "terraform/backend.tf",
    "kubernetes/deployment.yaml"
  ]
}
```

---

### Reports

#### GET `/api/v1/reports/{report_id}`

Get an analysis report by ID.

**Response:** Same as `/api/v1/analysis/{job_id}/report`

---

#### GET `/api/v1/reports/{report_id}/download`

Download an analysis report.

**Query Parameters:**
- `format` - Response format (default: `json`, options: `json`, `pdf`)

**Response:** File download with appropriate Content-Type header

---

## Error Responses

### 400 Bad Request
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [...]
  }
}
```

### 404 Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later."
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

---

## Rate Limiting

- Default: 100 requests per minute per IP
- Analysis jobs: 10 concurrent jobs per user

---

## OpenAPI Specification

Interactive API documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
