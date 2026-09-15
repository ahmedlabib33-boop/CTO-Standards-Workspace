import DurationCalculator from "./DurationCalculator";
import { getPlanningActivities } from "@/lib/planning";
import { getLatestProjectScope, quantityLabel } from "@/lib/project-scope";

export const dynamic = "force-dynamic";

export default async function PlanningPage(){
  const rows = await getPlanningActivities(30);
  const intakeRows = (await getLatestProjectScope(40)).filter(r=>r.completeness?.has_boq);
  return <main className="page">
    <section className="panel"><span className="tag">Planning Core · Synchronous</span><h1 style={{fontSize:48}}>Activities & Durations</h1><p className="lead">Planning activities, productivity and duration calculations remain available even when Redis, historical projects, live projects, ML or LLM services are unavailable.</p>
      <div className="flow"><span className="node">SAM-CTO Activity</span><span className="arrow">→</span><span className="node">Quantity</span><span className="arrow">→</span><span className="node">Productivity × Crews</span><span className="arrow">→</span><span className="node">Duration</span><span className="arrow">→</span><span className="node">Logic / Calendar / P6</span></div>
    </section>
    <section className="grid"><div className="metric">Duration Formula<b style={{fontSize:18}}>Q ÷ (P × Crews)</b></div><div className="metric">Source<b style={{fontSize:18}}>DB → JSON fallback</b></div><div className="metric">Historical Data<b style={{fontSize:18}}>Optional</b></div><div className="metric">ML / LLM<b style={{fontSize:18}}>Optional</b></div></section>
    <DurationCalculator/>
    <section className="panel" style={{marginTop:18}}><div className="section-title-row"><div><h2>Incoming Scope from Project Intake</h2><p className="muted">Document-derived quantities and approved/proposed SAM-CTO mappings arrive here before schedule build-up. The intake engine does not change the deterministic duration equations.</p></div><a className="button secondary" href="/intake">Open Intake</a></div>{!intakeRows.length?<p className="muted">No persisted intake scope yet. Planning remains fully usable from the corporate activity/productivity library.</p>:<div className="table-wrap"><table><thead><tr><th>Project</th><th>CSI</th><th>Scope</th><th>Quantity</th><th>SAM-CTO</th><th>Mapping Status</th></tr></thead><tbody>{intakeRows.map((r,i)=><tr key={i}><td>{r.project_code}</td><td>{r.csi_code}</td><td>{r.payload?.boq_items?.[0]?.description||r.csi_title}</td><td>{quantityLabel(r.quantity_by_unit)}</td><td>{r.selected_samco_code||r.payload?.samco_candidates?.[0]?.master_code||"Review"}</td><td>{r.mapping_status.replaceAll("_"," ")}</td></tr>)}</tbody></table></div>}</section>
    <section className="panel" style={{marginTop:18}}><h2>Planning Activity Library</h2><table><thead><tr><th>SAM-CTO ID</th><th>Legacy</th><th>Activity</th><th>UOM</th><th>Productivity</th><th>Crew</th><th>Source</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td>{r.master_code}</td><td>{r.legacy_activity_code||"—"}</td><td>{r.title}</td><td>{r.uom||"—"}</td><td>{r.productivity??"—"}</td><td>{r.crew_type||"—"}</td><td>{r.source}</td></tr>)}</tbody></table></section>
    <section className="panel" style={{marginTop:18}}><h2>Supported Duration Methods</h2><p className="muted">PRODUCTIVITY · FIXED · CONTRACTUAL · LEAD_TIME · QUANTITY_RATIO · CALENDAR_PERIOD · MANUAL_CONTROLLED · ENGINEERING_REVIEW. Engineering and procurement chains remain governed by their own review/lead-time components rather than an LLM.</p></section>
  </main>
}
