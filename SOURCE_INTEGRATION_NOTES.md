# Source Integration Notes

The supplied Construction Drawing AI reference is preserved under `docs/reference/construction-drawing-ai-source.md` for traceability.

## Adopted concepts

- Dedicated document classifier and parsers.
- PDF native text/table extraction.
- DXF/PDF drawing evidence extraction.
- CSI-keyed integration.
- BOQ/specification/drawing conflict checks.
- QS/scope-oriented normalized output.
- Optional OCR fallback for low-text PDFs.

## Re-engineered for SAMCO

- Removed bridge/project-specific assumptions.
- Removed process-global accumulated project state; all results are project/ingestion scoped.
- Added SAM-CTO candidate mapping using the corporate activity master.
- Added human-governed confidence gates and mapping review.
- Added Admin-controlled mapping dictionaries instead of fixed Python-only mappings.
- Added PostgreSQL persistence and transactional outbox events.
- Added department fan-out to Technical, Tender, Planning and Cost Control.
- Kept the corporate Excel/JSON baseline independent so document ingestion cannot bring down core pricing/planning functions.
- BOQ parsing prefers PDF table extraction and falls back to text-line heuristics.
- OCR remains optional/last-resort; low-text documents are flagged rather than silently accepted as complete.
