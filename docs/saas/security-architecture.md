# DevArchAI - Security Architecture Document

> **Version:** 1.0.0  
> **Status:** Production-Ready  
> **Last Updated:** April 14, 2026  
> **Classification:** Confidential

---

## 1. Overview

This document defines the complete security architecture for DevArchAI, covering authentication, authorization, data protection, infrastructure security, and compliance requirements.

**Security Principles:**
- Defense in depth
- Least privilege access
- Zero trust architecture
- Encryption at rest and in transit
- Comprehensive audit logging

---

## 2. Authentication Security

### 2.1 JWT Token Security

**Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "type": "access",
    "exp": 1713097200,
    "iat": 1713095400,
    "jti": "unique-token-id"
  }
}
```

**Security Measures:**
- **Algorithm:** HMAC-SHA256 (HS256)
- **Secret Key:** Minimum 256-bit random string
- **Access Token Expiry:** 30 minutes (short-lived)
- **Refresh Token Expiry:** 7 days
- **Token Rotation:** New refresh token issued on each refresh
- **Token Blacklisting:** Revoked tokens stored in Redis with TTL
- **JTI Claim:** Unique token ID for revocation tracking

**Token Storage:**
```
Frontend (Browser):
  - localStorage: access_token, refresh_token
  - Encrypted: No (tokens are self-contained)
  - Risk: XSS can steal tokens
  - Mitigation: CSP headers, input sanitization

Backend (Server):
  - Redis: Blacklisted tokens (TTL = token expiry)
  - Database: API key hashes (never store plain keys)
```

### 2.2 Password Security

**Hashing Algorithm:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Hash password
hashed = pwd_context.hash("SecureP@ssw0rd!")

# Verify password
is_valid = pwd_context.verify("SecureP@ssw0rd!", hashed)
```

**Password Requirements:**
- Minimum length: 8 characters
- Maximum length: 128 characters
- Must contain: uppercase, lowercase, number, special character
- Blocked passwords: Common passwords, breached passwords (HaveIBeenPwned API)
- Rate limiting: 5 failed attempts per 15 minutes

**Password Reset Flow:**
```
1. User requests password reset → POST /auth/reset-request
2. Generate secure token (UUID v4, 1-hour expiry)
3. Send email with reset link: https://app.devarchai.com/reset?token=xxx
4. User clicks link, enters new password → POST /auth/reset
5. Validate token (not expired, not used)
6. Hash new password, update database
7. Invalidate all existing tokens (force re-login)
8. Send confirmation email
```

### 2.3 GitHub OAuth Security

**OAuth Flow:**
```
1. User clicks "Login with GitHub"
2. Backend generates OAuth state parameter (CSRF protection)
3. Redirect to GitHub:
   https://github.com/login/oauth/authorize?
     client_id=xxx&
     redirect_uri=yyy&
     scope=user:email,read:user&
     state=random-uuid
4. User authorizes app
5. GitHub redirects to /auth/github/callback?code=xxx&state=yyy
6. Backend validates state parameter (prevent CSRF)
7. Exchange code for access token (server-side, secure)
8. Fetch user info from GitHub API
9. Create/update user in database
10. Generate JWT tokens
11. Return tokens to frontend
```

**Security Measures:**
- **State Parameter:** UUID v4, stored in session, validated on callback
- **PKCE:** Proof Key for Code Exchange (for public clients)
- **Scope Minimization:** Only request `user:email` and `read:user`
- **Token Encryption:** GitHub access tokens encrypted at rest (AES-256)
- **Token Refresh:** GitHub tokens refreshed automatically on expiry
- **Revocation:** User can revoke GitHub access from settings

**GitHub Token Permissions:**
```
Required Scopes:
  - user:email → Access user's email addresses
  - read:user → Access user's profile info
  - repo (optional) → Access private repositories

NOT Requested:
  - admin:repo_hook → No webhook management
  - delete_repo → No repository deletion
  - gist → No gist access
  - workflow → No workflow trigger access
```

---

## 3. Authorization & Access Control

### 3.1 Role-Based Access Control (RBAC)

**Roles:**
```
user → Basic user, can scan own repositories
admin → Can manage organization members
owner → Full access, billing, organization settings
viewer → Read-only access to scans and reports
```

