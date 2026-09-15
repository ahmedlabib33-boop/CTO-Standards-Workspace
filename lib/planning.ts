import { dbQuery, getPool } from "@/lib/db";
import { readJsonSafe } from "@/lib/fixed-data";

export type DurationMethod = "PRODUCTIVITY" | "FIXED" | "CONTRACTUAL" | "LEAD_TIME" | "QUANTITY_RATIO" | "CALENDAR_PERIOD" | "MANUAL_CONTROLLED" | "ENGINEERING_REVIEW";

export type DurationInput = {
  method: DurationMethod;
  quantity?: number;
  productivity?: number;
  crews?: number;
  fixed_days?: number;
  preparation_days?: number;
  first_review_days?: number;
  revision_days?: number;
  next_review_days?: number;
  approval_days?: number;
  rfq_days?: number;
  evaluation_days?: number;
  po_days?: number;
  manufacture_days?: number;
  shipping_days?: number;
  customs_days?: number;
  delivery_days?: number;
};

export function calculateDuration(input: DurationInput) {
  const positive = (v: unknown) => Math.max(0, Number(v || 0));
  const method = input.method;
  if (method === "PRODUCTIVITY" || method === "QUANTITY_RATIO") {
    const q = positive(input.quantity);
    const p = positive(input.productivity);
    const c = Math.max(1, positive(input.crews));
    if (!p) return { days: null, valid: false, reason: "Productivity must be greater than zero." };
    return { days: Math.ceil(q / (p * c)), valid: true, basis: `${q} / (${p} × ${c})` };
  }
  if (method === "FIXED" || method === "CONTRACTUAL" || method === "CALENDAR_PERIOD" || method === "MANUAL_CONTROLLED") {
    return { days: Math.ceil(positive(input.fixed_days)), valid: true, basis: "Controlled fixed duration" };
  }
  if (method === "LEAD_TIME") {
    const days = [input.approval_days,input.rfq_days,input.evaluation_days,input.po_days,input.manufacture_days,input.shipping_days,input.customs_days,input.delivery_days].map(positive).reduce((a,b)=>a+b,0);
    return { days: Math.ceil(days), valid: true, basis: "Approval + RFQ + Evaluation + PO + Manufacture + Shipping + Customs + Delivery" };
  }
  const engineeringDays = [input.preparation_days,input.first_review_days,input.revision_days,input.next_review_days,input.approval_days].map(positive).reduce((a,b)=>a+b,0);
  return { days: Math.ceil(engineeringDays), valid: true, basis: "Preparation + Review + Revision + Approval" };
}

export type PlanningActivity = {
  [key: string]: unknown;
  master_code: string;
  legacy_activity_code?: string | null;
  title: string;
  uom?: string | null;
  productivity?: number | null;
  crew_type?: string | null;
  crew_hours_per_unit?: number | null;
  source: "postgres" | "excel_json";
};

export async function getPlanningActivities(limit = 200): Promise<PlanningActivity[]> {
  if (getPool()) {
    try {
      const result = await dbQuery<PlanningActivity>(
        `select master_code, legacy_activity_code, title, uom, daily_production as productivity, crew_type, crew_hours_per_unit, 'postgres'::text as source
         from public.activities order by master_code limit $1`, [limit]
      );
      if (result.rows.length) return result.rows;
    } catch {}
  }

  const activities = readJsonSafe<Record<string, unknown>[]>("data/generated/master/activity_master.json", []);
  const productivity = readJsonSafe<Record<string, unknown>[]>("data/generated/master/manpower-productivity.json", []);
  const byLegacy = new Map(productivity.map(r => [String(r["Activity Code"] ?? ""), r]));
  return activities.slice(0, limit).map((a) => {
    const legacy = String(a["Activity Code"] ?? "");
    const p = byLegacy.get(legacy) || {};
    return {
      master_code: String(a["SAMCO Master ID"] ?? ""),
      legacy_activity_code: legacy,
      title: String(a["Activity description"] ?? ""),
      uom: p["UOM"] == null ? null : String(p["UOM"]),
      productivity: p["Daily Production"] == null ? null : Number(p["Daily Production"]),
      crew_type: p["Crew Type"] == null ? null : String(p["Crew Type"]),
      crew_hours_per_unit: p["CrewHr/ Unit"] == null ? null : Number(p["CrewHr/ Unit"]),
      source: "excel_json" as const,
    };
  });
}
