# SAMCO CTO Hub v0.4 — Intake Wiring Summary

## Front door
`/intake` accepts PDF/DXF project documents and calls the FastAPI ingestion engine.

## Processing
1. File/size validation.
2. Native PDF text + table extraction; DXF entity extraction.
3. Optional last-resort OCR if Tesseract exists.
4. Document classification.
5. BOQ / specification / contract / drawing parsing.
6. CSI inference using Admin-controlled rules.
7. BOQ-item-level scope creation.
8. Cross-document evidence association and conflict detection.
9. SAM-CTO candidate matching against the generated corporate Activity Master.
10. Confidence gate: auto-map / review / unmapped.
11. Optional PostgreSQL persistence + transactional outbox.
12. Worker fan-out to Technical, Tender, Planning and Cost Control scope feeds.

## Visible workspaces
- `/intake`
- `/technical`
- `/tender`
- `/planning` (intake scope + activity/duration engine)
- `/cost-control`
- `/admin/scope-review`
- `/system`

## Admin controls added
- Document classifier keywords.
- BOQ section → CSI rules.
- Keyword/symbol → CSI rules.
- Contract term rules.
- SAM-CTO synonym and confidence thresholds.
- Human approval/rejection of proposed SAM-CTO project mappings.

## Reliability
The ingestion service is not required for corporate baseline operation. Excel/JSON activity/resource/rate/productivity data, Tender calculations and Planning durations remain available independently.

## Validation performed
- Python compileall passed for ingestion/API/workers.
- FastAPI synthetic BOQ/spec/drawing smoke test passed.
- TypeScript compiler API found zero syntax errors in app/lib source.
- Full Next.js type/build requires `npm install` because node_modules are not present in this execution environment.
