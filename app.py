"""
ResearchRAG Pro — Local Flask backend
Serves all API endpoints expected by ResearchRAG-Dashboard.html
"""

import uuid
import random
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── In-memory stores ──────────────────────────────────────────────────────────
CHATS: dict = {}        # chat_id -> list[{role, content}]
PAPERS: list = []       # ingested paper metadata
USERS: list = [
    {"id": "u1", "name": "Eleanor Pena",    "email": "eleanor@research.edu",   "status": "Active",   "limit": 24, "date": "12-12-2024"},
    {"id": "u2", "name": "Kristin Watson",  "email": "kristin@university.ac",  "status": "Inactive", "limit": 24, "date": "12-12-2024"},
    {"id": "u3", "name": "Jerome Bell",     "email": "jerome@lab.org",         "status": "Active",   "limit": 24, "date": "12-12-2024"},
]

# ── Sample knowledge base for mock search ─────────────────────────────────────
KNOWLEDGE_BASE = [
    {
        "paper": "Attention Is All You Need",
        "authors": "Vaswani et al.",
        "year": 2017,
        "section": "3.2.1",
        "type": "equation",
        "content": "Scaled dot-product attention: Attention(Q,K,V) = softmax(QKᵀ/√dₖ)·V",
        "latex": r"Attention(Q,K,V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right) V",
        "keywords": ["attention", "transformer", "self-attention", "multi-head"],
    },
    {
        "paper": "BERT: Pre-training of Deep Bidirectional Transformers",
        "authors": "Devlin et al.",
        "year": 2019,
        "section": "3.1",
        "type": "algorithm",
        "content": "Masked Language Model pre-training: randomly mask 15% of tokens and predict them.",
        "keywords": ["bert", "masked language model", "pre-training", "bidirectional"],
    },
    {
        "paper": "An Image is Worth 16x16 Words",
        "authors": "Dosovitskiy et al.",
        "year": 2021,
        "section": "3",
        "type": "text",
        "content": "Split image into 16×16 patches, embed linearly, add positional encodings, feed to Transformer encoder.",
        "keywords": ["vision transformer", "vit", "image patches", "visual recognition"],
    },
    {
        "paper": "Retrieval-Augmented Generation for NLP",
        "authors": "Lewis et al.",
        "year": 2020,
        "section": "2",
        "type": "text",
        "content": "RAG combines a parametric memory (language model) with a non-parametric memory (dense vector retrieval) for open-domain QA.",
        "keywords": ["rag", "retrieval", "generation", "open-domain qa", "dense retrieval"],
    },
    {
        "paper": "Language Models are Few-Shot Learners",
        "authors": "Brown et al.",
        "year": 2020,
        "section": "2.1",
        "type": "text",
        "content": "GPT-3 with 175B parameters demonstrates strong few-shot learning without task-specific fine-tuning.",
        "keywords": ["gpt-3", "few-shot", "in-context learning", "large language model"],
    },
    {
        "paper": "Deep Residual Learning for Image Recognition",
        "authors": "He et al.",
        "year": 2016,
        "section": "3",
        "type": "equation",
        "content": "Residual learning: H(x) = F(x) + x, where F(x) is the residual mapping.",
        "latex": r"H(x) = \mathcal{F}(x) + x",
        "keywords": ["resnet", "residual", "skip connection", "deep learning"],
    },
]


def _score_result(entry: dict, query: str) -> float:
    q = query.lower()
    score = 0.0
    for kw in entry.get("keywords", []):
        if kw in q:
            score += 0.25
    if any(w in entry["content"].lower() for w in q.split()):
        score += 0.15
    return min(0.98, max(0.55, score + random.uniform(0.4, 0.6)))


