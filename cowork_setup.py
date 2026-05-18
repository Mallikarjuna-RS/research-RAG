#!/usr/bin/env python3
"""
ResearchRAG Pro - Cowork Desktop Automation Setup Script

This script automates the organization of ResearchRAG Pro files in Cowork.
It will:
1. Create folder structure
2. Download/move files to correct locations
3. Setup environment
4. Prepare for deployment
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List
import subprocess
import json

# ========================================
# CONFIGURATION
# ========================================

# Target directory in Cowork (adjust based on your setup)
COWORK_BASE_PATH = Path.home() / "Cowork" / "ResearchRAG-Pro"
DOWNLOADS_PATH = Path.home() / "Downloads"

# Project structure
FOLDER_STRUCTURE = {
    "root": [
        "docker-compose.production.yml",
        "k8s-manifests.yaml",
        "DEPLOYMENT.md",
        "PHASE5_SUMMARY.md",
        "PHASE6_7_SUMMARY.md",
        ".env.example",
        ".gitignore",
    ],
    "terraform": [
        "main.tf",
        "variables.tf",
        "terraform.tfvars.example",
        "outputs.tf",
    ],
    "config": [
        "nginx.conf",
        "prometheus.yml",
        "prometheus-alerts.yml",
        "prometheus-alerts-phase6.yml",
        "grafana-datasources.yml",
        "milvus.yaml",
    ],
    "backend/app": [
        "metrics.py",
        "security.py",
        "tracing.py",
        "__init__.py",
    ],
    "backend": [
        "Dockerfile",
        "requirements.txt",
    ],
    ".github/workflows": [
        "cicd-pipeline.yml",
    ],
    ".github/scripts": [
        "run_ragas_evaluation.py",
        "smoke_tests.py",
    ],
    "scripts": [
        "production_readiness_check.py",
        "setup.sh",
        "deploy.sh",
    ],
    "dashboards": [
        "rag-quality.json",
        "performance.json",
        "cost-monitoring.json",
    ],
    "docs": [
        "API_GUIDE.md",
        "RUNBOOK.md",
        "TROUBLESHOOTING.md",
    ],
}


# ========================================
# SETUP FUNCTIONS
# ========================================

def create_folder_structure():
    """Create the complete folder structure."""
    print("\n📁 Creating folder structure...\n")
    
    folders_to_create = [
        COWORK_BASE_PATH,
        COWORK_BASE_PATH / "terraform",
        COWORK_BASE_PATH / "config",
        COWORK_BASE_PATH / "backend" / "app",
        COWORK_BASE_PATH / ".github" / "workflows",
        COWORK_BASE_PATH / ".github" / "scripts",
        COWORK_BASE_PATH / "scripts",
        COWORK_BASE_PATH / "dashboards",
        COWORK_BASE_PATH / "docs",
        COWORK_BASE_PATH / "tests" / "unit",
        COWORK_BASE_PATH / "tests" / "integration",
        COWORK_BASE_PATH / "tests" / "evaluation",
    ]
    
    for folder in folders_to_create:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {folder.relative_to(COWORK_BASE_PATH)}")
    
    print(f"\n✅ Folder structure created at: {COWORK_BASE_PATH}\n")
    return COWORK_BASE_PATH


def find_files_in_downloads() -> Dict[str, Path]:
    """Find ResearchRAG Pro files in Downloads folder."""
    print("\n🔍 Searching for ResearchRAG Pro files in Downloads...\n")
    
    found_files = {}
    expected_files = [
        "docker-compose.production.yml",
        "k8s-manifests.yaml",
        "main.tf",
        "variables.tf",
        "nginx.conf",
        "prometheus.yml",
        "prometheus-alerts.yml",
        "prometheus-alerts-phase6.yml",
        "metrics.py",
        "security.py",
        "tracing.py",
        "cicd-pipeline.yml",
        "run_ragas_evaluation.py",
        "production_readiness_check.py",
        "PHASE5_SUMMARY.md",
        "PHASE6_7_SUMMARY.md",
        "DEPLOYMENT.md",
    ]
    
    for filename in expected_files:
        filepath = DOWNLOADS_PATH / filename
        if filepath.exists():
            found_files[filename] = filepath
            print(f"✅ Found: {filename}")
        else:
            print(f"⚠️  Missing: {filename}")
    
    print(f"\n📊 Found {len(found_files)}/{len(expected_files)} files\n")
    return found_files


def move_files_to_cowork(found_files: Dict[str, Path]):
    """Move files from Downloads to Cowork structure."""
    print("\n📦 Moving files to Cowork...\n")
    
    # Mapping of filename -> target subfolder
    file_mapping = {
        "docker-compose.production.yml": ".",
        "k8s-manifests.yaml": ".",
        "DEPLOYMENT.md": ".",
        "PHASE5_SUMMARY.md": "docs",
        "PHASE6_7_SUMMARY.md": "docs",
        "main.tf": "terraform",
        "variables.tf": "terraform",
        "nginx.conf": "config",
        "prometheus.yml": "config",
        "prometheus-alerts.yml": "config",
        "prometheus-alerts-phase6.yml": "config",
        "metrics.py": "backend/app",
        "security.py": "backend/app",
        "tracing.py": "backend/app",
        "cicd-pipeline.yml": ".github/workflows",
        "run_ragas_evaluation.py": ".github/scripts",
        "production_readiness_check.py": "scripts",
    }
    
    moved_count = 0
    
    for filename, source_path in found_files.items():
        target_subfolder = file_mapping.get(filename, ".")
        target_path = COWORK_BASE_PATH / target_subfolder / filename
        
        try:
            shutil.move(str(source_path), str(target_path))
            print(f"✅ Moved: {filename} → {target_subfolder}/")
            moved_count += 1
        except Exception as e:
            print(f"❌ Failed to move {filename}: {str(e)}")
    
    print(f"\n✅ Moved {moved_count}/{len(found_files)} files\n")


def create_env_file():
    """Create .env.example file."""
    print("\n🔐 Creating .env.example...\n")
    
    env_content = """# ResearchRAG Pro - Environment Configuration
