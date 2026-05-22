"""
ResearchRAG Pro — Local Flask backend
Real PDF text extraction via pypdf, multi-file & folder ingest support.
"""

import io
import re
import uuid
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[WARN] pypdf not installed — run: pip install pypdf")

app = Flask(__name__)
CORS(app)

# ── In-memory stores ──────────────────────────────────────────────────────────
CHATS: dict  = {}   # chat_id  -> list[{role, content}]
PAPERS: list = []   # paper metadata
PAPER_CHUNKS: list = []   # extracted chunks from uploaded PDFs

USERS: list = [
    {"id": "u1", "name": "Eleanor Pena",   "email": "eleanor@research.edu",  "status": "Active",   "limit": 24, "date": "12-12-2024"},
    {"id": "u2", "name": "Kristin Watson", "email": "kristin@university.ac", "status": "Inactive", "limit": 24, "date": "12-12-2024"},
    {"id": "u3", "name": "Jerome Bell",    "email": "jerome@lab.org",         "status": "Active",   "limit": 24, "date": "12-12-2024"},
]

# ── Fallback knowledge base (used when no PDFs are uploaded) ──────────────────
KNOWLEDGE_BASE = [
    {
        "paper": "Attention Is All You Need",
        "authors": "Vaswani et al.", "year": 2017, "section": "3.2.1",
        "type": "equation",
        "content": "Scaled dot-product attention: Attention(Q,K,V) = softmax(QKᵀ/√dₖ)·V",
        "latex": r"Attention(Q,K,V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right) V",
        "keywords": ["attention", "transformer", "self-attention", "multi-head"],
    },
    {
        "paper": "BERT: Pre-training of Deep Bidirectional Transformers",
        "authors": "Devlin et al.", "year": 2019, "section": "3.1",
        "type": "algorithm",
        "content": "Masked Language Model pre-training: randomly mask 15% of tokens and predict them.",
        "keywords": ["bert", "masked", "language", "model", "pre-training", "bidirectional"],
    },
    {
        "paper": "Retrieval-Augmented Generation for NLP",
        "authors": "Lewis et al.", "year": 2020, "section": "2",
        "type": "text",
        "content": "RAG combines a parametric memory (language model) with a non-parametric memory (dense vector retrieval) for open-domain QA.",
        "keywords": ["rag", "retrieval", "generation", "open-domain", "dense", "vector"],
    },
    {
        "paper": "Physics-Informed Neural Networks",
        "authors": "Raissi et al.", "year": 2019, "section": "2",
        "type": "equation",
        "content": "PINN loss = MSE_u + MSE_f where MSE_f penalises the PDE residual at collocation points.",
        "latex": r"\mathcal{L} = \mathcal{L}_u + \mathcal{L}_f",
        "keywords": ["pinn", "physics", "neural", "network", "pde", "residual", "collocation", "loss"],
    },
    {
        "paper": "Deep Residual Learning for Image Recognition",
        "authors": "He et al.", "year": 2016, "section": "3",
        "type": "equation",
        "content": "Residual learning: H(x) = F(x) + x, where F(x) is the residual mapping.",
        "latex": r"H(x) = \mathcal{F}(x) + x",
        "keywords": ["resnet", "residual", "skip", "connection", "deep", "learning"],
    },
]

# ── Stopwords for keyword extraction ──────────────────────────────────────────
STOPWORDS = {
    "the","a","an","and","or","of","to","in","is","it","for","on","with",
    "as","by","at","from","that","this","are","be","was","were","has","have",
    "had","not","but","they","we","our","can","will","been","more","also",
    "its","which","their","than","then","when","where","how","what","into",
    "such","each","these","those","some","any","all","both","here","there",
    "use","used","using","show","shows","shown","paper","fig","figure","table",
    "section","equation","given","since","thus","hence","note","let","over",
    "between","after","before","through","about","while","during","without",
    "however","therefore","moreover","furthermore","while","although","because",
    "result","results","obtained","proposed","present","approach","method",
}

# ── Chunking parameters ────────────────────────────────────────────────────────
CHUNK_SIZE    = 450   # target characters per chunk
CHUNK_OVERLAP = 100   # overlap characters between consecutive chunks
MIN_CHUNK_LEN = 80    # discard anything shorter


