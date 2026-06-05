import { useState, useRef } from "react";

const CLIENTS = [
  { id: "denodo", name: "Denodo", color: "#E84040" },
  { id: "knowbe4", name: "KnowBe4", color: "#FF4B00" },
  { id: "netscout", name: "NETSCOUT", color: "#6DBE45" },
  { id: "illumio", name: "Illumio", color: "#FF6B2B" },
  { id: "phosphorus", name: "Phosphorus", color: "#3D5AFE" },
  { id: "qlik", name: "Qlik", color: "#009845" },
  { id: "custom", name: "Other / Custom", color: "#1F497D" },
];

const SECTIONS = [
  "Campaign Overview",
  "Coverage Highlights",
  "Deliverables Overview",
  "Coverage Analysis",
  "Media Relations & Engagement",
  "Driving the Narrative",
  "Observation & Feedback",
  "Strategic Recommendations",
  "90-Day Plan",
];

const SYSTEM_PROMPT = `You are a senior communications strategist at Active DMC (Active Digital Marketing Communications), a premium PR agency in the Middle East. Your task is to generate a client-ready communications report strictly following Active DMC's structure, tone, and storytelling logic.

BRAND & FORMAT RULES:
- Premium consulting tone: concise, strategic, non-generic
- Clear headings, bullet points, tables where relevant
- Content must be directly presentation-ready for PowerPoint
- Font: Trebuchet MS. Headlines: bold 12pt navy. Body: 10pt.
- Header: client logo left, Active DMC logo right, navy separator rule

INSIGHT GENERATION (CRITICAL):
Every insight MUST follow this framework:
1. What happened (fact/data)
2. Why it happened (reason/cause)
3. What it means (strategic implication)
Minimum 3-5 insights per section. NEVER repeat data without interpretation.

DATA INTEGRITY:
- Do NOT fabricate media titles, metrics, or deliverables
- Only use provided data
- If data is missing, clearly state assumptions or gaps

CROSS-SECTION CONSISTENCY:
- Deliverables → must connect to coverage outcomes
- Coverage → must reflect narrative themes
- Insights → must support recommendations
The report must read as ONE coherent story.

FORMAT OUTPUT:
Use markdown with clear section headers (##), bullet points (-), and tables where needed.
Each section must begin with its ADMC section header exactly as specified.`;

