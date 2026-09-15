import { NextRequest, NextResponse } from "next/server";
import { calculateDuration, type DurationInput } from "@/lib/planning";
export async function POST(req: NextRequest){
  try { return NextResponse.json(calculateDuration(await req.json() as DurationInput)); }
  catch(error){ return NextResponse.json({error:error instanceof Error?error.message:String(error)},{status:400}); }
}
