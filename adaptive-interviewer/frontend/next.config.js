/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Use explicit IPv4 — Node 18+ resolves "localhost" to ::1 (IPv6)
    // and uvicorn only binds IPv4 by default, causing ECONNREFUSED.
    const backend = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8002";
    return [{ source: "/api/backend/:path*", destination: `${backend}/:path*` }];
  },
};
module.exports = nextConfig;