export default function ADMCReportingAgent() {
  const [step, setStep] = useState(0); // 0=config, 1=data, 2=generating, 3=report
  const [client, setClient] = useState("denodo");
  const [customClient, setCustomClient] = useState("");
  const [period, setPeriod] = useState("");
  const [selectedSections, setSelectedSections] = useState(new Set(SECTIONS));
  const [coverageData, setCoverageData] = useState("");
  const [asanaData, setAsanaData] = useState("");
  const [additionalContext, setAdditionalContext] = useState("");
  const [report, setReport] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const reportRef = useRef(null);

  const clientInfo = CLIENTS.find((c) => c.id === client) || CLIENTS[0];
  const clientName = client === "custom" ? customClient || "Client" : clientInfo.name;
  const accentColor = clientInfo.color;

  function toggleSection(s) {
    setSelectedSections((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });
  }

  async function generateReport() {
    if (!period.trim()) { setError("Please enter a reporting period."); return; }
    if (!coverageData.trim() && !asanaData.trim()) { setError("Please provide at least coverage data or Asana data."); return; }
    setError("");
    setIsGenerating(true);
    setStep(2);
    setReport("");
    setProgress(0);

    const sectionsRequested = [...selectedSections].join(", ");
    const userPrompt = `Generate a complete Active DMC communications report for the following:

CLIENT: ${clientName}
REPORTING PERIOD: ${period}
SECTIONS TO INCLUDE: ${sectionsRequested}

COVERAGE DATA:
${coverageData || "(Not provided — flag as data gap)"}

ASANA / DELIVERABLES DATA:
${asanaData || "(Not provided — flag as data gap)"}

ADDITIONAL CONTEXT:
${additionalContext || "None"}

Generate the full report following Active DMC structure exactly. For each section requested, provide:
- Section header in format: ## [NUMBER]. [SECTION NAME]
- Minimum 3-5 strategic insights following the What/Why/What-it-means framework
- Tables where relevant (Deliverables Overview requires a table)
- Driving the Narrative section must include messaging evolution and strategic communications analysis
- 90-Day Plan must break down by month with specific activities

Begin with a brief executive summary line, then proceed section by section.`;

    try {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: userPrompt }],
          stream: true,
        }),
      });

      if (!resp.ok) throw new Error(`API error ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      let totalTokens = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "content_block_delta" && parsed.delta?.text) {
                accumulated += parsed.delta.text;
                setReport(accumulated);
                totalTokens++;
                setProgress(Math.min(95, Math.floor((totalTokens / 800) * 95)));
              }
            } catch {}
          }
        }
      }

      setProgress(100);
      setStep(3);
    } catch (e) {
      setError(`Generation failed: ${e.message}`);
      setStep(1);
    } finally {
      setIsGenerating(false);
    }
  }

  function copyReport() {
    navigator.clipboard.writeText(report).catch(() => {});
  }

  function resetAgent() {
    setStep(0);
    setReport("");
    setProgress(0);
    setError("");
  }

  const styles = {
    wrap: { fontFamily: "'Trebuchet MS', sans-serif", maxWidth: 760, margin: "0 auto", padding: "1.5rem 0" },
    header: {
      display: "flex", alignItems: "center", justifyContent: "space-between",
      borderBottom: `2px solid ${accentColor}`, paddingBottom: "1rem", marginBottom: "1.5rem",
    },
    brandLeft: { display: "flex", alignItems: "center", gap: 10 },
    brandDot: { width: 10, height: 10, borderRadius: "50%", background: accentColor },
    brandName: { fontSize: 15, fontWeight: 500, color: "var(--color-text-primary)", letterSpacing: "0.02em" },
    agencyTag: { fontSize: 12, color: "var(--color-text-secondary)", fontStyle: "italic" },
    stepBar: { display: "flex", gap: 6, alignItems: "center", marginBottom: "1.5rem" },
    stepDot: (active, done) => ({
      width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 12, fontWeight: 500, flexShrink: 0,
      background: done ? accentColor : active ? "var(--color-background-secondary)" : "var(--color-background-secondary)",
      color: done ? "#fff" : active ? "var(--color-text-primary)" : "var(--color-text-tertiary)",
      border: active ? `1.5px solid ${accentColor}` : "1.5px solid var(--color-border-tertiary)",
      transition: "all 0.2s",
    }),
    stepLine: { flex: 1, height: 1, background: "var(--color-border-tertiary)" },
    card: {
      background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: 12, padding: "1.25rem 1.5rem", marginBottom: "1rem",
    },
    label: { fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: 6, display: "block", textTransform: "uppercase", letterSpacing: "0.06em" },
    input: { width: "100%", fontSize: 14, padding: "8px 12px", borderRadius: 8, boxSizing: "border-box" },
    textarea: { width: "100%", fontSize: 13, padding: "10px 12px", borderRadius: 8, minHeight: 100, resize: "vertical", boxSizing: "border-box", lineHeight: 1.5 },
    clientGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 8, marginBottom: 8 },
    clientBtn: (selected, color) => ({
      padding: "8px 10px", borderRadius: 8, fontSize: 13, fontWeight: selected ? 500 : 400, cursor: "pointer",
      border: selected ? `2px solid ${color}` : "0.5px solid var(--color-border-tertiary)",
      background: selected ? `${color}18` : "var(--color-background-secondary)",
      color: selected ? "var(--color-text-primary)" : "var(--color-text-secondary)",
      transition: "all 0.15s", textAlign: "left",
    }),
    sectionGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 },
    sectionToggle: (on) => ({
      padding: "7px 10px", borderRadius: 8, fontSize: 12, cursor: "pointer",
      border: on ? `1.5px solid ${accentColor}` : "0.5px solid var(--color-border-tertiary)",
      background: on ? `${accentColor}15` : "var(--color-background-secondary)",
      color: on ? "var(--color-text-primary)" : "var(--color-text-secondary)",
      display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s",
    }),
    primaryBtn: {
      background: accentColor, color: "#fff", border: "none", padding: "10px 20px",
      borderRadius: 8, fontSize: 14, fontWeight: 500, cursor: "pointer",
      display: "flex", alignItems: "center", gap: 8,
    },
    secondaryBtn: {
      background: "transparent", color: "var(--color-text-secondary)",
      border: "0.5px solid var(--color-border-tertiary)", padding: "9px 16px",
      borderRadius: 8, fontSize: 13, cursor: "pointer",
    },
    progressWrap: { textAlign: "center", padding: "3rem 1rem" },
    progressBar: { width: "100%", height: 4, background: "var(--color-background-secondary)", borderRadius: 2, overflow: "hidden", margin: "1rem 0" },
    progressFill: { height: "100%", background: accentColor, borderRadius: 2, transition: "width 0.4s ease" },
    reportWrap: { background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "2rem", fontFamily: "'Trebuchet MS', sans-serif" },
    reportHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: `2px solid ${accentColor}`, paddingBottom: "1rem", marginBottom: "1.5rem" },
    reportTitle: { fontSize: 18, fontWeight: 600, color: "var(--color-text-primary)", marginBottom: 4 },
    reportMeta: { fontSize: 12, color: "var(--color-text-secondary)" },
    reportBody: { fontSize: 13, lineHeight: 1.8, color: "var(--color-text-primary)", whiteSpace: "pre-wrap" },
    errBox: { background: "var(--color-background-danger)", border: "0.5px solid var(--color-border-danger)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "var(--color-text-danger)", marginBottom: "1rem" },
  };

  const stepLabels = ["Configure", "Input Data", "Generating", "Report"];

  return (
    <div style={styles.wrap}>
      <h2 className="sr-only">Active DMC AI Reporting Agent</h2>

      <div style={styles.header}>
        <div style={styles.brandLeft}>
          <div style={styles.brandDot} />
          <div>
            <div style={styles.brandName}>Active DMC · Reporting Agent</div>
            <div style={styles.agencyTag}>Active Digital Marketing Communications</div>
          </div>
        </div>
        <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", textAlign: "right" }}>
          AI-powered<br />Client Report Generator
        </div>
      </div>

      <div style={styles.stepBar}>
        {stepLabels.map((label, i) => (
          <>
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <div style={styles.stepDot(step === i, step > i)}>
                {step > i ? <i className="ti ti-check" aria-hidden="true" /> : i + 1}
              </div>
              <span style={{ fontSize: 10, color: step === i ? "var(--color-text-primary)" : "var(--color-text-tertiary)", whiteSpace: "nowrap" }}>{label}</span>
            </div>
            {i < stepLabels.length - 1 && <div style={{ ...styles.stepLine, marginBottom: 18 }} />}
          </>
        ))}
      </div>

      {error && <div style={styles.errBox}><i className="ti ti-alert-circle" aria-hidden="true" /> {error}</div>}

      {step === 0 && (
        <div>
          <div style={styles.card}>
            <label style={styles.label}>Select Client</label>
            <div style={styles.clientGrid}>
              {CLIENTS.map((c) => (
                <button key={c.id} style={styles.clientBtn(client === c.id, c.color)} onClick={() => setClient(c.id)}>
                  <span style={{ display: "block", width: 8, height: 8, borderRadius: "50%", background: c.color, display: "inline-block", marginRight: 6 }} />
                  {c.name}
                </button>
              ))}
            </div>
            {client === "custom" && (
              <input style={styles.input} placeholder="Enter client name…" value={customClient} onChange={(e) => setCustomClient(e.target.value)} />
            )}
          </div>

          <div style={styles.card}>
            <label style={styles.label}>Reporting Period</label>
            <input style={styles.input} placeholder="e.g. January 2026 / Q1 2026 / 01–31 March 2026" value={period} onChange={(e) => setPeriod(e.target.value)} />
          </div>

          <div style={styles.card}>
            <label style={styles.label}>Report Sections</label>
            <div style={styles.sectionGrid}>
              {SECTIONS.map((s) => (
                <button key={s} style={styles.sectionToggle(selectedSections.has(s))} onClick={() => toggleSection(s)}>
                  <i className={`ti ${selectedSections.has(s) ? "ti-circle-check" : "ti-circle"}`} style={{ fontSize: 14 }} aria-hidden="true" />
                  <span>{s}</span>
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button style={styles.primaryBtn} onClick={() => { if (!period.trim()) { setError("Please enter a reporting period."); return; } setError(""); setStep(1); }}>
              Next: Add Data <i className="ti ti-arrow-right" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div>
          <div style={styles.card}>
            <label style={styles.label}>Coverage Data</label>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 8 }}>
              Paste media hits, publications, dates, tiers, headlines, reach figures, language split
            </div>
            <textarea style={styles.textarea} rows={8} placeholder={"Example:\n- CXO Insight ME – 26.03.2026 – Tier 1 – English – Denodo joins Snowflake…\n- Gulf Tech News – 26.03.2026 – Tier 1 – English – Denodo and Snowflake…\n- Saudi Tech Post – 26.03.2026 – Tier 1 – Arabic – …\n\nTotal: 14 placements (12 English, 2 Arabic)"} value={coverageData} onChange={(e) => setCoverageData(e.target.value)} />
          </div>

          <div style={styles.card}>
            <label style={styles.label}>Asana / Deliverables Data</label>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 8 }}>
              Planned vs delivered: press releases, interviews, bylines, events, briefings
            </div>
            <textarea style={styles.textarea} rows={6} placeholder={"Example:\nActivity | Planned | Delivered\nPress Releases | 2 | 2\nMedia Interviews | 3 | 2\nBylines | 1 | 1\nMedia Briefings | 2 | 2"} value={asanaData} onChange={(e) => setAsanaData(e.target.value)} />
          </div>

          <div style={styles.card}>
            <label style={styles.label}>Additional Context (Optional)</label>
            <textarea style={styles.textarea} rows={4} placeholder="Campaign themes, key narratives, spokesperson details, special initiatives, market context…" value={additionalContext} onChange={(e) => setAdditionalContext(e.target.value)} />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button style={styles.secondaryBtn} onClick={() => { setError(""); setStep(0); }}>
              <i className="ti ti-arrow-left" aria-hidden="true" /> Back
            </button>
            <button style={styles.primaryBtn} onClick={generateReport}>
              <i className="ti ti-report" aria-hidden="true" /> Generate Report
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div style={styles.progressWrap}>
          <div style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 8 }}>
            Generating {clientName} report…
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
            Applying Active DMC structure · Building insights · Crafting narrative
          </div>
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>{progress}%</div>
          {report && (
            <div style={{ textAlign: "left", marginTop: "1.5rem", background: "var(--color-background-secondary)", borderRadius: 8, padding: "1rem", fontSize: 12, color: "var(--color-text-secondary)", maxHeight: 200, overflow: "hidden", whiteSpace: "pre-wrap" }}>
              {report.slice(-600)}
            </div>
          )}
        </div>
      )}

      {step === 3 && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>
                Report ready — {clientName} · {period}
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                {selectedSections.size} sections · Generated by Active DMC Reporting Agent
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button style={styles.secondaryBtn} onClick={copyReport}>
                <i className="ti ti-copy" aria-hidden="true" /> Copy
              </button>
              <button style={styles.secondaryBtn} onClick={resetAgent}>
                <i className="ti ti-refresh" aria-hidden="true" /> New Report
              </button>
            </div>
          </div>

          <div style={styles.reportWrap} ref={reportRef}>
            <div style={styles.reportHeader}>
              <div>
                <div style={styles.reportTitle}>{clientName}</div>
                <div style={styles.reportMeta}>Communications Report · {period}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: accentColor, letterSpacing: "0.08em", textTransform: "uppercase" }}>Active DMC</div>
                <div style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>Active Digital Marketing Communications</div>
              </div>
            </div>
            <div style={styles.reportBody}>
              <ReportRenderer content={report} accentColor={accentColor} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ReportRenderer({ content, accentColor }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements = [];
  let tableLines = [];
  let inTable = false;
  let key = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith("|")) {
      inTable = true;
      tableLines.push(line);
      continue;
    }

    if (inTable && !line.trim().startsWith("|")) {
      elements.push(<TableBlock key={key++} lines={tableLines} accentColor={accentColor} />);
      tableLines = [];
      inTable = false;
    }

    if (line.startsWith("## ")) {
      const text = line.replace(/^##\s+/, "");
      elements.push(
        <div key={key++} style={{ borderLeft: `3px solid ${accentColor}`, paddingLeft: 12, margin: "1.5rem 0 0.5rem", fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)", letterSpacing: "0.01em" }}>
          {text}
        </div>
      );
    } else if (line.startsWith("# ")) {
      const text = line.replace(/^#\s+/, "");
      elements.push(
        <div key={key++} style={{ fontSize: 15, fontWeight: 600, color: "var(--color-text-primary)", margin: "0 0 0.5rem", paddingBottom: 6, borderBottom: `1px solid var(--color-border-tertiary)` }}>
          {text}
        </div>
      );
    } else if (line.startsWith("### ")) {
      const text = line.replace(/^###\s+/, "");
      elements.push(
        <div key={key++} style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)", margin: "1rem 0 0.25rem" }}>
          {text}
        </div>
      );
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      const text = line.replace(/^[-*]\s+/, "");
      elements.push(
        <div key={key++} style={{ display: "flex", gap: 8, fontSize: 12, lineHeight: 1.7, margin: "2px 0", paddingLeft: 8 }}>
          <span style={{ color: accentColor, flexShrink: 0, marginTop: 2 }}>•</span>
          <span style={{ color: "var(--color-text-primary)" }} dangerouslySetInnerHTML={{ __html: formatInline(text) }} />
        </div>
      );
    } else if (/^\d+\.\s/.test(line)) {
      const match = line.match(/^(\d+)\.\s(.*)/);
      if (match) {
        elements.push(
          <div key={key++} style={{ display: "flex", gap: 8, fontSize: 12, lineHeight: 1.7, margin: "2px 0", paddingLeft: 8 }}>
            <span style={{ color: accentColor, flexShrink: 0, fontWeight: 600, minWidth: 16 }}>{match[1]}.</span>
            <span style={{ color: "var(--color-text-primary)" }} dangerouslySetInnerHTML={{ __html: formatInline(match[2]) }} />
          </div>
        );
      }
    } else if (line.trim() === "" || line.trim() === "---") {
      elements.push(<div key={key++} style={{ height: line.trim() === "---" ? 1 : 8, background: line.trim() === "---" ? "var(--color-border-tertiary)" : "transparent", margin: line.trim() === "---" ? "1rem 0" : 0 }} />);
    } else if (line.trim()) {
      elements.push(
        <p key={key++} style={{ fontSize: 12, lineHeight: 1.8, color: "var(--color-text-primary)", margin: "4px 0" }} dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
      );
    }
  }

  if (inTable && tableLines.length > 0) {
    elements.push(<TableBlock key={key++} lines={tableLines} accentColor={accentColor} />);
  }

  return <div>{elements}</div>;
}

function TableBlock({ lines, accentColor }) {
  const rows = lines.filter((l) => !l.match(/^\|[-\s|]+\|$/)).map((l) =>
    l.split("|").filter((_, i, arr) => i > 0 && i < arr.length - 1).map((c) => c.trim())
  );

  if (rows.length < 1) return null;
  const [header, ...body] = rows;

  return (
    <div style={{ overflowX: "auto", margin: "1rem 0" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, tableLayout: "fixed" }}>
        <thead>
          <tr>
            {header.map((h, i) => (
              <th key={i} style={{ background: `${accentColor}18`, color: "var(--color-text-primary)", fontWeight: 600, padding: "7px 10px", textAlign: "left", border: "0.5px solid var(--color-border-tertiary)", fontSize: 11 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri} style={{ background: ri % 2 === 0 ? "var(--color-background-primary)" : "var(--color-background-secondary)" }}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ padding: "6px 10px", border: "0.5px solid var(--color-border-tertiary)", color: "var(--color-text-primary)", lineHeight: 1.5 }} dangerouslySetInnerHTML={{ __html: formatInline(cell) }} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatInline(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code style='background:var(--color-background-secondary);padding:1px 4px;border-radius:3px;font-size:11px;'>$1</code>");
}
