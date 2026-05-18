# ResearchRAG Pro - Phase 5 Deployment Infrastructure

Complete production deployment infrastructure with security hardening, RAGAS quality gates, and auto-scaling.

## 📋 Overview

This deployment package includes:

- **Docker Compose**: Full-stack local/single-server deployment
- **Kubernetes**: Production EKS deployment with HPA (3-20 replicas)
- **Terraform**: AWS infrastructure provisioning
- **CI/CD**: GitHub Actions with RAGAS quality gates (faithfulness >0.95)
- **Monitoring**: Prometheus + Grafana with custom RAG metrics
- **Security**: NetworkPolicy, AWS Secrets Manager, WAF, rate limiting (100 req/s)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │              EKS Cluster (Kubernetes 1.28)            │    │
│  ├───────────────────────────────────────────────────────┤    │
│  │                                                       │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │  Backend API (FastAPI)                       │   │    │
│  │  │  - HPA: 3-20 replicas                        │   │    │
│  │  │  - CPU: 70% target                           │   │    │
│  │  │  - Memory: 80% target                        │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  │                                                       │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │  Frontend (React)                            │   │    │
│  │  │  - HPA: 2-10 replicas                        │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  │                                                       │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Milvus Cloud  │  │ Neo4j Aura   │  │ ElastiCache  │       │
│  │ (Vector DB)   │  │ (Graph DB)   │  │ (Redis)      │       │
│  └───────────────┘  └──────────────┘  └──────────────┘       │
│                                                                 │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ S3 Buckets    │  │ Secrets Mgr  │  │ CloudWatch   │       │
│  └───────────────┘  └──────────────┘  └──────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Local Development (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/yourorg/research-rag-pro.git
cd research-rag-pro

# 2. Set environment variables
cp .env.example .env
nano .env  # Add your API keys

# 3. Start all services
docker-compose -f docker-compose.production.yml up -d

# 4. Verify services
docker-compose ps

# 5. Access application
open http://localhost
# Backend API: http://localhost:8000
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9092
```

### Option 2: Production Kubernetes (EKS)

```bash
# 1. Provision AWS infrastructure with Terraform
cd terraform
terraform init
terraform plan -var-file=production.tfvars
terraform apply

# 2. Configure kubectl
aws eks update-kubeconfig --name research-rag-prod --region us-east-1

# 3. Deploy application
kubectl apply -f k8s-manifests.yaml

# 4. Verify deployment
kubectl get pods -n research-rag
kubectl get hpa -n research-rag
kubectl get ingress -n research-rag

# 5. Access application
# URL will be shown in ingress output
kubectl get ingress -n research-rag
```

## 📊 RAGAS Quality Gates (CI/CD)

The GitHub Actions pipeline enforces quality gates before production deployment:

### Required Metrics

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| **Faithfulness** | ≥ 0.95 | Answers grounded in retrieved context |
| **Answer Relevancy** | ≥ 0.90 | Answers address user questions |
| **Context Precision** | ≥ 0.85 | Low noise in retrieved context |

### Workflow

```
┌──────────────┐
│ Push to main │
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Build & Test       │
│ - Unit tests       │
│ - Integration tests│
└──────┬─────────────┘
       │
       ▼
┌────────────────────────────┐
│ Deploy to Staging          │
└──────┬─────────────────────┘
       │
       ▼
┌────────────────────────────┐
│ Run RAGAS Evaluation       │
│ - 100 test queries         │
│ - Calculate metrics        │
│ - Check thresholds         │
└──────┬─────────────────────┘
       │
       ├─ PASS ──────────┐
       │                 ▼
       │          ┌──────────────────┐
       │          │ Deploy Production│
       │          └──────────────────┘
       │
       └─ FAIL ──────────┐
                         ▼
                  ┌──────────────────┐
                  │ Block Deployment │
                  │ Notify Team      │
                  └──────────────────┘
```

### Example Evaluation Results

```json
{
  "faithfulness": 0.9687,
  "answer_relevancy": 0.9234,
  "context_precision": 0.8891,
  "context_recall": 0.9412,
  "passed": true,
  "avg_latency_ms": 1247.3,
  "p99_latency_ms": 2891.2
}
```

## 🔒 Security Features

### Network Security

- **Kubernetes NetworkPolicy**: Isolates backend/frontend pods
- **WAF Rules**: Blocks SQL injection, XSS, path traversal
- **Rate Limiting**: 100 req/s global, 20 req/s search, 5 req/min ingestion
- **DDoS Protection**: Connection limits, request body rate limiting

### Secrets Management

```bash
# All secrets stored in AWS Secrets Manager
aws secretsmanager create-secret \
  --name research-rag/openai-api-key \
  --secret-string $OPENAI_API_KEY

# Kubernetes pods access via IRSA (IAM Roles for Service Accounts)
# No hardcoded credentials
```

### TLS/SSL

- TLS 1.2/1.3 only
- Modern cipher suites
- HSTS enabled
- OCSP stapling

## 📈 Monitoring & Observability

### Prometheus Metrics

Custom metrics exposed at `/metrics` endpoint:

```
# RAGAS quality metrics
ragas_faithfulness{model="gpt-4",retrieval_mode="hybrid"} 0.968
ragas_answer_relevancy{model="gpt-4",retrieval_mode="hybrid"} 0.923
ragas_context_precision{retrieval_mode="hybrid"} 0.889

# Math rendering accuracy
rag_math_equation_accuracy 0.987

# Performance metrics
rag_search_duration_seconds_bucket{retrieval_mode="hybrid",le="1.0"} 2847
rag_search_duration_seconds_bucket{retrieval_mode="hybrid",le="2.0"} 3102

# Cost tracking
rag_openai_api_cost_usd_total{model="gpt-4",operation="search"} 127.43
```

### Grafana Dashboards

Pre-configured dashboards in `./dashboards/`:

1. **RAG Quality Overview**: RAGAS metrics, math accuracy, retrieval recall
2. **Performance Metrics**: Latency P50/P95/P99, throughput, error rates
3. **Cost Monitoring**: API costs, token usage, resource utilization
4. **Infrastructure Health**: Pod status, HPA scaling, database metrics

### Alerts

Prometheus alerts configured in `config/prometheus-alerts.yml`:

- 🚨 **Critical**: Faithfulness < 0.95, Memory > 90%, Search errors > 5%
- ⚠️  **Warning**: Answer relevancy < 0.90, CPU > 85%, Latency > 2s
- ℹ️  **Info**: HPA at max replicas, costs spiking, underutilized resources

## 🔧 Configuration

### Environment Variables

Required secrets in AWS Secrets Manager or `.env`:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database Credentials
NEO4J_PASSWORD=...
REDIS_PASSWORD=...
MILVUS_TOKEN=...

# API Security
API_KEYS=key1,key2,key3

# Application Config
LOG_LEVEL=INFO
WORKERS=8
MAX_UPLOAD_SIZE=104857600  # 100MB
CORS_ORIGINS=https://rag.production.com
```

### Terraform Variables

Edit `terraform/production.tfvars`:

```hcl
aws_region         = "us-east-1"
cluster_name       = "research-rag-prod"
kubernetes_version = "1.28"
environment        = "production"

# Network configuration
vpc_cidr            = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# Sensitive data (use environment variables or secrets)
openai_api_key     = var.OPENAI_API_KEY
anthropic_api_key  = var.ANTHROPIC_API_KEY
```

## 📦 File Structure

```
research-rag-pro/
├── backend/
│   ├── app/
│   │   ├── metrics.py          # Prometheus instrumentation
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── terraform/
│   ├── main.tf                 # EKS cluster, VPC, IAM
│   ├── variables.tf
│   └── production.tfvars
├── config/
│   ├── prometheus.yml          # Metrics scraping config
│   ├── prometheus-alerts.yml   # Alert rules
│   ├── nginx.conf              # Reverse proxy + WAF
│   └── grafana-datasources.yml
├── dashboards/
│   ├── rag-quality.json
│   ├── performance.json
│   └── cost-monitoring.json
├── .github/
│   ├── workflows/
│   │   └── cicd-pipeline.yml   # CI/CD with RAGAS gate
│   └── scripts/
│       ├── run_ragas_evaluation.py
│       └── smoke_tests.py
├── docker-compose.production.yml
├── k8s-manifests.yaml          # Kubernetes deployments, HPA, NetworkPolicy
└── README.md                   # This file
```

## 🧪 Testing

### Run RAGAS Evaluation Locally

```bash
# 1. Install dependencies
pip install ragas datasets openai anthropic

# 2. Prepare test dataset
cat > test_dataset.json << 'EOF'
[
  {
    "question": "What is the time complexity of QuickSort?",
    "ground_truth": "O(n log n) average case, O(n²) worst case",
    "paper_id": "cs.DS/0001234"
  }
]
EOF

# 3. Run evaluation
python .github/scripts/run_ragas_evaluation.py \
  --api-url http://localhost:8000 \
  --test-dataset test_dataset.json \
  --output results.json \
  --faithfulness-threshold 0.95

# 4. View results
cat results.json | jq '.'
```

### Load Testing

```bash
# Install k6
brew install k6  # macOS

# Run load test
k6 run --vus 100 --duration 5m tests/load/search_test.js

# Expected results:
# - P95 latency < 2s
# - Error rate < 1%
# - Throughput > 100 req/s
```

## 💰 Cost Estimation

### AWS Infrastructure (Monthly)

| Service | Configuration | Cost |
|---------|--------------|------|
| **EKS Cluster** | 1 cluster | $73 |
| **EC2 Nodes** | 3x t3.xlarge + 3x c6i.2xlarge spot | $280 |
| **ElastiCache Redis** | cache.r6g.large, 2 nodes | $220 |
| **S3 Storage** | 500GB documents | $12 |
| **Data Transfer** | 1TB outbound | $90 |
| **Secrets Manager** | 10 secrets | $4 |
| **CloudWatch Logs** | 50GB ingestion | $25 |
| **ECR Storage** | 20 images | $2 |

**Subtotal**: ~$706/month

### External Services

| Service | Configuration | Cost |
|---------|--------------|------|
| **Zilliz Cloud** (Milvus) | 1M vectors, 1536d | $99 |
| **Neo4j Aura** | Professional | $65 |
| **OpenAI API** | GPT-4 + embeddings (variable) | $200-500 |

**Total Estimate**: **$1,070 - $1,370/month**

## 🆘 Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n research-rag

# Common issues:
# - Image pull errors: Check ECR permissions
# - Resource limits: Increase CPU/memory requests
# - Secret not found: Verify AWS Secrets Manager setup
```

### HPA not scaling

```bash
# Check HPA status
kubectl get hpa -n research-rag
kubectl describe hpa research-rag-backend-hpa -n research-rag

# Verify metrics server is running
kubectl get deployment metrics-server -n kube-system

# Check pod resource usage
kubectl top pods -n research-rag
```

### RAGAS evaluation failing

```bash
# Test individual components
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/search -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'

# Check test dataset format
python -c "import json; print(json.load(open('test_dataset.json')))"

# Run with verbose logging
python .github/scripts/run_ragas_evaluation.py \
  --api-url http://localhost:8000 \
  --test-dataset test_dataset.json \
  --output results.json \
  2>&1 | tee evaluation.log
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [RAGAS Framework](https://docs.ragas.io/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Nginx Rate Limiting](https://www.nginx.com/blog/rate-limiting-nginx/)

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Support

For issues or questions:
- GitHub Issues: https://github.com/yourorg/research-rag-pro/issues
- Email: support@research-rag.com
- Slack: #research-rag-support
