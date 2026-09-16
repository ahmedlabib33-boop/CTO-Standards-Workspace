from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from .extract import extract_pdf, try_ocr_pdf
from .classifier import detect_document_type
from .parsers import parse_boq, parse_specs, parse_contract
from .drawings import parse_pdf_drawing, parse_dxf
from .integrator import integrate_project
from .models import DocumentResult, IntegratedProject
from .persistence import persist_project

MAX_BYTES=int(os.getenv("SAMCO_INGESTION_MAX_BYTES","50000000"))
MAX_FILES=int(os.getenv("SAMCO_INGESTION_MAX_FILES","40"))
ALLOWED={".pdf",".dxf"}

app=FastAPI(title="SAMCO Project Intake Engine",version="0.4.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],allow_credentials=True,allow_methods=["GET","POST"],allow_headers=["*"])

@app.get("/")
@app.get("/api/intake/health")
def health():
    return {"ok":True,"engine":"SAMCO Project Intake & Scope Integration","version":"0.4.0","core_dependency":False,"supported":["pdf","dxf"],"ocr":"optional_last_resort"}

async def process_upload_batch(project_code: str, project_name: str, files) -> IntegratedProject:
    if not project_code.strip() or not project_name.strip(): raise HTTPException(400,"project_code and project_name are required")
    if len(files)>MAX_FILES: raise HTTPException(413,f"maximum {MAX_FILES} files per batch")
    boq=[]; specs=[]; contracts=[]; drawings=[]; docs=[]; names=[]
    for f in files:
        name=os.path.basename(f.filename or "unnamed")
        ext=os.path.splitext(name)[1].lower()
        if ext not in ALLOWED: raise HTTPException(415,f"unsupported file type: {ext}")
        data=await f.read()
        if not data: continue
        if len(data)>MAX_BYTES: raise HTTPException(413,f"{name} exceeds file limit")
        names.append(name)
        warnings=[]
        if ext==".dxf":
            els=parse_dxf(name,data); drawings.extend(els)
            docs.append(DocumentResult(filename=name,document_type="drawing",pages=0,chars=0,extraction_mode="dxf",warnings=[]))
            continue
        try:
            extracted=extract_pdf(data)
        except Exception as exc:
            docs.append(DocumentResult(filename=name,document_type="unknown",warnings=[f"PDF extraction failed: {exc}"]))
            continue
        if extracted.needs_ocr:
            ocr=try_ocr_pdf(data)
            if ocr and ocr.chars>extracted.chars:
                extracted=ocr
            else:
                warnings.append("Low-text PDF: OCR is not available in this runtime; vector/text evidence may be incomplete.")
        full="\n".join(p.text for p in extracted.pages)
        kind,confidence=detect_document_type(name,full)
        if kind=="boq": boq.extend(parse_boq(extracted,name))
        elif kind=="spec": specs.extend(parse_specs(extracted,name))
        elif kind=="contract": contracts.extend(parse_contract(extracted,name))
        elif kind=="drawing":
            els,needs=parse_pdf_drawing(name,data); drawings.extend(els)
            if needs and not els: warnings.append("Drawing has little native text; OCR/visual review may be required.")
        else:
            # Unknown PDFs are still inspected as drawings/specs without pretending confidence.
            maybe_specs=parse_specs(extracted,name)
            if maybe_specs: specs.extend(maybe_specs); kind="spec"
            else:
                els,needs=parse_pdf_drawing(name,data); drawings.extend(els)
                if els: kind="drawing"
        docs.append(DocumentResult(filename=name,document_type=kind,pages=len(extracted.pages),chars=extracted.chars,extraction_mode=extracted.mode,needs_ocr=extracted.needs_ocr,warnings=warnings+[f"classification_confidence={confidence:.2f}"]))
    return integrate_project(project_code.strip(),project_name.strip(),names,docs,boq,specs,contracts,drawings)


async def finalize_integrated_result(request: Request):
    try:
        body=await request.json()
    except Exception as exc:
        raise HTTPException(400,"finalize request must contain JSON") from exc
    if body.get("operation") != "finalize":
        raise HTTPException(400,"JSON intake requests must use operation=finalize")
    try:
        result=IntegratedProject.model_validate(body.get("result"))
    except Exception as exc:
        raise HTTPException(422,f"invalid integrated intake result: {exc}") from exc
    payload=result.model_dump(mode="json")
    payload["persistence"]=persist_project(result)
    return payload


@app.post("/")
@app.post("/api/intake")
async def intake(request: Request):
    content_type=request.headers.get("content-type","").lower()
    if content_type.startswith("application/json"):
        return await finalize_integrated_result(request)

    form=await request.form()
    project_code=str(form.get("project_code") or "")
    project_name=str(form.get("project_name") or "")
    files=list(form.getlist("files"))
    if not files or any(not hasattr(file,"read") for file in files):
        raise HTTPException(400,"at least one PDF or DXF file is required")

    result=await process_upload_batch(project_code,project_name,files)
    payload=result.model_dump(mode="json")
    # Browser batch uploads must not create one incomplete persisted project per
    # document. The browser merges all evidence, then sends one finalize request.
    if str(form.get("batch_mode") or "") == "partial":
        payload["persistence"]={"persisted":False,"mode":"batch_partial","message":"Document processed; awaiting integrated batch finalization."}
    else:
        payload["persistence"]=persist_project(result)
    return payload
