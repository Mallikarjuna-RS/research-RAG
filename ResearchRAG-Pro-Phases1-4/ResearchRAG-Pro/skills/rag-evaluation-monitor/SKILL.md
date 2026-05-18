---
name: rag-evaluation-monitor
description: >
  Continuous evaluation and monitoring of RAG pipeline performance. Runs automated
  tests, tracks metrics over time, and alerts on quality degradation. Also run
  manually when the user wants to check system health or benchmark performance.
  Automatically triggered after every 100 queries or on a weekly schedule.

  TRIGGERS ON: "evaluate RAG", "run tests", "check quality", "benchmark",
  "monitor performance", "drift detection", "how is the system performing",
  "quality report", "metrics", "accuracy check", "run eval"

  AUTO-RUN: After every 100 queries, or weekly (every Monday 00:00 UTC).

allowed-tools:
  - mcp:evaluator
  - mcp:vector-db
  - mcp:math-renderer
  - Read
  - Bash
  - Write
---

# RAG Evaluation & Monitoring Protocol v2.1

## EVALUATION TRIGGERS

Run evaluation when ANY of the following:
- User explicitly requests it
- Query counter reaches 100 (tracked in `data/query_counter.json`)
- Weekly scheduled run (Monday 00:00 UTC)
- Metric alert threshold breached (immediate re-eval)
- After major changes (new paper batch, model update, config change)

## TEST SUITE DEFINITIONS

### Suite 1: Retrieval Quality Tests

**1a. Math Equivalence Test**
```
Query: "Find papers using mass-energy equivalence"
Expected chunks: contain $E=mc^2$, $E = mc^{2}$, or semantic variants
CALL: mcp:evaluator.evaluate_retrieval(queries, ground_truth)
Target: Recall@10 > 0.80
```

**1b. Table Lookup Test**
```
Query: "What are the experimental results comparing methods?"
Expected chunks: table chunks with numerical results
Target: Precision@5 > 0.90
```

**1c. Algorithm Comparison Test**
```
Query: "Compare time complexity of sorting algorithms"
Expected: Multiple algorithm chunks with complexity notation
Target: MRR > 0.70
```

**1d. Cross-Modal Retrieval Test**
```
Query: "What equation is referenced by Table 2 in the Smith paper?"
Expected: Both the table AND its referencing equation
Target: Cross-modal recall > 0.75
```

**1e. LaTeX Query Test**
```
Query: "$$\\nabla \\times B = \\mu_0 J$$"
Expected: Chunks containing Maxwell's equation or semantic equivalents
Target: Recall@5 > 0.85
```

### Suite 2: Generation Quality Tests

**2a. Faithfulness Test**
```
Generate 50 QA pairs from ingested papers (known answers)
CALL: mcp:evaluator.evaluate_generation(answers, contexts, ground_truth)
Method: Check if answer claims are supported by retrieved context
Target: Faithfulness > 0.95
```

**2b. Citation Accuracy Test**
```
For 30 generated answers:
- Verify each [Author, Year] citation exists in corpus
- Verify cited claim matches source content
- Verify equation numbers are correct
Target: Citation Precision > 0.98
```

**2c. Math Accuracy Test**
```
20 equation transcription tests: Does answer LaTeX match source?
10 derivation tests: Are derivation steps correct and cited?
CALL: mcp:math-renderer.validate_latex(equation) for each
Target: Math Accuracy > 0.95
```

**2d. No-Hallucination Test**
```
For 20 questions with known false premises:
- "Find the paper where Smith proved P=NP"
- "What is the accuracy of method X on dataset Y?" (X not in corpus)
System must respond: "The retrieved context does not contain..."
Target: Hallucination rate < 0.02
```

### Suite 3: Performance/Latency Tests

```
Run 100 queries of each type, measure:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| p50 retrieval | < 500ms | > 750ms |
| p99 retrieval | < 2000ms | > 3000ms |
| p50 end-to-end | < 3000ms | > 5000ms |
| p99 end-to-end | < 8000ms | > 12000ms |
| Throughput | > 10 QPS | < 5 QPS |
```

