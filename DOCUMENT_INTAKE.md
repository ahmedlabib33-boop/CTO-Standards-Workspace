# SAMCO Project Intake & Scope Integration

## Purpose

Turn raw tender/project information into one controlled scope register before Technical, Tender, Planning and Cost Control begin separate work.

## Accepted sources

- BOQ PDF
- Technical specification PDF
- Contract / ITT / conditions PDF
- Drawing PDF
- DXF

## Processing pipeline

```text
Upload
  -> safe filename / file-size validation
  -> native PDF extraction (text + tables) or DXF extraction
  -> document classification
  -> dedicated parser
  -> CSI inference
  -> cross-document merge
  -> conflict detection
  -> SAM-CTO candidate matching
  -> confidence gate
  -> PostgreSQL persistence
  -> transactional outbox
  -> Technical/Tender/Planning/Cost Control feeds
```

## SAM-CTO mapping policy

The matcher uses activity descriptions plus division context from the generated corporate Activity Master. It returns ranked candidates with scores and reasons. The thresholds live in `data/control/document_mappings.json`.

- score >= `auto_accept_threshold`: `auto_mapped`
- score >= `review_threshold`: `review_required`
- below review threshold: `unmapped`

An auto-mapped result is still project working data; it does not alter the permanent corporate activity record.

## Conflict checks currently implemented

- BOQ scope without drawing evidence
- Drawing scope without BOQ evidence
- BOQ scope without mapped specification section

These are evidence checks, not final contractual conclusions. They create a review queue.

## Local development

Terminal 1:

```powershell
npm install
npm run dev
```

Terminal 2:

```powershell
pip install -r requirements-ingestion.txt
npm run ingestion:dev
```

`.env.local`:

```text
NEXT_PUBLIC_INGESTION_API_URL=http://127.0.0.1:8010/api/intake
```

Open `http://localhost:3000/intake`.

## Production

Apply migrations 001, 002 and 003. Configure `DATABASE_URL`. The Vercel Python entrypoint is `api/intake.py`; if the Python intake service is deployed separately, set `NEXT_PUBLIC_INGESTION_API_URL` to that endpoint.

The public Vercel page sends each selected source file in its own request, then merges the returned evidence and finalizes one integrated scope. This avoids the Vercel request-body ceiling without creating a separate document store. The default public per-file ceiling is 3 MB (`NEXT_PUBLIC_INGESTION_MAX_REQUEST_BYTES`); larger documents must use the local Python intake service or a separately approved storage-backed production pipeline.

Server-side Tesseract is optional and intentionally not a core dependency. Native PDF extraction is attempted first. For a runtime that provides Tesseract, install `requirements-ocr.txt`.
