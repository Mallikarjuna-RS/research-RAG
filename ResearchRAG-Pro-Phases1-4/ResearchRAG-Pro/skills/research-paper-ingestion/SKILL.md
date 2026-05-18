---
name: research-paper-ingestion
description: >
  Ingest research papers into the vector database with full multimodal extraction.
  Handles PDFs, Word docs, and LaTeX sources. Preserves mathematical equations,
  tables, algorithms, and cross-references. Use this skill whenever the user wants
  to add papers to the corpus, process documents, or build the research knowledge base.

  TRIGGERS ON: "ingest paper", "add PDF", "process research article",
  "extract equations", "build corpus", "index paper", "parse document",
  "upload research", "process arxiv", "batch ingest", "add paper",
  "load document", "index this paper", "add to database"

  DO NOT use for: general text files, non-academic documents,
  simple Q&A without ingestion.

allowed-tools:
  - Read
  - Bash
  - mcp:doc-parser
  - mcp:vector-db
  - mcp:knowledge-graph
  - mcp:math-renderer
  - mcp:evaluator
---

# Research Paper Ingestion Protocol v2.1

## PRE-INGESTION CHECKLIST

Before processing any paper, verify:

1. **Format check**: Is file PDF, DOCX, or TEX?
   - If unsupported → tell user: "Supported formats: PDF, DOCX, .tex (LaTeX source)"
2. **Size check**: Is file < 100MB?
   - If larger → split by sections using `Bash: split_pdf.py --input FILE --max-size 100MB`
3. **Duplicate check**: Already ingested? Check via:
   ```
   mcp:vector-db.hybrid_search(query=TITLE, filters={confidence: >0.99}, top_k=1)
   ```
   - If found → confirm with user: "This paper may already exist. Overwrite? (yes/no)"
4. **Quota check**: `mcp:vector-db.get_stats()` — confirm space available

## INGESTION PIPELINE (5 Stages)

### STAGE 1: Document Parsing

Call: `mcp:doc-parser.parse_pdf(pdf_path, paper_id=UUID)`

Returns `chunks[]` array. For each chunk:

**IF type == "equation":**
```
CALL mcp:math-renderer.validate_latex(chunk.latex)
  IF invalid:
    → Log to errors[], flag for manual review
    → Skip embedding for this chunk
    → Continue to next chunk
  ELSE:
    → Normalize: remove unnecessary braces, standardize \frac vs \dfrac
    → chunk.latex = normalized_latex
```

**IF type == "table":**
```
→ chunk.markdown = to_markdown(rows, alignment=True)
→ chunk.metadata.col_stats = {min, max, mean} for numeric columns
→ chunk.metadata.description = generate_nl_description(headers, sample_rows)
```

**IF type == "algorithm":**
```
→ Extract: name, inputs, outputs from header line
→ Link equations: scan pseudocode for equation references (e.g., "using Eq. 3")
→ chunk.metadata.referenced_equations = [eq_ids]
→ chunk.metadata.complexity = extract_complexity_notation(text)
```

**IF type == "text":**
```
→ Extract keywords (TF-IDF top 10)
→ Detect cross-references: "see Table 3", "Equation (2.1)", "Algorithm 2"
→ chunk.metadata.cross_refs = [detected_refs]
```

### STAGE 2: Content Enrichment

For each chunk, generate:
- **Surrounding context**: ±500 chars for text chunks, ±2 paragraphs for equations
- **Keyword extraction**: TF-IDF top 10 domain-specific terms
- **Cross-reference links**: Map "see Table 3" → table_chunk_id
- **Confidence score**: 0.0–1.0 based on extraction quality
  - High (0.9–1.0): clean parse, validated LaTeX, clear table structure
  - Medium (0.7–0.9): minor issues, low-confidence OCR regions
  - Low (0.0–0.7): flag for manual review

### STAGE 3: Embedding Generation

**Batch processing in parallel (batch_size=32):**

| Chunk Type | Embedder | Dimension | Input Construction |
|------------|----------|-----------|-------------------|
| `text` | text-embedding-3-large | 1536d | `{title} \n {section_heading} \n {content}` |
| `equation` | math-aware-embedder | 384d | `{normalized_latex} \n Variables: {var_definitions}` |
| `table` | text-embedding-3-large | 1536d | `{caption} \n {col_names} \n {sample_rows[:3]}` |
| `algorithm` | text-embedding-3-large | 1536d | `{name} \n {description} \n {pseudocode}` |

