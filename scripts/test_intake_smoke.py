"""Self-contained intake smoke test. Creates synthetic PDFs in memory; writes no project data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fitz
from fastapi.testclient import TestClient
from ingestion.service import app

def make_pdf(lines):
    doc=fitz.open(); page=doc.new_page(); y=72
    for line in lines:
        page.insert_text((72,y),line,fontsize=10); y+=16
    out=doc.tobytes(); doc.close(); return out

def main():
    boq=make_pdf(["BILL OF QUANTITIES","Section 03 - Concrete Works","1 Reinforced concrete raft m3 120","2 Reinforced concrete walls m3 85"])
    spec=make_pdf(["DIVISION 03 CONCRETE","SECTION 03 30 00 - CAST-IN-PLACE CONCRETE","PART 1 - GENERAL"])
    drawing=make_pdf(["DRAWING NO STR-101","REINFORCED CONCRETE RAFT"])
    client=TestClient(app)
    response=client.post("/api/intake",data={"project_code":"SMOKE-001","project_name":"Smoke Test"},files=[
        ("files",("Smoke_BOQ.pdf",boq,"application/pdf")),("files",("Smoke_Specification.pdf",spec,"application/pdf")),("files",("STR_Drawing.pdf",drawing,"application/pdf"))])
    assert response.status_code==200,response.text
    payload=response.json(); assert payload["coverage"]["with_boq"]>=2; assert payload["coverage"]["with_spec"]>=1
    assert any(x["samco_candidates"] for x in payload["scope_entries"] if x["boq_items"])
    print("INTAKE_SMOKE_OK",payload["coverage"])
if __name__=="__main__": main()