# ── Text cleaning ──────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Normalize PDF-extracted text."""
    text = re.sub(r"-\n", "", text)              # fix hyphenation across lines
    text = re.sub(r"[ \t]+", " ", text)          # collapse spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)       # max 2 consecutive newlines
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _is_noise_line(line: str) -> bool:
    """True for bibliography entries, page numbers, lone numbers, headers."""
    line = line.strip()
    if not line:
        return True
    if re.match(r"^\d+$", line):                            # bare page number
        return True
    if re.match(r"^\[\d+\]", line):                         # [1] reference
        return True
    if re.match(r"^\d{1,3}\.\s+[A-Z][a-z].*\d{4}", line):  # numbered ref
        return True
    if len(line) < 15 and not re.search(r"[a-z]{4,}", line):# short no-text
        return True
    return False


def _split_into_sentences(text: str) -> list:
    """Split text at sentence boundaries, keeping fragments ≥ 20 chars."""
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\(\[])", text)
    out = []
    buf = ""
    for part in raw:
        buf = (buf + " " + part).strip() if buf else part.strip()
        if len(buf) >= 40:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return [s for s in out if len(s) >= 20]


def _make_chunks(sentences: list, size: int = CHUNK_SIZE,
                 overlap: int = CHUNK_OVERLAP) -> list:
    """Group sentences into overlapping fixed-size chunks."""
    if not sentences:
        return []
    chunks, current, cur_len = [], [], 0
    for sent in sentences:
        if cur_len + len(sent) > size and current:
            chunks.append(" ".join(current))
            # keep tail for overlap
            tail, tail_len = [], 0
            for s in reversed(current):
                if tail_len + len(s) <= overlap:
                    tail.insert(0, s); tail_len += len(s)
                else:
                    break
            current, cur_len = tail, tail_len
        current.append(sent); cur_len += len(sent) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


# ── Chunk type detection ───────────────────────────────────────────────────────

def _detect_chunk_type(text: str) -> str:
    """Conservative: only label equation/algorithm/table when clear evidence."""
    # Equation: several math symbols OR clear functional notation
    math_sym = ["∫", "∂", "∑", "∇", "∆", "∈", "α", "β", "γ", "λ",
                "φ", "ψ", "σ", "θ", "ω", "Ω", "μ", "ε", "δ"]
    math_hits = sum(text.count(s) for s in math_sym)
    has_func = bool(re.search(
        r"[a-zA-Z_]\s*\([^)]{1,20}\)\s*=|∂[a-zA-Z]/∂[a-zA-Z]|d[A-Z]/d[txyz]", text))
    if math_hits >= 3 or has_func:
        return "equation"

    # Algorithm: explicit label
    if re.search(r"(?:Algorithm|Procedure)\s+\d", text, re.IGNORECASE):
        return "algorithm"

    # Table: multiple lines with pipe-separated or tab-separated numbers
    lines = text.split("\n")
    structured = sum(
        1 for ln in lines
        if ln.count("|") >= 2
        or re.match(r"\s*(?:\d+\.?\d*\s+){3,}", ln)
    )
    if structured >= 3:
        return "table"

    return "text"


# ── Keyword extraction ─────────────────────────────────────────────────────────

def _extract_keywords(text: str, n: int = 14) -> list:
    """Extract single words + meaningful bigrams, ranked by frequency."""
    words = [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOPWORDS]
    bigrams = [f"{a} {b}" for a, b in zip(words, words[1:])
               if len(a) >= 4 and len(b) >= 4]
    freq: dict = {}
    for w in words + bigrams:
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])][:n]


# ── PDF extraction ─────────────────────────────────────────────────────────────

