import { NextResponse } from "next/server";
import { brokerHealth } from "@/lib/events";
import { dbHealth } from "@/lib/db";
export const dynamic = "force-dynamic";
export async function GET(){
  const [database, broker] = await Promise.all([dbHealth(), brokerHealth()]);
  return NextResponse.json({database, broker, principle:"Database and broker enrich reliability, but JSON corporate baseline keeps the app available."});
}
