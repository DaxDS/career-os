import { MarketingFooter, MarketingHeader } from "@/components/marketing/marketing-chrome";

export default function TermsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingHeader />
      <main className="mx-auto max-w-3xl flex-1 px-4 py-16 prose prose-slate">
        <h1>Terms of Service</h1>
        <p className="lead">
          By using CareerOS, you agree to these terms. CareerOS is a job-search assistance tool — not
          an immigration consultant, recruiter, or employer.
        </p>

        <h2>Service description</h2>
        <p>
          CareerOS helps you discover jobs, understand NOC/TEER classification, compare wages, evaluate
          published immigration pathway criteria, and prepare tailored application materials. You review
          and submit all applications yourself unless you explicitly approve dispatch.
        </p>

        <h2>Not immigration advice</h2>
        <p>
          Pathway flags and reports are informational only, based on publicly available program criteria.
          They are not a guarantee of eligibility. Consult a licensed RCIC or immigration lawyer for
          decisions affecting your status in Canada.
        </p>

        <h2>Acceptable use</h2>
        <ul>
          <li>Do not use the service to spam employers or misrepresent qualifications</li>
          <li>Do not attempt to bypass daily send caps or plan limits</li>
          <li>Provide accurate information in your profile and work history</li>
        </ul>

        <h2>Subscriptions</h2>
        <p>
          Pro plans are billed monthly in CAD via Stripe. Cancel anytime; access continues until the
          end of the billing period. Refunds are handled per Stripe and our refund policy at launch.
        </p>

        <h2>Limitation of liability</h2>
        <p>
          CareerOS is provided &quot;as is.&quot; We are not liable for hiring outcomes, immigration
          decisions, or third-party job posting accuracy.
        </p>
      </main>
      <MarketingFooter />
    </div>
  );
}
