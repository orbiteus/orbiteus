/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In Docker: BACKEND_URL=http://backend:8000
    // Locally:   BACKEND_URL unset → falls back to localhost
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