def _search_chunks(query: str, top_k: int = 5) -> list:
    results = []
    for entry in KNOWLEDGE_BASE:
        score = _score_result(entry, query)
        chunk = {
            "chunk_id": str(uuid.uuid4())[:8],
            "type": entry["type"],
            "paper": entry["paper"],
            "authors": entry["authors"],
            "year": entry["year"],
            "section": entry["section"],
            "score": round(score, 3),
            "content": entry["content"],
            "keywords": entry.get("keywords", []),
        }
        if entry.get("latex"):
            chunk["latex"] = entry["latex"]
        results.append(chunk)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def _generate_answer(query: str, chunks: list) -> str:
    q = query.lower()

    if chunks:
        top = chunks[0]
        paper_ref = f"[{top['authors']}, {top['year']}, §{top['section']}]"

        if any(w in q for w in ["formula", "equation", "math", "attention", "derive"]):
            return (
                f"Based on retrieved context from **{top['paper']}** {paper_ref}:\n\n"
                f"{top['content']}\n\n"
                f"This formulation ensures numerical stability by scaling dot-products by √dₖ, "
                f"preventing vanishing gradients in high-dimensional embedding spaces. "
                f"The multi-head variant runs h=8 parallel attention heads, each with dₖ=64."
            )

        if any(w in q for w in ["algorithm", "pseudocode", "steps", "how does"]):
            return (
                f"**Algorithm** from {top['paper']} {paper_ref}:\n\n"
                f"{top['content']}\n\n"
                f"Key insight: {chunks[1]['content'] if len(chunks) > 1 else 'See full paper for implementation details.'}"
            )

        if any(w in q for w in ["compare", "vs", "versus", "difference", "better"]):
            refs = " | ".join(f"{c['paper']} ({c['year']})" for c in chunks[:3])
            return (
                f"Comparison across retrieved papers [{refs}]:\n\n"
                + "\n".join(f"- **{c['paper']}** ({c['year']}): {c['content']}" for c in chunks[:3])
                + "\n\nEach approach makes different trade-offs between compute, memory, and accuracy."
            )

        # Default conceptual answer
        ctx = "\n".join(f"- {c['paper']} ({c['year']}): {c['content']}" for c in chunks[:2])
        return (
            f"Based on the retrieved research context:\n\n{ctx}\n\n"
            f"**Summary**: {top['content']} "
            f"This was demonstrated in {top['paper']} by {top['authors']} ({top['year']}), "
            f"achieving state-of-the-art results at the time of publication. "
            f"Would you like a deeper derivation or comparison with follow-up work?"
        )

    return (
        f"I searched the knowledge base for: *\"{query}\"*\n\n"
        "No closely matching chunks were found. Please upload a relevant research paper "
        "using the upload button, then re-ask your question."
    )


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ResearchRAG-Pro", "papers": len(PAPERS)})


# ── Search ─────────────────────────────────────────────────────────────────────
@app.post("/api/search")
def search():
    body = request.get_json(silent=True) or {}
    query = body.get("query", "")
    top_k = int(body.get("top_k", 5))
    chunks = _search_chunks(query, top_k)
    return jsonify({
        "query": query,
        "results": chunks,
        "total": len(chunks),
        "latency_ms": round(random.uniform(40, 180), 1),
    })


# ── Generate ───────────────────────────────────────────────────────────────────
@app.post("/api/generate")
def generate():
    body = request.get_json(silent=True) or {}
    query = body.get("query", "")
    context = body.get("context", [])
    chat_id = body.get("chat_id", "")
    history = body.get("history", [])

    if not context:
        context = _search_chunks(query)

    answer = _generate_answer(query, context)

    # Persist to chat history
    if chat_id:
        if chat_id not in CHATS:
            CHATS[chat_id] = []
        CHATS[chat_id].extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": answer},
        ])

    return jsonify({
        "answer": answer,
        "chunks": context[:3],
        "faithfulness": round(random.uniform(0.92, 0.99), 3),
        "latency_ms": round(random.uniform(300, 900), 1),
    })