# Copy this file to .env and fill in your actual values

# ========================================
# LLM API KEYS (Required)
# ========================================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ========================================
# DATABASE CREDENTIALS
# ========================================
NEO4J_PASSWORD=change-me-strong-password
REDIS_PASSWORD=change-me-strong-password
MINIO_PASSWORD=change-me-strong-password
MINIO_USER=change-me-admin-user
MILVUS_TOKEN=your-milvus-token

# ========================================
# API SECURITY
# ========================================
API_KEYS=key1,key2,key3
JWT_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key

# ========================================
# AWS CONFIGURATION
# ========================================
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
EKS_CLUSTER_NAME=research-rag-prod

# ========================================
# APPLICATION CONFIGURATION
# ========================================
ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=8
MAX_UPLOAD_SIZE=104857600

# ========================================
# DOMAIN & URLS
# ========================================
DOMAIN=rag.production.com
API_URL=https://rag.production.com/api
WS_URL=wss://rag.production.com/ws

# ========================================
# MONITORING
# ========================================
JAEGER_HOST=jaeger
PROMETHEUS_PORT=9090
GRAFANA_PASSWORD=admin

# ========================================
# EXTERNAL SERVICES
# ========================================
MILVUS_HOST=milvus.zillizcloud.com
NEO4J_URI=bolt+s://xxxxx.databases.neo4j.io:7687
REDIS_HOST=research-rag.xxxxx.ng.0001.use1.cache.amazonaws.com
"""
    
    env_path = COWORK_BASE_PATH / ".env.example"
    env_path.write_text(env_content)
    print(f"✅ Created: .env.example\n")


def create_gitignore():
    """Create .gitignore file."""
    print("📝 Creating .gitignore...\n")
    
    gitignore_content = """# Environment variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/
.venv

# Docker
.dockerignore
docker-compose.override.yml

# Kubernetes
kubeconfig
*.kubeconfig

# Terraform
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl
*.tfvars
!terraform.tfvars.example

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Node
node_modules/
package-lock.json

# Build artifacts
uploads/
dist/
build/

# Secrets
secrets/
*.pem
*.key
*.crt
"""
    
    gitignore_path = COWORK_BASE_PATH / ".gitignore"
    gitignore_path.write_text(gitignore_content)
    print(f"✅ Created: .gitignore\n")


def create_readme():
    """Create README.md file."""
    print("📚 Creating README.md...\n")
    
    readme_content = """# ResearchRAG Pro - Enterprise RAG System

Production-ready Retrieval-Augmented Generation (RAG) system with:
- Advanced paper parsing (PDF, images, LaTeX math)
- Vector search (Milvus) + Knowledge graph (Neo4j)
- Multi-modal RAG (text + equations + code)
- RAGAS quality gates (faithfulness > 0.95)
- Auto-scaling (3-20 replicas)
- Security hardening (OAuth, RBAC, GDPR)
- Full observability (traces, logs, metrics)

## 🚀 Quick Start

### Local Development (Docker Compose)
```bash
# 1. Copy environment file
cp .env.example .env
nano .env  # Add your API keys

# 2. Start services
docker-compose -f docker-compose.production.yml up -d

# 3. Access application
open http://localhost
# Backend API: http://localhost:8000
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9092
```

### Production (Kubernetes + Terraform)
```bash
# 1. Provision AWS infrastructure
cd terraform
terraform init
terraform plan -var-file=production.tfvars
terraform apply

# 2. Configure kubectl
aws eks update-kubeconfig --name research-rag-prod --region us-east-1

# 3. Deploy application
kubectl apply -f ../k8s-manifests.yaml

# 4. Verify
kubectl get pods -n research-rag
kubectl get ingress -n research-rag
```

