from __future__ import annotations
import re
from collections import defaultdict
from .models import BOQItem, SpecSection, ContractFinding, Evidence
from .csi import infer_csi, normalize_csi, load_mappings
from .extract import ExtractedPDF

UNIT_RX = r"(?:m3|m³|cum|m2|m²|sqm|lm|lin\.?m|m|kg|ton|tonne|t|nr|no\.?|nos|ea|each|ls|lot|set|day|hr|hour)"
NUM_RX = r"[-+]?\d[\d,]*(?:\.\d+)?"
CSI_HEADER_RE = re.compile(r"(?:SECTION\s+)?(\d{2}\s*\d{2}\s*\d{2}|\d{5,6})\s*[-–:]?\s*(.{0,140})", re.I)

def _num(s: str) -> float | None:
    try: return float(s.replace(",", ""))
    except Exception: return None

def _find_header_index(headers: list[str], names: tuple[str, ...]) -> int | None:
    for i,h in enumerate(headers):
        low=(h or "").lower().replace("\n"," ").strip()
        if any(n in low for n in names): return i
    return None

def _parse_boq_tables(extracted: ExtractedPDF, filename: str) -> list[BOQItem]:
    out: list[BOQItem] = []
    for pg in extracted.pages:
        for table in pg.tables:
            if len(table)<2: continue
            header_row = 0
            # Try first three rows because exported BOQs often have multi-row headings.
            for candidate in range(min(3,len(table))):
                text=" ".join(table[candidate]).lower()
                if "description" in text and ("qty" in text or "quantity" in text or "unit" in text):
                    header_row=candidate; break
            headers=[str(x or "") for x in table[header_row]]
            d_i=_find_header_index(headers,("description","item description","work description"))
            q_i=_find_header_index(headers,("quantity","qty"))
            u_i=_find_header_index(headers,("unit","uom"))
            c_i=_find_header_index(headers,("item no","item code","code","item"))
            r_i=_find_header_index(headers,("unit rate","rate","price"))
            a_i=_find_header_index(headers,("amount","total"))
            if d_i is None or q_i is None: continue
            current_section=""
            for row in table[header_row+1:]:
                if d_i>=len(row) or q_i>=len(row): continue
                desc=re.sub(r"\s+"," ",str(row[d_i] or "")).strip()
                if not desc: continue
                qty=_num(str(row[q_i] or ""))
                if qty is None:
                    if len(desc)<140 and any(k in desc.lower() for k in ("section","bill","division")): current_section=desc
                    continue
                unit=str(row[u_i] or "").strip() if u_i is not None and u_i<len(row) else ""
                item_code=str(row[c_i] or "").strip() if c_i is not None and c_i<len(row) else ""
                rate=_num(str(row[r_i] or "")) if r_i is not None and r_i<len(row) else None
                amount=_num(str(row[a_i] or "")) if a_i is not None and a_i<len(row) else None
                csi,_=infer_csi(desc,current_section)
                out.append(BOQItem(item_code=item_code,description=desc[:500],unit=unit,quantity=qty,unit_rate=rate,amount=amount,csi_code=csi,section=current_section[:250],evidence=[Evidence(filename=filename,page=pg.page,excerpt=" | ".join(str(x or "") for x in row)[:900],source_type="boq_table")]))
    return out

def parse_boq(extracted: ExtractedPDF, filename: str) -> list[BOQItem]:
    table_items=_parse_boq_tables(extracted,filename)
    # Table extraction is preferred because it preserves item/quantity/unit alignment.
    if table_items: return table_items
    items: list[BOQItem] = []
    current_section = ""
    unit_qty = re.compile(rf"\b({UNIT_RX})\b\s*({NUM_RX})", re.I)
    qty_unit = re.compile(rf"({NUM_RX})\s*\b({UNIT_RX})\b", re.I)
    for pg in extracted.pages:
        lines = [re.sub(r"\s+", " ", x).strip() for x in pg.text.splitlines() if x.strip()]
        for line in lines:
            if len(line) < 3: continue
            if re.match(r"^(section|bill|division)\b", line, re.I) and len(line) < 180:
                current_section = line
            mq = unit_qty.search(line); reverse=False
            if not mq: mq=qty_unit.search(line); reverse=True
            if not mq: continue
            if reverse: qty,unit=_num(mq.group(1)),mq.group(2)
            else: unit,qty=mq.group(1),_num(mq.group(2))
            if qty is None or qty < 0: continue
            desc=(line[:mq.start()]+" "+line[mq.end():]).strip(" -|:")
            if len(desc)<4: continue
            csi,_=infer_csi(desc,current_section)
            item_code=""
            cm=re.match(r"^([A-Za-z0-9.\-/]{1,20})\s+",desc)
            if cm and any(ch.isdigit() for ch in cm.group(1)):
                item_code=cm.group(1)
                desc=desc[cm.end():].strip() or desc
                csi,_=infer_csi(desc,current_section)
            items.append(BOQItem(item_code=item_code,description=desc[:500],unit=unit,quantity=qty,csi_code=csi,section=current_section[:250],evidence=[Evidence(filename=filename,page=pg.page,excerpt=line[:700],source_type="boq_text")]))
    return items

def parse_specs(extracted: ExtractedPDF, filename: str) -> list[SpecSection]:
    found: dict[str, SpecSection] = {}
    for pg in extracted.pages:
        lines = pg.text.splitlines()
        for i, raw in enumerate(lines):
            line = re.sub(r"\s+", " ", raw).strip()
            m = CSI_HEADER_RE.search(line)
            if not m: continue
            code = normalize_csi(m.group(1))
            if code == "00 00 00": continue
            title = (m.group(2) or "").strip(" -–:") or (lines[i+1].strip() if i+1 < len(lines) else "Untitled")
            body = "\n".join(x.strip() for x in lines[i+1:i+22] if x.strip())[:1800]
            if code not in found:
                found[code] = SpecSection(csi_code=code,title=title[:220],division=code[:2],body_preview=body,
                    evidence=[Evidence(filename=filename,page=pg.page,excerpt=line[:700],source_type="spec")])
    return list(found.values())

def parse_contract(extracted: ExtractedPDF, filename: str) -> list[ContractFinding]:
    maps = load_mappings()
    findings: list[ContractFinding] = []
    seen: set[tuple[str,int]] = set()
    for pg in extracted.pages:
        low = pg.text.lower()
        lines = [re.sub(r"\s+", " ", x).strip() for x in pg.text.splitlines() if x.strip()]
        for term, phrases in maps.get("contract_terms", {}).items():
            if not any(str(p).lower() in low for p in phrases): continue
            for line in lines:
                if any(str(p).lower() in line.lower() for p in phrases):
                    key=(term,pg.page)
                    if key in seen: break
                    seen.add(key)
                    findings.append(ContractFinding(term=term, excerpt=line[:900], evidence=[Evidence(filename=filename,page=pg.page,excerpt=line[:900],source_type="contract")]))
                    break
    return findings

def aggregate_quantities(items: list[BOQItem]) -> dict[str, float]:
    totals=defaultdict(float)
    for x in items: totals[x.unit]+=x.quantity
    return {k:round(v,4) for k,v in totals.items()}
