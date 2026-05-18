# ResearchRAG Pro - Windows + Cowork Setup Guide

Complete step-by-step instructions for organizing and deploying ResearchRAG Pro in Cowork on Windows.

## 📋 Prerequisites

Before you start, ensure you have these installed on Windows:

- [ ] Python 3.10+ (https://www.python.org/downloads/)
- [ ] Docker Desktop (https://www.docker.com/products/docker-desktop)
- [ ] Git for Windows (https://git-scm.com/download/win)
- [ ] Visual Studio Code (optional but recommended)

## 🚀 Step 1: Download the Setup Script

1. **Download** `cowork_setup.py` from this chat
2. **Save it** to `C:\Users\malli\Downloads\cowork_setup.py`

## 🎯 Step 2: Download All ResearchRAG Pro Files

Download these files from the chat and save them to `C:\Users\malli\Downloads\`:

### Critical Files (Must Download)
```
- docker-compose.production.yml
- k8s-manifests.yaml
- main.tf
- variables.tf
- PHASE5_SUMMARY.md
- PHASE6_7_SUMMARY.md
- DEPLOYMENT.md
```

### Configuration Files
```
- nginx.conf
- prometheus.yml
- prometheus-alerts.yml
- prometheus-alerts-phase6.yml
```

### Backend Code
```
- metrics.py
- security.py
- tracing.py
```

### CI/CD & Scripts
```
- cicd-pipeline.yml
- run_ragas_evaluation.py
- production_readiness_check.py
```

**Total: 17+ files to download**

## 🔧 Step 3: Run the Automated Setup

### Option A: Using PowerShell (Recommended)

1. **Open PowerShell as Administrator**
   - Press `Win + X`
   - Click "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. **Navigate to Downloads**
   ```powershell
   cd C:\Users\malli\Downloads
   ```

3. **Run the setup script**
   ```powershell
   python cowork_setup.py
   ```

4. **Wait for completion** (2-3 minutes)
   - Script will create folder structure
   - Move files automatically
   - Generate configuration templates

### Option B: Using Command Prompt

1. **Open Command Prompt as Administrator**
   - Press `Win + R`
   - Type `cmd` and press Enter
   - Right-click and select "Run as administrator"

2. **Run**
   ```cmd
   cd %USERPROFILE%\Downloads
   python cowork_setup.py
   ```

## 📂 Step 4: Verify Folder Structure

After the script completes, check that Cowork contains this structure:

```
Cowork/ResearchRAG-Pro/
├── docker-compose.production.yml      ✅ Root
├── k8s-manifests.yaml                 ✅ Root
├── DEPLOYMENT.md                      ✅ Root
├── README.md                          ✅ Created
├── .env.example                       ✅ Created
├── .gitignore                         ✅ Created
│
├── terraform/
│   ├── main.tf                        ✅ Moved
│   ├── variables.tf                   ✅ Moved
│   └── terraform.tfvars.example       ✅ Created
│
├── config/
│   ├── nginx.conf                     ✅ Moved
│   ├── prometheus.yml                 ✅ Moved
│   ├── prometheus-alerts.yml          ✅ Moved
│   └── prometheus-alerts-phase6.yml   ✅ Moved
│
├── backend/
│   └── app/
│       ├── metrics.py                 ✅ Moved
│       ├── security.py                ✅ Moved
│       └── tracing.py                 ✅ Moved
│
├── .github/
│   ├── workflows/
│   │   └── cicd-pipeline.yml          ✅ Moved
│   └── scripts/
│       └── run_ragas_evaluation.py    ✅ Moved
│
├── scripts/
│   ├── production_readiness_check.py  ✅ Moved
│   ├── setup.sh                       ✅ Created
│   └── deploy.sh                      ✅ Created
│
└── docs/
    ├── PHASE5_SUMMARY.md              ✅ Moved
    └── PHASE6_7_SUMMARY.md            ✅ Moved
```

## 🔐 Step 5: Configure Environment

1. **Navigate to your project**
   ```powershell
   cd $env:USERPROFILE\Cowork\ResearchRAG-Pro
   ```

2. **Create .env file**
   ```powershell
   Copy-Item .env.example .env
   code .env
   ```

3. **Edit .env with your API keys**
   ```
   OPENAI_API_KEY=sk-your-key-here
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   NEO4J_PASSWORD=your-password
   REDIS_PASSWORD=your-password
   ```

4. **Save the file** (Ctrl + S)

## 🐳 Step 6: Deploy Locally with Docker Compose

1. **Verify Docker is running**
   ```powershell
   docker --version
   docker ps
   ```

2. **Start ResearchRAG Pro**
   ```powershell
   cd $env:USERPROFILE\Cowork\ResearchRAG-Pro
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **Wait for services** (2-3 minutes)
   ```powershell
   docker-compose ps
   ```

4. **Check all services are healthy**
   - All containers should show "Up" status
   - Health checks should show "(healthy)" or "Restarting..."

## 🌐 Step 7: Access the Application

Once deployed, access these endpoints:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost |
| **Backend API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Grafana** | http://localhost:3001 |
| **Prometheus** | http://localhost:9092 |
| **Swagger UI** | http://localhost:8000/redoc |

**Grafana Login:**
- Username: `admin`
- Password: `admin`

## 🧪 Step 8: Run Production Readiness Check

1. **Open PowerShell** in your project directory
   ```powershell
   cd $env:USERPROFILE\Cowork\ResearchRAG-Pro
   ```

2. **Run the readiness check**
   ```powershell
   python scripts/production_readiness_check.py
   ```

3. **Expected output** (with backend running):
   ```
   ✅ Passed:   6/9
   ❌ Failed:   0/9
   ⚠️  Warnings: 1/9
   ⏭️  Skipped:  2/9
   
   🎉 PRODUCTION READY!
   ```

## 📊 Step 9: Monitor the System

### View Logs
```powershell
# Backend logs
docker-compose logs -f backend

# All services
docker-compose logs -f

# Specific service
docker-compose logs -f milvus
```

### View Resource Usage
```powershell
docker stats
```

### Access Grafana Dashboards
1. Go to http://localhost:3001
2. Login with `admin/admin`
3. Navigate to **Dashboards** → **Browse**
4. View pre-configured RAG dashboards

## 🚨 Troubleshooting

### Problem: "Port 8000 already in use"
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process
taskkill /PID <PID> /F

# Or change the port in docker-compose
# Edit docker-compose.production.yml and change 8000:8000 to 8001:8000
```

### Problem: "Docker daemon not running"
```powershell
# Restart Docker Desktop
# Or from PowerShell:
# In Docker Desktop Settings → General → Enable Hyper-V
```

### Problem: "No such file: docker-compose.production.yml"
```powershell
# Make sure you're in the correct directory
Get-Location
cd $env:USERPROFILE\Cowork\ResearchRAG-Pro

# List files to verify
ls *.yml
```

### Problem: "API connection refused"
```powershell
# Check if backend is running
docker-compose ps

# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Problem: Can't access http://localhost:8000
```powershell
# Test connection
curl http://localhost:8000/health

# Or in PowerShell
Invoke-WebRequest http://localhost:8000/health
```

## 📚 Next Steps

Once running locally:

1. **Ingest test papers** into the system
2. **Run RAGAS evaluation** to validate quality
3. **Explore the API** at http://localhost:8000/docs
4. **Review dashboards** in Grafana
5. **Read deployment guide**: `DEPLOYMENT.md`

## 🌍 Deploy to Production (AWS)

When ready for production:

1. **Install Terraform**
   ```powershell
   choco install terraform  # Using Chocolatey
   ```

2. **Configure AWS credentials**
   ```powershell
   aws configure
   ```

3. **Deploy infrastructure**
   ```powershell
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

4. **Deploy application**
   ```powershell
   kubectl apply -f ../k8s-manifests.yaml
   ```

## 📞 Support

**If you encounter issues:**

1. Check the **troubleshooting section** above
2. View **docker-compose logs**:
   ```powershell
   docker-compose logs -f
   ```
3. Run the **readiness check**:
   ```powershell
   python scripts/production_readiness_check.py
   ```
4. Check documentation:
   - `DEPLOYMENT.md` - Deployment guide
   - `docs/PHASE6_7_SUMMARY.md` - Security & compliance

## ✅ Checklist

- [ ] Downloaded all files to `C:\Users\malli\Downloads\`
- [ ] Ran `cowork_setup.py` successfully
- [ ] Verified folder structure in Cowork
- [ ] Created and edited `.env` file
- [ ] Docker is installed and running
- [ ] Started `docker-compose up -d`
- [ ] All services are healthy (`docker-compose ps`)
- [ ] Can access http://localhost:8000/health
- [ ] Ran production readiness check
- [ ] Accessed Grafana at http://localhost:3001

---

## 🎉 You're All Set!

ResearchRAG Pro is now organized in Cowork and ready to run locally or deploy to production!

**Next:** Edit `.env` with your API keys and run `docker-compose up -d`

Questions? Check `DEPLOYMENT.md` or `docs/TROUBLESHOOTING.md`
