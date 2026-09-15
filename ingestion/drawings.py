from __future__ import annotations
import io, re
from .models import DrawingElement, Evidence
from .csi import infer_csi
from .extract import extract_pdf

try:
    import ezdxf
except Exception:
    ezdxf = None

def parse_pdf_drawing(filename: str, data: bytes) -> tuple[list[DrawingElement], bool]:
    ext = extract_pdf(data)
    out: list[DrawingElement] = []
    for pg in ext.pages:
        # Text spans preserve evidence and location better than flattened lines.
        for block in pg.blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt=(span.get("text") or "").strip()
                    if len(txt)<2: continue
                    code, reason=infer_csi(txt)
                    if code=="00 00 00": continue
                    out.append(DrawingElement(element_id=f"{filename}:p{pg.page}:{len(out)+1}",text=txt[:500],csi_code=code,
                        geometry={"bbox":span.get("bbox"),"mapping_reason":reason},confidence=.82,
                        evidence=[Evidence(filename=filename,page=pg.page,sheet=filename.rsplit('.',1)[0],excerpt=txt[:700],source_type="drawing")]))
    return out, ext.needs_ocr

def parse_dxf(filename: str, data: bytes) -> list[DrawingElement]:
    if ezdxf is None: return []
    try:
        # Most DXF files are ASCII. Binary DXF is intentionally rejected rather than guessed.
        doc=ezdxf.read(io.StringIO(data.decode("utf-8",errors="ignore")))
        msp=doc.modelspace()
    except Exception:
        return []
    out=[]
    for ent in msp:
        try:
            typ=ent.dxftype()
            text=""
            geom={"entity":typ}
            if typ=="INSERT":
                text=str(ent.dxf.name or "")
                geom["insert"]=[float(ent.dxf.insert.x),float(ent.dxf.insert.y)]
            elif typ=="TEXT":
                text=str(ent.dxf.text or "")
                geom["insert"]=[float(ent.dxf.insert.x),float(ent.dxf.insert.y)]
            elif typ=="MTEXT":
                text=str(ent.text or "")
            else:
                continue
            code, reason=infer_csi(text)
            if code=="00 00 00": continue
            geom["mapping_reason"]=reason
            out.append(DrawingElement(element_id=str(getattr(ent.dxf,"handle","") or f"{filename}:{len(out)+1}"),text=text[:500],element_type=typ,csi_code=code,geometry=geom,confidence=.88,
                evidence=[Evidence(filename=filename,sheet=filename.rsplit('.',1)[0],excerpt=text[:700],source_type="drawing")]))
        except Exception:
            continue
    return out