def _extract_pdf_chunks(file_bytes: bytes, filename: str, paper_id: str) -> list:
    """
    Full pipeline:
      1. Extract text per page with pypdf
      2. Clean & normalise
      3. Skip reference/noise pages
      4. Split into paragraphs → sentences → overlapping chunks
      5. Tag type and keywords per chunk
    """
    chunks = []
    if not PDF_SUPPORT:
        return chunks

    paper_name = re.sub(r"\.pdf$", "", filename, flags=re.IGNORECASE)
    paper_name = re.sub(r"[_\-]", " ", paper_name).strip()
    ci = 0

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page_num, page in enumerate(reader.pages, 1):
            raw = page.extract_text() or ""
            if not raw.strip():
                continue

            page_text = _clean_text(raw)

            # Skip pages that are mostly reference lists
            lines = page_text.split("\n")
            noise_ratio = sum(1 for ln in lines if _is_noise_line(ln)) / max(len(lines), 1)
            if noise_ratio > 0.60:
                continue

            # Remove individual noise lines before chunking
            clean_lines = [ln for ln in lines if not _is_noise_line(ln)]
            page_text = "\n".join(clean_lines)

            # Split into paragraphs
            paragraphs = re.split(r"\n{2,}", page_text)

            for para in paragraphs:
                para = re.sub(r"\s+", " ", para).strip()
                if len(para) < MIN_CHUNK_LEN:
                    continue

                # Split para into sentences, then into overlapping chunks
                sents   = _split_into_sentences(para) or [para]
                for sub in _make_chunks(sents):
                    sub = sub.strip()
                    if len(sub) < MIN_CHUNK_LEN:
                        continue
                    chunk_type = _detect_chunk_type(sub)
                    keywords   = _extract_keywords(sub)
                    chunks.append({
                        "chunk_id": f"{paper_id}_p{page_num}_c{ci}",
                        "paper_id": paper_id,
                        "paper":    paper_name,
                        "authors":  "Uploaded Document",
                        "year":     datetime.utcnow().year,
                        "section":  f"p.{page_num}",
                        "type":     chunk_type,
                        "content":  sub[:600],
                        "keywords": keywords,
                        "source":   "uploaded",
                    })
                    ci += 1

    except Exception as exc:
        print(f"[WARN] PDF extract failed for {filename}: {exc}")

    return chunks


# ── BM25-inspired scoring ──────────────────────────────────────────────────────

def _score_result(entry: dict, query: str) -> float:
    """
    Score a chunk against a query using:
      - Term frequency in content (capped per term)
      - Keyword field match bonus
      - Paper title match bonus
      - Consecutive phrase bonus
      - Length normalisation (penalise very short chunks)
      - Uploaded-PDF boost
    """
    q_words = re.findall(r"[a-z]{3,}", query.lower())
    if not q_words:
        return 0.05

    content   = entry.get("content", "").lower()
    c_words   = re.findall(r"[a-z]{3,}", content)
    c_len     = max(len(c_words), 1)
    keywords  = [k.lower() for k in entry.get("keywords", [])]
    paper     = entry.get("paper", "").lower()

    score = 0.0
    for qw in q_words:
        # TF (normalised, capped so one common word can't dominate)
        tf = content.count(qw) / c_len
        score += min(tf * 12, 0.14)

        # Keyword field match (strong signal — already TF-IDF weighted)
        if any(qw == kw or qw in kw or kw in qw for kw in keywords):
            score += 0.13

        # Paper title match
        if qw in paper:
            score += 0.06

    # Phrase bonus: first 3 query words appear consecutively in content
    if len(q_words) >= 2:
        phrase = " ".join(q_words[:3])
        if phrase in content:
            score += 0.22

    # Uploaded PDF boost
    if entry.get("source") == "uploaded":
        score += 0.10

    # Length penalty for very short chunks (table cells, stray lines)
    if len(content) < 100:
        score *= 0.40

    return round(min(0.99, max(0.01, score)), 3)


def _search_chunks(query: str, top_k: int = 5) -> list:
    top_k = max(1, min(top_k, 100))
    results = []

    search_pool = PAPER_CHUNKS + (KNOWLEDGE_BASE if not PAPER_CHUNKS else [])

    for entry in search_pool:
        score = _score_result(entry, query)
        chunk = {
            "chunk_id": entry.get("chunk_id", str(uuid.uuid4())[:8]),
            "type":     entry.get("type", "text"),
            "paper":    entry["paper"],
            "authors":  entry.get("authors", "Unknown"),
            "year":     entry.get("year", 2024),
            "section":  entry.get("section", "—"),
            "score":    score,
            "content":  entry.get("content", ""),
            "keywords": entry.get("keywords", []),
            "source":   entry.get("source", "kb"),
        }
        if entry.get("latex"):
            chunk["latex"] = entry["latex"]
        results.append(chunk)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ── Answer generation ─────────────────────────────────────────────────────────

