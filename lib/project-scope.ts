import { dbQuery, getPool } from "@/lib/db";

export type ScopeRow={
  id:string; project_code:string; project_name:string; scope_key:string; csi_code:string; csi_title:string; selected_samco_code:string|null;
  mapping_status:string; mapping_confidence:number; quantity_by_unit:Record<string,number>; completeness:Record<string,boolean>; conflicts:string[]; payload:any;
};
export async function getLatestProjectScope(limit=80):Promise<ScopeRow[]>{
  if(!getPool()) return [];
  try{
    const result=await dbQuery<any>(`select s.id,p.project_code,p.project_name,s.scope_key,s.csi_code,s.csi_title,s.selected_samco_code,s.mapping_status,s.mapping_confidence,s.quantity_by_unit,s.completeness,s.conflicts,s.payload
      from public.project_scope_entries s join public.projects p on p.id=s.project_id
      order by s.updated_at desc limit $1`,[limit]);
    return result.rows as ScopeRow[];
  }catch{return []}
}
export function quantityLabel(q:Record<string,number>|null|undefined){
  if(!q) return "—"; const parts=Object.entries(q).map(([u,v])=>`${v} ${u}`); return parts.length?parts.join(" · "):"—";
}
