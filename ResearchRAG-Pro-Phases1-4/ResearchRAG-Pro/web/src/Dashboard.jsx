import { useState, useEffect, useRef, useCallback } from "react";

const COLORS = {
  eq: "#7C3AED",
  table: "#0D9488",
  algo: "#B45309",
  text: "#1E40AF",
  bg: "var(--color-background-primary)",
  bgSec: "var(--color-background-secondary)",
  border: "var(--color-border-tertiary)",
  borderSec: "var(--color-border-secondary)",
  textPrimary: "var(--color-text-primary)",
  textSec: "var(--color-text-secondary)",
  success: "var(--color-background-success)",
  successText: "var(--color-text-success)",
  info: "var(--color-background-info)",
  infoText: "var(--color-text-info)",
  warn: "var(--color-background-warning)",
  warnText: "var(--color-text-warning)",
  danger: "var(--color-background-danger)",
  dangerText: "var(--color-text-danger)",
};

const typeColor = { equation: COLORS.eq, table: COLORS.table, algorithm: COLORS.algo, text: COLORS.text };
const typeBg = { equation: "#F5F3FF", table: "#F0FDFA", algorithm: "#FFFBEB", text: "#EFF6FF" };
const typeIcon = { equation: "∑", table: "⊞", algorithm: "◈", text: "¶" };

const MOCK_PAPERS = [
  { id: "p1", title: "Attention Is All You Need", authors: "Vaswani et al.", year: 2017, chunks: 142, equations: 23, tables: 8, algorithms: 3 },
  { id: "p2", title: "BERT: Pre-training of Deep Bidirectional Transformers", authors: "Devlin et al.", year: 2019, chunks: 98, equations: 15, tables: 12, algorithms: 2 },
  { id: "p3", title: "An Image is Worth 16×16 Words", authors: "Dosovitskiy et al.", year: 2021, chunks: 117, equations: 19, tables: 10, algorithms: 4 },
];

const MOCK_RESULTS = [
  {
    id: "c1", type: "equation", paper: "Attention Is All You Need", year: 2017, section: "3.2.1", page: 4, score: 0.96,
    content: "\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V",
    variables: [{ s: "Q", m: "Query matrix" }, { s: "K", m: "Key matrix" }, { s: "V", m: "Value matrix" }, { s: "d_k", m: "Key dimension" }],
    surrounding: "An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors."
  },
  {
    id: "c2", type: "table", paper: "Attention Is All You Need", year: 2017, section: "6.1", page: 8, score: 0.91,
    caption: "Machine translation results on WMT 2014 English-to-German and English-to-French datasets",
    content: `| Model | EN-DE | EN-FR | Params |
|-------|-------|-------|--------|
| Transformer (base) | **27.3** | **38.1** | 65M |
| Transformer (big) | **28.4** | **41.0** | 213M |
| ByteNet | 23.75 | — | — |
| ConvS2S | 25.16 | 40.46 | — |`,
    colStats: { "EN-DE": { min: 23.75, max: 28.4, mean: 26.2 }, "EN-FR": { min: 38.1, max: 41.0, mean: 39.9 } }
  },
  {
    id: "c3", type: "algorithm", paper: "BERT", year: 2019, section: "3.1", page: 5, score: 0.88,
    name: "Algorithm 1: Masked Language Model Pre-training",
    inputs: ["token_sequence T", "mask_prob p = 0.15"],
    outputs: ["pre-trained model θ"],
    complexity: "O(L × H²)",
    pseudocode: `1: for each token t_i in T do
2:   r ← uniform(0, 1)
3:   if r < p then
4:     with prob 0.8: replace t_i with [MASK]
5:     with prob 0.1: replace t_i with random token
6:     with prob 0.1: keep t_i unchanged
7: return MLM_loss(model(T_masked), T_original)`
  },
  {
    id: "c4", type: "text", paper: "An Image is Worth 16×16 Words", year: 2021, section: "3", page: 4, score: 0.84,
    content: "We split an image into fixed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder. In order to perform classification, we use the standard approach of adding an extra learnable classification token to the sequence.",
    keywords: ["patch embedding", "position encoding", "classification token", "ViT"]
  }
];

const EVAL_METRICS = [
  { name: "Faithfulness", value: 0.967, target: 0.95, trend: "+0.012", status: "green" },
  { name: "Citation Precision", value: 0.991, target: 0.98, trend: "+0.003", status: "green" },
  { name: "Math Accuracy", value: 0.952, target: 0.95, trend: "-0.008", status: "yellow" },
  { name: "Recall@10", value: 0.834, target: 0.80, trend: "+0.021", status: "green" },
  { name: "nDCG@10", value: 0.891, target: 0.80, trend: "+0.015", status: "green" },
  { name: "p99 Latency", value: 1842, target: 2000, trend: "-203ms", status: "green", unit: "ms" },
];

