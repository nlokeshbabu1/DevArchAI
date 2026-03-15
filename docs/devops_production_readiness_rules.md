DevOps Production Readiness Rules (Enterprise
SaaS V1)
This document lists practical production-readiness rules commonly used in real-world companies to
validate Docker, Kubernetes, Terraform, CI/CD, and security configurations before deploying
applications to production environments.
Docker Rules
1. Containers must not run as root user
2. Use minimal base images (alpine/distroless)
3. Avoid using latest image tag
4. Define HEALTHCHECK in Dockerfile
5. Use multi-stage builds
6. Remove unnecessary packages
7. Do not store secrets inside Dockerfile
8. Use explicit version for dependencies
Kubernetes Rules
1. Define CPU and memory resource limits
2. Define resource requests
3. Add liveness probe
4. Add readiness probe
5. Avoid privileged containers
6. Run containers as non-root
7. Use imagePullPolicy appropriately
8. Avoid hostPath volumes when possible
Terraform / IaC Rules
1. No public access for storage buckets
2. No open security groups (0.0.0.0/0) for SSH
3. Enable encryption for storage
4. Enable logging for critical resources
5. Use least privilege IAM policies
6. Use remote state backend
7. Enable versioning for storage buckets
8. Tag all infrastructure resources
CI/CD Rules
1. Pipeline must include automated tests
2. Pipeline must include security scanning
3. Use artifact versioning
4. Do not expose secrets in pipeline logs
5. Separate build and deploy stages
6. Use environment-based deployments
7. Add approval step for production deploy
8. Cache dependencies to improve pipeline performance
