import { createClient } from "redis";
import { dbQuery } from "@/lib/db";

export type SamcoEvent = {
  event_type: string;
  aggregate_type: string;
  aggregate_key: string;
  payload: Record<string, unknown>;
  actor?: string | null;
  idempotency_key?: string | null;
};

let redis: ReturnType<typeof createClient> | null = null;

async function getRedis(): Promise<ReturnType<typeof createClient> | null> {
  const url = process.env.REDIS_URL;
  if (!url) return null;
  if (!redis) {
    redis = createClient({ url });
    redis.on("error", () => {});
  }
  if (!redis.isOpen) await redis.connect();
  return redis;
}

export async function brokerHealth() {
  try {
    const client = await getRedis();
    if (!client) return { available: false, message: "Redis not configured; core application remains synchronous." };
    const pong = await client.ping();
    return { available: pong === "PONG", message: "Redis event broker online." };
  } catch (error) {
    return { available: false, message: `Redis unavailable: ${error instanceof Error ? error.message : String(error)}` };
  }
}

export async function enqueueEvent(event: SamcoEvent) {
  // The durable event is written first. Redis is only the delivery accelerator.
  let outboxId: number | null = null;
  try {
    const inserted = await dbQuery<any>(
      `insert into public.outbox_events(event_type, aggregate_type, aggregate_key, payload, actor_label, idempotency_key)
       values ($1,$2,$3,$4::jsonb,$5,$6)
       on conflict (idempotency_key) where idempotency_key is not null do update set idempotency_key=excluded.idempotency_key
       returning id`,
      [event.event_type, event.aggregate_type, event.aggregate_key, JSON.stringify(event.payload), event.actor ?? null, event.idempotency_key ?? null]
    );
    outboxId = inserted.rows[0]?.id ?? null;
  } catch {
    // If PostgreSQL is not configured, async infrastructure must not break core operation.
  }

  try {
    const client = await getRedis();
    if (!client) return { queued: Boolean(outboxId), transport: outboxId ? "postgres_outbox" : "none", outbox_id: outboxId };
    const messageId = await client.xAdd(process.env.SAMCO_EVENT_STREAM || "samco:events", "*", {
      outbox_id: outboxId == null ? "" : String(outboxId),
      event_type: event.event_type,
      aggregate_type: event.aggregate_type,
      aggregate_key: event.aggregate_key,
      payload: JSON.stringify(event.payload),
      actor: event.actor ?? "system",
      created_at: new Date().toISOString(),
    });
    if (outboxId != null) {
      try { await dbQuery(`update public.outbox_events set status='published', published_at=now() where id=$1`, [outboxId]); } catch {}
    }
    return { queued: true, transport: "redis_stream", outbox_id: outboxId, message_id: messageId };
  } catch {
    return { queued: Boolean(outboxId), transport: outboxId ? "postgres_outbox" : "none", outbox_id: outboxId };
  }
}
