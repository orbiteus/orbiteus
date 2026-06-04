/** @type {import('next').NextConfig} */
const path = require("node:path");

const repoRoot = path.join(__dirname, "..");

const nextConfig = {
  transpilePackages: ["@orbiteus/i18n"],
  /**
   * npm workspaces hoist `next` to the repo root. Point Turbopack there so
   * `next/package.json` resolves; paths still resolve under this app's `src/`.
   */
  turbopack: {
    root: repoRoot,
    // Paths are relative to `root` — never use absolute paths (Turbopack breaks on those).
    resolveAlias: {
      "@orbiteus/i18n": "./packages/i18n/src/index.ts",
    },
  },
  /** Monorepo Docker dev: keep a single React copy when using `--webpack`. */
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      react: path.join(repoRoot, "node_modules/react"),
      "react-dom": path.join(repoRoot, "node_modules/react-dom"),
    };
    return config;
  },
};

module.exports = nextConfig;
