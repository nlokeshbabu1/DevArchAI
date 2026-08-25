"""Pytest configuration and fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_dockerfile_content():
    """Sample Dockerfile content for testing."""
    return """FROM node:latest

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
"""


@pytest.fixture
def sample_dockerfile_with_user():
    """Sample Dockerfile with non-root user."""
    return """FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 3000

CMD ["node", "server.js"]
"""


@pytest.fixture
def sample_kubernetes_deployment():
    """Sample Kubernetes deployment without best practices."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "my-app",
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "my-app"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "my-app"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "myapp:latest",
                            "ports": [
                                {"containerPort": 8080}
                            ]
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_kubernetes_deployment_secure():
    """Sample Kubernetes deployment with security best practices."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "my-app",
        },
        "spec": {
            "replicas": 3,
            "selector": {
                "matchLabels": {
                    "app": "my-app"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "my-app"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "myapp:1.0.0",
                            "ports": [
                                {"containerPort": 8080}
                            ],
                            "resources": {
                                "requests": {
                                    "memory": "256Mi",
                                    "cpu": "250m"
                                },
                                "limits": {
                                    "memory": "512Mi",
                                    "cpu": "500m"
                                }
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/healthz",
                                    "port": 8080
                                },
                                "initialDelaySeconds": 30
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/ready",
                                    "port": 8080
                                },
                                "initialDelaySeconds": 5
                            },
                            "securityContext": {
                                "runAsNonRoot": True,
                                "runAsUser": 1000
                            }
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_terraform_s3_public():
    """Sample Terraform with public S3 bucket."""
    return {
        "resources": [
            {
                "type": "aws_s3_bucket",
                "name": "data_bucket",
                "values": {
                    "bucket": "my-data-bucket",
                    "acl": "public-read"
                }
            }
        ]
    }


@pytest.fixture
def sample_terraform_s3_private():
    """Sample Terraform with private S3 bucket."""
    return {
        "resources": [
            {
                "type": "aws_s3_bucket",
                "name": "data_bucket",
                "values": {
                    "bucket": "my-data-bucket",
                    "acl": "private",
                    "server_side_encryption_configuration": {
                        "rule": {
                            "apply_server_side_encryption_by_default": {
                                "sse_algorithm": "AES256"
                            }
                        }
                    },
                    "versioning": {
                        "enabled": True
                    }
                }
            }
        ]
    }


@pytest.fixture
def sample_rule_findings():
    """Sample rule findings for testing."""
    from app.rule_engine.base import Category, RuleFinding, Severity

    return [
        RuleFinding(
            rule_id="DOCKER-001",
            rule_name="Container Runs as Root",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Container runs as root user",
            recommendation="Add USER instruction",
            file_path="Dockerfile",
        ),
        RuleFinding(
            rule_id="K8S-001",
            rule_name="Missing Resource Limits",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="Container has no resource limits",
            recommendation="Set CPU and memory limits",
            file_path="k8s/deployment.yaml",
        ),
        RuleFinding(
            rule_id="TF-001",
            rule_name="Public S3 Bucket",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            description="S3 bucket has public ACL",
            recommendation="Set ACL to private",
            file_path="terraform/s3.tf",
        ),
    ]


@pytest_asyncio.fixture
async def db_session():
    """Provide an async database session against the test database.

    Uses ``DATABASE_URL`` from settings (which tests override to point at
    ``devarchai_test``).  The session is rolled back after each test so
    fixtures never leak between tests.
    """
    from app.config import settings

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _flush_rate_limit_keys():
    """Clear persisted rate-limiter counters around the whole session.

    The auth/general limiters keep sliding-window counters in Redis keyed
    by client id ("testclient").  Without this, counters left over from a
    previous full-suite run trip HTTP 429s in every later run until the
    window TTL expires.
    """
    import redis as redis_lib

    from app.config import settings

    try:
        client = redis_lib.Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
        )
        keys = list(client.scan_iter("ratelimit:*"))
        if keys:
            client.delete(*keys)
        yield
        keys = list(client.scan_iter("ratelimit:*"))
        if keys:
            client.delete(*keys)
    except Exception:
        yield


@pytest.fixture(autouse=True)
def _reset_redis_singleton():
    """Reset Redis cache singleton before each test.

    The Redis cache is a module-level singleton.  Tests run in different
    event loops, so the cached connection becomes stale and causes
    ``RuntimeError: Event loop is closed``.
    """
    import app.cache.redis_cache as redis_mod
    import app.db.session as session_mod

    orig_cache = redis_mod._cache_instance
    orig_engine = session_mod._engine
    orig_sf = session_mod._session_factory

    redis_mod._cache_instance = None
    session_mod._engine = None
    session_mod._session_factory = None

    yield

    redis_mod._cache_instance = orig_cache
    session_mod._engine = orig_engine
    session_mod._session_factory = orig_sf


@pytest.fixture
def mock_settings():
    """A mock ``settings`` object with safe defaults for unit tests."""
    mock = MagicMock()
    mock.VERSION = "1.0.0"
    mock.DEBUG = False
    mock.DATABASE_URL = "sqlite+aiosqlite:///test.db"
    mock.REDIS_URL = None
    mock.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
    mock.ALGORITHM = "HS256"
    mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    mock.REFRESH_TOKEN_EXPIRE_DAYS = 7
    mock.GITHUB_CLIENT_ID = None
    mock.GITHUB_CLIENT_SECRET = None
    mock.GITHUB_REDIRECT_URI = "http://localhost:3000/auth/github/callback"
    mock.GITLAB_CLIENT_ID = None
    mock.GITLAB_CLIENT_SECRET = None
    mock.ENCRYPTION_KEY = "test-encryption-key-for-testing-only-32c!"
    mock.AUTH_REFRESH_TOKEN_STORAGE_MODE = "legacy"
    mock.COOKIE_SECURE = False
    mock.COOKIE_SAMESITE = "lax"
    mock.COOKIE_PATH = "/"
    mock.COOKIE_DOMAIN = None
    mock.MAX_FAILED_LOGIN_ATTEMPTS = 5
    mock.ACCOUNT_LOCKOUT_MINUTES = 30
    return mock
