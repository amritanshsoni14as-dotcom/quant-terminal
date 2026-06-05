import { NextRequest, NextResponse } from "next/server";

// Optional HTTP Basic Auth gate. Active only when DASHBOARD_PASSWORD is set
// (it is, by default, since this app is exposed over a public tunnel).
// To disable: remove DASHBOARD_PASSWORD from frontend/.env.local and rebuild.
export function middleware(req: NextRequest) {
  const user = process.env.DASHBOARD_USER || "rain";
  const pass = process.env.DASHBOARD_PASSWORD;
  if (!pass) return NextResponse.next();

  const header = req.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    try {
      const [u, p] = atob(header.slice(6)).split(":");
      if (u === user && p === pass) return NextResponse.next();
    } catch {
      /* fall through to challenge */
    }
  }
  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="RAINMUMBAI Terminal"' },
  });
}

export const config = {
  // Protect everything except Next internals and static assets.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
