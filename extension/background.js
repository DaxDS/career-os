/** Service worker: talks to the Career OS API so content scripts never hold the token. */

const DEFAULT_API_URL = "http://localhost:8000";

async function getConfig() {
  const { apiUrl, apiToken } = await chrome.storage.local.get(["apiUrl", "apiToken"]);
  return { apiUrl: (apiUrl || DEFAULT_API_URL).replace(/\/$/, ""), apiToken: apiToken || "" };
}

async function apiGet(path, expectJson = true) {
  const { apiUrl, apiToken } = await getConfig();
  if (!apiToken) throw new Error("No API token set. Click the extension icon to add one.");
  const response = await fetch(`${apiUrl}/api/v1${path}`, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (response.status === 401) throw new Error("Token rejected. Paste a fresh token in the extension popup.");
  if (!response.ok) throw new Error(`Career OS API error ${response.status} on ${path}`);
  return expectJson ? response.json() : response;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

async function fetchAutofillData() {
  const [me, profile, resumes] = await Promise.all([
    apiGet("/auth/me"),
    apiGet("/profile"),
    apiGet("/resumes/master"),
  ]);

  // Prefer the active "General" resume, else any active one.
  const active = resumes.filter((r) => r.is_active);
  const resumeMeta =
    active.find((r) => /general/i.test(r.label)) || active[0] || null;

  let resumeFile = null;
  if (resumeMeta) {
    try {
      const fileResponse = await apiGet(`/resumes/master/${resumeMeta.id}/download`, false);
      const buffer = await fileResponse.arrayBuffer();
      resumeFile = {
        name: resumeMeta.original_filename || "resume.pdf",
        type: fileResponse.headers.get("content-type") || "application/octet-stream",
        base64: arrayBufferToBase64(buffer),
      };
    } catch (err) {
      console.warn("Career OS: resume download failed, skipping file autofill", err);
    }
  }

  return {
    email: me.email,
    legalName: profile.legal_name || "",
    phone: profile.phone || "",
    linkedinUrl: profile.linkedin_url || "",
    locationCity: profile.location_city || "",
    locationProvince: profile.location_province || "",
    workAuthorization: profile.work_authorization || "",
    resumeFile,
  };
}

async function testConnection() {
  const me = await apiGet("/auth/me");
  return { ok: true, email: me.email };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const handlers = {
    "careeros.fetchAutofillData": fetchAutofillData,
    "careeros.testConnection": testConnection,
  };
  const handler = handlers[message?.type];
  if (!handler) return false;
  handler()
    .then((data) => sendResponse({ ok: true, data }))
    .catch((err) => sendResponse({ ok: false, error: err.message }));
  return true; // keep the message channel open for the async response
});
