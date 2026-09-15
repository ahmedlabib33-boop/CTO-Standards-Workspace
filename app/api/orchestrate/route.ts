import { NextRequest, NextResponse } from "next/server";
import { orchestrate, type OrchestrationRequest } from "@/lib/orchestration";

function adminAuthorized(req: NextRequest){
  const expected=process.env.SAMCO_ADMIN_KEY;
  return Boolean(expected && req.headers.get("x-admin-key")===expected);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as OrchestrationRequest;
    if (!body?.action) return NextResponse.json({error:"Missing action"},{status:400});
    if ((body.action === "rate.update" || body.action === "github.publish") && !adminAuthorized(req)) {
      return NextResponse.json({error:"Admin authorization required"},{status:401});
    }
    return NextResponse.json(await orchestrate(body));
  } catch (error) {
    return NextResponse.json({error:error instanceof Error ? error.message : String(error)},{status:500});
  }
}
