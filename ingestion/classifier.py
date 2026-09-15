from __future__ import annotations
from .csi import load_mappings

def detect_document_type(filename: str, text: str) -> tuple[str, float]:
    maps = load_mappings()
    lower = filename.lower()
    filename_hints = {
        "boq": ["boq", "bill of quantities"],
        "spec": ["spec", "spc", "specification"],
        "contract": ["contract", "itt", "conditions", "poc", "coc"],
        "drawing": ["dwg", "drawing", "ga-", "ar-", "str-", "mep-"],
        "qc": ["quality", "inspection", "itp", "ncr"]
    }
    for kind, hints in filename_hints.items():
        if any(h in lower for h in hints): return kind, 0.92
    sample = (text or "")[:40000].lower()
    scores: dict[str, int] = {}
    for kind, words in maps.get("document_keywords", {}).items():
        scores[kind] = sum(1 for w in words if str(w).lower() in sample)
    if not scores or max(scores.values(), default=0) == 0: return "unknown", 0.0
    best = max(scores, key=scores.get)
    total = max(len(maps.get("document_keywords", {}).get(best, [])), 1)
    return best, min(0.95, 0.45 + scores[best] / total * 0.5)
