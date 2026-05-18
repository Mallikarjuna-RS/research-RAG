---
name: math-aware-retrieval
description: >
  Retrieve research content with mathematical semantic awareness. Handles conceptual
  queries, formula-specific searches, and cross-modal reasoning across equations,
  tables, and algorithms. Always use this before answering any research question —
  never answer from memory alone. Use when users ask about equations, proofs,
  algorithms, tables, or any research content from ingested papers.

  TRIGGERS ON: "find equation", "search formula", "compare algorithms",
  "what does this mean", "derive", "proof", "theorem", "solve",
  "explain table", "algorithm complexity", "related work", "find papers",
  "show me", "what is", "how does", "why does", "which papers"

  DO NOT use for: simple factual lookup without corpus, non-math topics,
  creative writing, code generation outside research context.

allowed-tools:
  - mcp:vector-db
  - mcp:knowledge-graph
  - mcp:math-renderer
  - mcp:evaluator
  - Read
---

# Math-Aware Retrieval Protocol v2.1

## STEP 0: QUERY CLASSIFICATION

Auto-detect query type before choosing retrieval strategy:

| Type | Signals | Example |
|------|---------|---------|
| `CONCEPTUAL` | Abstract terms, "what is", "explain" | "What is attention in transformers?" |
| `FORMULA_SPECIFIC` | LaTeX ($, \\), math symbols, equation numbers | "Find papers using $E=mc^2$" |
| `DERIVATION` | "derive", "prove", "show that", "step by step" | "Derive the Navier-Stokes equations" |
| `COMPARISON` | "compare", "vs", "difference between", "better" | "Compare Dijkstra vs A* complexity" |
| `MULTI_MODAL` | Cross-references between types | "What table supports Equation 3.2 in Smith 2023?" |

Store classification in `query_type` for downstream routing.

## LAYER 1: Query Embedding

**IF `FORMULA_SPECIFIC` or `DERIVATION`:**
```
1. Extract LaTeX fragments from query (detect $...$ and \[...\] patterns)
2. Generate semantic variants:
   - "$E=mc^2$" → ["energy mass equivalence", "mass energy relation", "Einstein equation"]
3. Embed with math-aware embedder (384d) for LaTeX fragments
4. Embed full query with text-embedding-3-large (1536d) for context
5. Use BOTH embeddings in parallel retrieval
```

**IF `CONCEPTUAL` or `COMPARISON`:**
```
1. Expand query with domain synonyms:
   - "attention" → ["self-attention", "cross-attention", "scaled dot-product attention"]
2. Generate 3 semantic query variants
3. Embed with text-embedding-3-large (1536d)
4. Use ensemble embedding (average of variants)
```

**IF `MULTI_MODAL`:**
```
1. Parse entity references: paper name, equation numbers, table numbers
2. Create targeted sub-queries for each entity
3. Embed each sub-query separately
4. Merge results post-retrieval
```

## LAYER 2: Hybrid Search

Call: `mcp:vector-db.hybrid_search(query, filters, top_k=50)`

**Search configuration by query type:**

| Query Type | Dense Weight | Sparse Weight | Chunk Type Filter |
|------------|-------------|---------------|-------------------|
| `CONCEPTUAL` | 0.7 | 0.3 | all |
| `FORMULA_SPECIFIC` | 0.5 | 0.5 | equation preferred |
| `DERIVATION` | 0.6 | 0.4 | equation + text |
| `COMPARISON` | 0.6 | 0.4 | algorithm + table |
| `MULTI_MODAL` | 0.7 | 0.3 | all (KG-guided) |

**Available filters to apply:**
```json
{
  "type": "equation|table|algorithm|text",
  "paper_id": "specific_paper_uuid",
  "section": "3.*",
  "confidence": 0.8,
  "date_range": {"start": "2020", "end": "2024"}
}
```

Retrieve `top_k=50` candidates for reranking.

## LAYER 3: Cross-Modal Expansion