**Permission Matrix:**
```
Action                  | user | admin | owner | viewer
------------------------|------|-------|-------|-------
Create scan             | ✓    | ✓     | ✓     | ✗
View own scans          | ✓    | ✓     | ✓     | ✓
Delete own scans        | ✓    | ✓     | ✓     | ✗
View org scans          | ✗    | ✓     | ✓     | ✓
Create PR               | ✓    | ✓     | ✓     | ✗
Manage members          | ✗    | ✓     | ✓     | ✗
Manage billing          | ✗    | ✗     | ✓     | ✗
View audit logs         | ✗    | ✓     | ✓     | ✗
```

**Implementation:**
```python
from fastapi import Depends, HTTPException

def require_role(required_role: str):
    def checker(current_user: User = Depends(get_current_user)):
        role_hierarchy = {
            'viewer': 0,
            'user': 1,
            'admin': 2,
            'owner': 3
        }
        
        if role_hierarchy.get(current_user.role, 0) < role_hierarchy[required_role]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return checker

# Usage
@router.post("/scans")
async def create_scan(
    scan_data: ScanCreate,
    current_user: User = Depends(require_role('user'))
):
    ...
```

### 3.2 Resource-Level Authorization

**Ownership Checks:**
```python
async def verify_scan_ownership(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    scan = await db.get(Scan, scan_id)
    
    if not scan:
        raise HTTPException(404, "Scan not found")
    
    # Allow if user owns the scan
    if scan.user_id == current_user.id:
        return scan
    
    # Allow if user is org admin/owner
    if scan.organization_id:
        membership = await get_org_membership(
            db, current_user.id, scan.organization_id
        )
        if membership and membership.role in ['admin', 'owner']:
            return scan
    
    raise HTTPException(403, "Access denied")
```

---

## 4. Data Protection

### 4.1 Encryption at Rest

**Sensitive Fields:**
```python
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, secret_key: str):
        self.cipher = Fernet(secret_key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Usage
email_encrypted = encryption_service.encrypt("user@example.com")
github_token_encrypted = encryption_service.encrypt("ghp_xxx...")
```

**Encrypted Fields:**
- `users.email_encrypted` - User email address
- `users.github_access_token` - GitHub OAuth token
- `users.api_key` - API key (hashed, not encrypted)
- Payment metadata (if stored)

**Database Encryption:**
```
PostgreSQL:
  - TDE (Transparent Data Encryption): Enabled at disk level
  - Column-level encryption: Application-level (AES-256)
  - Backups: Encrypted with AWS KMS

Redis:
  - In-memory: Not encrypted (trusted network)
  - Persistence (RDB/AOF): Encrypted at rest
  - TLS: Enabled for client connections
```

### 4.2 Encryption in Transit

**TLS Configuration:**
```
All external communication:
  - HTTPS (TLS 1.2+) for all API endpoints
  - HSTS (HTTP Strict Transport Security) enabled
  - Certificate: Let's Encrypt (auto-renewal)

Internal communication (Kubernetes):
  - mTLS (mutual TLS) between services
  - Service mesh: Istio (optional)
  - Certificate rotation: Automatic

Database connections:
  - PostgreSQL: SSL mode = require
  - Redis: TLS enabled
  - AWS S3: HTTPS only
```

**CSP Headers:**
```http
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'unsafe-inline' https://js.stripe.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https://avatars.githubusercontent.com;
  connect-src 'self' https://api.devarchai.com wss://api.devarchai.com;
  frame-src https://js.stripe.com;
```

### 4.3 Email Privacy

**Hash-Based Lookups:**
```python
import hashlib

def hash_email(email: str) -> str:
    """Create SHA-256 hash for email lookup."""
    return hashlib.sha256(email.lower().strip()).hexdigest()

# Login flow
email_hash = hash_email("User@Example.com")
user = db.query(User).filter(User.email_hash == email_hash).first()

# Benefits:
# - Fast indexed lookups
# - No plaintext email in query logs
# - Case-insensitive matching
```

---

## 5. Infrastructure Security

### 5.1 Network Security