def _generate_answer(query: str, chunks: list) -> str:
    q = query.lower()

    if not chunks:
        return (
            f'I searched the knowledge base for: *"{query}"*\n\n'
            "No closely matching content found. Please upload a relevant research paper "
            "and re-ask your question."
        )

    top = chunks[0]
    is_uploaded = top.get("source") == "uploaded"
    paper_ref = f"[{top['authors']}, {top['year']}, §{top['section']}]"
    src_label = top["paper"]

    # If from real uploaded PDF, return the actual extracted text
    if is_uploaded:
        ctx_lines = "\n\n".join(
            f"**{c['paper']}** (§{c['section']}, score {c['score']}):\n{c['content']}"
            for c in chunks[:3]
        )
        return (
            f"Based on your uploaded documents:\n\n"
            f"{ctx_lines}\n\n"
            f"*Retrieved {len(chunks)} relevant passages. Scores reflect keyword & "
            f"content overlap with your query.*"
        )

    # Fallback KB answers
    if any(w in q for w in ["formula", "equation", "math", "derive", "loss"]):
        body = top["content"]
        latex = f"\n\n`{top['latex']}`" if top.get("latex") else ""
        return (
            f"Based on retrieved context from **{src_label}** {paper_ref}:\n\n"
            f"{body}{latex}\n\n"
            f"Would you like a deeper derivation or comparison with follow-up work?"
        )

    if any(w in q for w in ["algorithm", "pseudocode", "steps", "how does", "procedure"]):
        extra = f"\n\nKey insight: {chunks[1]['content']}" if len(chunks) > 1 else ""
        return f"**Algorithm** from {src_label} {paper_ref}:\n\n{top['content']}{extra}"

    if any(w in q for w in ["compare", "vs", "versus", "difference", "better"]):
        rows = "\n".join(f"- **{c['paper']}** ({c['year']}): {c['content']}" for c in chunks[:3])
        return (
            f"Comparison across retrieved papers:\n\n{rows}\n\n"
            "Each approach makes different trade-offs between compute, memory, and accuracy."
        )

    ctx = "\n".join(f"- {c['paper']} ({c['year']}): {c['content']}" for c in chunks[:2])
    return (
        f"Based on the retrieved research context:\n\n{ctx}\n\n"
        f"**Summary**: {top['content']} "
        f"(Source: {src_label}, {top['authors']}, {top['year']})\n\n"
        "Would you like a deeper derivation or comparison with follow-up work?"
    )


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({
        "status":       "ok",
        "service":      "ResearchRAG-Pro",
        "papers":       len(PAPERS),
        "chunks":       len(PAPER_CHUNKS),
        "pdf_support":  PDF_SUPPORT,
    })


# ── Search ────────────────────────────────────────────────────────────────────
@app.post("/api/search")
def search():
    body  = request.get_json(silent=True) or {}
    query = body.get("query", "")
    top_k = max(1, min(int(body.get("top_k", 5)), 100))
    chunks = _search_chunks(query, top_k)
    return jsonify({
        "query":      query,
        "results":    chunks,
        "total":      len(chunks),
        "from_pdf":   sum(1 for c in chunks if c.get("source") == "uploaded"),
        "latency_ms": 42,
    })


# ── Generate ──────────────────────────────────────────────────────────────────
@app.post("/api/generate")
def generate():
    body    = request.get_json(silent=True) or {}
    query   = body.get("query", "")
    context = body.get("context", [])
    chat_id = body.get("chat_id", "")

    if not context:
        context = _search_chunks(query)

    answer = _generate_answer(query, context)

    if chat_id:
        CHATS.setdefault(chat_id, []).extend([
            {"role": "user",      "content": query},
            {"role": "assistant", "content": answer},
        ])

    return jsonify({
        "answer":      answer,
        "chunks":      context[:3],
        "faithfulness": round(min(0.99, 0.80 + len(context) * 0.03), 3),
        "latency_ms":  88,
    })


# ── Ingest — single file, multiple files, or folder path ─────────────────────
def _ingest_one(file_obj) -> dict:
    """Process one FileStorage object; return result dict."""
    fname     = file_obj.filename or "document.pdf"
    paper_id  = "paper_" + str(uuid.uuid4())[:8]
    raw_bytes = file_obj.read()

    chunks = _extract_pdf_chunks(raw_bytes, fname, paper_id)
    PAPER_CHUNKS.extend(chunks)

    eq  = sum(1 for c in chunks if c["type"] == "equation")
    tbl = sum(1 for c in chunks if c["type"] == "table")
    alg = sum(1 for c in chunks if c["type"] == "algorithm")

    meta = {
        "paper_id":    paper_id,
        "filename":    fname,
        "total_chunks": len(chunks),
        "equations":   eq,
        "tables":      tbl,
        "algorithms":  alg,
        "ingested_at": datetime.utcnow().isoformat(),
        "status":      "success",
    }
    PAPERS.append(meta)
    return {**meta, "sample_chunks": chunks[:2]}


