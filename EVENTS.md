# SAMCO Business Event Catalog

Use business events rather than generic `update` messages.

## Corporate master
- `activity.created`
- `activity.updated`
- `activity.retired`
- `resource.created`
- `resource.updated`
- `productivity.updated`
- `duration.updated`
- `rate.updated`
- `corporate.standard.approved`

## Tender
- `boq.imported`
- `bid.created`
- `bid.recalculation.requested`
- `bid.calculated`
- `bid.approved`

## Planning
- `schedule.generated`
- `schedule.updated`
- `schedule.bulk_recalculation.requested`

## Project controls
- `project.progress.updated`
- `cost.actual.updated`
- `eac.updated`
- `forecast.requested`
- `forecast.completed`

## Output / integration
- `report.requested`
- `report.completed`
- `json.snapshot.requested`
- `json.snapshot.generated`
- `github.publish.requested`
- `github.publish.completed`
- `vercel.deploy.requested`
- `vercel.deploy.completed`

## Optional intelligence
- `ml.prediction.requested`
- `ml.prediction.completed`
- `llm.narrative.requested`
- `llm.narrative.completed`

Every event should contain at least `event_type`, `aggregate_type`, `aggregate_key`, `payload`, actor/context and a timestamp. Use an idempotency key for retryable externally initiated jobs.

## Project intake / scope integration — v0.4
- `document.processed` — one source document has been classified/extracted.
- `scope.mapped` — a CSI scope entry has received a controlled SAM-CTO mapping decision.
- `scope.conflict.detected` — BOQ/specification/drawing evidence does not align.
- `project.scope.ready` — the integrated scope register is persisted and ready to fan out to departments.

`project.scope.ready` is consumed by the Python worker to create department feed records for Technical, Tender, Planning and Cost Control. Mapping recommendations do not silently overwrite the corporate master; low-confidence results remain in `review_required` or `unmapped` status.
