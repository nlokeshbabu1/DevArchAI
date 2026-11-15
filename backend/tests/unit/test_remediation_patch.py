"""Repository-independent tests for safe remediation patch application."""

import pytest

from app.services.remediation_patch import (
    PatchValidationError,
    apply_unified_diff,
    build_unified_diff,
    file_content_hash,
    reconcile_file_patches,
    resolve_proposed_content,
    validate_preservation,
)

GO_DOCKERFILE = """FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/server .

FROM gcr.io/distroless/static-debian12
COPY --from=builder /out/server /server
ENTRYPOINT ["/server"]
"""

NODE_DOCKERFILE = """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "start"]
"""

K8S_DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: go-web-app
  labels:
    app: go-web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: go-web-app
  template:
    metadata:
      labels:
        app: go-web-app
    spec:
      containers:
      - name: app
        image: example/go-web-app:1.0.0
        ports:
        - containerPort: 8080
"""

K8S_HPA_ONLY = """apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: go-web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: invented-backend
  minReplicas: 2
  maxReplicas: 10
"""


class TestFilePreservation:
    def test_rejects_dockerfile_technology_swap(self):
        with pytest.raises(PatchValidationError, match="technology stack|base image"):
            validate_preservation(GO_DOCKERFILE, NODE_DOCKERFILE, "Dockerfile")

    def test_rejects_k8s_workload_removal(self):
        with pytest.raises(PatchValidationError, match="workload removed"):
            validate_preservation(K8S_DEPLOYMENT, K8S_HPA_ONLY, "helm/chart/templates/deployment.yaml")

    def test_rejects_emptying_file(self):
        with pytest.raises(PatchValidationError, match="empty the file"):
            validate_preservation(GO_DOCKERFILE, "", "Dockerfile")

    def test_accepts_minimal_user_addition_via_diff(self):
        updated = GO_DOCKERFILE.replace(
            "FROM gcr.io/distroless/static-debian12",
            "FROM gcr.io/distroless/static-debian12\nUSER 65532:65532",
        )
        meta = validate_preservation(GO_DOCKERFILE, updated, "Dockerfile")
        assert meta["valid"] is True


class TestUnifiedDiff:
    def test_apply_unified_diff_roundtrip(self):
        updated = GO_DOCKERFILE + "\nUSER 65532:65532\n"
        diff = build_unified_diff("Dockerfile", GO_DOCKERFILE, updated)
        result = apply_unified_diff(GO_DOCKERFILE, diff)
        assert result == updated

    def test_rejects_bad_context(self):
        diff = """--- a/Dockerfile
+++ b/Dockerfile
@@ -1,3 +1,3 @@
-FROM wrong
+FROM golang:1.22 AS builder
 WORKDIR /app
"""
        with pytest.raises(PatchValidationError, match="mismatch"):
            apply_unified_diff(GO_DOCKERFILE, diff)


class TestResolveProposedContent:
    def test_rejects_partial_snippet_without_diff(self):
        with pytest.raises(PatchValidationError, match="unified diff"):
            resolve_proposed_content(
                GO_DOCKERFILE,
                {"fix_code": "USER 65532:65532"},
                rel_path="Dockerfile",
            )

    def test_rejects_llm_full_example_node_dockerfile(self):
        with pytest.raises(PatchValidationError):
            resolve_proposed_content(
                GO_DOCKERFILE,
                {"fix_code": NODE_DOCKERFILE},
                rel_path="Dockerfile",
            )

    def test_accepts_unified_diff_payload(self):
        updated = GO_DOCKERFILE.replace(
            "ENTRYPOINT [\"/server\"]",
            "USER 65532:65532\nENTRYPOINT [\"/server\"]",
        )
        diff = build_unified_diff("Dockerfile", GO_DOCKERFILE, updated)
        result = resolve_proposed_content(
            GO_DOCKERFILE,
            {"unified_diff": diff},
            rel_path="Dockerfile",
        )
        assert "USER 65532:65532" in result
        assert "golang:1.22" in result


class TestMultiFindingSameFile:
    def test_sequential_diffs_on_single_base(self):
        step1 = GO_DOCKERFILE.replace(
            "FROM gcr.io/distroless/static-debian12",
            "FROM gcr.io/distroless/static-debian12\nUSER 65532:65532",
        )
        diff1 = build_unified_diff("Dockerfile", GO_DOCKERFILE, step1)
        final, applied = reconcile_file_patches(
            "Dockerfile",
            GO_DOCKERFILE,
            [
                {"finding_id": "f1", "unified_diff": diff1},
            ],
        )
        assert "USER 65532:65532" in final
        assert "golang:1.22" in final
        assert len(applied) == 1

    def test_stale_hash_rejected(self):
        diff = build_unified_diff(
            "Dockerfile",
            GO_DOCKERFILE,
            GO_DOCKERFILE + "\nUSER 65532:65532\n",
        )
        with pytest.raises(PatchValidationError, match="Stale patch"):
            reconcile_file_patches(
                "Dockerfile",
                GO_DOCKERFILE,
                [
                    {
                        "finding_id": "f1",
                        "unified_diff": diff,
                        "original_sha256": "deadbeef",
                    },
                ],
            )

    def test_second_full_rewrite_rejected_after_first(self):
        diff1 = build_unified_diff(
            "Dockerfile",
            GO_DOCKERFILE,
            GO_DOCKERFILE + "\nUSER 65532:65532\n",
        )
        with pytest.raises(PatchValidationError):
            reconcile_file_patches(
                "Dockerfile",
                GO_DOCKERFILE,
                [
                    {"finding_id": "f1", "unified_diff": diff1},
                    {"finding_id": "f2", "fix_code": NODE_DOCKERFILE},
                ],
            )


class TestHashAndDiff:
    def test_file_hash_stable(self):
        h1 = file_content_hash(GO_DOCKERFILE)
        h2 = file_content_hash(GO_DOCKERFILE)
        assert h1 == h2
        assert h1 != file_content_hash(GO_DOCKERFILE + "\n")


def test_allow_full_file_flag_from_llm_is_ignored():
    """LLM-only allow_full_file must not bypass diff requirement."""
    with pytest.raises(PatchValidationError, match="not a safe full-file"):
        resolve_proposed_content(
            GO_DOCKERFILE,
            {"allow_full_file": True, "fix_code": NODE_DOCKERFILE},
            rel_path="Dockerfile",
        )
