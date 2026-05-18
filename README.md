# ResearchRAG Pro

**AI-powered research assistant** — upload academic papers (PDF / DOCX / TeX), ask questions, and get cited answers grounded in your document library.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Starting the App](#starting-the-app)
3. [Opening the Dashboard](#opening-the-dashboard)
4. [How to Use](#how-to-use)
5. [Where Files Are Stored](#where-files-are-stored)
6. [API Endpoints](#api-endpoints)
7. [Tech Stack](#tech-stack)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9 + | Use **Miniconda** install — Windows Store Python lacks required packages |
| Flask | 2.x | Installed in Miniconda base env |
| flask-cors | any | Installed alongside Flask |

### Install dependencies (first time only)

```bash
C:\Users\malli\miniconda3\Scripts\conda.exe run -n base pip install flask flask-cors
```

---

## Starting the App

Open **PowerShell** and run:

```powershell
Start-Process "C:\Users\malli\miniconda3\python.exe" `
  -ArgumentList "C:\Users\malli\Downloads\RAG\app.py" `
  -WorkingDirectory "C:\Users\malli\Downloads\RAG" `
  -WindowStyle Minimized
```

Verify the backend is running:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:
```json
{ "status": "ok", "service": "ResearchRAG-Pro", "papers": 0 }
```

> The backend runs on **http://localhost:8000** and must stay running while you use the dashboard.

---

## Opening the Dashboard

Double-click the file in File Explorer:

```
C:\Users\malli\Downloads\RAG\ResearchRAG-Dashboard.html
```

Or open it from PowerShell:

```powershell
Start-Process "C:\Users\malli\Downloads\RAG\ResearchRAG-Dashboard.html"
```

The dashboard opens in your default browser. No web server needed for the frontend — it is a self-contained HTML file.

---

## How to Use

### 1. Upload a Research Paper

- The app opens on the **Upload** screen by default.
- Click **"Upload Document"** or the paperclip icon in the message bar.
- Supported formats: `.pdf`, `.docx`, `.tex`
- After selecting a file, a progress bar appears. When complete, the dashboard shows extracted statistics:
  - Number of chunks, equations, tables, and algorithms detected.

### 2. Ask Questions

- Type your question in the **"Type a message to Rag."** input bar and press **Enter** (or click the send button).
- The system:
  1. Searches the knowledge base for relevant chunks (`/api/search`)
  2. Generates a grounded answer with citations (`/api/generate`)
  3. Displays the response with paper references and section numbers

### 3. Example Questions

| Question | What it returns |
|---|---|
| `What is the attention formula?` | Scaled dot-product equation from Vaswani et al. 2017 |
| `How does BERT pre-training work?` | Masked Language Model algorithm from Devlin et al. 2019 |
| `Compare ViT vs CNN approaches` | Side-by-side comparison across retrieved papers |
| `Explain RAG step by step` | Algorithm walkthrough from Lewis et al. 2020 |

### 4. New Conversation

- Click **"New conversation"** in the left sidebar to start a fresh chat session.
- Each conversation has its own isolated message history.

### 5. Sidebar Navigation

| Icon | Section | Purpose |
|---|---|---|
| 💬 | Chats | Conversation history |
| 📊 | Requests | Live API request log |
| 👥 | Users | Manage research team members |
| ⚙️ | Settings | Customization options |

---

## Where Files Are Stored

### Uploaded Documents

> **Current version: in-memory only.**

Uploaded files are processed by the backend and their metadata (filename, paper ID, chunk counts) is stored in RAM inside the running Python process. **The file bytes themselves are not written to disk.**

| Data | Location | Persists after restart? |
|---|---|---|
| Uploaded file contents | RAM (`PAPERS` list in `app.py`) | ❌ No |
| Chat message history | RAM (`CHATS` dict in `app.py`) | ❌ No |
| Paper metadata (filename, chunk counts) | RAM | ❌ No |

**What this means:** if you stop the Flask backend and restart it, all uploaded papers and chat history are cleared. You will need to re-upload your documents.

### Future persistence (production setup)

The production infrastructure defined in `docker-compose.production.yml` uses:

| Store | Purpose |
|---|---|
| **Milvus** (vector DB) | Stores document embeddings for semantic search |
| **Neo4j** (graph DB) | Stores knowledge graph relationships between papers |
| **Redis** | Caches query results for faster repeated lookups |

These require Docker and are not active in the current local setup.

### Asset files (always on disk)

| File | Location |
|---|---|
| PINNRAG logo | `C:\Users\malli\Downloads\RAG\pinnrag-logo.png` |
| M avatar logo | `C:\Users\malli\Downloads\RAG\m-logo.png` |
| Dashboard UI | `C:\Users\malli\Downloads\RAG\ResearchRAG-Dashboard.html` |
| Backend server | `C:\Users\malli\Downloads\RAG\app.py` |

---

## API Endpoints

All endpoints served at `http://localhost:8000`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend health check |
| `POST` | `/api/search` | Semantic chunk search — body: `{ "query": "...", "top_k": 5 }` |
| `POST` | `/api/generate` | RAG answer generation — body: `{ "query": "...", "chat_id": "..." }` |
| `POST` | `/api/ingest` | Upload a document — multipart form with `file` field |
| `GET` | `/api/chats/<id>/messages` | Fetch message history for a conversation |
| `POST` | `/api/cite` | Generate citations for a text snippet |
| `GET` | `/api/users` | List team members |
| `POST` | `/api/users` | Create a new team member |
| `GET` | `/metrics` | Prometheus metrics scrape endpoint |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML / CSS / JavaScript (single file) |
| Backend | Python 3 · Flask · flask-cors |
| Fonts | Space Grotesk · DM Sans · JetBrains Mono |
| Vector DB (prod) | Milvus v2.3 |
| Graph DB (prod) | Neo4j 5.15 Enterprise |
| Cache (prod) | Redis 7.2 |
| Reverse proxy (prod) | Nginx 1.25 |
| Monitoring (prod) | Prometheus + Grafana |

---

## Troubleshooting

### Backend won't start — `ModuleNotFoundError: flask`

Use the Miniconda Python explicitly. The Windows Store Python (`python.exe` on PATH) does not have Flask installed.

```powershell
# Wrong — uses Windows Store Python
python app.py

# Correct — uses Miniconda Python
C:\Users\malli\miniconda3\python.exe app.py
```

### Dashboard shows "Backend offline" or no responses

1. Check the backend is running:
   ```powershell
   Invoke-RestMethod http://localhost:8000/health
   ```
2. If no response, restart it using the command in [Starting the App](#starting-the-app).

### Uploaded file seems to do nothing after restart

The current backend is in-memory. Re-upload your document after every backend restart.

### Port 8000 already in use

Find and stop the existing process:

```powershell
# Find the process using port 8000
netstat -ano | findstr :8000

# Stop it (replace 1234 with the actual PID)
Stop-Process -Id 1234 -Force
```

---

*Built by Dr. M. Mallikarjuna — ResearchRAG Pro v1.0*
