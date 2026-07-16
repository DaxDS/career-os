"""Create Stripe test-mode Products and Prices for Career OS plans.

Usage:
    set STRIPE_SECRET_KEY=sk_test_...   (PowerShell: $env:STRIPE_SECRET_KEY="sk_test_...")
    py -3.14 scripts/create_stripe_prices.py

Prints the price IDs to copy into backend/.env as STRIPE_PRICE_PRO and
STRIPE_PRICE_TEAM. Uses the raw Stripe REST API — no SDK dependency.
"""

import json
import os
import sys
import urllib.parse
import urllib.request

STRIPE_API = "https://api.stripe.com/v1"

PLANS = [
    {
        "env_var": "STRIPE_PRICE_PRO",
        "product_name": "Career OS Pro",
        "amount_cents": 2900,
        "lookup_key": "career_os_pro_monthly_cad",
    },
    {
        "env_var": "STRIPE_PRICE_TEAM",
        "product_name": "Career OS Career Coach",
        "amount_cents": 9900,
        "lookup_key": "career_os_team_monthly_cad",
    },
]


def stripe_post(secret_key: str, path: str, fields: dict) -> dict:
    request = urllib.request.Request(
        f"{STRIPE_API}{path}",
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"Stripe error on {path}: {body}") from exc


def main() -> None:
    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key.startswith("sk_"):
        raise SystemExit("Set STRIPE_SECRET_KEY (test mode: sk_test_...) in the environment first.")
    if not secret_key.startswith("sk_test_"):
        print("WARNING: this does not look like a test-mode key.", file=sys.stderr)

    env_lines = []
    for plan in PLANS:
        product = stripe_post(secret_key, "/products", {"name": plan["product_name"]})
        price = stripe_post(
            secret_key,
            "/prices",
            {
                "product": product["id"],
                "currency": "cad",
                "unit_amount": str(plan["amount_cents"]),
                "recurring[interval]": "month",
                "lookup_key": plan["lookup_key"],
            },
        )
        print(f"{plan['product_name']}: product={product['id']} price={price['id']}")
        env_lines.append(f"{plan['env_var']}={price['id']}")

    print("\nAdd to backend/.env:")
    for line in env_lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
