import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  transpilePackages: ["@openhuman/api-client"],
  experimental: {
    viewTransition: true,
  },
};

export default nextConfig;
