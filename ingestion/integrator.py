from __future__ import annotations
import re, uuid
from collections import defaultdict
from .models import BOQItem, SpecSection, ContractFinding, DrawingElement, ScopeEntry, IntegratedProject
from .csi import csi_title, load_mappings
from .samco_matcher import match_samco

def _slug(value:str)->str:
    s=re.sub(r"[^A-Za-z0-9]+","-",value or "").strip("-")
    return s[:50] or "item"

def _mapping(description:str, code:str):
    cfg=load_mappings().get("matching",{})
    accept=float(cfg.get("auto_accept_threshold",.78)); review=float(cfg.get("review_threshold",.48))
    candidates=match_samco(description,code) if description else []
    score=candidates[0].score if candidates else 0.0
    selected=candidates[0].master_code if candidates and score>=accept else None
    status="auto_mapped" if selected else ("review_required" if score>=review else "unmapped")
    return candidates,score,selected,status

def integrate_project(project_code: str, project_name: str, files: list[str], docs, boq: list[BOQItem], specs: list[SpecSection], contracts: list[ContractFinding], drawings: list[DrawingElement]) -> IntegratedProject:
    specs_by=defaultdict(list); drawings_by=defaultdict(list); boq_by=defaultdict(list)
    for x in specs: specs_by[x.csi_code].append(x)
    for x in drawings: drawings_by[x.csi_code].append(x)
    for x in boq: boq_by[x.csi_code].append(x)
    entries=[]; conflicts=[]; unmapped=[]; used_codes=set()

    # BOQ is the preferred atomic scope level: one item can become one planning/pricing activity.
    for idx,item in enumerate(boq,1):
        code=item.csi_code; used_codes.add(code)
        sp=specs_by.get(code,[]); dr=drawings_by.get(code,[])
        issues=[]
        if code!="00 00 00" and not dr: issues.append("BOQ item has no mapped drawing evidence")
        if code!="00 00 00" and not sp: issues.append("BOQ item has no mapped specification section")
        candidates,score,selected,status=_mapping(item.description,code)
        key=f"{code}:{item.item_code or idx}:{_slug(item.description)}"
        completeness={"has_boq":True,"has_spec":bool(sp),"has_drawing":bool(dr),"has_contract":False}
        entry=ScopeEntry(scope_key=key,csi_code=code,csi_title=csi_title(code),division=code[:2],boq_items=[item],spec_sections=sp,contract_references=[],drawing_elements=dr[:300],quantity_by_unit={item.unit:round(item.quantity,4)} if item.unit else {},completeness=completeness,conflicts=issues,samco_candidates=candidates,selected_samco_code=selected,mapping_status=status,mapping_confidence=score)
        entries.append(entry)
        if status=="unmapped" and code!="01 00 00": unmapped.append(key)
        for issue in issues: conflicts.append({"scope_key":key,"csi_code":code,"issue":issue})

    # Preserve drawing/spec scope not represented in the BOQ as a separate review item.
    for code in sorted(set(specs_by)|set(drawings_by)):
        if code in used_codes: continue
        sp=specs_by.get(code,[]); dr=drawings_by.get(code,[])
        desc=" | ".join(x.title for x in sp[:5]) or " | ".join(x.text for x in dr[:8])
        candidates,score,selected,status=_mapping(desc,code)
        issues=[]
        if dr and not boq_by.get(code): issues.append("Drawing scope has no mapped BOQ item")
        if sp and not boq_by.get(code): issues.append("Specification scope has no mapped BOQ item")
        key=f"{code}:orphan"
        entry=ScopeEntry(scope_key=key,csi_code=code,csi_title=csi_title(code),division=code[:2],boq_items=[],spec_sections=sp,contract_references=[],drawing_elements=dr[:300],quantity_by_unit={},completeness={"has_boq":False,"has_spec":bool(sp),"has_drawing":bool(dr),"has_contract":False},conflicts=issues,samco_candidates=candidates,selected_samco_code=selected,mapping_status=status,mapping_confidence=score)
        entries.append(entry)
        if status=="unmapped": unmapped.append(key)
        for issue in issues: conflicts.append({"scope_key":key,"csi_code":code,"issue":issue})

    # Contractual terms remain project-level evidence under Division 01.
    if contracts:
        key="01 00 00:contract"
        entries.append(ScopeEntry(scope_key=key,csi_code="01 00 00",csi_title=csi_title("01 00 00"),division="01",contract_references=contracts,completeness={"has_boq":False,"has_spec":False,"has_drawing":False,"has_contract":True},mapping_status="unmapped"))

    coverage={
        "scope_entries":len(entries),"with_boq":sum(bool(x.completeness.get("has_boq")) for x in entries),"with_spec":sum(bool(x.completeness.get("has_spec")) for x in entries),"with_drawing":sum(bool(x.completeness.get("has_drawing")) for x in entries),"with_contract":sum(bool(x.completeness.get("has_contract")) for x in entries),"fully_integrated":sum(bool(x.completeness.get("has_boq")) and bool(x.completeness.get("has_spec")) and bool(x.completeness.get("has_drawing")) for x in entries),"auto_mapped":sum(x.mapping_status=="auto_mapped" for x in entries),"review_required":sum(x.mapping_status=="review_required" for x in entries),"conflicts":len(conflicts)
    }
    return IntegratedProject(project_code=project_code,project_name=project_name,ingestion_id=str(uuid.uuid4()),source_files=files,documents=docs,scope_entries=entries,coverage=coverage,conflicts=conflicts,unmapped_scope=unmapped)
