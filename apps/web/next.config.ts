import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Keep tracing inside this app (avoid parent ~/package-lock.json)
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
