import { getDataMode, getFixedDataBundle } from "@/lib/fixed-data";

export const dynamic = "force-dynamic";

export default function Home() {
  const bundle = getFixedDataBundle();
  const dataMode = getDataMode(bundle);
  const rates = bundle.datasets.rates.slice(0, 12);
  const activities = bundle.datasets.activities.slice(0, 8);
  return <main className="page">
    <section className="hero">
      <div className="panel">
        <span className="tag">SAM-CTO Corporate Baseline</span>
        <h1>One controlled project backbone.<br/><span className="accent">Documents enter once. Every department works from the same scope.</span></h1>
        <p className="lead">The corporate Excel baseline keeps the platform operational, while the Project Intake engine converts BOQ, specifications, contracts and drawings into one CSI/SAM-CTO scope register. Historical data and live projects only enrich forecasting when they exist.</p>
        <div className="flow"><span className="node">Project Documents</span><span className="arrow">→</span><span className="node">CSI / SAM-CTO Scope</span><span className="arrow">→</span><span className="node">Technical · Tender · Planning · Cost</span><span className="arrow">+</span><span className="node">Corporate Baseline</span></div><div className="button-row"><a className="button" href="/intake">Open Project Intake</a><a className="button secondary" href="/planning">Planning Activities & Durations</a></div>
      </div>
      <div className="panel">
        <h2>Runtime Status</h2>
        <p className="status"><span className={`dot ${bundle.availability.excel_baseline ? "" : "warn"}`}></span>{dataMode.message}</p>
        <p className="muted">Mode: <b>{dataMode.mode}</b></p>
        <p className="muted">Generated: {bundle.generated_at ?? "Not generated"}</p>
      </div>
    </section>
    <section className="grid">
      <div className="metric">Activities<b>{bundle.counts.activities ?? 0}</b></div>
      <div className="metric">Resources<b>{bundle.counts.resources ?? 0}</b></div>
      <div className="metric">Unified Rates<b>{bundle.counts.rates ?? 0}</b></div>
      <div className="metric">Source Workbooks<b>{bundle.counts.workbooks ?? 0}</b></div>
    </section>
    <section id="rates" className="panel" style={{marginTop:18}}>
      <h2>Unified Rates — both Excel sources</h2>
      <p className="muted">Tender pricing rates and Activity Library resource/manpower/crew rates are normalized into one governed register.</p>
      <table><thead><tr><th>ID</th><th>Category</th><th>Description</th><th>Unit</th><th>Rate</th><th>Source</th></tr></thead><tbody>
        {rates.length ? rates.map((r:any,i)=><tr key={i}><td>{String(r.rate_id ?? "")}</td><td>{String(r.category ?? "")}</td><td>{String(r.description ?? "")}</td><td>{String(r.unit ?? "")}</td><td>{r.rate == null ? "—" : String(r.rate)}</td><td>{String(r.source ?? "")}</td></tr>) : <tr><td colSpan={6}>No generated rates yet. Run create_json.bat.</td></tr>}
      </tbody></table>
    </section>
    <section id="activities" className="panel" style={{marginTop:18}}>
      <h2>SAMCO Activity Master</h2>
      <table><thead><tr><th>SAMCO Master ID</th><th>Legacy Code</th><th>Description</th><th>CSI Division</th></tr></thead><tbody>
        {activities.length ? activities.map((a:any,i)=><tr key={i}><td>{String(a["SAMCO Master ID"] ?? "")}</td><td>{String(a["Activity Code"] ?? "")}</td><td>{String(a["Activity description"] ?? "")}</td><td>{String(a["Division Description"] ?? "")}</td></tr>) : <tr><td colSpan={4}>No generated activities yet. Run create_json.bat.</td></tr>}
      </tbody></table>
    </section>
  </main>;
}
