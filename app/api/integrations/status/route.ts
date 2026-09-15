import { NextResponse } from "next/server";
import { integrationStatus } from "@/lib/integration-gateway";
export async function GET(){ return NextResponse.json({ integrations: integrationStatus() }); }
