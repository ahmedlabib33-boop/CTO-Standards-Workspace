import { NextResponse } from "next/server";
import { getDataMode, getFixedDataBundle } from "@/lib/fixed-data";

export const dynamic = "force-dynamic";

export async function GET() {
  const bundle = getFixedDataBundle();
  return NextResponse.json({ ...bundle, runtime: getDataMode(bundle) });
}
