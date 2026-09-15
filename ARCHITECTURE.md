# SAMCO CTO Hub — Applied Event-Driven Architecture

## Principle

The architecture is now **PostgreSQL-first for transactional production work** while preserving the governed Excel/JSON baseline as a safe fallback. The Event Broker, ML, LLM, reporting workers and external integrations are enrichment/background layers and are never required for the core application to open or calculate Planning/Tender/Cost functions.

```text
Next.js UI / Admin / Departments
              |
              v
      Orchestration Core
       /             \
      v               v
PostgreSQL       Transactional Outbox
   |                    |
   |                    v
   |                 Redis Stream
   |                    |
   |       +------------+-------------+
   |       v            v             v
   |    ML/LLM       Reports       Git/Vercel
   |    Worker        Worker         Sync
   |
   +--> Planning / Tender / Cost / Technical synchronous core
```

## Core synchronous path

The following functions must not depend on Redis or an LLM:

- Activity and resource lookup
- Planning activity library
- Activity duration calculation
- Productivity lookup
- Rate lookup/update
- Tender pricing equations
- Saving bids/projects
- Admin master-data updates
- Cost-control calculations

If PostgreSQL is not configured or temporarily unavailable, approved Excel-derived JSON remains readable. Local Admin overrides remain available through the Git/JSON workflow.

## Async path

The following are suitable for event-driven execution:

- Bulk bid recalculation
- Bulk schedule recalculation
- Report generation
- ML prediction / anomaly screening
- LLM management wording
- JSON snapshot generation
- GitHub publishing
- Vercel deployment trigger
- Notifications
- Cache invalidation

## Transactional outbox

Core writes create an outbox event in the same PostgreSQL transaction. This prevents the failure mode where a database update succeeds but the message broker publish fails.

`supabase/migrations/002_event_driven_core.sql` adds:

- `outbox_events`
- `background_jobs`
- `planning_duration_rules`
- `integration_endpoints`
- `claim_outbox_batch()`

The Python worker publishes pending outbox events to Redis Streams. If Redis is unavailable, it can process the durable outbox directly instead of blocking the application.

## Planning activities and durations

Planning remains a first-class core engine:

```text
SAM-CTO Activity
   + Quantity
   + Productivity
   + Crews
   + Duration Method
   + Calendar
   + Logic
   + Engineering prerequisites
   + Procurement prerequisites
            |
            v
       P6-ready activity
```

Supported duration methods:

- `PRODUCTIVITY`
- `FIXED`
- `CONTRACTUAL`
- `LEAD_TIME`
- `QUANTITY_RATIO`
- `CALENDAR_PERIOD`
- `MANUAL_CONTROLLED`
- `ENGINEERING_REVIEW`

The main construction formula is `Duration = Quantity / (Productivity x Crews)`, rounded up to whole working days by the current API.

## Integration Gateway

External systems are isolated from the core. Current integration keys are GitHub, Vercel, Primavera, SAP, Microsoft 365 and Power BI. None is required for core application availability.

## Source-of-truth order

1. PostgreSQL approved corporate master (production)
2. Admin-controlled overrides / governed working records
3. Excel-derived JSON corporate baseline (fallback/snapshot)
4. Historical project data — optional
5. Live project data — optional
6. ML prediction — optional
7. LLM wording — optional

The absence of levels 4–7 reduces enrichment, not capability.

# Project Intake & Scope Integration — applied in v0.4

The document engine from the supplied Construction Drawing AI concept is now the **front door** of the SAMCO platform rather than a separate utility.

```text
Project Documents
  BOQ / Specifications / Contract / ITT / PDF Drawings / DXF
                    |
                    v
          Intake Classification
                    |
        +-----------+-----------+
        |           |           |
       BOQ        Specs      Contract       Drawings
      parser      parser       parser       PDF / DXF
        |           |           |              |
        +-----------+-----------+--------------+
                    |
                    v
               CSI Scope
                    |
                    v
        SAM-CTO Candidate Matcher
                    |
             human-control gate
                    |
                    v
      Controlled Project Scope Register
                    |
                    v
          PostgreSQL + Outbox
                    |
         +----------+----------+----------+
         |          |          |          |
     Technical    Tender    Planning   Cost Control
```

## Design decisions

1. **No global in-memory accumulator.** Every result is project/ingestion scoped. This avoids cross-user/project contamination in a multi-user web app.
2. **CSI is classification, SAM-CTO is corporate identity.** The engine may propose a SAM-CTO candidate, but CSI never replaces the permanent SAMCO ID.
3. **Mapping is confidence-gated.** High-confidence mappings may be marked `auto_mapped`; medium confidence is `review_required`; low confidence remains `unmapped`.
4. **Evidence is preserved.** BOQ, specification and drawing entries retain source filename/page/sheet excerpts.
5. **OCR is last-resort and optional.** Native PDF text/vector evidence is attempted first. Low-text PDFs are explicitly flagged if OCR is unavailable.
6. **Admin mappings are data, not Python constants.** `data/control/document_mappings.json` governs document keywords, CSI rules, contract terms and matching thresholds and is editable from Admin in local mode. Production rules have a PostgreSQL table.
7. **Corporate engines remain independent.** If the intake engine is unavailable, the Activity/Resource/Productivity/Rate libraries, Tender calculations and Planning duration engine continue to operate from the corporate baseline.

## New runtime components

```text
ingestion/models.py          canonical intake models
ingestion/csi.py             CSI map + Admin-controlled rules
ingestion/extract.py         PDF native/table extraction + optional OCR fallback
ingestion/classifier.py      document type classification
ingestion/parsers.py         BOQ/spec/contract parsers
ingestion/drawings.py        PDF/DXF drawing evidence
ingestion/samco_matcher.py    CSI/scope -> SAM-CTO candidates
ingestion/integrator.py      cross-document merge/conflict engine
ingestion/persistence.py     PostgreSQL + transactional outbox persistence
ingestion/service.py         FastAPI intake service
api/intake.py                Vercel Python entrypoint
app/intake/*                 Next.js intake workspace
```

The database migration is `supabase/migrations/003_project_intake_scope.sql`.
