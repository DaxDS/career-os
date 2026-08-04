/**
 * Constrain post-login redirects to same-origin paths.
 *
 * The login page read `?redirect=` straight from the query string and pushed it. A
 * value like `https://evil.com` or the protocol-relative `//evil.com` turns a link on
 * your own domain into a phishing hop, which is exactly what makes open redirects
 * valuable to attackers — the domain the victim inspects is genuinely yours.
 *
 * The auth callback already normalised its redirect; this makes the rule shared and
 * explicit rather than something each caller has to remember.
 */

const DEFAULT_REDIRECT = "/dashboard";

/** Any scheme prefix: https:, javascript:, data:, mailto:. */
const HAS_SCHEME = /^\/?[a-z][a-z0-9+.-]*:/i;

/**
 * Control characters or whitespace anywhere in the path.
 *
 * Written as an explicit code-point test rather than a regex character class: a range
 * like [ -] silently also matches a literal hyphen, which would reject legitimate
 * paths such as /onboarding/work-history.
 */
function hasControlOrSpace(value: string): boolean {
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    if (code <= 0x20 || code === 0x7f) return true;
  }
  return false;
}

function isProtocolRelative(value: string): boolean {
  return value.startsWith("//") || value.startsWith("/\\");
}

export function safeRedirect(value: string | null | undefined, fallback = DEFAULT_REDIRECT): string {
  if (!value) return fallback;

  const trimmed = value.trim();
  if (!trimmed.startsWith("/")) return fallback;
  if (isProtocolRelative(trimmed)) return fallback;

  // Decode once so `/%2f%2fevil.com` style bypasses are caught too.
  let decoded = trimmed;
  try {
    decoded = decodeURIComponent(trimmed);
  } catch {
    return fallback;
  }

  if (hasControlOrSpace(decoded)) return fallback;
  if (isProtocolRelative(decoded)) return fallback;
  if (HAS_SCHEME.test(decoded)) return fallback;

  return trimmed;
}
