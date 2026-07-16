"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CANADIAN_PROVINCES } from "@/lib/onboarding/constants";

const selectClassName =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

export function WaitlistForm() {
  const t = useTranslations("waitlist");
  const tc = useTranslations("common");
  const [email, setEmail] = useState("");
  const [province, setProvince] = useState("");
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = e.currentTarget;
    const honeypot = (form.elements.namedItem("website") as HTMLInputElement | null)?.value ?? "";

    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          province: province || null,
          source: "landing",
          website: honeypot,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.error === "string" ? data.error : t("errorGeneric"));
        return;
      }

      setSuccess(true);
      setEmail("");
      setProvince("");
      form.reset();
    } catch {
      setError(t("errorGeneric"));
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div
        className="rounded-lg border border-emerald-200 bg-emerald-50 px-6 py-4 text-emerald-900"
        role="status"
      >
        <p className="font-medium">{t("successTitle")}</p>
        <p className="mt-1 text-sm">{t("successMessage")}</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 text-left">
      <div className="space-y-2">
        <Label htmlFor="waitlist-email">{t("emailLabel")}</Label>
        <Input
          id="waitlist-email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder={t("emailPlaceholder")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="bg-background"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="waitlist-province">{t("provinceLabel")}</Label>
        <select
          id="waitlist-province"
          name="province"
          className={selectClassName}
          value={province}
          onChange={(e) => setProvince(e.target.value)}
        >
          <option value="">{t("provinceOptional")}</option>
          {CANADIAN_PROVINCES.map((code) => (
            <option key={code} value={code}>
              {t(`provinces.${code}`)}
            </option>
          ))}
        </select>
      </div>

      {/* Honeypot — hidden from users, filled by bots */}
      <input
        type="text"
        name="website"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        className="absolute -left-[9999px] h-0 w-0 opacity-0"
      />

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? tc("loading") : t("submit")}
      </Button>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
