import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import { emptyOverrides, type AdminOverrides } from "@/lib/admin-overrides";

function authorized(req: NextRequest) {
  const expected = process.env.SAMCO_ADMIN_KEY;
  if (!expected) return false;
  return req.headers.get("x-admin-key") === expected;
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (process.env.VERCEL || process.env.SAMCO_ALLOW_LOCAL_FILE_WRITES !== "true") {
    return NextResponse.json({ error: "Filesystem editing is disabled in deployed mode. Use Supabase for production Admin persistence or edit locally and publish through create_json.bat." }, { status: 409 });
  }
  const payload = await req.json() as Partial<AdminOverrides>;
  const target = path.join(process.cwd(), "data/control/admin_overrides.json");
  let current: AdminOverrides = emptyOverrides;
  try { current = JSON.parse(fs.readFileSync(target, "utf8")); } catch {}
  const merged: AdminOverrides = {
    ...current,
    ...payload,
    version: current.version || 1,
    activities: payload.activities ?? current.activities ?? {},
    resources: payload.resources ?? current.resources ?? {},
    rates: payload.rates ?? current.rates ?? {},
    assumptions: payload.assumptions ?? current.assumptions ?? {},
    updated_at: new Date().toISOString()
  };
  fs.writeFileSync(target, JSON.stringify(merged, null, 2), "utf8");
  return NextResponse.json({ ok: true, saved: "data/control/admin_overrides.json", updated_at: merged.updated_at });
}
