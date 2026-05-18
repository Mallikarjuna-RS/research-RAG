# ResearchRAG Pro - Cowork Setup - Quick Reference

## ⚡ 5-Minute Setup

### 1️⃣ Download Setup Script
```
📥 Download: cowork_setup.py
📂 Save to: C:\Users\malli\Downloads\
```

### 2️⃣ Download All ResearchRAG Files
```
📥 Download 17+ files from this chat
📂 Save all to: C:\Users\malli\Downloads\
```

### 3️⃣ Run Setup
```powershell
cd C:\Users\malli\Downloads
python cowork_setup.py
```

### 4️⃣ Configure API Keys
```powershell
cd $env:USERPROFILE\Cowork\ResearchRAG-Pro
code .env
# Add your OpenAI and Anthropic API keys
```

### 5️⃣ Start Services
```powershell
docker-compose -f docker-compose.production.yml up -d
```

### 6️⃣ Verify Running
```
✅ Frontend: http://localhost
✅ Backend: http://localhost:8000
✅ Grafana: http://localhost:3001
```

---

## 📂 Files to Download

### Critical (Must Have)
- [ ] docker-compose.production.yml
- [ ] k8s-manifests.yaml
- [ ] DEPLOYMENT.md
- [ ] production_readiness_check.py

### Infrastructure
- [ ] main.tf
- [ ] variables.tf
- [ ] nginx.conf
- [ ] prometheus.yml
- [ ] prometheus-alerts.yml
- [ ] prometheus-alerts-phase6.yml

### Code
- [ ] metrics.py
- [ ] security.py
- [ ] tracing.py
- [ ] cicd-pipeline.yml
- [ ] run_ragas_evaluation.py

### Documentation
- [ ] PHASE5_SUMMARY.md
- [ ] PHASE6_7_SUMMARY.md
- [ ] WINDOWS_COWORK_SETUP.md
- [ ] cowork_setup.py

**Total: 18 files**

---

## 🎯 Expected Folder Structure

After setup completes:

```
C:\Users\malli\Cowork\ResearchRAG-Pro\
├── docker-compose.production.yml
├── k8s-manifests.yaml
├── README.md
├── .env (your API keys here)
├── terraform/
├── config/
├── backend/
├── .github/
├── scripts/
└── docs/
```

---

## 🚀 Common Commands

### Start Services
```powershell
cd $env:USERPROFILE\Cowork\ResearchRAG-Pro
docker-compose -f docker-compose.production.yml up -d
```

### Stop Services
```powershell
docker-compose -f docker-compose.production.yml down
```

### View Logs
```powershell
docker-compose logs -f backend
```

### Run Readiness Check
```powershell
python scripts/production_readiness_check.py
```

### View Services Status
```powershell
docker-compose ps
```

---

## 🌐 Access Points

| Service | URL | Login |
|---------|-----|-------|
| Frontend | http://localhost | - |
| Backend | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3001 | admin/admin |
| Prometheus | http://localhost:9092 | - |

---

## 🆘 Quick Troubleshooting

### Port Already in Use
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Docker Not Running
```
Open Docker Desktop application
Or: Restart Docker service
```

### Files Not Found
```powershell
# Verify you're in correct directory
$env:USERPROFILE\Cowork\ResearchRAG-Pro
ls
```

### API Connection Refused
```powershell
# Check service status
docker-compose ps

# View logs
docker-compose logs backend

# Restart
docker-compose restart backend
```

---

## 📋 Setup Checklist

- [ ] Python 3.10+ installed
- [ ] Docker Desktop installed
- [ ] All 18 files downloaded to C:\Users\malli\Downloads
- [ ] Setup script ran successfully
- [ ] Folder structure created in Cowork
- [ ] .env file configured with API keys
- [ ] Docker services started
- [ ] All containers healthy
- [ ] Can access http://localhost:8000/health
- [ ] Readiness check passed (6/9)

---

## 📚 Documentation Files

Located in: `C:\Users\malli\Cowork\ResearchRAG-Pro\docs\`

- **PHASE5_SUMMARY.md** - Infrastructure & deployment
- **PHASE6_7_SUMMARY.md** - Security & compliance
- **WINDOWS_COWORK_SETUP.md** - This setup guide
- **DEPLOYMENT.md** - Complete deployment reference
- **README.md** - Project overview

---

## 🎉 You're Ready!

```
1. Download cowork_setup.py ✅
2. Download 17 files ✅
3. Run python cowork_setup.py ✅
4. Edit .env with API keys ✅
5. docker-compose up -d ✅
6. Access http://localhost:8000 ✅
```

**Next Step:** Edit `.env` and start services!

---

## 💡 Pro Tips

1. **Use Windows Terminal** instead of Command Prompt
   ```
   Download from Microsoft Store (free)
   Better formatting and colors
   ```

2. **Set VS Code as default editor**
   ```powershell
   # Edit .env easily
   code .env
   ```

3. **Create PowerShell alias**
   ```powershell
   # Quick navigation
   Set-Alias -Name ragpro -Value "cd $env:USERPROFILE\Cowork\ResearchRAG-Pro"
   # Then just type: ragpro
   ```

4. **Monitor Docker resources**
   ```powershell
   docker stats
   ```

5. **Keep .env secure**
   - Never commit to Git
   - Never share your API keys
   - Use AWS Secrets Manager in production

---

**Created:** January 2025
**Version:** 1.0.0
**Status:** Production Ready ✅
