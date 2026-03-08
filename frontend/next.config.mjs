/** @type {import('next').NextConfig} */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

const parseApiBase = (apiBase) => {
  if (!apiBase) {
    return null;
  }
  try {
    return new URL(apiBase);
  } catch {
    throw new Error(
      `Invalid NEXT_PUBLIC_API_BASE value: ${apiBase}. Use a fully-qualified URL, e.g. https://api.example.com`
    );
  }
};

const parsedApiBase = parseApiBase(API_BASE);

// NOTE:
// - In AWS, the ALB/CloudFront path rules route /api/* directly to the backend.
// - In local/docker, we often use http://localhost:8000.
// So we treat NEXT_PUBLIC_API_BASE as optional and only enforce HTTPS for non-local hosts.
const _isLocalHost = (hostname) =>
  hostname === "localhost" ||
  hostname === "127.0.0.1" ||
  hostname === "::1" ||
  hostname === "backend";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,

  typescript: {
    ignoreBuildErrors: false,
  },

  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 60,
    remotePatterns: parsedApiBase
      ? [
          {
            protocol: parsedApiBase.protocol.replace(":", ""),
            hostname: parsedApiBase.hostname,
          },
        ]
      : [],
  },

  async rewrites() {
    if (!parsedApiBase) return [];

    if (process.env.NODE_ENV === "production" && parsedApiBase.protocol !== "https:" && !_isLocalHost(parsedApiBase.hostname)) {
      throw new Error(
        `NEXT_PUBLIC_API_BASE must use HTTPS for non-local hosts (got ${API_BASE}).`
      );
    }

    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE}/api/:path*`,
      },
      {
        source: "/track/:path*",
        destination: `${API_BASE}/track/:path*`,
      },
    ];
  },

  async redirects() {
    return [
      // Intentionally left empty to avoid shadowing active App Router pages.
    ];
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value:
              "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
