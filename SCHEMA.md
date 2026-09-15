# SAMCO CTO Hub — Domain / Data Schema

## Corporate master
- `activities`: permanent `SAM-CTO-#########` identity, legacy code, CSI mapping, discipline, UOM and productivity attributes.
- `resources`: material, crew, equipment and subcontract resource records.
- `rate_register`: governed corporate rates.
- `commercial_assumptions`: overhead, contingency, escalation, profit and commercial settings.

## Planning
- `planning_duration_rules`: duration method, corporate productivity, default crews, min/typical/max duration, calendar, logic and prerequisites.
- `planning_working`: project-specific quantity, crews, productivity, predecessor, relationship, lag, calendar and WBS override.

## Tender / cost / projects
- `projects`
- `project_boq_items`
- `evm_periods`
- `technical_working`

## Governance
- `profiles`
- `role_page_access`
- `app_settings`
- `ui_nodes`
- `audit_log`
- `deadlines`
- `report_templates`

## Event-driven core
- `outbox_events`: durable business events created with transactional writes.
- `background_jobs`: worker execution history/results.
- `integration_endpoints`: external integration configuration/health metadata.

## Storage
Excel sources, report templates, logos, soundtrack files, PDFs and generated reports belong in object storage/file storage; PostgreSQL stores metadata and references rather than large binaries.

## Fallback datasets
`data/generated/master/*.json` remains the version-controlled fallback/snapshot generated from the two Excel workbooks. It is not discarded when PostgreSQL is introduced.

# v0.4 Project Intake schema

Migration `003_project_intake_scope.sql` adds:

- `project_documents` — processed source-document metadata and extraction mode.
- `project_scope_entries` — project/ingestion-scoped CSI scope, quantities, completeness, conflicts, SAM-CTO mapping and full normalized payload.
- `document_mapping_rules` — Admin-controlled production mapping rules.
- `scope_review_actions` — human review/audit trail for mapping/conflict decisions.
- `project_scope_feeds` — event-generated department work queues for Technical, Tender, Planning and Cost Control.

The corporate `activities` table remains the SAM-CTO master. `project_scope_entries.selected_samco_code` references it; extraction can recommend a candidate but cannot create or modify the corporate standard without the governed Admin/department workflow.
