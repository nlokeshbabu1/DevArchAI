# Production Dockerfile for DevArchAI Backend
FROM python:3.11-slim as base

# Set environment variables
# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies and scanner CLIs
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gcc \
    libpq-dev \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

# Optional scanner CLIs used by the scan pipeline (Gitleaks, Hadolint, govulncheck, kube-score)
# plus core scanners Trivy and Checkov.
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sfL https://raw.githubusercontent.com/gitleaks/gitleaks/master/tools/install.sh | sh -s -- -b /usr/local/bin \
    && curl -fsSL https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 -o /usr/local/bin/hadolint \
    && chmod +x /usr/local/bin/hadolint \
    && curl -fsSL https://github.com/zegl/kube-score/releases/download/v1.20.0/kube-score_1.20.0_linux_amd64 -o /usr/local/bin/kube-score \
    && chmod +x /usr/local/bin/kube-score \
    && GOBIN=/usr/local/bin go install golang.org/x/vuln/cmd/govulncheck@latest

# ===========================================
# Builder Stage
# ===========================================
FROM base as builder

COPY requirements.txt .

# Install Python dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ===========================================
# Production Stage
# ===========================================
FROM base as production

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* checkov

# Copy application code
COPY --chown=appuser:appgroup . .

# Create temp directory
RUN mkdir -p /tmp/devarchai && chown appuser:appgroup /tmp/devarchai

# Copy and set up entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/ready || curl -f http://localhost:8000/api/v1/health || exit 1

# Run entrypoint which orchestrates: wait-for-db → migrate → validate → start
ENTRYPOINT ["/docker-entrypoint.sh"]
# Render and other PaaS hosts inject $PORT — must bind to it, not a hardcoded 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1}"]

# ===========================================
# Development Stage
# ===========================================
# FROM base as development

# # Install development dependencies
# COPY requirements.txt .
# RUN pip install -r requirements.txt

# # Copy application code
# COPY . .

# # Install app for development
# RUN pip install -e .

# # Default command for development
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
