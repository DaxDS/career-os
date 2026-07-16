const apiUrlInput = document.getElementById("apiUrl");
const apiTokenInput = document.getElementById("apiToken");
const statusEl = document.getElementById("status");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

chrome.storage.local.get(["apiUrl", "apiToken"]).then(({ apiUrl, apiToken }) => {
  apiUrlInput.value = apiUrl || "http://localhost:8000";
  apiTokenInput.value = apiToken || "";
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({
    apiUrl: apiUrlInput.value.trim() || "http://localhost:8000",
    apiToken: apiTokenInput.value.trim(),
  });
  setStatus("Saved.");
});

document.getElementById("test").addEventListener("click", async () => {
  await chrome.storage.local.set({
    apiUrl: apiUrlInput.value.trim() || "http://localhost:8000",
    apiToken: apiTokenInput.value.trim(),
  });
  setStatus("Testing…");
  chrome.runtime.sendMessage({ type: "careeros.testConnection" }, (response) => {
    if (response?.ok) setStatus(`Connected as ${response.data.email}`);
    else setStatus(response?.error || "Connection failed", true);
  });
});
