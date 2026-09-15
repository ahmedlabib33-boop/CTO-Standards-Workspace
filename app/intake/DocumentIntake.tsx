"use client";
import { useMemo, useState } from "react";

type IntakeResult = any;
function endpoint(){ return process.env.NEXT_PUBLIC_INGESTION_API_URL || "/api/intake"; }

export default function DocumentIntake(){
  const [projectCode,setProjectCode]=useState("TENDER-001");
  const [projectName,setProjectName]=useState("New Tender Project");
  const [files,setFiles]=useState<File[]>([]);
  const [result,setResult]=useState<IntakeResult|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const coverage=result?.coverage||{};
  const entries=result?.scope_entries||[];
  const stats=useMemo(()=>({
    docs:result?.documents?.length||0,scope:coverage.scope_entries||0,mapped:coverage.auto_mapped||0,review:coverage.review_required||0,conflicts:coverage.conflicts||0
  }),[result,coverage]);
  async function run(){
    if(!files.length){setError("Please select at least one PDF or DXF file.");return;}
    setBusy(true);setError("");setResult(null);
    try{
      const form=new FormData();form.append("project_code",projectCode);form.append("project_name",projectName);files.forEach(f=>form.append("files",f));
      const res=await fetch(endpoint(),{method:"POST",body:form});
      const text=await res.text();let out:any;try{out=JSON.parse(text)}catch{throw new Error(text||`HTTP ${res.status}`)}
      if(!res.ok) throw new Error(out.detail||out.error||`HTTP ${res.status}`);
      setResult(out);
    }catch(e:any){setError(`${e.message}. Local Next.js development requires the Python intake service (see README).`)}finally{setBusy(false)}
  }
  return <>
    <section className="panel intake-uploader">
      <div className="section-title-row"><div><span className="tag">Project Front Door</span><h2 style={{marginTop:10}}>Upload tender / project information once</h2></div><span className="engine-badge">CSI → SAM-CTO</span></div>
      <div className="intake-fields"><label>Project Code<input className="input" value={projectCode} onChange={e=>setProjectCode(e.target.value)}/></label><label>Project Name<input className="input" value={projectName} onChange={e=>setProjectName(e.target.value)}/></label></div>
      <label className="dropzone"><input type="file" accept=".pdf,.dxf" multiple onChange={e=>setFiles(Array.from(e.target.files||[]))}/><b>{files.length?`${files.length} file(s) selected`:`Choose PDF / DXF files`}</b><span>{files.length?files.map(f=>f.name).join(" · "):"BOQ · Specifications · Contract / ITT · Drawings"}</span></label>
      <div className="button-row"><button className="button" disabled={busy} onClick={run}>{busy?"Extracting & integrating…":"Build Controlled Project Scope"}</button>{files.length>0&&<button className="button secondary" onClick={()=>{setFiles([]);setResult(null);setError("")}}>Clear</button>}</div>
      {error&&<div className="alert error">{error}</div>}
    </section>
    {result&&<>
      <section className="grid intake-metrics"><div className="metric">Documents<b>{stats.docs}</b></div><div className="metric">Scope Entries<b>{stats.scope}</b></div><div className="metric">Auto-Mapped<b>{stats.mapped}</b></div><div className="metric">Conflicts<b>{stats.conflicts}</b></div></section>
      <section className="panel" style={{marginTop:18}}><div className="section-title-row"><div><h2>Controlled Scope Register</h2><p className="muted">Same extracted scope becomes the source for Technical, Tender, Planning and Cost Control. Low-confidence mappings are held for review rather than silently accepted.</p></div><span className={`status-pill ${result.persistence?.persisted?"ok":"warn"}`}>{result.persistence?.persisted?"POSTGRES + OUTBOX":"RESULT ONLY / SAFE"}</span></div>
        <div className="table-wrap"><table><thead><tr><th>CSI</th><th>Scope</th><th>Qty</th><th>BOQ</th><th>Spec</th><th>Drawing</th><th>SAM-CTO Mapping</th><th>Confidence</th><th>Status</th><th>Issues</th></tr></thead><tbody>
          {entries.map((e:any)=><tr key={e.scope_key}><td><b>{e.csi_code}</b><br/><span className="tiny">{e.csi_title}</span></td><td>{e.boq_items?.[0]?.description||e.spec_sections?.[0]?.title||e.drawing_elements?.[0]?.text||"General / contractual"}</td><td>{Object.entries(e.quantity_by_unit||{}).map(([u,q])=><div key={u}>{String(q)} {u}</div>)}</td><td>{e.completeness?.has_boq?"✓":"—"}</td><td>{e.completeness?.has_spec?"✓":"—"}</td><td>{e.completeness?.has_drawing?"✓":"—"}</td><td>{e.selected_samco_code||e.samco_candidates?.[0]?.master_code||"Unmapped"}<br/><span className="tiny">{e.samco_candidates?.[0]?.title||""}</span></td><td>{Math.round((e.mapping_confidence||0)*100)}%</td><td><span className={`status-pill ${e.mapping_status==="auto_mapped"?"ok":e.mapping_status==="review_required"?"warn":""}`}>{String(e.mapping_status).replaceAll("_"," ")}</span></td><td>{e.conflicts?.length?<span className="conflict-count">{e.conflicts.length}</span>:"—"}</td></tr>)}
        </tbody></table></div>
      </section>
      <section className="hero" style={{marginTop:18}}><div className="panel"><h2>Coverage</h2><div className="coverage-bars">{[["BOQ",coverage.with_boq],["Specifications",coverage.with_spec],["Drawings",coverage.with_drawing],["Fully Integrated",coverage.fully_integrated]].map(([label,val]:any)=><div className="coverage-row" key={label}><span>{label}</span><b>{val||0} / {coverage.scope_entries||0}</b></div>)}</div></div><div className="panel"><h2>Review Queue</h2><p><b>{coverage.review_required||0}</b> mappings need human approval.</p><p><b>{result.unmapped_scope?.length||0}</b> CSI scopes have no credible SAM-CTO match.</p><p><b>{coverage.conflicts||0}</b> cross-document scope conflicts detected.</p></div></section>
      {result.conflicts?.length>0&&<section className="panel" style={{marginTop:18}}><h2>Cross-Document Conflicts</h2>{result.conflicts.map((c:any,i:number)=><div className="conflict-line" key={i}><b>{c.csi_code}</b><span>{c.issue}</span></div>)}</section>}
      <section className="panel" style={{marginTop:18}}><h2>Document Processing Audit</h2><div className="doc-cards">{result.documents?.map((d:any)=><div className="doc-card" key={d.filename}><b>{d.filename}</b><span>{d.document_type} · {d.extraction_mode}</span><small>{d.pages} pages · {d.chars} chars {d.needs_ocr?"· OCR/visual review may be needed":""}</small></div>)}</div></section>
    </>}
  </>
}
