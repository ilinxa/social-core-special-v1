import type { NextConfig } from "next";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,

  async redirects() {
    return [
      {
        source: "/dashboard",
        destination: "/home",
        permanent: true,
      },
      {
        source: "/business/:slug/:path+",
        destination: "/bconsole/:slug/:path+",
        permanent: true,
      },
      {
        source: "/platform/:path((?!profile).+)",
        destination: "/pconsole/:path",
        permanent: true,
      },
    ];
  },

  async rewrites() {
    return [
      {
        source: "/media/:path*",
        destination: `${apiUrl}/media/:path*`,
      },
    ];
  },

  async headers() {
    // CSP directives — permissive for dev (unsafe-inline/eval needed for HMR).
    // Production hardening: replace unsafe-inline/eval with nonce-based CSP via middleware.
    const cspDirectives = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      `img-src 'self' data: blob: https: ${apiUrl}`,
      "font-src 'self'",
      `connect-src 'self' ${apiUrl}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; ");

    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "0" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          { key: "Content-Security-Policy", value: cspDirectives },
        ],
      },
    ];
  },
};

export default nextConfig;
