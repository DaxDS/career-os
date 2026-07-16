import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "fbclid",
        "gclid",
    }
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_url(url: str) -> str:
    if not url or not url.strip():
        return ""
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    host = (parsed.hostname or "").lower()
    if not host:
        return normalize_text(url)
    port = parsed.port
    netloc = host
    if port and port not in (80, 443):
        netloc = f"{host}:{port}"
    path = parsed.path.rstrip("/") or "/"
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in query_params.items() if k.lower() not in _TRACKING_PARAMS}
    query = urlencode(filtered, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def compute_description_hash(description: str) -> str:
    return hashlib.sha256(normalize_text(description).encode()).hexdigest()


def compute_dedup_key(company: str, title: str, province: str, city: str) -> str:
    parts = [
        normalize_text(company),
        normalize_text(title),
        province.strip().upper(),
        normalize_text(city),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