### Validate Production Readiness
```bash
python scripts/production_readiness_check.py --api-url http://localhost:8000
```

## 📚 Documentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide
- **[PHASE5_SUMMARY.md](./docs/PHASE5_SUMMARY.md)** - Infrastructure overview
- **[PHASE6_7_SUMMARY.md](./docs/PHASE6_7_SUMMARY.md)** - Security & compliance
- **[API_GUIDE.md](./docs/API_GUIDE.md)** - API reference
- **[RUNBOOK.md](./docs/RUNBOOK.md)** - Operations runbook
- **[TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** - Common issues

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         EKS Kubernetes Cluster              │
├─────────────────────────────────────────────┤
│                                             │
│  Backend (FastAPI)  ← Auto-scaling 3-20    │
│  Frontend (React)   ← Auto-scaling 2-10    │
│                                             │
│  Dependencies:                              │
│  - Milvus (vector DB)                      │
│  - Neo4j (knowledge graph)                 │
│  - Redis (caching)                         │
│  - Prometheus (metrics)                    │
│  - Grafana (dashboards)                    │
│                                             │
└─────────────────────────────────────────────┘
```

## 🔒 Security Features

- OAuth 2.0 + OIDC authentication
- Role-based access control (RBAC)
- AES-256 encryption at rest
- TLS 1.3 for all communication
- GDPR + HIPAA compliance
- Immutable audit logging
- DDoS protection (rate limiting, WAF)
- NetworkPolicy pod isolation

## 📊 Monitoring

- **Prometheus**: 100+ custom metrics
- **Grafana**: Pre-configured dashboards
- **Jaeger**: Distributed tracing
- **Alerts**: PagerDuty/Slack integration

Key metrics:
- RAGAS faithfulness (target: > 0.95)
- API latency P99 (target: < 5s)
- Math accuracy (target: > 0.98)
- GPU utilization (target: < 95%)

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Load testing
k6 run tests/load/search_test.js

# Production readiness
python scripts/production_readiness_check.py
```

## 💰 Cost Estimation

- **AWS Infrastructure**: ~$700/month
- **External Services**: ~$165/month
- **Total**: ~$1,000-1,370/month

## 📋 Project Structure

```
ResearchRAG-Pro/
├── docker-compose.production.yml    # Local development
├── k8s-manifests.yaml               # Kubernetes deployment
├── terraform/                        # AWS infrastructure
├── config/                           # Configuration files
├── backend/                          # FastAPI application
├── frontend/                         # React dashboard
├── scripts/                          # Utility scripts
├── docs/                             # Documentation
├── tests/                            # Test suites
└── dashboards/                       # Grafana dashboards
```

## 🤝 Contributing

1. Create a feature branch
2. Make changes
3. Run tests: `pytest`
4. Submit pull request
5. CI/CD pipeline validates with RAGAS quality gates

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

- **Documentation**: See docs/ folder
- **Issues**: Create GitHub issue
- **Email**: support@research-rag.com
- **Slack**: #research-rag-support

---

**ResearchRAG Pro v1.0.0** | Production Ready ✅
"""
    
    readme_path = COWORK_BASE_PATH / "README.md"
    readme_path.write_text(readme_content)
    print(f"✅ Created: README.md\n")


def create_setup_scripts():
    """Create automation scripts."""
    print("🔧 Creating setup scripts...\n")
    
    # setup.sh
    setup_sh = """#!/bin/bash
set -e

echo "🚀 ResearchRAG Pro Setup Script"
echo "================================"

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v python3 &> /dev/null || { echo "❌ Python 3 not found"; exit 1; }
command -v docker &> /dev/null || { echo "⚠️  Docker not found (required for local deployment)"; }

# Create Python virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt 2>/dev/null || echo "⚠️  requirements.txt not found"

# Create .env file
if [ ! -f .env ]; then
    echo "🔐 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Edit .env and add your API keys before running"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📖 Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. For local deployment: docker-compose -f docker-compose.production.yml up -d"
echo "3. For production: cd terraform && terraform apply"
echo "4. Run readiness check: python scripts/production_readiness_check.py"
echo ""
"""
    
    setup_path = COWORK_BASE_PATH / "setup.sh"
    setup_path.write_text(setup_sh)
    setup_path.chmod(0o755)
    print("✅ Created: setup.sh")
    
    # deploy.sh
    deploy_sh = """#!/bin/bash
set -e

echo "🚀 ResearchRAG Pro Deployment Script"
echo "===================================="

DEPLOYMENT_TYPE=${1:-local}

if [ "$DEPLOYMENT_TYPE" = "local" ]; then
    echo "📦 Deploying locally with Docker Compose..."
    
    if [ ! -f .env ]; then
        echo "❌ .env file not found. Run setup.sh first."
        exit 1
    fi
    
    docker-compose -f docker-compose.production.yml down 2>/dev/null || true
    docker-compose -f docker-compose.production.yml up -d
    
    echo "✅ Local deployment complete!"
    echo ""
    echo "📍 Access points:"
    echo "  - Frontend: http://localhost"
    echo "  - Backend API: http://localhost:8000"
    echo "  - Grafana: http://localhost:3001"
    echo "  - Prometheus: http://localhost:9092"
    
elif [ "$DEPLOYMENT_TYPE" = "production" ]; then
    echo "🌍 Deploying to AWS EKS..."
    
    if [ ! -d terraform ]; then
        echo "❌ terraform directory not found"
        exit 1
    fi
    
    echo "1️⃣  Provisioning infrastructure..."
    cd terraform
    terraform apply -var-file=production.tfvars || exit 1
    cd ..
    
    echo "2️⃣  Updating kubeconfig..."
    aws eks update-kubeconfig --name research-rag-prod --region us-east-1 || exit 1
    
    echo "3️⃣  Deploying application..."
    kubectl apply -f k8s-manifests.yaml || exit 1
    
    echo "✅ Production deployment complete!"
    echo ""
    echo "📍 Access:"
    kubectl get ingress -n research-rag
    
else
    echo "❌ Unknown deployment type: $DEPLOYMENT_TYPE"
    echo "Usage: ./deploy.sh [local|production]"
    exit 1
fi

echo ""
echo "🧪 Run production readiness check:"
echo "   python scripts/production_readiness_check.py"
"""
    
    deploy_path = COWORK_BASE_PATH / "deploy.sh"
    deploy_path.write_text(deploy_sh)
    deploy_path.chmod(0o755)
    print("✅ Created: deploy.sh")
    
    print()


def create_summary_report(found_files: Dict[str, Path]):
    """Create a summary report."""
    print("\n" + "="*70)
    print("  📊 SETUP SUMMARY REPORT")
    print("="*70 + "\n")
    
    print(f"📁 Project Location: {COWORK_BASE_PATH}\n")
    
    print(f"✅ Files Organized: {len(found_files)}")
    print(f"📂 Folders Created: 12")
    print(f"📝 Configuration Files: 3")
    print(f"🔧 Setup Scripts: 2\n")
    
    print("📋 Key Files:")
    print(f"  • Docker Compose: {COWORK_BASE_PATH / 'docker-compose.production.yml'}")
    print(f"  • K8s Manifests: {COWORK_BASE_PATH / 'k8s-manifests.yaml'}")
    print(f"  • Terraform: {COWORK_BASE_PATH / 'terraform'}")
    print(f"  • Backend: {COWORK_BASE_PATH / 'backend'}")
    print(f"  • Documentation: {COWORK_BASE_PATH / 'docs'}\n")
    
    print("🚀 Next Steps:")
    print(f"  1. Navigate to: {COWORK_BASE_PATH}")
    print(f"  2. Edit .env with your API keys")
    print(f"  3. Run: ./setup.sh")
    print(f"  4. Run: ./deploy.sh local  (for development)")
    print(f"  5. Run: ./deploy.sh production  (for AWS)\n")
    
    print("📖 Documentation:")
    print(f"  • {COWORK_BASE_PATH / 'README.md'}")
    print(f"  • {COWORK_BASE_PATH / 'DEPLOYMENT.md'}")
    print(f"  • {COWORK_BASE_PATH / 'docs' / 'PHASE5_SUMMARY.md'}")
    print(f"  • {COWORK_BASE_PATH / 'docs' / 'PHASE6_7_SUMMARY.md'}\n")
    
    print("="*70)
    print("  ✅ Setup Complete!")
    print("="*70 + "\n")


# ========================================
# MAIN EXECUTION
# ========================================

def main():
    """Run the complete setup process."""
    
    print("\n" + "="*70)
    print("  🚀 ResearchRAG Pro - Cowork Setup Automation")
    print("="*70)
    
    try:
        # Step 1: Create folder structure
        project_path = create_folder_structure()
        
        # Step 2: Find files in Downloads
        found_files = find_files_in_downloads()
        
        # Step 3: Move files to Cowork
        if found_files:
            move_files_to_cowork(found_files)
        
        # Step 4: Create configuration files
        create_env_file()
        create_gitignore()
        create_readme()
        create_setup_scripts()
        
        # Step 5: Create summary report
        create_summary_report(found_files)
        
        print("✅ All done! Your ResearchRAG Pro project is ready in Cowork!")
        print(f"📂 Location: {COWORK_BASE_PATH}\n")
        
    except Exception as e:
        print(f"\n❌ Error during setup: {str(e)}\n")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
