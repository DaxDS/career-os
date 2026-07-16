import { MarketingFooter, MarketingHeader } from "@/components/marketing/marketing-chrome";

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingHeader />
      <main className="mx-auto max-w-3xl flex-1 px-4 py-16 prose prose-slate">
        <h1>Privacy Policy</h1>
        <p className="lead">
          CareerOS is designed with PIPEDA-oriented privacy practices. Your data is stored in Canada
          (Supabase ca-central-1 region).
        </p>

        <h2>What we collect</h2>
        <ul>
          <li>Account information (email, name) via Supabase Auth</li>
          <li>Profile data: work history, NOC mappings, immigration status, job preferences</li>
          <li>Resumes and tailored application materials you upload or generate</li>
          <li>Activity log of agent actions (transparency feature)</li>
          <li>Billing status via Stripe (we do not store card numbers)</li>
        </ul>

        <h2>How we use your data</h2>
        <p>
          To match jobs, classify NOC codes, evaluate pathway flags, tailor applications, and operate
          your account. We do not sell your personal information. AI processing uses Anthropic Claude
          with JSON-schema-validated outputs; resume tailoring never fabricates experience.
        </p>

        <h2>Your rights (PIPEDA)</h2>
        <ul>
          <li><strong>Access & export:</strong> Export all your data from Settings at any time</li>
          <li><strong>Deletion:</strong> Permanently delete your account and associated data</li>
          <li><strong>Transparency:</strong> Review the activity log of agent actions</li>
          <li><strong>Correction:</strong> Edit your profile, work history, and NOC mappings directly</li>
        </ul>

        <h2>Data location</h2>
        <p>
          Primary storage is in Canada (ca-central-1). Third-party processors (Anthropic, Stripe) may
          process data under their respective terms when you use those features.
        </p>

        <h2>Contact</h2>
        <p>
          Privacy inquiries: privacy@careeros.ca (placeholder — update before launch).
        </p>

        <p className="text-sm text-muted-foreground not-prose">
          Last updated: July 2025. This policy will be finalized with legal review before public launch.
        </p>
      </main>
      <MarketingFooter />
    </div>
  );
}
