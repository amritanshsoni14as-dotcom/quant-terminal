"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Periodically re-runs the server components so an open tab pulls fresh data
// without a manual reload. Also refreshes when the tab regains focus.
export default function AutoRefresh({ seconds = 180 }: { seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), seconds * 1000);
    const onFocus = () => router.refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [router, seconds]);
  return null;
}
