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
      // CMS routes migrated from bconsole/pconsole to cconsole
      {
        source: "/bconsole/:slug/cms/:path*",
        destination: "/cconsole/:slug/:path*",
        permanent: true,
      },
      {
        source: "/pconsole/cms/:path*",
        destination: "/cconsole/:path*",
        permanent: true,
      },
    ];
  },

  async rewrites() {
    // API requests are proxied by app/api/[...path]/route.ts (not rewrites)
    // to properly handle cookies, trailing slashes, and headers.
    return [
      {
        source: "/media/:path*",
        destination: `${apiUrl}/media/:path*`,
      },
      {
        source: "/health",
        destination: `${apiUrl}/health/`,
      },
      {
        source: "/ready",
        destination: `${apiUrl}/ready/`,
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
      `connect-src 'self' ${apiUrl} ${apiUrl.replace(/^http/, "ws")}`,
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
