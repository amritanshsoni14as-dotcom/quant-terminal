import { NextRequest, NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const symbol = encodeURIComponent(body.symbol ?? "");
    const res = await fetch(`${API_BASE}/intel/${symbol}/copilot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: body.question ?? "" }),
      signal: AbortSignal.timeout(240_000),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { available: false, answer: `Request failed: ${(e as Error).message}` },
      { status: 502 },
    );
  }
}
