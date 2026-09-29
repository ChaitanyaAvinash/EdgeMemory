import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // No on-screen dev badge (it showed in demo recordings and screenshots); compile errors still surface.
  devIndicators: false,
};

export default nextConfig;
