/** Career OS Autofill content script.
 *  Detects Workday / Greenhouse / Lever application forms, shows a floating
 *  button, and fills fields it can confidently match. Never clicks Submit.
 */

(() => {
  if (window.__careerOsAutofillLoaded) return;
  window.__careerOsAutofillLoaded = true;

  // ---------- ATS detection ----------

  function detectAts() {
    const host = location.hostname;
    if (/myworkdayjobs\.com$|myworkdaysite\.com$/.test(host) || host.includes("myworkday")) {
      if (document.querySelector("[data-automation-id]")) return "workday";
    }
    if (/greenhouse\.io$/.test(host) || host.endsWith(".greenhouse.io")) {
      if (
        document.querySelector("#application_form, #application-form") ||
        document.querySelector('input[name="first_name"], #first_name')
      )
        return "greenhouse";
    }
    if (host === "jobs.lever.co") {
      if (document.querySelector(".application-form, form[action*='apply']")) return "lever";
    }
    return null;
  }

  // ---------- React-safe value setting ----------

  function setNativeValue(el, value) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function fillInput(el, value) {
    if (!el || !value || el.disabled || el.readOnly) return false;
    if (el.value && el.value.trim()) return false; // never overwrite user input
    setNativeValue(el, value);
    return true;
  }

  function fillFileInput(el, resumeFile) {
    if (!el || !resumeFile) return false;
    try {
      const bytes = Uint8Array.from(atob(resumeFile.base64), (c) => c.charCodeAt(0));
      const file = new File([bytes], resumeFile.name, { type: resumeFile.type });
      const dt = new DataTransfer();
      dt.items.add(file);
      el.files = dt.files;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    } catch (err) {
      console.warn("Career OS: file autofill failed", err);
      return false;
    }
  }

  function splitName(legalName) {
    const parts = (legalName || "").trim().split(/\s+/);
    if (parts.length === 0) return { first: "", last: "" };
    if (parts.length === 1) return { first: parts[0], last: "" };
    return { first: parts.slice(0, -1).join(" "), last: parts[parts.length - 1] };
  }

  // ---------- Work authorization (best-effort, checkbox/select/radio) ----------

  function isAuthorized(workAuthorization) {
    // Everything except needs_sponsorship can work without sponsorship.
    return workAuthorization && workAuthorization !== "needs_sponsorship";
  }

  function answerAuthorizationQuestions(data) {
    let filled = 0;
    const authorized = isAuthorized(data.workAuthorization);
    const needsSponsorship = data.workAuthorization === "needs_sponsorship";

    document.querySelectorAll("select").forEach((select) => {
      const label = labelTextFor(select);
      if (!label) return;
      let want = null;
      if (/authoriz|legally (able|entitled)|eligib.*work/i.test(label)) want = authorized;
      else if (/sponsor/i.test(label)) want = needsSponsorship;
      if (want === null || select.value) return;
      const option = [...select.options].find((o) =>
        want ? /^yes\b/i.test(o.text.trim()) : /^no\b/i.test(o.text.trim())
      );
      if (option) {
        setNativeValue(select, option.value);
        filled += 1;
      }
    });
    return filled;
  }

  function labelTextFor(el) {
    if (el.labels && el.labels.length) return el.labels[0].textContent || "";
    const id = el.getAttribute("id");
    if (id) {
      const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label) return label.textContent || "";
    }
    return el.closest("label")?.textContent || el.getAttribute("aria-label") || "";
  }

  // ---------- Per-ATS field maps ----------

  function fillWorkday(data) {
    const { first, last } = splitName(data.legalName);
    let filled = 0;
    const byId = (id) => document.querySelector(`input[data-automation-id="${id}"]`);
    filled += fillInput(byId("legalNameSection_firstName"), first) ? 1 : 0;
    filled += fillInput(byId("legalNameSection_lastName"), last) ? 1 : 0;
    filled += fillInput(byId("email"), data.email) ? 1 : 0;
    filled += fillInput(byId("phone-number"), data.phone) ? 1 : 0;
    filled += fillInput(byId("addressSection_city"), data.locationCity) ? 1 : 0;
    const fileInput = document.querySelector('input[data-automation-id="file-upload-input-ref"]');
    filled += fillFileInput(fileInput, data.resumeFile) ? 1 : 0;
    filled += answerAuthorizationQuestions(data);
    return filled;
  }

  function fillGreenhouse(data) {
    const { first, last } = splitName(data.legalName);
    let filled = 0;
    const q = (sel) => document.querySelector(sel);
    filled += fillInput(q('#first_name, input[name="first_name"]'), first) ? 1 : 0;
    filled += fillInput(q('#last_name, input[name="last_name"]'), last) ? 1 : 0;
    filled += fillInput(q('#email, input[name="email"]'), data.email) ? 1 : 0;
    filled += fillInput(q('#phone, input[name="phone"]'), data.phone) ? 1 : 0;
    filled += fillInput(
      q('input[name*="linkedin" i], input[id*="linkedin" i], input[autocomplete="url"]'),
      data.linkedinUrl
    )
      ? 1
      : 0;
    const fileInput = q('#resume, input[type="file"][name*="resume" i], input[type="file"]');
    filled += fillFileInput(fileInput, data.resumeFile) ? 1 : 0;
    filled += answerAuthorizationQuestions(data);
    return filled;
  }

  function fillLever(data) {
    let filled = 0;
    const q = (sel) => document.querySelector(sel);
    filled += fillInput(q('input[name="name"]'), data.legalName) ? 1 : 0;
    filled += fillInput(q('input[name="email"]'), data.email) ? 1 : 0;
    filled += fillInput(q('input[name="phone"]'), data.phone) ? 1 : 0;
    filled += fillInput(q('input[name="urls[LinkedIn]"]'), data.linkedinUrl) ? 1 : 0;
    filled += fillInput(
      q('input[name="location"]'),
      [data.locationCity, data.locationProvince].filter(Boolean).join(", ")
    )
      ? 1
      : 0;
    const fileInput = q('input[name="resume"], input[type="file"]');
    filled += fillFileInput(fileInput, data.resumeFile) ? 1 : 0;
    filled += answerAuthorizationQuestions(data);
    return filled;
  }

  const FILLERS = { workday: fillWorkday, greenhouse: fillGreenhouse, lever: fillLever };

  // ---------- UI ----------

  function toast(message, isError = false) {
    const el = document.createElement("div");
    el.className = "careeros-toast" + (isError ? " careeros-toast-error" : "");
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }

  function mountButton(ats) {
    const button = document.createElement("button");
    button.className = "careeros-autofill-btn";
    button.type = "button";
    button.textContent = "Autofill from Career OS";
    button.addEventListener("click", () => {
      button.disabled = true;
      button.textContent = "Filling…";
      chrome.runtime.sendMessage({ type: "careeros.fetchAutofillData" }, (response) => {
        button.disabled = false;
        button.textContent = "Autofill from Career OS";
        if (!response?.ok) {
          toast(response?.error || "Career OS: could not reach backend", true);
          return;
        }
        const filled = FILLERS[ats](response.data);
        toast(
          filled > 0
            ? `Career OS filled ${filled} field${filled === 1 ? "" : "s"}. Review before submitting — nothing was submitted.`
            : "Career OS: no empty matching fields found on this page.",
          filled === 0
        );
      });
    });
    document.body.appendChild(button);
  }

  // ---------- Boot (SPA-aware: Workday renders late) ----------

  let mounted = false;
  function tryMount() {
    if (mounted) return;
    const ats = detectAts();
    if (ats) {
      mounted = true;
      mountButton(ats);
    }
  }

  tryMount();
  const observer = new MutationObserver(() => tryMount());
  observer.observe(document.documentElement, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 30000); // stop watching after 30s
})();