const INGEST_LOG = [
  { time: "14:32:01", msg: "Parsing attention_is_all_you_need.pdf…", status: "info" },
  { time: "14:32:04", msg: "Detected 23 equations, 8 tables, 3 algorithms", status: "info" },
  { time: "14:32:08", msg: "Validating LaTeX — 23/23 valid", status: "success" },
  { time: "14:32:15", msg: "Generating embeddings — batch 1/5 (32 chunks)", status: "info" },
  { time: "14:32:28", msg: "Generating embeddings — batch 5/5 ✓", status: "success" },
  { time: "14:32:31", msg: "Building knowledge graph — 147 nodes, 89 edges", status: "info" },
  { time: "14:32:33", msg: "✅ Complete — 142 chunks indexed in 32.1s", status: "success" },
  { time: "14:33:10", msg: "Parsing bert_paper.pdf…", status: "info" },
  { time: "14:33:41", msg: "⚠ Equation (B.3) — invalid LaTeX, queued for review", status: "warn" },
  { time: "14:33:55", msg: "✅ Complete — 98 chunks indexed in 44.8s", status: "success" },
];

// ─── Utility components ───────────────────────────────────────────────────────

function Badge({ type }) {
  const col = typeColor[type] || "#666";
  const bg = typeBg[type] || "#f5f5f5";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 20, background: bg, border: `1px solid ${col}22`, fontSize: 11, fontWeight: 500, color: col, fontFamily: "var(--font-mono)" }}>
      {typeIcon[type]} {type}
    </span>
  );
}

function Score({ val }) {
  const pct = Math.round(val * 100);
  const col = pct > 90 ? "#059669" : pct > 75 ? "#D97706" : "#DC2626";
  return <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: col, fontWeight: 600 }}>{pct}%</span>;
}

function Chip({ label, onRemove }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 20, background: COLORS.bgSec, border: `0.5px solid ${COLORS.border}`, fontSize: 12, color: COLORS.textSec }}>
      {label}
      {onRemove && <button onClick={onRemove} style={{ background: "none", border: "none", cursor: "pointer", color: COLORS.textSec, padding: 0, lineHeight: 1, fontSize: 14 }}>×</button>}
    </span>
  );
}

function StatusDot({ status }) {
  const col = { green: "#10B981", yellow: "#F59E0B", red: "#EF4444" }[status] || "#888";
  return <span style={{ width: 8, height: 8, borderRadius: "50%", background: col, display: "inline-block", flexShrink: 0 }} />;
}

// ─── LaTeX Renderer ───────────────────────────────────────────────────────────

function MathRenderer({ latex, inline = false }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard?.writeText(latex); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  const style = inline
    ? { display: "inline-block", padding: "1px 6px", background: "#F5F3FF", borderRadius: 4, fontFamily: "var(--font-mono)", fontSize: 13, color: COLORS.eq }
    : { position: "relative", padding: "16px 20px", background: "#F5F3FF", borderRadius: 8, border: `1px solid ${COLORS.eq}22`, fontFamily: "var(--font-mono)", fontSize: 13, color: COLORS.eq, lineHeight: 1.8, overflowX: "auto" };

  return (
    <div style={{ ...(!inline && { position: "relative" }) }}>
      <div style={style}>{latex}</div>
      {!inline && (
        <button onClick={copy} style={{ position: "absolute", top: 8, right: 8, background: copied ? "#EDE9FE" : "white", border: `0.5px solid ${COLORS.border}`, borderRadius: 4, padding: "2px 8px", fontSize: 11, cursor: "pointer", color: COLORS.eq }}>
          {copied ? "✓ Copied" : "Copy LaTeX"}
        </button>
      )}
    </div>
  );
}

// ─── Table Viewer ─────────────────────────────────────────────────────────────

