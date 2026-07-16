# Career OS Autofill — Chrome Extension (MV3)

Free browser-extension autofill for job application forms, powered by your Career OS
profile and master resume. Supports **Workday**, **Greenhouse**, and **Lever** in this
first version.

It fills what it can confidently match — name, email, phone, LinkedIn, location,
resume upload, and yes/no work-authorization questions — and **never clicks
Submit/Apply**. You always review and submit yourself.

## Requirements

- A Career OS account with the backend running (default `http://localhost:8000`)
- Your profile filled in (Career OS → profile: legal name, phone, work authorization)
- At least one active master resume uploaded

## Load unpacked (local testing)

1. Open Chrome and go to `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. Click **Load unpacked** and select this `extension/` folder
4. Pin "Career OS Autofill" from the puzzle-piece menu

## Get an API token

The extension reuses Career OS JWT auth — no separate signup. Grab a token with:

```powershell
$body = '{"email":"user@example.com","password":"careeros-dev-password"}'
(Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json").access_token
```

or with curl:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"careeros-dev-password"}' | jq -r .access_token
```

Then click the extension icon, paste the token, set the backend URL if it is not
`http://localhost:8000`, hit **Save**, and use **Test connection** to confirm.

Tokens expire (default 7 days) — paste a fresh one when the button reports a
rejected token.

## Use it

1. Open a job application form on:
   - `*.myworkdayjobs.com` / `*.myworkdaysite.com` (Workday)
   - `boards.greenhouse.io` / `job-boards.greenhouse.io` (Greenhouse)
   - `jobs.lever.co` (Lever)
2. A floating **"Autofill from Career OS"** button appears bottom-right
3. Click it — filled fields are counted in a toast
4. Review everything, answer the questions it could not match, and submit manually

## Behavior notes

- Fields that already contain text are never overwritten
- Resume upload uses your active master resume (prefers the "General" label)
- Work-authorization dropdowns are answered yes/no from your profile's
  `work_authorization` (only `needs_sponsorship` answers "No" to
  authorized-to-work questions)
- If the backend is hosted somewhere other than localhost, add its origin to
  `host_permissions` in `manifest.json` and reload the extension

## Not in v1

- Other ATS platforms (iCIMS, Taleo, SuccessFactors, Ashby)
- Multi-page Workday flows beyond the first page's fields
- Custom screening questions / essay answers
- Auto-submit — deliberately out of scope; Career OS is human-in-the-loop
