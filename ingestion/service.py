from __future__ import annotations
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .extract import extract_pdf, try_ocr_pdf
from .classifier import detect_document_type
from .parsers import parse_boq, parse_specs, parse_contract
from .drawings import parse_pdf_drawing, parse_dxf
from .integrator import integrate_project
from .models import DocumentResult
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

@app.post("/")
@app.post("/api/intake")
async def intake(project_code: str=Form(...), project_name: str=Form(...), files: list[UploadFile]=File(...)):
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
    result=integrate_project(project_code.strip(),project_name.strip(),names,docs,boq,specs,contracts,drawings)
    persistence=persist_project(result)
    payload=result.model_dump(mode="json")
    payload["persistence"]=persistence
    return payload
