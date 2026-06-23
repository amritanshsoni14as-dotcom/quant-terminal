import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// Minimal config — no incremental cache backend yet. ISR pages still work
// (Workers honour the revalidate window in memory per isolate); add R2 if
// cross-isolate cache sharing becomes a bottleneck.
export default defineCloudflareConfig({});