**Firewall Rules:**
```
Inbound:
  - Port 443 (HTTPS): Public access
  - Port 80 (HTTP): Redirect to HTTPS
  - Port 5432 (PostgreSQL): Backend only
  - Port 6379 (Redis): Backend only
  - All other ports: DENY

Outbound:
  - Port 443 (HTTPS): GitHub API, Stripe, AWS S3, LLM APIs
  - Port 587 (SMTP): Email service
  - All other ports: DENY
```

**VPC Architecture:**
```
┌─────────────────────────────────────────────┐
│                  VPC                         │
│                                              │
│  ┌──────────────┐  ┌──────────────┐         │
│  │  Public      │  │  Private     │         │
│  │  Subnet      │  │  Subnet      │         │
│  │              │  │              │         │
│  │ - Load       │  │ - Backend    │         │
│  │   Balancer   │  │ - Database   │         │
│  │ - NAT Gateway│  │ - Redis      │         │
│  └──────────────┘  └──────────────┘         │
│                                              │
└─────────────────────────────────────────────┘
```

### 5.2 Container Security

**Docker Best Practices:**
```dockerfile
# Use minimal base image
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m appuser
USER appuser

# No secrets in image
ENV DATABASE_URL=${DATABASE_URL}
ENV SECRET_KEY=${SECRET_KEY}

# Read-only filesystem (except /tmp)
RUN chmod 555 /app
VOLUME /tmp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Kubernetes Security:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: backend
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
  
  containers:
  - name: backend
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
    
    resources:
      limits:
        memory: "1Gi"
        cpu: "500m"
      requests:
        memory: "512Mi"
        cpu: "250m"
    
    # No host network
    hostNetwork: false
    hostPID: false
    hostIPC: false
```

### 5.3 Secret Management

**Environment Variables:**
```
Development:
  - .env file (gitignored)
  - docker-compose.yml environment section

Production:
  - Kubernetes Secrets (encrypted at rest)
  - AWS Secrets Manager (preferred)
  - HashiCorp Vault (enterprise)

NEVER commit secrets to Git:
  - .env in .gitignore
  - pre-commit hooks detect secrets
  - GitHub secret scanning enabled
```

**AWS Secrets Manager:**
```python
import boto3

def get_secret(secret_name: str) -> dict:
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
db_credentials = get_secret('devarchai/prod/database')
DATABASE_URL = f"postgresql://{db_credentials['username']}:{db_credentials['password']}@{db_credentials['host']}/{db_credentials['dbname']}"
```

---

## 6. Payment Security

### 6.1 PCI Compliance

**Stripe Integration:**
```
✅ DO:
  - Use Stripe Elements (hosted payment fields)
  - Process payments server-side with Stripe SDK
  - Store only Stripe customer/subscription IDs
  - Validate webhook signatures
  - Use idempotency keys for retries

❌ DON'T:
  - Store credit card numbers
  - Store CVV codes
  - Log full payment details
  - Handle raw card data
```

**Webhook Verification:**
```python
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(400, "Invalid signature")
    
    # Process event
    if event.type == "checkout.session.completed":
        handle_successful_payment(event.data.object)
    
    return {"received": True}
```

### 6.2 Subscription Security

**Preventing Subscription Fraud:**
```
1. Email verification required before checkout
2. Rate limit checkout creation (5 per hour)
3. Validate plan exists and pricing is correct
4. Use Stripe's built-in fraud detection
5. Monitor for unusual patterns:
   - Multiple subscriptions with same card
   - Rapid upgrade/downgrade cycles
   - Chargeback patterns
```

---

## 7. AWS S3 Security

### 7.1 Bucket Configuration

