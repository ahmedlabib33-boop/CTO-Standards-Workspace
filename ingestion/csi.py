from __future__ import annotations
import json, os, re, time
from pathlib import Path
from typing import Any

CSI_DIVISIONS = {
    "00":"Procurement and Contracting Requirements","01":"General Requirements","02":"Existing Conditions",
    "03":"Concrete","04":"Masonry","05":"Metals","06":"Wood, Plastics, and Composites",
    "07":"Thermal and Moisture Protection","08":"Openings","09":"Finishes","10":"Specialties",
    "11":"Equipment","12":"Furnishings","13":"Special Construction","14":"Conveying Equipment",
    "21":"Fire Suppression","22":"Plumbing","23":"Heating, Ventilating, and Air Conditioning",
    "25":"Integrated Automation","26":"Electrical","27":"Communications","28":"Electronic Safety and Security",
    "31":"Earthwork","32":"Exterior Improvements","33":"Utilities","34":"Transportation",
    "35":"Waterway and Marine Construction","40":"Process Integration","41":"Material Processing and Handling Equipment",
    "42":"Process Heating, Cooling, and Drying Equipment","43":"Process Gas and Liquid Handling, Purification, and Storage Equipment",
    "44":"Pollution and Waste Control Equipment","45":"Industry-Specific Manufacturing Equipment","46":"Water and Wastewater Equipment",
    "48":"Electrical Power Generation"
}
_CACHE: tuple[float,dict[str,Any]]|None=None

def _root() -> Path: return Path(__file__).resolve().parents[1]

def _json_baseline() -> dict[str,Any]:
    path=_root()/"data"/"control"/"document_mappings.json"
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {"document_keywords":{},"boq_section_to_csi":{},"symbol_to_csi":{},"keyword_to_csi":{},"contract_terms":{},"matching":{},"samco_synonyms":{}}

def _merge_db_rules(base:dict[str,Any])->dict[str,Any]:
    url=os.getenv("DATABASE_URL","")
    if not url: return base
    try:
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("select rule_type,match_value,mapped_value from public.document_mapping_rules where enabled=true order by priority,id")
                rows=cur.fetchall()
        if not rows: return base
        out=json.loads(json.dumps(base))
        for typ,match,mapped in rows:
            if typ=="document_keyword": out.setdefault("document_keywords",{}).setdefault(mapped,[]).append(match)
            elif typ in {"boq_section_to_csi","symbol_to_csi","keyword_to_csi"}: out.setdefault(typ,{})[match]=mapped
            elif typ=="contract_term": out.setdefault("contract_terms",{}).setdefault(mapped,[]).append(match)
        return out
    except Exception:
        return base

def load_mappings() -> dict[str, Any]:
    global _CACHE
    now=time.time()
    if _CACHE and now-_CACHE[0]<30: return _CACHE[1]
    value=_merge_db_rules(_json_baseline())
    _CACHE=(now,value)
    return value

def normalize_csi(raw: str | None) -> str:
    if not raw: return "00 00 00"
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 6: return f"{digits[:2]} {digits[2:4]} {digits[4:6]}"
    if len(digits) == 5: return f"{digits[:2]} {digits[2:4]} {digits[4]}0"
    if len(digits) == 2: return f"{digits} 00 00"
    return "00 00 00"

def csi_title(code: str) -> str: return CSI_DIVISIONS.get((code or "00")[:2], "Unclassified")

def infer_csi(text: str, section: str = "", mappings: dict[str, Any] | None = None) -> tuple[str, str]:
    mappings = mappings or load_mappings(); hay = f"{section} {text}".lower()
    m = re.search(r"\b(\d{2})\s*[-.]?\s*(\d{2})\s*[-.]?\s*(\d{2})\b", hay)
    if m: return f"{m.group(1)} {m.group(2)} {m.group(3)}", "explicit_code"
    # Description-specific evidence wins over a broad BOQ section heading.
    for key, code in mappings.get("keyword_to_csi", {}).items():
        if str(key).lower() in (text or "").lower(): return normalize_csi(str(code)), f"keyword:{key}"
    for key, code in mappings.get("symbol_to_csi", {}).items():
        if str(key).lower() in (text or "").lower(): return normalize_csi(str(code)), f"symbol:{key}"
    for key, code in mappings.get("boq_section_to_csi", {}).items():
        if str(key).lower() in section.lower(): return normalize_csi(str(code)), f"section:{key}"
    return "00 00 00", "unclassified"
