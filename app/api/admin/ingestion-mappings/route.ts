import fs from "node:fs";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";
import { getPool, withTransaction } from "@/lib/db";

export const dynamic = "force-dynamic";
const mappingPath = () => path.join(process.cwd(), "data/control/document_mappings.json");
function authorized(req: NextRequest){const required=process.env.SAMCO_ADMIN_KEY;return Boolean(required && req.headers.get("x-admin-key")===required)}
export async function GET(){try{return NextResponse.json(JSON.parse(fs.readFileSync(mappingPath(),"utf8")))}catch{return NextResponse.json({error:"Mapping file unavailable"},{status:404})}}

function flatten(body:any){
  const rows:{type:string;match:string;mapped:string}[]=[];
  for(const [doc,words] of Object.entries(body.document_keywords||{})) for(const word of (words as any[])) rows.push({type:"document_keyword",match:String(word),mapped:String(doc)});
  for(const type of ["boq_section_to_csi","symbol_to_csi","keyword_to_csi"]){for(const [match,mapped] of Object.entries(body[type]||{})) rows.push({type,match,mapped:String(mapped)})}
  for(const [term,phrases] of Object.entries(body.contract_terms||{})) for(const phrase of (phrases as any[])) rows.push({type:"contract_term",match:String(phrase),mapped:String(term)});
  return rows;
}
export async function POST(req: NextRequest){
  if(!authorized(req)) return NextResponse.json({error:"Admin authentication required"},{status:401});
  try{
    const body=await req.json(); if(!body||typeof body!=="object") throw new Error("JSON object required");
    const required=["document_keywords","boq_section_to_csi","symbol_to_csi","keyword_to_csi","contract_terms","matching"]; for(const key of required) if(!(key in body)) throw new Error(`Missing ${key}`);
    let localSaved=false,dbSaved=false;
    if(process.env.SAMCO_ALLOW_LOCAL_FILE_WRITES==="true"){fs.writeFileSync(mappingPath(),JSON.stringify(body,null,2)+"\n","utf8");localSaved=true}
    if(getPool()){
      const rows=flatten(body); await withTransaction(async client=>{await client.query(`delete from public.document_mapping_rules`);for(const r of rows) await client.query(`insert into public.document_mapping_rules(rule_type,match_value,mapped_value,enabled,priority) values($1,$2,$3,true,100)`,[r.type,r.match,r.mapped]);}); dbSaved=true;
    }
    if(!localSaved&&!dbSaved) return NextResponse.json({error:"Neither local writes nor PostgreSQL mapping storage is available."},{status:503});
    return NextResponse.json({saved:true,local:localSaved,database:dbSaved,path:localSaved?"data/control/document_mappings.json":null});
  }catch(error){return NextResponse.json({error:error instanceof Error?error.message:String(error)},{status:400})}
}