**Bucket Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::devarchai-reports/*",
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "AllowBackendAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789:role/backend-role"
      },
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::devarchai-reports/*"
    }
  ]
}
```

**Access Control:**
```
Public Access: BLOCKED (all 4 settings enabled)
Encryption: AES-256 (server-side)
Versioning: Enabled (accidental deletion protection)
Lifecycle Rules:
  - Transition to IA after 30 days
  - Delete temporary files after 7 days
  - Delete old versions after 90 days
```

### 7.2 Presigned URLs

**Secure Download:**
```python
import boto3
from botocore.exceptions import ClientError

def generate_presigned_url(scan_id: str, format: str) -> str:
    s3_client = boto3.client('s3')
    
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': 'devarchai-reports',
                'Key': f'reports/{scan_id}.{format}'
            },
            ExpiresIn=900  # 15 minutes
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise
```

**Security Benefits:**
- Time-limited access (15 min default)
- No need to expose S3 bucket publicly
- User authentication required before URL generation
- Single-use URLs (can be tracked in database)

---

## 8. API Security

### 8.1 Rate Limiting

**Implementation (Redis-based):**
```python
import time
from redis import Redis

class RateLimiter:
    def __init__(self, redis_client: Redis, max_requests: int, window_seconds: int):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window = window_seconds
    
    def is_allowed(self, user_id: str) -> bool:
        key = f"rate_limit:{user_id}"
        current_time = int(time.time())
        window_start = current_time - self.window
        
        # Remove old requests
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        request_count = self.redis.zcard(key)
        
        if request_count >= self.max_requests:
            return False
        
        # Add current request
        self.redis.zadd(key, {str(current_time): current_time})
        self.redis.expire(key, self.window)
        
        return True

# Usage
rate_limiter = RateLimiter(redis_client, max_requests=100, window_seconds=60)

@router.get("/scans")
async def list_scans(current_user: User = Depends(get_current_user)):
    if not rate_limiter.is_allowed(str(current_user.id)):
        raise HTTPException(429, "Rate limit exceeded")
    
    return await get_scans(current_user)
```

### 8.2 Input Validation

**Pydantic Validation:**
```python
from pydantic import BaseModel, field_validator, HttpUrl
import re

class ScanCreate(BaseModel):
    repository_url: HttpUrl
    branch: str = "main"
    commit_hash: str | None = None
    
    @field_validator('branch')
    @classmethod
    def validate_branch(cls, v: str) -> str:
        # Branch name validation
        if not re.match(r'^[a-zA-Z0-9_\-/.]+$', v):
            raise ValueError('Invalid branch name')
        if len(v) > 255:
            raise ValueError('Branch name too long')
        return v
    
    @field_validator('commit_hash')
    @classmethod
    def validate_commit_hash(cls, v: str | None) -> str | None:
        if v and not re.match(r'^[a-f0-9]{40}$', v):
            raise ValueError('Invalid commit hash format')
        return v
```

### 8.3 SQL Injection Prevention

**SQLAlchemy ORM (Safe):**
```python
# ✅ SAFE - Parameterized query
user = await db.execute(
    select(User).where(User.email_hash == email_hash)
)

# ❌ UNSAFE - Raw SQL (never do this)
user = await db.execute(
    text(f"SELECT * FROM users WHERE email_hash = '{email_hash}'")
)
```

### 8.4 XSS Prevention

**Frontend (React):**
```tsx
// ✅ SAFE - React automatically escapes content
<div>{userInput}</div>

// ❌ UNSAFE - Never use dangerouslySetInnerHTML with user input
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// ✅ SAFE - Sanitize HTML if needed
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

**Backend (Response Headers):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

## 9. Audit Logging

### 9.1 Log Structure

```json
{
  "id": "log-uuid",
  "timestamp": "2026-04-14T10:30:00Z",
  "user_id": "user-uuid",
  "action": "scan.create",
  "resource_type": "scan",
  "resource_id": "scan-uuid",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "request_method": "POST",
  "request_path": "/api/v1/scans",
  "status_code": 201,
  "details": {
    "repository_url": "https://github.com/example/infra",
    "branch": "main"
  }
}
```

### 9.2 Logged Actions

```
Authentication:
  - auth.login.success
  - auth.login.failed
  - auth.logout
  - auth.token.refresh
  - auth.password.reset

Scans:
  - scan.create
  - scan.cancel
  - scan.delete
  - scan.result.view

Findings:
  - finding.ai.generate
  - finding.fix.generate

GitHub:
  - github.pr.create
  - github.pr.merged
  - github.webhook.received

Billing:
  - subscription.create
  - subscription.cancel
  - payment.succeeded
  - payment.failed

Admin:
  - user.role.changed
  - org.member.added
  - org.member.removed
```

### 9.3 Log Retention

```
Hot Storage (PostgreSQL): 30 days
Warm Storage (S3): 1 year
Cold Storage (Glacier): 7 years (compliance)

Access Control:
  - Only admins and owners can view audit logs
  - Logs are append-only (no DELETE/UPDATE)
  - Integrity verification with checksums
```

---

## 10. Vulnerability Management

### 10.1 Dependency Scanning

**CI/CD Pipeline:**
```yaml
- name: Security Audit
  run: |
    # Python dependencies
    pip-audit
    safety check
    
    # Node dependencies
    npm audit --audit-level=high
    
    # Docker image
    docker scan backend:latest
    
    # Fail build on critical vulnerabilities
    pip-audit --fail-on=CRITICAL
```

### 10.2 Security Headers

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 10.3 Penetration Testing

**Quarterly Security Audits:**
1. Automated vulnerability scanning
2. Manual penetration testing
3. Social engineering tests
4. API security tests
5. Infrastructure security review

**Bug Bounty Program:**
- Platform: HackerOne or Bugcrowd
- Scope: All production systems
- Rewards: $100 - $10,000 based on severity
- Response time: 24 hours for critical issues

---

## 11. Incident Response

### 11.1 Incident Classification

| Severity | Response Time | Examples |
|----------|---------------|----------|
| P0 - Critical | 15 minutes | Data breach, service down |
| P1 - High | 1 hour | Authentication bypass |
| P2 - Medium | 4 hours | Rate limit bypass |
| P3 - Low | 24 hours | Information disclosure |

### 11.2 Incident Response Process

```
1. Detection → Automated alerts, user reports
2. Triage → Classify severity, assign responder
3. Containment → Isolate affected systems
4. Eradication → Fix vulnerability, patch systems
5. Recovery → Restore services, monitor for recurrence
6. Post-Mortem → Document lessons learned, update runbooks
```

### 11.3 Communication Plan

```
Internal:
  - Slack #security-incidents channel
  - PagerDuty for P0/P1 incidents
  - Weekly security review meeting

External:
  - Status page updates (status.devarchai.com)
  - Email notification for data breaches (72 hours, GDPR)
  - Public post-mortem (within 7 days)
```

---

## 12. Compliance

### 12.1 GDPR Compliance

```
✅ Data Processing Agreement (DPA) with all vendors
✅ Right to access: Users can download their data
✅ Right to deletion: Users can delete their account
✅ Data portability: Export all user data in JSON
✅ Consent management: Explicit consent for data processing
✅ Data Protection Officer (DPO) appointed
✅ Privacy by design: Data minimization, purpose limitation
```

### 12.2 SOC 2 Type II

```
✅ Security: Access controls, encryption, monitoring
✅ Availability: 99.9% uptime SLA, disaster recovery
✅ Confidentiality: NDA with employees, data classification
✅ Privacy: GDPR compliance, data retention policies
✅ Processing Integrity: Quality assurance, error handling
```

### 12.3 Data Residency

```
Primary Region: US East (N. Virginia)
EU Region: EU West (Ireland) - for EU customers
Data Transfer:
  - EU → US: Standard Contractual Clauses (SCCs)
  - Encryption: All data encrypted in transit
  - Access: Only authorized personnel
```

---

## 13. Security Checklist

### Pre-Launch Checklist

- [ ] All dependencies updated to latest stable versions
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured (no wildcards in production)
- [ ] JWT secret key is strong and unique
- [ ] Database credentials rotated
- [ ] AWS S3 bucket policies reviewed
- [ ] Webhook signatures validated
- [ ] Audit logging enabled
- [ ] Penetration test completed
- [ ] Incident response plan documented
- [ ] Backup and recovery tested
- [ ] SSL certificates configured
- [ ] CSP headers tested
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive information

### Ongoing Security Tasks

- [ ] Weekly dependency updates
- [ ] Monthly access review
- [ ] Quarterly penetration tests
- [ ] Annual SOC 2 audit
- [ ] Continuous monitoring and alerting
- [ ] Regular backup testing
- [ ] Security training for developers
- [ ] Incident response drills

---

*This document is maintained by the DevArchAI security team. Last reviewed: April 14, 2026.*
