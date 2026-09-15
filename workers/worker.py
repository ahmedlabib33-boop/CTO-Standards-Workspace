"""SAMCO event worker.

The worker is deliberately non-critical. Core Planning/Tender/Cost functions read/write
PostgreSQL directly and can fall back to the Excel-derived JSON baseline. Redis, ML, LLM,
reporting and Git/Vercel synchronization are enrichment/background layers.
"""
import json
import os
import time
from datetime import datetime, timezone

try:
    import psycopg
except Exception:
    psycopg = None
try:
    import redis
except Exception:
    redis = None

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
STREAM = os.getenv("SAMCO_EVENT_STREAM", "samco:events")
GROUP = os.getenv("SAMCO_EVENT_GROUP", "samco-workers")
CONSUMER = os.getenv("SAMCO_EVENT_CONSUMER", f"worker-{os.getpid()}")


def db_conn():
    return psycopg.connect(DATABASE_URL) if psycopg and DATABASE_URL else None


def redis_client():
    return redis.from_url(REDIS_URL, decode_responses=True) if redis and REDIS_URL else None


def process_event(event_type, payload):
    if event_type in {"rate.updated", "productivity.updated", "duration.updated"}:
        return {"status": "accepted", "action": "invalidate-derived-benchmarks"}
    if event_type in {"bid.recalculation.requested", "schedule.bulk_recalculation.requested"}:
        return {"status": "accepted", "action": "bulk-recalculation"}
    if event_type == "report.requested":
        return {"status": "accepted", "action": "report-generation"}
    if event_type in {"github.publish.requested", "vercel.deploy.requested", "json.snapshot.requested"}:
        return {"status": "accepted", "action": "integration-sync"}
    if event_type.startswith("ml.") or event_type.startswith("llm."):
        return {"status": "accepted", "action": "optional-intelligence"}
    return {"status": "ignored", "reason": "No background handler required"}


def record_completed(event_id, event_type, payload, result):
    conn = db_conn()
    if not conn:
        return
    with conn:
        with conn.cursor() as cur:
            if event_id:
                cur.execute("update public.outbox_events set status='completed', completed_at=now(), last_error=null where id=%s", (event_id,))
            cur.execute(
                """insert into public.background_jobs(event_id,job_type,payload,status,result,completed_at)
                values(%s,%s,%s::jsonb,'completed',%s::jsonb,now())
                on conflict(event_id) where event_id is not null do update
                set status='completed', result=excluded.result, completed_at=now(), error=null""",
                (event_id or None, event_type, json.dumps(payload), json.dumps(result)),
            )
    conn.close()


def record_failed(event_id, error):
    if not event_id:
        return
    conn = db_conn()
    if not conn:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute("update public.outbox_events set status='failed', last_error=%s where id=%s", (str(error), event_id))
    conn.close()


def claim_outbox(limit=20):
    conn = db_conn()
    if not conn:
        return []
    with conn:
        with conn.cursor() as cur:
            cur.execute("select * from public.claim_outbox_batch(%s)", (limit,))
            cols = [d.name for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def publish_outbox(limit=20):
    """Publish durable PostgreSQL events to Redis. If Redis is absent, process directly."""
    rows = claim_outbox(limit)
    if not rows:
        return 0
    r = redis_client()
    published = 0
    for row in rows:
        try:
            if r:
                r.xadd(STREAM, {
                    "outbox_id": str(row["id"]),
                    "event_type": row["event_type"],
                    "aggregate_type": row["aggregate_type"],
                    "aggregate_key": row["aggregate_key"],
                    "payload": json.dumps(row["payload"]),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                conn = db_conn()
                if conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute("update public.outbox_events set status='published', published_at=now() where id=%s", (row["id"],))
                    conn.close()
            else:
                # Broker outage cannot block business processing. Handle durable event directly.
                result = process_event(row["event_type"], row["payload"])
                record_completed(row["id"], row["event_type"], row["payload"], result)
            published += 1
        except Exception as exc:
            record_failed(row["id"], exc)
    return published


def ensure_group(r):
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def consume_stream_once(block_ms=1000, count=10):
    r = redis_client()
    if not r:
        return 0
    ensure_group(r)
    batches = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=count, block=block_ms)
    handled = 0
    for _, messages in batches:
        for message_id, fields in messages:
            event_id = int(fields.get("outbox_id") or 0) or None
            event_type = fields.get("event_type", "unknown")
            try:
                payload = json.loads(fields.get("payload") or "{}")
                result = process_event(event_type, payload)
                record_completed(event_id, event_type, payload, result)
                r.xack(STREAM, GROUP, message_id)
                handled += 1
            except Exception as exc:
                record_failed(event_id, exc)
    return handled


def run_once():
    published = publish_outbox(20)
    consumed = consume_stream_once(100, 20) if REDIS_URL else 0
    return {"published_or_fallback_processed": published, "redis_consumed": consumed}


def main():
    print("SAMCO worker started. Core application does not depend on this worker.")
    while True:
        try:
            stats = run_once()
            if not any(stats.values()):
                time.sleep(2)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(datetime.now(timezone.utc).isoformat(), "worker error", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
