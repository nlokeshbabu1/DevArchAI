# Deployment Guide

## Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.5.0
- AWS CLI configured
- Docker and Docker Compose (for local development)
- kubectl (for Kubernetes deployment)

## Local Development

### Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-org/devarchai.git
cd devarchai

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# Required: OPENAI_API_KEY or ANTHROPIC_API_KEY for AI features

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## AWS Deployment

### 1. Prepare Infrastructure

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init

# Create S3 bucket for state (if not using remote backend)
aws s3 mb s3://devarchai-terraform-state
aws dynamodb create-table \
  --table-name devarchai-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Review and apply configuration
terraform plan -var="environment=production" -var="acm_certificate_arn=arn:aws:acm:..."
terraform apply
```

### 2. Build and Push Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
docker build -t devarchai-backend ./backend
docker tag devarchai-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/devarchai-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/devarchai-backend:latest

# Build and push frontend
docker build -t devarchai-frontend ./frontend
docker tag devarchai-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/devarchai-frontend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/devarchai-frontend:latest
```

### 3. Deploy to ECS

```bash
# Create ECS task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create or update ECS service
aws ecs create-service \
  --cluster devarchai-cluster \
  --service-name devarchai-backend-service \
  --task-definition devarchai-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"

# Or update existing service
aws ecs update-service \
  --cluster devarchai-cluster \
  --service devarchai-backend-service \
  --force-new-deployment
```

### 4. Configure DNS

Point your domain to the ALB:
```bash
# Get ALB DNS name
aws elbv2 describe-load-balancers --names devarchai-alb --query 'LoadBalancers[0].DNSName'

# Create Route53 record
aws route53 change-resource-record-sets --hosted-zone-id ZONE_ID --change-batch file://dns-change.json
```

## Kubernetes Deployment

### 1. Create Cluster (EKS)

```bash
# Using eksctl
eksctl create cluster \
  --name devarchai \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 4

# Or using Terraform (see infrastructure/terraform/eks.tf)
```

### 2. Apply Manifests

```bash
# Configure kubectl
aws eks update-kubeconfig --name devarchai --region us-east-1

# Create namespace
kubectl create namespace devarchai

# Create secrets
kubectl create secret generic devarchai-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=openai-api-key="sk-..." \
  --from-literal=secret-key="your-secret-key" \
  -n devarchai

# Apply manifests
kubectl apply -f infrastructure/kubernetes/

# Verify deployment
kubectl get pods -n devarchai
kubectl get services -n devarchai
kubectl get ingress -n devarchai
```

### 3. Setup Monitoring

```bash
# Install Prometheus Stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Install cert-manager for TLS
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true
```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `LLM_PROVIDER` | LLM provider (openai/anthropic/mock) | `mock` |
| `GITHUB_TOKEN` | GitHub personal access token | - |
| `SECRET_KEY` | Secret key for JWT | - |
| `S3_BUCKET_NAME` | S3 bucket for reports | `devarchai-reports` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | (empty, uses proxy) |

## CI/CD Setup

### GitHub Actions

1. Create repository secrets:
   - `AWS_ACCOUNT_ID`
   - `AWS_REGION`

2. Create IAM role for GitHub Actions (see infrastructure/terraform/github-actions.tf)

3. Configure environments in GitHub:
   - `staging`
   - `production`

### Manual Deployment Pipeline

```bash
# 1. Build
docker-compose -f docker-compose.build.yml build

# 2. Test
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# 3. Deploy to staging
./scripts/deploy.sh staging

# 4. Run smoke tests
./scripts/smoke-tests.sh staging

# 5. Deploy to production
./scripts/deploy.sh production
```

## Monitoring and Logging

### CloudWatch

- Logs: `/ecs/devarchai-backend`, `/ecs/devarchai-frontend`
- Metrics: CPU, Memory, Network, Request Count

### Prometheus Metrics

- `/metrics` endpoint on backend
- Key metrics: request_duration, request_count, error_count, analysis_duration

### Alerts

Configure CloudWatch Alarms for:
- Error rate > 5%
- Response time p99 > 2s
- CPU utilization > 80%
- Memory utilization > 80%

## Backup and Recovery

### Database Backups

- Automated daily snapshots (RDS)
- Retention: 30 days (production), 7 days (staging)

### Manual Backup

```bash
# Export database
pg_dump $DATABASE_URL > backup.sql

# Export to S3
aws s3 cp backup.sql s3://devarchai-backups/database/$(date +%Y%m%d).sql
```

### Disaster Recovery

1. Restore RDS from snapshot
2. Redeploy ECS services
3. Update DNS if needed

## Cost Optimization

- Use Spot instances for worker nodes
- Enable S3 Intelligent Tiering
- Right-size ECS tasks based on metrics
- Use Reserved Capacity for RDS
- Configure auto-scaling policies
