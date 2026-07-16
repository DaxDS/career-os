import re
import urllib.request

html = urllib.request.urlopen(
    urllib.request.Request(
        "https://www.jobbank.gc.ca/jobsearch/jobposting/49788195",
        headers={"User-Agent": "Mozilla/5.0 CareerOS/1.0"},
    ),
    timeout=30,
).read().decode("utf-8", "replace")

for pattern in [
    r'property="description"[^>]*content="([^"]+)"',
    r"<div[^>]*class=\"[^\"]*job-posting-details[^\"]*\"[^>]*>(.*?)</div>",
]:
    m = re.search(pattern, html, re.S | re.I)
    print(pattern[:40], "->", (m.group(1)[:150] if m else "none"))
