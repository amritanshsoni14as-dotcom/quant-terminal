import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

// Lets `next dev` resolve Cloudflare bindings (env, R2, etc.) the same way
// the deployed worker does. Safe no-op outside the Cloudflare context.
initOpenNextCloudflareForDev();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
