const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/**
 * Security headers.
 *
 * The deployment previously sent only Strict-Transport-Security. Most relevant for an
 * app with a login form: without X-Frame-Options / frame-ancestors the sign-in page can
 * be framed by an attacker and clickjacked.
 *
 * No Content-Security-Policy yet — Next.js inlines hydration scripts and the theme
 * script, so a CSP needs nonces to avoid breaking the app. Adding a broken or
 * unsafe-inline CSP would be worse than none, so it is left as a deliberate follow-up
 * rather than shipped half-done.
 */
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-DNS-Prefetch-Control", value: "on" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@careeros/shared"],
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

module.exports = withNextIntl(nextConfig);
