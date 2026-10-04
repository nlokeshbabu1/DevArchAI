"""Server-side credential access for Kubernetes connections.

Credentials are decrypted only on the server and never logged or returned via API.
"""

from __future__ import annotations

from app.core.encryption import get_encryption_service
from app.models.kubernetes import KubernetesConnection


def get_kubeconfig_text(connection: KubernetesConnection) -> str | None:
    """Return decrypted kubeconfig text for generic connections only."""
    if not connection.kubeconfig_encrypted:
        return None
    return get_encryption_service().decrypt(connection.kubeconfig_encrypted)
