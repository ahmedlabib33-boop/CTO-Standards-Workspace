from __future__ import annotations
import json, os
from .models import IntegratedProject

try:
    import psycopg
except Exception:
    psycopg=None

def available() -> bool:
    return bool(psycopg and os.getenv("DATABASE_URL"))

def persist_project(result: IntegratedProject) -> dict:
    if not available(): return {"persisted":False,"mode":"memory_result","message":"DATABASE_URL/psycopg unavailable; structured result returned without persistence."}
    conn=psycopg.connect(os.environ["DATABASE_URL"])
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""insert into public.projects(project_code,project_name,status,source) values(%s,%s,'Intake',%s::jsonb)
                    on conflict(project_code) do update set project_name=excluded.project_name, updated_at=now()
                    returning id""",(result.project_code,result.project_name,json.dumps({"ingestion_id":result.ingestion_id})))
                project_id=cur.fetchone()[0]
                for d in result.documents:
                    cur.execute("""insert into public.project_documents(project_id,ingestion_id,filename,document_type,pages,char_count,extraction_mode,needs_ocr,status,metadata)
                        values(%s,%s,%s,%s,%s,%s,%s,%s,'processed',%s::jsonb)""",(project_id,result.ingestion_id,d.filename,d.document_type,d.pages,d.chars,d.extraction_mode,d.needs_ocr,json.dumps({"warnings":d.warnings})))
                    cur.execute("""insert into public.outbox_events(event_type,aggregate_type,aggregate_key,payload,actor_label)
                        values('document.processed','document',%s,%s::jsonb,'document-intake')""",(d.filename,json.dumps({"project_id":str(project_id),"project_code":result.project_code,"ingestion_id":result.ingestion_id,"filename":d.filename,"document_type":d.document_type,"needs_ocr":d.needs_ocr})))
                for e in result.scope_entries:
                    cur.execute("""insert into public.project_scope_entries(project_id,ingestion_id,scope_key,csi_code,csi_title,division,selected_samco_code,mapping_status,mapping_confidence,quantity_by_unit,completeness,conflicts,payload)
                        values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)
                        on conflict(project_id,ingestion_id,scope_key) do update set selected_samco_code=excluded.selected_samco_code,mapping_status=excluded.mapping_status,mapping_confidence=excluded.mapping_confidence,quantity_by_unit=excluded.quantity_by_unit,completeness=excluded.completeness,conflicts=excluded.conflicts,payload=excluded.payload,updated_at=now()""",
                        (project_id,result.ingestion_id,e.scope_key,e.csi_code,e.csi_title,e.division,e.selected_samco_code,e.mapping_status,e.mapping_confidence,json.dumps(e.quantity_by_unit),json.dumps(e.completeness),json.dumps(e.conflicts),json.dumps(e.model_dump(mode="json"))))
                    if e.mapping_status != "unmapped":
                        cur.execute("""insert into public.outbox_events(event_type,aggregate_type,aggregate_key,payload,actor_label)
                            values('scope.mapped','scope',%s,%s::jsonb,'document-intake')""",(e.scope_key,json.dumps({"project_id":str(project_id),"project_code":result.project_code,"ingestion_id":result.ingestion_id,"scope_key":e.scope_key,"mapping_status":e.mapping_status,"selected_samco_code":e.selected_samco_code,"confidence":e.mapping_confidence,"candidates":[x.model_dump() for x in e.samco_candidates]})))
                for conflict in result.conflicts:
                    cur.execute("""insert into public.outbox_events(event_type,aggregate_type,aggregate_key,payload,actor_label)
                        values('scope.conflict.detected','scope',%s,%s::jsonb,'document-intake')""",(conflict.get("scope_key") or conflict.get("csi_code") or result.project_code,json.dumps({"project_id":str(project_id),"project_code":result.project_code,"ingestion_id":result.ingestion_id,**conflict})))
                cur.execute("""insert into public.outbox_events(event_type,aggregate_type,aggregate_key,payload,actor_label)
                    values('project.scope.ready','project',%s,%s::jsonb,'document-intake')""",(result.project_code,json.dumps({"project_id":str(project_id),"project_code":result.project_code,"ingestion_id":result.ingestion_id,"coverage":result.coverage})))
        return {"persisted":True,"mode":"postgres_plus_outbox","project_id":str(project_id)}
    finally:
        conn.close()