For each of the top 20 results, expand via knowledge graph:

**IF result.type == "equation":**
```
CALL mcp:knowledge-graph.get_related_chunks(chunk_id, depth=2)
→ Fetch:
  - Surrounding text paragraphs (±2 from same section)
  - Tables referenced by this equation ("Table 3 shows...")
  - Algorithms that USE this equation
  - Other equations CITED by this equation
```

**IF result.type == "table":**
```
→ Fetch:
  - Equations that REFERENCE this table
  - Surrounding analysis text (±2 paragraphs)
  - Caption and footnotes
```

**IF result.type == "algorithm":**
```
→ Fetch:
  - Complexity equations (time/space)
  - Variable definition text
  - Related algorithms in same paper
  - Referenced equations in pseudocode
```

**IF result.type == "text":**
```
→ Fetch:
  - Any equations cited inline
  - Any tables mentioned
  - Related text chunks (same section)
```

**Deduplication**: `EXPANDED_CONTEXT = original_chunks ∪ related_chunks` (by chunk_id)

## LAYER 4: Reranking

Use cross-encoder (ms-marco-MiniLM-L-6-v2 fine-tuned on academic QA):

```
FOR each chunk in EXPANDED_CONTEXT:
  score = cross_encoder.predict([query, chunk.content])  # 0.0–1.0
  
SORT by rerank_score DESC
KEEP top_k=10
```

**Special handling for math queries:**
- Boost equation chunks that share variable names with query: +0.1
- Boost chunks from highly-cited papers: +0.05
- Penalize low-confidence chunks (< 0.7): -0.15

## CONTEXT ASSEMBLY FOR GENERATION

Format the top 10 results as structured blocks for the generation step:

```markdown
## Retrieved Context ({total} chunks from {n_papers} papers)

---

### [1] Text Passage — {paper_title} ({year})
**Section {section} | Page {page} | Confidence: {confidence:.2f} | Score: {score:.3f}**

{text_content}

**Keywords:** {keywords}
**Cross-references:** {cross_refs}

---

### [2] Equation ({eq_number}) — {paper_title} ({year})
**Section {section} | Page {page}**

$$
{latex_content}
$$

**Variables:** {variable_definitions}
**Defined in:** Section {section}
**Used in algorithms:** {algorithm_names}
**Referenced by:** {referencing_chunks}

---

### [3] Table {table_number} — {paper_title} ({year})
**Caption:** {caption}

{markdown_table}

**Column Statistics:** {col_stats}
**Referenced by equations:** {eq_refs}

---

### [4] Algorithm {alg_number} — {paper_title} ({year})
**Input:** {inputs}
**Output:** {outputs}
**Complexity:** Time {time_complexity}, Space {space_complexity}

```pseudocode
{pseudocode}
```

---
```

## FAITHFULNESS GUARDRAILS

Before returning context to generation, verify:

1. ✅ Every text chunk has `paper_id`, `section`, `page` filled
2. ✅ Every equation has valid `latex` (already validated during ingestion)
3. ✅ Every table has readable `markdown` 
4. ✅ Every algorithm has `complexity` populated
5. ✅ No duplicate chunk_ids in final context
6. ✅ Total context ≤ 100,000 tokens (trim lower-scored chunks if needed)

**IF context is insufficient** (total_chunks < 3 OR max_score < 0.5):
```
State explicitly in response:
"The retrieved context does not contain sufficient information about [X].
 Available information covers: [list what was found].
 Consider: [suggestion to add more papers / rephrase query]"
```

## OUTPUT FORMAT

Return structured object for the generation orchestrator:

```json
{
  "query": "original query",
  "query_type": "FORMULA_SPECIFIC",
  "total_chunks": 10,
  "num_papers": 3,
  "max_score": 0.94,
  "context_blocks": [...],
  "retrieval_stats": {
    "dense_candidates": 50,
    "after_kg_expansion": 78,
    "after_reranking": 10,
    "latency_ms": 342
  }
}
```
