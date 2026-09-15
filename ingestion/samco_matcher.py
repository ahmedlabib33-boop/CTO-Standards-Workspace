from __future__ import annotations
import json, re
from difflib import SequenceMatcher
from pathlib import Path
from .models import SamcoCandidate
from .csi import load_mappings

STOP={"work","works","including","complete","all","for","and","the","of","to","in","with","supply","install","installation"}

def _tokens(s: str, synonyms: dict | None=None) -> set[str]:
    base={x for x in re.findall(r"[a-z0-9]+",(s or "").lower()) if len(x)>1 and x not in STOP}
    if synonyms:
        for token in list(base):
            for alt in synonyms.get(token,[]):
                base.add(str(alt).lower())
    return base

def _load_activities() -> list[dict]:
    root=Path(__file__).resolve().parents[1]
    for name in ["activity_master.json","activity-master.json"]:
        p=root/"data"/"generated"/"master"/name
        try:
            val=json.loads(p.read_text(encoding="utf-8"))
            if isinstance(val,list): return val
        except Exception: pass
    return []

def match_samco(description: str, csi_code: str, limit: int | None=None) -> list[SamcoCandidate]:
    cfg=load_mappings().get("matching",{})
    limit=int(limit or cfg.get("max_candidates",3))
    mappings=load_mappings()
    synonyms=mappings.get("samco_synonyms",{})
    qtok=_tokens(description,synonyms)
    div=(csi_code or "00")[:2]
    scored=[]
    for row in _load_activities():
        title=str(row.get("Activity description") or row.get("Column_2") or row.get("title") or "")
        if not title: continue
        ttok=_tokens(title,synonyms)
        inter=len(qtok & ttok); union=max(len(qtok | ttok),1)
        jacc=inter/union
        seq=SequenceMatcher(None,description.lower(),title.lower()).ratio()
        rowdiv=str(row.get("Div.") or row.get("legacy_division") or "").zfill(2)
        div_bonus=.10 if div!="00" and rowdiv==div else 0.0
        containment_bonus=.12 if ttok and ttok.issubset(qtok) else 0.0
        score=min(1.0, .58*jacc + .32*seq + div_bonus + containment_bonus)
        if score<=.08: continue
        reason=f"description_similarity={max(jacc,seq):.2f}" + (f"; division={div}" if div_bonus else "") + ("; full-title-token-match" if containment_bonus else "")
        scored.append(SamcoCandidate(master_code=str(row.get("SAMCO Master ID") or row.get("master_code") or ""),title=title,score=round(score,4),reason=reason,legacy_code=str(row.get("Activity Code") or "") or None))
    return sorted(scored,key=lambda x:x.score,reverse=True)[:limit]
