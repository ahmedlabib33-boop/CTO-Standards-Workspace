import { NextRequest, NextResponse } from "next/server";
import { getPool, withTransaction } from "@/lib/db";
export const dynamic="force-dynamic";
function authorized(req:NextRequest){const key=process.env.SAMCO_ADMIN_KEY;return Boolean(key&&req.headers.get("x-admin-key")===key)}
export async function POST(req:NextRequest){
  if(!authorized(req)) return NextResponse.json({error:"Admin authentication required"},{status:401});
  if(!getPool()) return NextResponse.json({error:"PostgreSQL is not configured"},{status:503});
  try{
    const body=await req.json(); const id=String(body.id||""); const action=String(body.action||"approve"); const samco=body.samco_code?String(body.samco_code):null;
    if(!id) throw new Error("scope entry id is required"); if(action==="approve"&&!samco) throw new Error("SAM-CTO code is required for approval");
    const out=await withTransaction(async client=>{
      const before=await client.query(`select * from public.project_scope_entries where id=$1 for update`,[id]); if(!before.rowCount) throw new Error("Scope entry not found");
      const status=action==="reject"?"rejected":"approved";
      await client.query(`update public.project_scope_entries set selected_samco_code=$2,mapping_status=$3,mapping_confidence=case when $3='approved' then 1 else mapping_confidence end,reviewed_at=now(),updated_at=now() where id=$1`,[id,action==="reject"?null:samco,status]);
      await client.query(`insert into public.scope_review_actions(scope_entry_id,action,before_value,after_value,note) values($1,$2,$3::jsonb,$4::jsonb,$5)`,[id,action==="reject"?"reject_mapping":"approve_mapping",JSON.stringify(before.rows[0]),JSON.stringify({selected_samco_code:samco,mapping_status:status}),body.note||null]);
      await client.query(`insert into public.outbox_events(event_type,aggregate_type,aggregate_key,payload,actor_label) values('scope.mapped','scope',$1,$2::jsonb,'admin-review')`,[id,JSON.stringify({scope_entry_id:id,selected_samco_code:samco,mapping_status:status})]);
      return {id,status,samco_code:action==="reject"?null:samco};
    });
    return NextResponse.json({saved:true,...out});
  }catch(error){return NextResponse.json({error:error instanceof Error?error.message:String(error)},{status:400})}
}