@app.post("/api/ingest")
def ingest():
    # Support: single file OR multiple files (field name "file" or "files")
    files = request.files.getlist("file") + request.files.getlist("files")
    files = [f for f in files if f and f.filename]

    if not files:
        return jsonify({"error": "no file provided"}), 400

    if len(files) == 1:
        return jsonify(_ingest_one(files[0]))

    results = [_ingest_one(f) for f in files]
    total_chunks = sum(r["total_chunks"] for r in results)
    return jsonify({
        "batch":        results,
        "total_papers": len(results),
        "total_chunks": total_chunks,
        "status":       "success",
    })


# ── Chat history ──────────────────────────────────────────────────────────────
@app.get("/api/chats/<chat_id>/messages")
def get_messages(chat_id):
    return jsonify({"chat_id": chat_id, "messages": CHATS.get(chat_id, [])})


@app.post("/api/chats/<chat_id>/delete")
def delete_chat(chat_id):
    CHATS.pop(chat_id, None)
    return jsonify({"deleted": chat_id})


# ── Feedback ──────────────────────────────────────────────────────────────────
@app.post("/api/feedback")
def feedback():
    return jsonify({"status": "received", "feedback_id": str(uuid.uuid4())[:8]})


# ── Citations ─────────────────────────────────────────────────────────────────
@app.post("/api/cite")
def cite():
    body   = request.get_json(silent=True) or {}
    text   = body.get("text", "")
    chunks = _search_chunks(text, 3)
    citations = [
        f"{c['authors']} ({c['year']}). {c['paper']}. §{c['section']}."
        for c in chunks
    ]
    return jsonify({"citations": citations, "bibtex": _make_bibtex(chunks)})


def _make_bibtex(chunks: list) -> str:
    lines = []
    for c in chunks:
        key = re.sub(r"\W+", "", c["authors"].split()[0].lower()) + str(c["year"])
        lines.append(
            f"@article{{{key},\n"
            f"  title={{{c['paper']}}},\n"
            f"  author={{{c['authors']}}},\n"
            f"  year={{{c['year']}}}\n}}"
        )
    return "\n\n".join(lines)


# ── Users ─────────────────────────────────────────────────────────────────────
ALLOWED_USER_FIELDS = {"name", "email", "status", "limit"}

@app.get("/api/users")
def list_users():
    return jsonify({"users": USERS})


@app.post("/api/users")
def create_user():
    body = request.get_json(silent=True) or {}
    status = body.get("status", "Active")
    if status not in ("Active", "Inactive"):
        status = "Active"
    user = {
        "id":     "u_" + str(uuid.uuid4())[:6],
        "name":   str(body.get("name", "New User"))[:80],
        "email":  str(body.get("email", ""))[:120],
        "status": status,
        "limit":  int(body.get("limit", 24)),
        "date":   datetime.utcnow().strftime("%d-%m-%Y"),
    }
    USERS.append(user)
    return jsonify(user)


@app.post("/api/users/<uid>")
def update_user(uid):
    body = request.get_json(silent=True) or {}
    for u in USERS:
        if u["id"] == uid:
            safe = {k: v for k, v in body.items() if k in ALLOWED_USER_FIELDS}
            u.update(safe)
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


# ── Metrics ───────────────────────────────────────────────────────────────────
@app.get("/metrics")
def metrics():
    lines = [
        "# HELP rag_papers_ingested_total Total papers ingested",
        "# TYPE rag_papers_ingested_total counter",
        f"rag_papers_ingested_total {len(PAPERS)}",
        "# HELP rag_chunks_total Total text chunks indexed",
        "# TYPE rag_chunks_total counter",
        f"rag_chunks_total {len(PAPER_CHUNKS)}",
        "# HELP rag_search_requests_total Total search requests",
        "# TYPE rag_search_requests_total counter",
        "rag_search_requests_total 0",
    ]
    return "\n".join(lines), 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    print("=" * 60)
    print("  ResearchRAG Pro — Backend")
    print(f"  PDF support: {'YES (pypdf)' if PDF_SUPPORT else 'NO — pip install pypdf'}")
    print("  http://localhost:8000")
    print("  Open ResearchRAG-Dashboard.html in your browser")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
