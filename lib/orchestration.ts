import { withTransaction, getPool } from "@/lib/db";
import { enqueueEvent } from "@/lib/events";
import { calculateDuration, type DurationInput } from "@/lib/planning";

export type OrchestrationRequest =
  | { action: "planning.calculate_duration"; input: DurationInput }
  | { action: "rate.update"; input: { code: string; rate: number; actor?: string; notes?: string } }
  | { action: "report.request"; input: { department: string; format: "html"|"docx"|"xlsx"; template_id?: string } }
  | { action: "github.publish"; input: { reason: string } };

export async function orchestrate(req: OrchestrationRequest) {
  if (req.action === "planning.calculate_duration") {
    return { mode: "synchronous_core", result: calculateDuration(req.input), async_dependency: false };
  }

  if (req.action === "rate.update") {
    if (!getPool()) {
      return {
        mode: "baseline_safe",
        saved: false,
        message: "PostgreSQL is not configured. Use Admin local override workflow; the core app remains online.",
      };
    }
    const outcome = await withTransaction(async (client) => {
      const before = await client.query(`select * from public.rate_register where code=$1`, [req.input.code]);
      await client.query(
        `insert into public.rate_register(code, category, name, avg_rate, source, effective_date, updated_at)
         values($1,'Admin','Admin controlled rate',$2,'Admin override',current_date,now())
         on conflict(code) do update set avg_rate=excluded.avg_rate, source=excluded.source, updated_at=now()`,
        [req.input.code, req.input.rate]
      );
      await client.query(
        `insert into public.audit_log(action, entity_type, entity_key, before_value, after_value)
         values('rate.update','rate',$1,$2::jsonb,$3::jsonb)`,
        [req.input.code, JSON.stringify(before.rows[0] ?? null), JSON.stringify(req.input)]
      );
      const outbox = await client.query(
        `insert into public.outbox_events(event_type,aggregate_type,aggregate_key,payload,actor_label)
         values('rate.updated','rate',$1,$2::jsonb,$3) returning id`,
        [req.input.code, JSON.stringify(req.input), req.input.actor ?? "admin"]
      );
      return { before: before.rows[0] ?? null, after: req.input, outbox_id: outbox.rows[0]?.id ?? null };
    });
    return { mode: "synchronous_write_async_fanout", saved: true, outcome, queue: { queued: true, transport: "postgres_outbox", outbox_id: outcome.outbox_id } };
  }

  const eventType = req.action === "report.request" ? "report.requested" : "github.publish.requested";
  const key = req.action === "report.request" ? `${req.input.department}:${req.input.format}` : "github";
  const queue = await enqueueEvent({ event_type: eventType, aggregate_type: req.action.split(".")[0], aggregate_key: key, payload: req.input });
  return { mode: "asynchronous", accepted: true, queue };
}
