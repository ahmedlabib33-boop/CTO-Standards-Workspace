"""Seed PostgreSQL/Supabase from the governed Excel-derived JSON baseline.

Safe to rerun. The Excel/JSON baseline is not destroyed; PostgreSQL becomes the production
transactional source of truth while JSON remains a versioned fallback/snapshot.
"""
import json
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "generated" / "master"
DB = os.getenv("DATABASE_URL")
if not DB:
    raise SystemExit("DATABASE_URL is required")

activities = json.loads((MASTER / "activity_master.json").read_text(encoding="utf-8"))
rates = json.loads((MASTER / "rates.json").read_text(encoding="utf-8"))
prod = json.loads((MASTER / "manpower-productivity.json").read_text(encoding="utf-8"))
prod_by_code = {str(r.get("Activity Code") or ""): r for r in prod}

with psycopg.connect(DB) as conn:
    with conn.cursor() as cur:
        for a in activities:
            master = str(a.get("SAMCO Master ID") or "")
            legacy = str(a.get("Activity Code") or "")
            p = prod_by_code.get(legacy, {})
            cur.execute(
                """insert into public.activities(master_code,title,legacy_activity_code,legacy_division,legacy_subdivision,discipline,uom,crew_type,daily_production,crew_hours_per_day,crew_hours_per_unit,status,source,updated_at)
                values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Approved',%s::jsonb,now())
                on conflict(master_code) do update set title=excluded.title, legacy_activity_code=excluded.legacy_activity_code,
                legacy_division=excluded.legacy_division, legacy_subdivision=excluded.legacy_subdivision, uom=excluded.uom,
                crew_type=excluded.crew_type, daily_production=excluded.daily_production, crew_hours_per_day=excluded.crew_hours_per_day,
                crew_hours_per_unit=excluded.crew_hours_per_unit, source=excluded.source, updated_at=now()""",
                (master, a.get("Activity description"), legacy, a.get("Div."), a.get("Sub Division"), a.get("Division Description"), p.get("UOM"), p.get("Crew Type"), p.get("Daily Production"), p.get("CrewHr/ day"), p.get("CrewHr/ Unit"), json.dumps({"workbook": a.get("_source_workbook"), "sheet": a.get("_source_sheet"), "row": a.get("_source_row")}))
            )
            cur.execute(
                """insert into public.planning_duration_rules(master_code,duration_method,corporate_productivity,corporate_crews,source,updated_at)
                values(%s,'PRODUCTIVITY',%s,1,%s::jsonb,now())
                on conflict(master_code) do update set corporate_productivity=excluded.corporate_productivity, source=excluded.source, updated_at=now()""",
                (master, p.get("Daily Production"), json.dumps({"basis": "Activity lists Final Tuning.xlsx / Manpower PR", "legacy_activity_code": legacy}))
            )
        for r in rates:
            code = str(r.get("rate_id") or "")
            if not code:
                continue
            value = r.get("rate")
            try:
                value = float(value) if value not in (None, "") else None
            except Exception:
                value = None
            cur.execute(
                """insert into public.rate_register(code,category,name,unit,avg_rate,source,effective_date,updated_at)
                values(%s,%s,%s,%s,%s,%s,current_date,now())
                on conflict(code) do update set category=excluded.category,name=excluded.name,unit=excluded.unit,avg_rate=excluded.avg_rate,source=excluded.source,updated_at=now()""",
                (code, r.get("category"), r.get("description") or code, r.get("unit"), value, r.get("source"))
            )
print(f"Seeded {len(activities)} activities and {len(rates)} rate records.")
