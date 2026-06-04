/** @type {import('next').NextConfig} */
const path = require("node:path");

const repoRoot = path.join(__dirname, "..");

const nextConfig = {
  transpilePackages: ["@orbiteus/i18n"],
  turbopack: {
    root: repoRoot,
    resolveAlias: {
      "@orbiteus/i18n": "./packages/i18n/src/index.ts",
    },
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      react: path.join(repoRoot, "node_modules/react"),
      "react-dom": path.join(repoRoot, "node_modules/react-dom"),
    };
    return config;
  },
  async rewrites() {
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
