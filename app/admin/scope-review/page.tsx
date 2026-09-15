import { getLatestProjectScope } from "@/lib/project-scope";
import ScopeReviewClient from "./ScopeReviewClient";
export const dynamic="force-dynamic";
export default async function ScopeReviewPage(){const rows=(await getLatestProjectScope(150)).filter(r=>r.mapping_status==="review_required"||r.mapping_status==="unmapped");return <main className="page"><section className="panel"><span className="tag">Admin / Governed Review</span><h1 style={{fontSize:48}}>SAM-CTO Scope Mapping Review</h1><p className="lead">The intake engine proposes mappings; this page makes the human-controlled decision explicit. Approval writes the project mapping, records the review action and emits a durable <code>scope.mapped</code> event.</p></section><ScopeReviewClient rows={rows}/></main>}