## DRIFT DETECTION

Run weekly analysis:

**Embedding drift:**
```python
# Compare current embeddings vs. baseline cosine similarity
drift_score = mean_cosine_similarity(current_embeddings, baseline_embeddings)
IF drift_score < 0.95:
  ALERT: "Embedding drift detected (score={drift_score:.3f}). Consider re-embedding."
```

**Query distribution shift:**
```
Cluster queries from last 7 days into topics
Compare topic distribution to previous 7 days
IF KL_divergence > 0.3:
  ALERT: "Query distribution shifted. New dominant topics: {topics}"
```

**Answer quality trend:**
```
Track rolling 7-day average of faithfulness scores
IF 3-day moving avg < 0.90:
  IMMEDIATE ALERT: "Faithfulness degradation detected"
  TRIGGER: Full evaluation suite
```

## ALERT THRESHOLDS

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Faithfulness | < 0.92 | < 0.88 | Re-run eval, check context assembly |
| Citation Precision | < 0.96 | < 0.93 | Audit citation logic |
| Math Accuracy | < 0.92 | < 0.88 | Validate LaTeX pipeline |
| Retrieval Recall@10 | < 0.77 | < 0.70 | Check embedding quality |
| p99 Latency | > 3s | > 6s | Scale infrastructure |
| Hallucination Rate | > 0.03 | > 0.05 | Emergency: investigate immediately |

**Alert routing:**
- Warning → Log to `data/alerts.jsonl`
- Critical → Log + print prominent warning to user
- Emergency → Stop auto-answers, require human review

## REPORTING

Generate structured weekly report:

```markdown
# RAG Performance Report — Week of {date}

## Executive Summary
{1-2 sentences summarizing overall health}

## Key Metrics

| Metric | Target | This Week | Last Week | Trend | Status |
|--------|--------|-----------|-----------|-------|--------|
| Faithfulness | >0.95 | {val} | {val} | {↑↓→} | {🟢🟡🔴} |
| Citation Precision | >0.98 | {val} | {val} | {↑↓→} | {🟢🟡🔴} |
| Math Accuracy | >0.95 | {val} | {val} | {↑↓→} | {🟢🟡🔴} |
| Retrieval Recall@10 | >0.80 | {val} | {val} | {↑↓→} | {🟢🟡🔴} |
| p50 Latency | <500ms | {val} | {val} | {↑↓→} | {🟢🟡🔴} |
| p99 Latency | <2000ms | {val} | {val} | {↑↓→} | {🟢🟡🔴} |

## Corpus Statistics
- Total papers: {n}
- Total chunks: {n}
- Equations indexed: {n} ({valid_pct}% valid LaTeX)
- Tables indexed: {n}
- Algorithms indexed: {n}
- Queries this week: {n}

## Top Issues
1. {Issue description} — Impact: {High/Med/Low} — Status: {Open/Resolved}
2. {Issue description} — Impact: {High/Med/Low} — Status: {Open/Resolved}

## Recommendations
1. {Actionable recommendation with expected impact}
2. {Actionable recommendation}

## Failed Tests
{List any tests below threshold with details}

## Drift Alerts
{Any embedding or query distribution drift detected}
```

Save report to: `data/reports/eval_report_{YYYYMMDD}.md`

## BENCHMARK HISTORY TRACKING

After each evaluation run, append to `data/metrics_history.jsonl`:

```json
{
  "timestamp": "2024-01-15T00:00:00Z",
  "trigger": "weekly|manual|threshold|100_queries",
  "metrics": {
    "faithfulness": 0.96,
    "citation_precision": 0.99,
    "math_accuracy": 0.97,
    "recall_at_10": 0.83,
    "ndcg_at_10": 0.89,
    "mrr": 0.81,
    "p50_latency_ms": 312,
    "p99_latency_ms": 1842
  },
  "corpus_size": {
    "papers": 250,
    "chunks": 18500
  },
  "tests_passed": 47,
  "tests_failed": 3
}
```

Use this history for trend charts and regression detection.