**Math embedding strategy (for equations):**
1. LaTeX AST features (256d): operator frequency, variable usage, nesting depth
2. Semantic description (384d): NL description via `_latex_to_description(latex)`
3. Symbolic features (128d): variable dependency graph encoding
4. Project to 384d via learned projection

**Normalization**: All vectors L2-normalized to unit sphere before insertion.

### STAGE 4: Vector Storage

Call: `mcp:vector-db.insert_chunks(chunks_with_embeddings)`

Each chunk payload:
```json
{
  "chunk_id": "uuid",
  "paper_id": "uuid",
  "type": "text|equation|table|algorithm",
  "section": "3.2",
  "page": 5,
  "text_embedding": [1536 floats],
  "math_embedding": [384 floats, null if not equation],
  "sparse_vector": {"token": weight, ...},
  "content": "raw content string",
  "latex": "normalized LaTeX or null",
  "markdown": "markdown table or null",
  "metadata": {
    "confidence": 0.95,
    "keywords": ["attention", "transformer"],
    "cross_refs": ["table_001", "eq_003"],
    "equation_number": "3.2",
    "caption": "Table caption text",
    "complexity": "O(n log n)"
  }
}
```

### STAGE 5: Knowledge Graph Construction

Call: `mcp:knowledge-graph.build_graph(paper_id, chunks)`

Creates the following graph structure:
```cypher
// Nodes
CREATE (p:Paper {id: paper_id, title: title, year: year, venue: venue})
CREATE (s:Section {id: section_id, number: "3.2", heading: heading})
CREATE (c:Chunk {id: chunk_id, type: type, page: page})

// Core hierarchy
(p)-[:HAS_SECTION]->(s)
(s)-[:CONTAINS]->(c)

// Cross-type relationships
(eq:Equation)-[:DEFINED_IN]->(s)
(tbl:Table)-[:REFERENCED_BY]->(eq:Equation)    // when text says "Table 3 shows..."
(alg:Algorithm)-[:USES]->(eq:Equation)          // when algorithm references equations
(c1:Chunk)-[:CITES]->(c2:Chunk)                 // for detected cross-references
```

## POST-INGESTION VALIDATION

After pipeline completes:

1. **Retrieval spot-check**: Sample 5 random chunks, verify they're retrievable
2. **Equation render check**: Randomly select 10 equations → `mcp:math-renderer.validate_latex()`
3. **Table structure check**: Randomly select 5 tables → verify markdown is valid
4. **Run benchmark**: `mcp:evaluator.run_benchmark("ingestion_test_suite")`
5. **Log metrics**: Report to user:
   ```
   ✅ Ingestion Complete — {paper_title}
   
   Stats:
   • Chunks processed: {n}
   • Equations found: {n} ({valid_pct}% valid LaTeX)
   • Tables found: {n}
   • Algorithms found: {n}
   • Errors/skipped: {n}
   • Avg embedding time: {ms}ms per chunk
   • Total time: {sec}s
   • Knowledge graph: {nodes} nodes, {edges} edges
   ```

## ERROR HANDLING

| Error | Action |
|-------|--------|
| Parse failure | Retry: Docling → MinerU → Grobid (fallback chain) |
| Invalid LaTeX | Queue for manual review; render preview; log chunk_id |
| Embedding timeout | Add to async queue, return `job_id` for status polling |
| Duplicate detected | Merge metadata; update embeddings only if content changed |
| File too large | Split by section automatically, ingest as linked chunks |
| Neo4j unavailable | Continue ingestion; queue graph build for retry |

## BATCH INGESTION (Multiple Papers)

For bulk ingestion:
```bash
# Usage: ingest a directory of PDFs
for pdf_file in /data/papers/*.pdf:
  IF already_ingested(pdf_file):
    SKIP with log
  ELSE:
    RUN ingestion_pipeline(pdf_file)
    WAIT for completion
    LOG status

# Progress format:
[1/50] ✅ attention_is_all_you_need.pdf — 142 chunks, 23 eq, 8 tables
[2/50] ✅ bert_paper.pdf — 98 chunks, 15 eq, 12 tables
[3/50] ❌ corrupted_paper.pdf — Parse failed, skipped
```
