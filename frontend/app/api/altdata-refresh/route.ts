import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const res = await fetch(`${API_BASE}/altdata/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(120_000),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { available: false, reason: `Request failed: ${(e as Error).message}` },
      { status: 502 },
    );
  }
}