function TableViewer({ content, caption, colStats }) {
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  const lines = content.trim().split("\n");
  const headers = lines[0].replace(/\|/g, "").trim().split("|").map(h => h.trim()).filter(Boolean);
  const rows = lines.slice(2).map(l => l.replace(/\|/g, "").trim().split("|").map(c => c.trim()).filter(Boolean));

  const toggleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
  };

  const sorted = sortCol ? [...rows].sort((a, b) => {
    const ai = headers.indexOf(sortCol), aVal = a[ai]?.replace(/\*|\*\*/g, "") || "", bVal = b[ai]?.replace(/\*|\*\*/g, "") || "";
    const aNum = parseFloat(aVal), bNum = parseFloat(bVal);
    if (!isNaN(aNum) && !isNaN(bNum)) return sortDir === "asc" ? aNum - bNum : bNum - aNum;
    return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
  }) : rows;

  const exportCSV = () => {
    const csv = [headers.join(","), ...sorted.map(r => r.join(","))].join("\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "table.csv"; a.click();
  };

  const thStyle = { padding: "8px 12px", fontSize: 12, fontWeight: 500, color: COLORS.textSec, textAlign: "left", cursor: "pointer", userSelect: "none", background: COLORS.bgSec, borderBottom: `0.5px solid ${COLORS.border}`, whiteSpace: "nowrap" };
  const tdStyle = { padding: "7px 12px", fontSize: 12, color: COLORS.textPrimary, borderBottom: `0.5px solid ${COLORS.border}` };

  return (
    <div style={{ border: `0.5px solid ${COLORS.table}44`, borderRadius: 8, overflow: "hidden" }}>
      <div style={{ padding: "8px 12px", background: "#F0FDFA", borderBottom: `0.5px solid ${COLORS.table}33`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "#0D9488", fontWeight: 500 }}>{caption}</span>
        <button onClick={exportCSV} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: COLORS.table, color: "white", border: "none", cursor: "pointer" }}>↓ CSV</button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {headers.map(h => (
                <th key={h} style={thStyle} onClick={() => toggleSort(h)}>
                  {h} {sortCol === h ? (sortDir === "asc" ? "↑" : "↓") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={i} style={{ background: i % 2 ? COLORS.bgSec : COLORS.bg }}>
                {row.map((cell, j) => (
                  <td key={j} style={{ ...tdStyle, fontFamily: /^\*?\*?[\d.]+\*?\*?$/.test(cell) ? "var(--font-mono)" : "inherit", fontWeight: cell.startsWith("**") ? 600 : 400 }}>
                    {cell.replace(/\*\*/g, "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {colStats && (
        <div style={{ padding: "8px 12px", borderTop: `0.5px solid ${COLORS.border}`, display: "flex", gap: 16, flexWrap: "wrap" }}>
          {Object.entries(colStats).map(([col, s]) => (
            <span key={col} style={{ fontSize: 11, color: COLORS.textSec }}>
              <b style={{ color: COLORS.textPrimary }}>{col}</b>: min {s.min} · max {s.max} · mean {s.mean.toFixed(1)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Algorithm Visualizer ─────────────────────────────────────────────────────

function AlgorithmVisualizer({ name, inputs, outputs, complexity, pseudocode }) {
  const [activeLine, setActiveLine] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef(null);
  const lines = pseudocode.split("\n");

  const play = useCallback(() => {
    setPlaying(true);
    let i = 0;
    timerRef.current = setInterval(() => {
      setActiveLine(i);
      i++;
      if (i >= lines.length) { clearInterval(timerRef.current); setPlaying(false); setActiveLine(-1); }
    }, 800);
  }, [lines.length]);

  const stop = () => { clearInterval(timerRef.current); setPlaying(false); setActiveLine(-1); };
  useEffect(() => () => clearInterval(timerRef.current), []);

  return (
    <div style={{ border: `0.5px solid ${COLORS.algo}44`, borderRadius: 8, overflow: "hidden" }}>
      <div style={{ padding: "10px 14px", background: "#FFFBEB", borderBottom: `0.5px solid ${COLORS.algo}33`, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 500, color: "#92400E" }}>{name}</div>
          <div style={{ fontSize: 11, color: "#B45309", marginTop: 2 }}>
            <b>In:</b> {inputs.join(", ")} · <b>Out:</b> {outputs.join(", ")} · <b>Time:</b> <span style={{ fontFamily: "var(--font-mono)" }}>{complexity}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={playing ? stop : play} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 4, background: playing ? "#FEF3C7" : COLORS.algo, color: playing ? "#92400E" : "white", border: `0.5px solid ${COLORS.algo}`, cursor: "pointer" }}>
            {playing ? "⏹ Stop" : "▶ Step"}
          </button>
        </div>
      </div>
      <div style={{ background: "#1E1B18", padding: "12px 0", overflowX: "auto" }}>
        {lines.map((line, i) => (
          <div key={i} style={{ padding: "2px 16px", fontFamily: "var(--font-mono)", fontSize: 12, color: activeLine === i ? "#FCD34D" : "#D4C5A9", background: activeLine === i ? "rgba(252,211,77,0.12)" : "transparent", borderLeft: activeLine === i ? "3px solid #FCD34D" : "3px solid transparent", transition: "all 0.15s" }}>
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Result Card ──────────────────────────────────────────────────────────────

function ResultCard({ r, onSelect, selected }) {
  const [expanded, setExpanded] = useState(false);
  const borderCol = typeColor[r.type];

  return (
    <div style={{ border: `0.5px solid ${selected ? borderCol : COLORS.border}`, borderLeft: `3px solid ${borderCol}`, borderRadius: 8, background: selected ? `${typeBg[r.type]}` : COLORS.bg, overflow: "hidden", cursor: "pointer" }} onClick={() => { onSelect(r); setExpanded(true); }}>
      <div style={{ padding: "12px 14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <Badge type={r.type} />
            <span style={{ fontSize: 12, color: COLORS.textSec }}>{r.paper} ({r.year})</span>
            <span style={{ fontSize: 11, color: COLORS.textSec }}>§{r.section} · p.{r.page}</span>
          </div>
          <Score val={r.score} />
        </div>

        {r.type === "equation" && <MathRenderer latex={r.content} />}
        {r.type === "text" && <p style={{ fontSize: 13, color: COLORS.textPrimary, lineHeight: 1.6, margin: 0 }}>{r.content}</p>}
        {r.type === "table" && !expanded && <p style={{ fontSize: 12, color: COLORS.textSec, margin: 0 }}>Table: {r.caption}</p>}
        {r.type === "algorithm" && !expanded && <p style={{ fontSize: 12, color: COLORS.textSec, margin: 0 }}>{r.name}</p>}
      </div>

      {expanded && (
        <div style={{ borderTop: `0.5px solid ${COLORS.border}`, padding: "12px 14px" }}>
          {r.type === "equation" && r.variables && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: COLORS.textSec, fontWeight: 500, marginBottom: 6 }}>VARIABLES</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {r.variables.map(v => (
                  <span key={v.s} style={{ fontSize: 12, padding: "2px 8px", borderRadius: 4, background: COLORS.bgSec, border: `0.5px solid ${COLORS.border}` }}>
                    <span style={{ fontFamily: "var(--font-mono)", color: COLORS.eq }}>{v.s}</span>
                    <span style={{ color: COLORS.textSec }}> = {v.m}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {r.type === "equation" && r.surrounding && (
            <div>
              <div style={{ fontSize: 11, color: COLORS.textSec, fontWeight: 500, marginBottom: 4 }}>CONTEXT</div>
              <p style={{ fontSize: 12, color: COLORS.textSec, margin: 0, lineHeight: 1.6, borderLeft: `2px solid ${COLORS.border}`, paddingLeft: 10 }}>{r.surrounding}</p>
            </div>
          )}
          {r.type === "table" && <TableViewer content={r.content} caption={r.caption} colStats={r.colStats} />}
          {r.type === "algorithm" && <AlgorithmVisualizer name={r.name} inputs={r.inputs} outputs={r.outputs} complexity={r.complexity} pseudocode={r.pseudocode} />}
          {r.type === "text" && r.keywords && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {r.keywords.map(k => <Chip key={k} label={k} />)}
            </div>
          )}
        </div>
      )}

      <div style={{ padding: "6px 14px", borderTop: `0.5px solid ${COLORS.border}`, display: "flex", gap: 12 }}>
        <button onClick={e => { e.stopPropagation(); setExpanded(ex => !ex); }} style={{ fontSize: 11, color: COLORS.textSec, background: "none", border: "none", cursor: "pointer", padding: 0 }}>
          {expanded ? "▲ Collapse" : "▼ Expand"}
        </button>
        <button onClick={e => e.stopPropagation()} style={{ fontSize: 11, color: COLORS.infoText, background: "none", border: "none", cursor: "pointer", padding: 0 }}>Cite</button>
        <button onClick={e => e.stopPropagation()} style={{ fontSize: 11, color: COLORS.textSec, background: "none", border: "none", cursor: "pointer", padding: 0 }}>Similar</button>
      </div>
    </div>
  );
}

// ─── Pages ────────────────────────────────────────────────────────────────────

function IngestPage() {
  const [files, setFiles] = useState([
    { name: "attention_is_all_you_need.pdf", status: "done", chunks: 142, eq: 23, tbl: 8 },
    { name: "bert_paper.pdf", status: "done", chunks: 98, eq: 15, tbl: 12 },
    { name: "vit_paper.pdf", status: "processing", progress: 67 },
  ]);
  const [dragging, setDragging] = useState(false);
  const [logExpanded, setLogExpanded] = useState(true);

  const addFile = () => setFiles(f => [...f, { name: `new_paper_${f.length}.pdf`, status: "queued" }]);

  const statusIcon = { done: "✅", processing: "⏳", queued: "🕐", error: "❌" };
  const statusColor = { done: COLORS.successText, processing: COLORS.infoText, queued: COLORS.textSec, error: COLORS.dangerText };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 20, height: "100%" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); addFile(); }}
          style={{ border: `2px dashed ${dragging ? "#6D28D9" : COLORS.border}`, borderRadius: 12, padding: "32px 24px", textAlign: "center", background: dragging ? "#F5F3FF" : COLORS.bgSec, transition: "all 0.15s", cursor: "pointer" }}
          onClick={addFile}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>📄</div>
          <div style={{ fontWeight: 500, marginBottom: 4 }}>Drop research PDFs here</div>
          <div style={{ fontSize: 12, color: COLORS.textSec }}>or click to browse · PDF, DOCX, TEX · max 100MB</div>
        </div>

        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, overflow: "hidden" }}>
          <div style={{ padding: "10px 14px", borderBottom: `0.5px solid ${COLORS.border}`, display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Uploaded files</span>
            <span style={{ fontSize: 12, color: COLORS.textSec }}>{files.length} files</span>
          </div>
          {files.map((f, i) => (
            <div key={i} style={{ padding: "10px 14px", borderBottom: i < files.length - 1 ? `0.5px solid ${COLORS.border}` : "none", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 16 }}>{statusIcon[f.status]}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</div>
                {f.status === "done" && <div style={{ fontSize: 11, color: COLORS.textSec }}>{f.chunks} chunks · {f.eq} equations · {f.tbl} tables</div>}
                {f.status === "processing" && (
                  <div style={{ marginTop: 4 }}>
                    <div style={{ height: 3, background: COLORS.border, borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${f.progress}%`, background: "#6D28D9", borderRadius: 2, transition: "width 0.3s" }} />
                    </div>
                  </div>
                )}
                {f.status === "queued" && <div style={{ fontSize: 11, color: COLORS.textSec }}>Queued</div>}
              </div>
              <span style={{ fontSize: 11, color: statusColor[f.status], fontWeight: 500 }}>{f.status}</span>
            </div>
          ))}
        </div>

        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, overflow: "hidden" }}>
          <div onClick={() => setLogExpanded(e => !e)} style={{ padding: "10px 14px", borderBottom: logExpanded ? `0.5px solid ${COLORS.border}` : "none", display: "flex", justifyContent: "space-between", cursor: "pointer" }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Processing log</span>
            <span style={{ fontSize: 12, color: COLORS.textSec }}>{logExpanded ? "▲" : "▼"}</span>
          </div>
          {logExpanded && (
            <div style={{ background: "#1A1A1A", padding: "12px 14px", maxHeight: 200, overflowY: "auto" }}>
              {INGEST_LOG.map((l, i) => (
                <div key={i} style={{ fontFamily: "var(--font-mono)", fontSize: 11, lineHeight: 1.8, color: l.status === "success" ? "#4ADE80" : l.status === "warn" ? "#FBBF24" : "#9CA3AF" }}>
                  <span style={{ color: "#4B5563" }}>[{l.time}]</span> {l.msg}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 12 }}>Processing queue</div>
          {["vit_paper.pdf", "gpt4_technical_report.pdf"].map((f, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderTop: i > 0 ? `0.5px solid ${COLORS.border}` : "none" }}>
              <span style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>{f}</span>
              <span style={{ fontSize: 11, color: i === 0 ? COLORS.infoText : COLORS.textSec }}>{i === 0 ? "Active" : "Queued"}</span>
            </div>
          ))}
        </div>

        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 12 }}>Corpus stats</div>
          {[["Papers", "3"], ["Chunks", "18,450"], ["Equations", "4,820"], ["Tables", "1,280"], ["Algorithms", "340"]].map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderTop: `0.5px solid ${COLORS.border}` }}>
              <span style={{ fontSize: 12, color: COLORS.textSec }}>{k}</span>
              <span style={{ fontSize: 12, fontWeight: 500, fontFamily: "var(--font-mono)" }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SearchPage() {
  const [query, setQuery] = useState("");
  const [queryType, setQueryType] = useState("auto");
  const [filters, setFilters] = useState({ types: [], confidence: false });
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [answered, setAnswered] = useState(false);

  const search = () => {
    if (!query.trim()) return;
    setLoading(true);
    setTimeout(() => { setResults(MOCK_RESULTS); setLoading(false); setAnswered(true); }, 600);
  };

  const detectedType = query.includes("$") || query.includes("\\") ? "formula" : query.toLowerCase().includes("table") ? "table" : query.toLowerCase().includes("algorithm") ? "algorithm" : "conceptual";

  const toggleType = (t) => setFilters(f => ({ ...f, types: f.types.includes(t) ? f.types.filter(x => x !== t) : [...f.types, t] }));

  const filteredResults = filters.types.length ? results.filter(r => filters.types.includes(r.type)) : results;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 20, minHeight: "100%" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 10, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
            <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()}
              placeholder="Search equations, tables, algorithms… or type LaTeX like $\\frac{1}{n}$"
              style={{ flex: 1, border: "none", padding: "12px 14px", fontSize: 13, background: "transparent", color: COLORS.textPrimary, outline: "none" }} />
            <button onClick={search} style={{ padding: "0 20px", height: "100%", background: "#4F46E5", color: "white", border: "none", cursor: "pointer", fontWeight: 500, fontSize: 13, borderRadius: "0 8px 8px 0" }}>
              Search
            </button>
          </div>
          <div style={{ display: "flex", gap: 8, padding: "8px 14px", borderTop: `0.5px solid ${COLORS.border}`, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: COLORS.textSec }}>Type:</span>
            {["auto", "conceptual", "formula", "comparison", "derivation"].map(t => (
              <button key={t} onClick={() => setQueryType(t)} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 12, border: `0.5px solid ${queryType === t ? "#4F46E5" : COLORS.border}`, background: queryType === t ? "#EEF2FF" : "transparent", color: queryType === t ? "#4F46E5" : COLORS.textSec, cursor: "pointer" }}>
                {t}
              </button>
            ))}
            {query && queryType === "auto" && <span style={{ fontSize: 11, color: COLORS.textSec }}>→ detected: <b>{detectedType}</b></span>}
          </div>
        </div>

        {loading && <div style={{ textAlign: "center", padding: 40, color: COLORS.textSec, fontSize: 13 }}>⟳ Retrieving from 18,450 chunks…</div>}

        {answered && !loading && (
          <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: "14px 16px", background: "#F8F7FF" }}>
            <div style={{ fontSize: 11, color: "#6D28D9", fontWeight: 500, marginBottom: 8 }}>SYNTHESIZED ANSWER · 4 chunks · 3 papers · Confidence: High</div>
            <p style={{ fontSize: 13, lineHeight: 1.7, margin: 0, color: COLORS.textPrimary }}>
              The scaled dot-product attention mechanism maps queries, keys, and values to outputs via <span style={{ fontFamily: "var(--font-mono)", background: "#EDE9FE", padding: "1px 4px", borderRadius: 3, color: "#6D28D9" }}>softmax(QKᵀ/√d_k)V</span> [Vaswani et al., 2017, §3.2.1]. The scaling factor √d_k prevents vanishing gradients for large key dimensions. Experimental results show this achieves 28.4 BLEU on EN-DE translation — surpassing all prior models [Vaswani et al., 2017, Table 2].
            </p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filteredResults.map(r => <ResultCard key={r.id} r={r} onSelect={setSelected} selected={selected?.id === r.id} />)}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 10 }}>Filter by type</div>
          {["equation", "table", "algorithm", "text"].map(t => (
            <label key={t} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", cursor: "pointer" }}>
              <input type="checkbox" checked={filters.types.includes(t)} onChange={() => toggleType(t)} style={{ cursor: "pointer" }} />
              <Badge type={t} />
            </label>
          ))}
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: `0.5px solid ${COLORS.border}` }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
              <input type="checkbox" checked={filters.confidence} onChange={() => setFilters(f => ({ ...f, confidence: !f.confidence }))} />
              High confidence only (≥0.85)
            </label>
          </div>
        </div>

        {selected && (
          <div style={{ border: `0.5px solid ${typeColor[selected.type]}44`, borderRadius: 8, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 10 }}>Chunk detail</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {[["Type", <Badge type={selected.type} />], ["Paper", selected.paper], ["Section", `§${selected.section}`], ["Page", selected.page], ["Score", <Score val={selected.score} />]].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: COLORS.textSec }}>{k}</span>
                  <span style={{ fontSize: 12 }}>{v}</span>
                </div>
              ))}
            </div>
            {selected.type === "equation" && selected.variables && (
              <div style={{ marginTop: 12, paddingTop: 10, borderTop: `0.5px solid ${COLORS.border}` }}>
                <div style={{ fontSize: 11, color: COLORS.textSec, marginBottom: 6 }}>RELATED</div>
                {["Eq 3.3 (multi-head)", "Table 3 (complexity)", "Algorithm 1 (training)"].map(r => (
                  <div key={r} style={{ fontSize: 12, color: COLORS.infoText, padding: "3px 0", cursor: "pointer" }}>→ {r}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function PapersPage() {
  const [selected, setSelected] = useState(MOCK_PAPERS[0]);
  const [activeSection, setActiveSection] = useState("abstract");

  const sections = ["abstract", "introduction", "model architecture", "training", "results", "conclusion"];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr 240px", gap: 20, height: "100%" }}>
      <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, overflow: "hidden", alignSelf: "start" }}>
        <div style={{ padding: "10px 14px", borderBottom: `0.5px solid ${COLORS.border}`, fontSize: 12, fontWeight: 500 }}>Papers ({MOCK_PAPERS.length})</div>
        {MOCK_PAPERS.map(p => (
          <div key={p.id} onClick={() => setSelected(p)} style={{ padding: "10px 14px", borderBottom: `0.5px solid ${COLORS.border}`, cursor: "pointer", background: selected?.id === p.id ? "#EEF2FF" : "transparent", borderLeft: selected?.id === p.id ? "3px solid #4F46E5" : "3px solid transparent" }}>
            <div style={{ fontSize: 12, fontWeight: 500, lineHeight: 1.4 }}>{p.title}</div>
            <div style={{ fontSize: 11, color: COLORS.textSec, marginTop: 2 }}>{p.authors} · {p.year}</div>
            <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
              <span style={{ fontSize: 10, color: COLORS.eq }}>∑{p.equations}</span>
              <span style={{ fontSize: 10, color: COLORS.table }}>⊞{p.tables}</span>
              <span style={{ fontSize: 10, color: COLORS.algo }}>◈{p.algorithms}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {selected && (
          <>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, margin: "0 0 4px" }}>{selected.title}</h2>
              <div style={{ fontSize: 12, color: COLORS.textSec }}>{selected.authors} · {selected.year} · {selected.chunks} chunks</div>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                {["PDF", "BibTeX", "Export"].map(a => <button key={a} style={{ fontSize: 11, padding: "3px 10px", border: `0.5px solid ${COLORS.border}`, borderRadius: 4, background: "transparent", cursor: "pointer", color: COLORS.textSec }}>{a}</button>)}
              </div>
            </div>

            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {sections.map(s => (
                <button key={s} onClick={() => setActiveSection(s)} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 12, border: `0.5px solid ${activeSection === s ? "#4F46E5" : COLORS.border}`, background: activeSection === s ? "#EEF2FF" : "transparent", color: activeSection === s ? "#4F46E5" : COLORS.textSec, cursor: "pointer" }}>
                  {s}
                </button>
              ))}
            </div>

            <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: "16px 18px" }}>
              <p style={{ fontSize: 13, lineHeight: 1.8, color: COLORS.textPrimary, margin: 0 }}>
                The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the <b>Transformer</b>, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.
              </p>
              <div style={{ marginTop: 14 }}>
                <MathRenderer latex="\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, ..., \text{head}_h)W^O" />
              </div>
            </div>
          </>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, alignSelf: "start" }}>
        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 10 }}>Chunk index</div>
          {[...MOCK_RESULTS.slice(0, 3)].map(r => (
            <div key={r.id} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0", borderBottom: `0.5px solid ${COLORS.border}` }}>
              <Badge type={r.type} />
              <span style={{ fontSize: 11, color: COLORS.textSec }}>§{r.section}</span>
            </div>
          ))}
        </div>
        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8 }}>Citations</div>
          {["Vaswani et al. 2017", "Bahdanau et al. 2015", "Hochreiter & Schmidhuber 1997"].map(c => (
            <div key={c} style={{ fontSize: 12, color: COLORS.infoText, padding: "3px 0" }}>→ {c}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EvalPage() {
  const statusColor = { green: "#10B981", yellow: "#F59E0B", red: "#EF4444" };

  const testResults = [
    { name: "Math Equivalence Test", passed: 18, total: 20, metric: "Recall@10", score: 0.90 },
    { name: "Table Lookup Test", passed: 14, total: 15, metric: "Precision@5", score: 0.93 },
    { name: "Algorithm Comparison Test", passed: 11, total: 15, metric: "MRR", score: 0.73 },
    { name: "Faithfulness Test", passed: 49, total: 50, metric: "Faithfulness", score: 0.98 },
    { name: "Citation Accuracy Test", passed: 30, total: 30, metric: "Citation Prec.", score: 1.00 },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {EVAL_METRICS.map(m => (
          <div key={m.name} style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: "12px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ fontSize: 11, color: COLORS.textSec, fontWeight: 500 }}>{m.name.toUpperCase()}</div>
              <StatusDot status={m.status} />
            </div>
            <div style={{ fontSize: 22, fontWeight: 500, fontFamily: "var(--font-mono)", margin: "6px 0 2px", color: statusColor[m.status] }}>
              {m.unit ? m.value : (m.value * 100).toFixed(1) + "%"}
              {m.unit && <span style={{ fontSize: 12 }}>{m.unit}</span>}
            </div>
            <div style={{ fontSize: 11, color: COLORS.textSec }}>
              Target: {m.unit ? m.target + m.unit : (m.target * 100) + "%"} · <span style={{ color: m.trend.startsWith("+") ? "#10B981" : "#EF4444" }}>{m.trend}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, overflow: "hidden" }}>
          <div style={{ padding: "10px 14px", borderBottom: `0.5px solid ${COLORS.border}`, display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Test suite results</span>
            <button style={{ fontSize: 11, padding: "2px 8px", background: "#4F46E5", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}>▶ Run All</button>
          </div>
          {testResults.map((t, i) => (
            <div key={i} style={{ padding: "10px 14px", borderBottom: i < testResults.length - 1 ? `0.5px solid ${COLORS.border}` : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 500 }}>{t.name}</span>
                <Score val={t.score} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ flex: 1, height: 4, background: COLORS.border, borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(t.passed / t.total) * 100}%`, background: t.passed === t.total ? "#10B981" : t.score > 0.85 ? "#F59E0B" : "#EF4444", borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: 11, color: COLORS.textSec, whiteSpace: "nowrap" }}>{t.passed}/{t.total} · {t.metric}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ border: `0.5px solid ${COLORS.border}`, borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 14 }}>Drift detection</div>
          {[
            { label: "Embedding drift", value: 0.98, status: "Stable" },
            { label: "Query topic shift", value: 0.12, status: "Low", note: "KL-divergence" },
            { label: "Faithfulness trend", value: 0.967, status: "↑ Improving" },
          ].map((d, i) => (
            <div key={i} style={{ padding: "10px 0", borderTop: i > 0 ? `0.5px solid ${COLORS.border}` : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12 }}>{d.label}</span>
                <span style={{ fontSize: 12, color: "#10B981", fontWeight: 500 }}>{d.status}</span>
              </div>
              {d.note && <div style={{ fontSize: 11, color: COLORS.textSec }}>{d.note}: {d.value}</div>}
            </div>
          ))}
          <div style={{ marginTop: 14, padding: 10, background: COLORS.bgSec, borderRadius: 6 }}>
            <div style={{ fontSize: 11, fontWeight: 500, marginBottom: 4 }}>No alerts active</div>
            <div style={{ fontSize: 11, color: COLORS.textSec }}>All metrics within threshold. Next weekly eval: Mon 00:00 UTC</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState("search");

  const nav = [
    { id: "ingest", label: "Ingest", icon: "⬆" },
    { id: "search", label: "Search", icon: "⌕" },
    { id: "papers", label: "Papers", icon: "◎" },
    { id: "eval", label: "Evaluation", icon: "◈" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", fontFamily: "var(--font-sans)" }}>
      <header style={{ borderBottom: `0.5px solid ${COLORS.border}`, padding: "0 20px", display: "flex", alignItems: "center", gap: 0, height: 48, position: "sticky", top: 0, background: COLORS.bg, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginRight: 32 }}>
          <div style={{ width: 22, height: 22, background: "#4F46E5", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontSize: 12, fontWeight: 700 }}>R</div>
          <span style={{ fontSize: 14, fontWeight: 500 }}>ResearchRAG Pro</span>
        </div>
        <nav style={{ display: "flex", gap: 0, flex: 1 }}>
          {nav.map(n => (
            <button key={n.id} onClick={() => setPage(n.id)} style={{ padding: "0 16px", height: 48, border: "none", background: "transparent", cursor: "pointer", fontSize: 13, color: page === n.id ? "#4F46E5" : COLORS.textSec, borderBottom: page === n.id ? "2px solid #4F46E5" : "2px solid transparent", fontWeight: page === n.id ? 500 : 400, display: "flex", alignItems: "center", gap: 6 }}>
              <span>{n.icon}</span> {n.label}
            </button>
          ))}
        </nav>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <StatusDot status="green" />
          <span style={{ fontSize: 12, color: COLORS.textSec }}>18,450 chunks · 3 papers</span>
        </div>
      </header>

      <main style={{ flex: 1, padding: "20px", maxWidth: 1200, margin: "0 auto", width: "100%", boxSizing: "border-box" }}>
        {page === "ingest" && <IngestPage />}
        {page === "search" && <SearchPage />}
        {page === "papers" && <PapersPage />}
        {page === "eval" && <EvalPage />}
      </main>
    </div>
  );
}