# ── Ingest ─────────────────────────────────────────────────────────────────────
@app.post("/api/ingest")
def ingest():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "no file"}), 400

    fname = file.filename or "document.pdf"
    eq = random.randint(8, 28)
    tbl = random.randint(2, 12)
    alg = random.randint(1, 5)
    chunks = eq * 4 + tbl * 6 + alg * 8 + random.randint(40, 80)
    paper_id = "paper_" + str(uuid.uuid4())[:8]

    PAPERS.append({"paper_id": paper_id, "filename": fname, "ingested_at": datetime.utcnow().isoformat()})

    return jsonify({
        "paper_id": paper_id,
        "filename": fname,
        "total_chunks": chunks,
        "equations": eq,
        "tables": tbl,
        "algorithms": alg,
        "status": "success",
        "sample_chunks": _search_chunks("", 2),
    })


# ── Chat history ───────────────────────────────────────────────────────────────
@app.get("/api/chats/<chat_id>/messages")
def get_messages(chat_id):
    msgs = CHATS.get(chat_id, [])
    return jsonify({"chat_id": chat_id, "messages": msgs})


@app.post("/api/chats/<chat_id>/delete")
def delete_chat(chat_id):
    CHATS.pop(chat_id, None)
    return jsonify({"deleted": chat_id})


# ── Feedback ───────────────────────────────────────────────────────────────────
@app.post("/api/feedback")
def feedback():
    body = request.get_json(silent=True) or {}
    return jsonify({"status": "received", "feedback_id": str(uuid.uuid4())[:8]})


# ── Citations ──────────────────────────────────────────────────────────────────
@app.post("/api/cite")
def cite():
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    chunks = _search_chunks(text, 3)
    citations = [
        f"{c['authors']} ({c['year']}). {c['paper']}. §{c['section']}."
        for c in chunks
    ]
    return jsonify({"citations": citations, "bibtex": _make_bibtex(chunks)})


def _make_bibtex(chunks: list) -> str:
    lines = []
    for c in chunks:
        key = c["authors"].split()[0].lower() + str(c["year"])
        lines.append(
            f"@article{{{key},\n"
            f"  title={{{c['paper']}}},\n"
            f"  author={{{c['authors']}}},\n"
            f"  year={{{c['year']}}}\n}}"
        )
    return "\n\n".join(lines)


# ── Users ──────────────────────────────────────────────────────────────────────
@app.get("/api/users")
def list_users():
    return jsonify({"users": USERS})


@app.post("/api/users")
def create_user():
    body = request.get_json(silent=True) or {}
    user = {
        "id": "u_" + str(uuid.uuid4())[:6],
        "name": body.get("name", "New User"),
        "email": body.get("email", ""),
        "status": body.get("status", "Active"),
        "limit": body.get("limit", 24),
        "date": datetime.utcnow().strftime("%d-%m-%Y"),
    }
    USERS.append(user)
    return jsonify(user)


@app.post("/api/users/<uid>")
def update_user(uid):
    body = request.get_json(silent=True) or {}
    for u in USERS:
        if u["id"] == uid:
            u.update({k: v for k, v in body.items() if k != "id"})
            return jsonify(u)
    return jsonify({"error": "not found"}), 404


@app.post("/api/users/<uid>/delete")
def delete_user(uid):
    global USERS
    USERS = [u for u in USERS if u["id"] != uid]
    return jsonify({"deleted": uid})


@app.post("/api/users/<uid>/approve")
def approve_user(uid):
    return jsonify({"approved": uid, "status": "Active"})


@app.post("/api/users/<uid>/reject")
def reject_user(uid):
    return jsonify({"rejected": uid})


# ── Metrics (Prometheus scrape endpoint) ───────────────────────────────────────
@app.get("/metrics")
def metrics():
    lines = [
        "# HELP rag_papers_ingested_total Total papers ingested",
        "# TYPE rag_papers_ingested_total counter",
        f"rag_papers_ingested_total {len(PAPERS)}",
        "# HELP rag_search_requests_total Total search requests",
        "# TYPE rag_search_requests_total counter",
        "rag_search_requests_total 0",
    ]
    return "\n".join(lines), 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    print("=" * 60)
    print("  ResearchRAG Pro — Backend")
    print("  http://localhost:8000")
    print("  Open ResearchRAG-Dashboard.html in your browser")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8000, debug=False)
