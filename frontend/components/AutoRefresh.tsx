"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

// Refresh ONLY when the user actively returns to the tab, and at most once
// every 5 minutes. The 3-minute polling that used to live here generated
// hundreds of SSR rerenders per open tab per day — that single change drove
// the bulk of our Vercel function-invocation bill and Render backend load.
// ISR (revalidate on the pages themselves) handles routine freshness now.
export default function AutoRefresh(_props: { seconds?: number }) {
  const router = useRouter();
  const lastRefresh = useRef(0);
  useEffect(() => {
    const COOLDOWN_MS = 5 * 60 * 1000;
    const onFocus = () => {
      const now = Date.now();
      if (now - lastRefresh.current < COOLDOWN_MS) return;
      lastRefresh.current = now;
      router.refresh();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [router]);
  return null;
}
