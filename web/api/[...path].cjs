/** Proxy /api/* to CAREER_OS_API_URL */
module.exports = async function handler(req, res) {
  try {
    const base = process.env.CAREER_OS_API_URL?.replace(/\/$/, "");

    let path = "";
    const segments = req.query && req.query.path;
    if (Array.isArray(segments)) path = segments.join("/");
    else if (typeof segments === "string") path = segments;

    if (!path && req.url) {
      const match = String(req.url).match(/\/api\/([^?]+)/);
      if (match) path = match[1];
    }

    if (!base) {
      res.statusCode = 503;
      res.setHeader("content-type", "application/json");
      res.end(
        JSON.stringify({
          detail:
            "Career OS API is not configured on Vercel. Set CAREER_OS_API_URL in Project → Settings → Environment Variables, then redeploy.",
        })
      );
      return;
    }

    const url = `${base}/api/${path}`;
    const headers = { "Bypass-Tunnel-Reminder": "true" };
    if (req.headers["content-type"]) headers["content-type"] = String(req.headers["content-type"]);
    if (req.headers.authorization) headers.authorization = String(req.headers.authorization);

    const init = { method: req.method || "GET", headers };
    if (req.method !== "GET" && req.method !== "HEAD" && req.body) {
      init.body = typeof req.body === "string" ? req.body : JSON.stringify(req.body);
    }

    const upstream = await fetch(url, init);
    const text = await upstream.text();
    res.statusCode = upstream.status;
    const contentType = upstream.headers.get("content-type");
    if (contentType) res.setHeader("content-type", contentType);
    res.end(text);
  } catch (err) {
    res.statusCode = 500;
    res.setHeader("content-type", "application/json");
    res.end(
      JSON.stringify({
        detail: "API proxy error",
        error: err && err.message ? err.message : String(err),
      })
    );
  }
};
