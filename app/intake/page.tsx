import DocumentIntake from "./DocumentIntake";
export const dynamic="force-dynamic";
export default function IntakePage(){return <main className="page">
  <section className="panel intake-hero"><span className="tag">Unified Intake & Scope Intelligence</span><h1>Documents become <span className="accent">controlled project data.</span></h1><p className="lead">Upload BOQ, specifications, contracts and drawings once. The intake engine classifies and extracts each source, maps scope to CSI, proposes SAM-CTO activities, detects cross-document gaps, and feeds one governed scope register to every department.</p>
    <div className="flow"><span className="node">Documents</span><span className="arrow">→</span><span className="node">Classify / Extract</span><span className="arrow">→</span><span className="node">CSI</span><span className="arrow">→</span><span className="node">SAM-CTO</span><span className="arrow">→</span><span className="node">Technical · Tender · Planning · Cost</span></div>
  </section>
  <DocumentIntake/>
</main>}
