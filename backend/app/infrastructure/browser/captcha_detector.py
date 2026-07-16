from typing import Any


async def detect_captcha(page: Any, config: dict) -> bool:
    """Detect CAPTCHA presence — never attempt bypass."""
    captcha_cfg = config.get("captcha", {})
    for selector in captcha_cfg.get("iframe_selectors", []):
        locator = page.locator(selector)
        count = await locator.count() if hasattr(locator, "count") else 0
        if count > 0:
            return True
    try:
        body_text = (await page.inner_text("body")).lower()
    except Exception:
        body_text = ""
    for indicator in captcha_cfg.get("text_indicators", []):
        if indicator.lower() in body_text:
            return True
  # Also check page title
    try:
        title = (await page.title()).lower()
        for indicator in captcha_cfg.get("text_indicators", []):
            if indicator.lower() in title:
                return True
    except Exception:
        pass
    return False
