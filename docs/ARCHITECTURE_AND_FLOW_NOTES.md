# DevArchAI - Complete Architecture & Flow Notes

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Frontend Architecture](#frontend-architecture)
3. [Backend Architecture](#backend-architecture)
4. [API Call Flows](#api-call-flows)
5. [Authentication Flow](#authentication-flow)
6. [Scan Flow](#scan-flow)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Key Components](#key-components)

---

## 🏗️ System Overview

### Tech Stack
**Frontend:**
- React 18 + TypeScript
- Vite 6 (build tool)
- Zustand (state management)
- TanStack Query (data fetching/caching)
- Axios (HTTP client)
- Tailwind CSS + Radix UI (styling)
- Framer Motion (animations)
- React Router v6 (routing)

**Backend:**
- FastAPI 0.116.2 (async Python web framework)
- PostgreSQL 15 + SQLAlchemy 2.0 (async ORM)
- Redis 7 (caching + Celery broker)
- Celery 5.4 (async task queue)
- Multiple LLM Providers (Gemini, OpenAI, Anthropic, Mistral)
- WebSockets (real-time updates)

---

## 🎨 Frontend Architecture

### 1. **State Management (Zustand)**
**File:** `frontend/src/stores/auth-store.ts`

```
AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

Actions:
  - login(token) → Stores token in localStorage + updates state
  - logout() → Clears all storage + redirects to /
  - setUser(user) → Sets user data
  - checkAuth() → Checks localStorage for token on app load
  - fetchUserInfo() → Calls /api/v1/auth/me to get user data
```

**Key Points:**
- Tokens stored in `localStorage` (access_token, refresh_token)
- State persisted via `persist()` middleware
- Auto-checks auth on app mount via `useEffect` in App.tsx

### 2. **API Client (Axios)**
**File:** `frontend/src/api/client.ts`

```typescript
// Configuration
baseURL: ''  // Relative - Vite proxy forwards /api to backend
timeout: 30000ms

// Request Interceptor:
  - Adds Authorization: Bearer {token} from localStorage
  - Adds X-Organization-ID header if available

// Response Interceptor:
  - On 401 error → Tries token refresh via /api/v1/auth/refresh
  - If refresh fails → Clears tokens + redirects to /login
  - If refresh succeeds → Retries original request with new token
```

### 3. **Routing Structure**
**File:** `frontend/src/App.tsx`

```
Public Routes (No Layout):
  / → Landing page
  /scan → Anonymous scan page
  /login → Login page
  /register → Register page
  /auth/github/callback → GitHub OAuth callback
  /pricing → Pricing page

Protected Routes (With Layout):
  /dashboard → User dashboard
  /scans → Scan history
  /scans/:id → Scan results
  /history → Scan history page
  /findings → All findings
  /repositories → Repository management
  /billing → Billing/subscription
  /settings → User settings
  /ai-suggestions → AI recommendations
  /integrations → GitHub integrations
```

**ProtectedRoute Component:**
- Checks `isAuthenticated` from Zustand store
- Calls `checkAuth()` on mount
- Redirects to `/login` if not authenticated
- Shows loading spinner while checking auth

---

## 🔧 Backend Architecture

### 1. **Application Structure**
**File:** `backend/app/main.py`

```
FastAPI App Lifespan:
  Startup:
    1. Initialize database connection
    2. Initialize Redis cache
    3. Initialize WebSocket manager
    4. Register middleware (CORS, error tracking, request logging)
    5. Register routers
  
  Shutdown:
    1. Close Redis connection
    2. Close database connection
```

**Middleware Stack:**
1. CORS (allow frontend origins)
2. TrustedHost (production only)
3. RequestLoggingMiddleware
4. ErrorTrackingMiddleware

**Endpoints:**
- `/api/v1/*` → Main API router
- `/ws/scan/{scan_id}` → WebSocket for real-time scan progress
- `/metrics` → Prometheus metrics
- `/health` → Health check
- `/api/v1/ready` → Readiness check (DB connectivity)

### 2. **API Routes**
**File:** `backend/app/api/v1/router.py`

```
Registered Routers:
  - /auth → Authentication (login, register, GitHub OAuth)
  - /scans → Scan management (create, list, get, cancel)
  - /scan/start → Unified scan endpoint (guest + authenticated)
  - /repositories → Repository CRUD
  - /findings → Finding queries
  - /ai-suggestions → AI-generated recommendations
  - /billing → Payment/subscription (Stripe, Razorpay)
  - /github → GitHub OAuth + repo sync
  - /reports → Report generation
  - /health → Health checks
  - /public-scans → Public scan data
  - /dashboard → Dashboard metrics
  - /unified-scan → Unified scan pipeline
```

### 3. **Database Models**
**Key Models:**
```
User:
  - id, email_encrypted, email_hash, username
  - hashed_password, full_name, avatar_url
  - github_id, github_access_token
  - role, is_active, is_verified
  - current_org_id, subscription_plan

Repository:
  - id, user_id, name, url, default_branch
  - github_repo_id, is_private

Scan:
  - id, user_id, repository_id
  - repository_url, branch, commit_hash
  - status (pending/processing/completed/failed)
  - progress (0-100), status_message
  - overall_score, security_score, scalability_score, etc.
  - detected_stack (JSON), celery_task_id
  - started_at, completed_at, analysis_duration_seconds

Finding:
  - id, scan_id, rule_id, rule_name
  - severity, category, description, recommendation
  - file_path, line_number
  - ai_explanation, ai_generated (boolean)
  - fix_code, fix_example, best_practices
  - confidence_score, documentation_url
```

---

## 🔄 API Call Flows

### 1. **Login Flow**

```
Frontend (Login.tsx):
  1. User enters email + password
  2. Calls authApi.login({ email, password })
     → POST /api/v1/auth/login
  
Backend (auth.py):
  1. Hash email → lookup user by email_hash
  2. Verify password with bcrypt
  3. Check user.is_active
  4. Generate tokens:
     - access_token (JWT, expires 30 min)
     - refresh_token (JWT, expires 7 days)
  5. Update user.last_login_at
  6. Return { access_token, refresh_token }
  
Frontend (after login):
  1. Store tokens in localStorage
  2. Call login(token) → updates Zustand state
  3. Call fetchUserInfo() → GET /api/v1/auth/me
  4. Set user data in Zustand
  5. Check for redirect intent:
     - If upgradeIntent → Call /api/v1/billing/checkout → redirect to payment
     - If postLoginRedirect → Navigate to saved path
     - Default → Navigate to /dashboard
```

**Token Refresh Flow:**
```
Frontend (api/client.ts):
  1. API call returns 401
  2. Axios interceptor catches error
  3. Calls POST /api/v1/auth/refresh with refresh_token
  4. Backend validates refresh_token → returns new tokens
  5. Store new tokens in localStorage
  6. Retry original request with new access_token
  
Backend (auth.py /refresh):
  1. Extract refresh_token from Authorization header
  2. Decode JWT → validate type="refresh"
  3. Lookup user by user_id
  4. Generate new access_token + refresh_token
  5. Return new tokens
```

### 2. **GitHub OAuth Flow**

```
Frontend:
  1. User clicks "Login with GitHub"
  2. Calls githubAuthApi.getAuthorizationUrl()
     → GET /api/v1/auth/github/url
  3. Backend returns OAuth URL
  4. Redirect user to GitHub: https://github.com/login/oauth/authorize
  
GitHub:
  1. User authorizes app
  2. GitHub redirects to /auth/github/callback?code={authorization_code}
  
Frontend (GithubCallback.tsx):
  1. Extract code from URL
  2. Call POST /api/v1/auth/github/callback with code
  
Backend (auth.py /github/callback):
  1. Exchange code for access token:
     POST https://github.com/login/oauth/access_token
  2. Get user info from GitHub:
     GET https://api.github.com/user
  3. Get user emails (if needed):
     GET https://api.github.com/user/emails
  4. Find or create user in DB (by email_hash)
  5. Update user.github_id, github_access_token
  6. Generate JWT tokens
  7. Return { access_token, refresh_token, user }
  
Frontend:
  1. Store tokens
  2. Update Zustand state
  3. Navigate to dashboard
```

### 3. **Scan Flow (Authenticated)**

```
Frontend (ScanPage.tsx):
  1. User enters GitHub repo URL + selects branch
  2. Fetches branches: GET /api/v1/github/branches?repo_url={url}
  3. User clicks "Start Scan"
  4. Calls POST /api/v1/scan/start
     Body: { repository_url, branch }
  
Backend (unified_scan.py or scans.py):
  1. Create Scan record in DB (status=pending)
  2. Clone repository from GitHub to /tmp/devarchai/
  3. Detect technologies (Docker, K8s, Terraform, CI/CD, etc.)
  4. Parse files using appropriate parsers
  5. Run rule engine (50+ rules across 5 categories)
  6. Generate findings
  7. Run AI enrichment (LLM explanations, fix examples)
  8. Calculate scores (security, scalability, reliability, cost, observability)
  9. Save findings to DB
  10. Update scan status to completed
  
Frontend (during scan):
  1. Connect to WebSocket: /ws/scan/{scan_id}
  2. Receive real-time updates:
     - progress_update → Update progress bar
     - log_message → Add to scan logs
     - stack_detected → Update detected technologies
     - scan_complete → Fetch results
  3. Poll for completion (every 500ms)
  4. When complete, call GET /api/v1/scan/results/{scan_id}
  5. Display results in ResultPage.tsx
  
Frontend (ResultPage.tsx):
  1. Fetch scan details: GET /scans/{id}
  2. Fetch findings: GET /scans/{id}/findings
  3. Display:
     - Security score (circular progress)
     - Category scores (scalability, reliability, cost, observability)
     - Severity counts (critical, high, medium, low, info)
     - Detected technology stack
     - Top priority fixes
     - All findings (filterable, sortable)
     - Code diff viewer (before/after fix)
```

### 4. **Scan Flow (Anonymous/Guest)**

```
Frontend (ScanPage.tsx - same as authenticated):
  1. User enters repo URL (no login required)
  2. Calls POST /api/v1/scan/start (same endpoint)
  
Backend:
  1. Check if user is authenticated
  2. If not, use anonymous user (username="anonymous")
  3. Create scan with user_id=NULL or anonymous user ID
  4. Same scan pipeline as authenticated users
  5. Results saved to DB (expire after 7 days for anonymous)
  
Frontend:
  1. Display results (same as authenticated)
  2. Show CTA: "Create free account to save results"
  3. Links to /login or /register
```

---

## 🔐 Authentication Flow

### JWT Token Structure

**Access Token (30 min expiry):**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

**Refresh Token (7 day expiry):**
```json
{
  "sub": "user_id",
  "type": "refresh",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Security Middleware

**Password Hashing:**
- Algorithm: bcrypt (via passlib)
- Salt rounds: 12 (default)

**Email Encryption:**
- Emails encrypted in DB (email_encrypted field)
- Hash stored separately for lookup (email_hash)
- Decrypted only when needed (e.g., JWT token generation)

**API Key Auth:**
- Users can generate API keys via POST /api/v1/auth/api-key
- API key stored hashed in DB
- Used for programmatic access (alternative to JWT)

---

## 📊 Scan Flow (Detailed)

### Scan Pipeline Steps

**Step 1: Repository Fetch**
```
Backend:
  1. Clone repo from GitHub to /tmp/devarchai/{scan_id}_repo/
  2. Checkout specified branch/commit
  3. Update progress: 10%
```

**Step 2: Technology Detection**
```
Backend (RepositoryScanner):
  1. Scan for file patterns:
     - Dockerfile*, *.dockerfile → Docker
     - *.tf, *.tfvars → Terraform
     - deployment.yaml, service.yaml, *-k8s.yaml → Kubernetes
     - .github/workflows/*.yml → GitHub Actions
     - Jenkinsfile → Jenkins
     - .gitlab-ci.yml → GitLab CI
     - chart.yaml, values.yaml → Helm
     - *.yml (prometheus, grafana) → Monitoring
  2. Build DetectedTechnologyStack object
  3. Update progress: 20%
  4. Send WebSocket event: stack_detected
```

**Step 3: File Parsing**
```
Backend (ParserRegistry):
  1. For each detected technology, use appropriate parser:
     - TerraformParser → Parse .tf files (resources, providers, backends)
     - KubernetesParser → Parse K8s YAML (deployments, services, ingress)
     - DockerfileParser → Parse Dockerfiles (base images, commands)
     - CICDParser → Parse CI/CD configs (workflows, jobs, steps)
  2. Extract structured data from files
  3. Update progress: 30%
```

**Step 4: Rule Engine Execution**
```
Backend (RuleRegistry):
  1. Load all rules (50+ rules across 5 categories):
     - Security (SEC-001 to SEC-XXX)
     - Scalability (SCA-001 to SCA-XXX)
     - Reliability (REL-001 to REL-XXX)
     - Cost (CST-001 to CST-XXX)
     - Observability (OBS-001 to OBS-XXX)
  2. For each parsed file, run applicable rules
  3. Generate RuleFinding objects:
     {
       rule_id: "SEC-001",
       rule_name: "Missing State Locking",
       severity: "critical",
       category: "security",
       description: "Terraform state backend lacks locking",
       recommendation: "Enable state locking with DynamoDB",
       file_path: "terraform/backend.tf",
       line_number: 5
     }
  4. Update progress: 60%
```

**Step 5: AI Enrichment**
```
Backend (findings_enricher.py):
  1. For each finding, call LLM provider:
     - Get explanation (what this issue means)
     - Get impact analysis (potential consequences)
     - Get fix code (code example)
     - Get fix example (before/after)
     - Get best practices (array)
  2. LLM Provider priority:
     Gemini → OpenAI → Anthropic → Mistral → Mock
  3. Update findings with AI-generated fields:
     - ai_explanation
     - ai_generated: true
     - fix_code
     - fix_example
     - best_practices
     - confidence_score
  4. Update progress: 80%
```

**Step 6: Score Calculation**
```
Backend (ScoringEngine):
  1. Calculate category scores (0-100):
     - Start with 100
     - Deduct points based on findings:
       * Critical: -15 points
       * High: -10 points
       * Medium: -5 points
       * Low: -2 points
       * Info: -1 point
     - Apply category weights
  2. Calculate overall score:
     - Weighted average of category scores
     - Security: 30%
     - Scalability: 20%
     - Reliability: 20%
     - Cost: 15%
     - Observability: 15%
  3. Update progress: 90%
```

**Step 7: Save Results**
```
Backend:
  1. Save scan scores to DB
  2. Save all findings to DB
  3. Update scan status: completed
  4. Update progress: 100%
  5. Send WebSocket event: scan_complete
  6. Clean up temp files (/tmp/devarchai/)
```

---

## 📡 Data Flow Diagrams

### 1. **Login Flow**
```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │         │   Backend    │         │  PostgreSQL  │
│  (React UI)  │         │  (FastAPI)   │         │   (Database) │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │  POST /auth/login      │                        │
       │  {email, password}     │                        │
       │───────────────────────▶│                        │
       │                        │  SELECT * FROM users   │
       │                        │  WHERE email_hash = ?  │
       │                        │───────────────────────▶│
       │                        │                        │
       │                        │  User record           │
       │                        │◀───────────────────────│
       │                        │                        │
       │                        │  Verify password       │
       │                        │  Generate JWT tokens   │
       │                        │                        │
       │  {access_token,        │                        │
       │   refresh_token}       │                        │
       │◀───────────────────────│                        │
       │                        │                        │
       │  GET /auth/me          │                        │
       │  Authorization: Bearer │                        │
       │───────────────────────▶│                        │
       │                        │  Validate JWT          │
       │                        │  Get user from DB      │
       │                        │───────────────────────▶│
       │                        │                        │
       │  User data             │                        │
       │◀───────────────────────│                        │
       │                        │                        │
       │  Store in Zustand      │                        │
       │  Navigate to /dashboard│                        │
```

### 2. **Scan Flow**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Frontend   │    │   Backend    │    │   GitHub     │    │   LLM API    │
│  (React UI)  │    │  (FastAPI)   │    │   (Repo)     │    │  (Gemini)    │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │                   │
       │ POST /scan/start  │                   │                   │
       │ {repo_url, branch}│                   │                   │
       │──────────────────▶│                   │                   │
       │                   │  Clone repo       │                   │
       │                   │──────────────────▶│                   │
       │                   │                   │                   │
       │                   │  Repo files       │                   │
       │                   │◀──────────────────│                   │
       │                   │                   │                   │
       │                   │  Detect tech      │                   │
       │                   │  Parse files      │                   │
       │                   │  Run rules        │                   │
       │                   │                   │                   │
       │                   │  AI enrichment    │                   │
       │                   │──────────────────────────────────────▶│
       │                   │                   │                   │
       │                   │  AI explanations  │                   │
       │                   │◀──────────────────────────────────────│
       │                   │                   │                   │
       │                   │  Calculate scores │                   │
       │                   │  Save to DB       │                   │
       │                   │                   │                   │
       │◀──────────────────│                   │                   │
       │  WebSocket events │                   │                   │
       │  (progress, logs) │                   │                   │
       │                   │                   │                   │
       │ GET /scan/results │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │                   │                   │
       │  Scan results     │                   │                   │
       │  + findings       │                   │                   │
       │◀──────────────────│                   │                   │
       │                   │                   │                   │
       │  Display results  │                   │                   │
```

---

## 🔑 Key Components

### 1. **Frontend API Endpoints**

**Auth Endpoints (`frontend/src/api/endpoints/auth.ts`):**
```typescript
authApi.register(data)      → POST /api/v1/auth/register
authApi.login(data)         → POST /api/v1/auth/login
authApi.getCurrentUser()    → GET /api/v1/auth/me
authApi.updateProfile(data) → PUT /api/v1/auth/me
authApi.createApiKey()      → POST /api/v1/auth/api-key
authApi.revokeApiKey()      → DELETE /api/v1/auth/api-key
```

**Scan Endpoints (`frontend/src/api/endpoints/scans.ts`):**
```typescript
scansApi.listScans()        → GET /scans
scansApi.createScan(data)   → POST /scans
scansApi.startUnifiedScan() → POST /scan/start
scansApi.getScan(id)        → GET /scans/{id}
scansApi.getScanProgress()  → GET /scan/status/{id}
scansApi.getScanResults()   → GET /scans/{id} + GET /scans/{id}/findings
scansApi.cancelScan(id)     → POST /scans/{id}/cancel
scansApi.deleteScan(id)     → DELETE /api/v1/scans/{id}
```

### 2. **Backend Security**

**JWT Authentication (`backend/app/core/security.py`):**
```python
create_access_token(data) → Generate JWT access token
create_refresh_token(data) → Generate JWT refresh token
decode_token(token) → Decode and validate JWT
get_current_user() → FastAPI dependency (extract user from token)
get_password_hash(password) → Hash password with bcrypt
verify_password(plain, hashed) → Verify password against hash
encrypt_user_email(email) → Encrypt email for DB storage
decrypt_user_email(encrypted) → Decrypt email from DB
hash_email(email) → Hash email for lookup
generate_api_key() → Generate secure API key
```

### 3. **WebSocket Communication**

**Backend (`backend/app/websockets/scan_progress.py`):**
```python
WebSocket Manager:
  - Tracks active connections per scan_id
  - Broadcasts updates to all listeners
  
WebSocket Events:
  - progress_update: { progress: number, current_step: string }
  - log_message: { message: string, timestamp: string }
  - stack_detected: { technology: string, files: string[] }
  - scan_complete: { scan_id: string }
  - scan_failed: { error: string }
```

**Frontend (ScanPage.tsx):**
```typescript
WebSocket Connection:
  1. Connect to /ws/scan/{scan_id}
  2. Listen for events
  3. Update UI state (progress, logs, technologies)
  4. When scan_complete → fetch results
  5. On disconnect → cleanup
```

### 4. **Celery Task Queue**

**Task: `scan_repository_task`**
```python
@celery_app.task(bind=True)
def scan_repository_task(
    self,
    scan_id: str,
    repository_url: str,
    branch: str = "main",
    include_ai_explanations: bool = True,
):
    """
    Async scan task (for background processing).
    
    Steps:
    1. Clone repository
    2. Detect technologies
    3. Parse files
    4. Run rule engine
    5. AI enrichment
    6. Calculate scores
    7. Save results
    8. Update scan status
    """
```

**Note:** Current implementation uses **synchronous scanning** for immediate results (avoids Celery dependency). Celery task is available for background processing.

---

## 🎯 Common Workflows

### 1. **User Registration + First Scan**
```
1. User visits /register
2. Fills form (email, username, password, org name)
3. POST /api/v1/auth/register
   - Create organization
   - Create user (encrypted email, hashed password)
   - Create organization membership (role: OWNER)
4. Auto-login (tokens returned)
5. Redirect to /dashboard
6. User clicks "New Scan"
7. Enter repo URL → POST /api/v1/scan/start
8. Wait for scan completion (WebSocket updates)
9. View results at /scans/{scan_id}
```

### 2. **Upgrade to Paid Plan**
```
1. User on free plan visits /pricing
2. Clicks "Upgrade" on Plus/Pro plan
3. If not logged in → redirect to /login
4. After login → POST /api/v1/billing/checkout
   - Create Stripe/Razorpay checkout session
   - Return checkout_url
5. Redirect user to payment gateway
6. User completes payment
7. Payment provider sends webhook to /api/v1/billing/webhook
8. Backend updates user.subscription_plan
9. Redirect user back to /dashboard?upgrade=success
```

### 3. **AI Fix Generation**
```
1. User views scan results
2. Clicks "Generate AI Fixes" on a finding
3. POST /api/v1/ai-suggestions/generate-fix
   Body: { finding_id: "..." }
4. Backend:
   - Get finding from DB
   - Call LLM provider with prompt:
     "Generate fix for: {description}
      File: {file_path}
      Recommendation: {recommendation}"
   - LLM returns:
     - fix_code (code snippet)
     - fix_example (before/after)
     - best_practices (array)
   - Save to finding.ai_fix fields
5. Return AI fix to frontend
6. Display in Code Diff Viewer
```

---

## 📦 Environment Variables

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM (at least one required)
GEMINI_API_KEY=xxx
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
MISTRAL_API_KEY=xxx
LLM_PROVIDER=gemini  # Priority: gemini > openai > anthropic > mistral > mock

# GitHub
GITHUB_TOKEN=xxx  # For API access
GITHUB_CLIENT_ID=xxx  # For OAuth
GITHUB_CLIENT_SECRET=xxx

# Security
SECRET_KEY=long-random-string-min-32-chars

# Payment
STRIPE_SECRET_KEY=xxx
STRIPE_PUBLISHABLE_KEY=xxx
RAZORPAY_KEY_ID=xxx
RAZORPAY_KEY_SECRET=xxx
```

### Frontend (Vite Proxy)
```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
    }
  }
}
```

---

## 🚀 Quick Start Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head  # Run migrations
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # Starts on port 5173/5174
```

### Docker Compose
```bash
docker-compose up -d  # Starts backend, frontend, PostgreSQL, Redis
```

---

## 🐛 Debugging Tips

### Frontend
- Check Network tab for API calls
- Check localStorage for tokens
- Zustand DevTools: `window.__ZUSTAND_DEVTOOLS__`
- React DevTools for component tree

### Backend
- Check logs: `tail -f backend/logs/app.log`
- Database: `psql -U postgres -d devarchai`
- Redis: `redis-cli`
- Celery: `celery -A app.workers.celery_config worker --loglevel=info`

### Common Issues
1. **401 Unauthorized** → Token expired, check refresh logic
2. **CORS errors** → Verify CORS_ORIGINS in .env
3. **WebSocket disconnects** → Check backend logs for errors
4. **Scan stuck** → Check Celery worker is running
5. **AI enrichment fails** → Verify LLM API key is set

---

## 📊 Performance Considerations

### Frontend
- TanStack Query caches API responses (5 min stale time)
- Zustand persists auth state (avoids re-fetch on reload)
- Lazy loading for heavy components (ResultPage)
- Debounced search inputs

### Backend
- Async database queries (asyncpg)
- Redis caching for frequently accessed data
- Celery for background tasks (optional)
- Connection pooling (DB_POOL_SIZE=10)
- LLM fallback (mock provider if API keys not set)

---

## 🔒 Security Best Practices

1. **Never commit .env files**
2. **Use strong SECRET_KEY in production**
3. **Enable HTTPS in production**
4. **Rotate API keys regularly**
5. **Use parameterized queries (SQLAlchemy handles this)**
6. **Validate all user inputs (Pydantic schemas)**
7. **Rate limiting enabled (100 req/min)**
8. **Email encryption at rest**
9. **Password hashing with bcrypt**
10. **JWT tokens with short expiry (30 min)**

---

## 📝 Notes

- **Anonymous scans** expire after 7 days
- **Free plan** users can run unlimited scans
- **Paid plans** offer priority scanning, AI fixes, team collaboration
- **LLM priority**: Gemini → OpenAI → Anthropic → Mistral → Mock
- **Scan timeout**: 5 minutes (configurable)
- **Max repo size**: 100MB (configurable)
- **Supported IaC**: Terraform, Kubernetes, Docker, CI/CD (GitHub Actions, GitLab CI, Jenkins)

---

*Last updated: April 14, 2026*
