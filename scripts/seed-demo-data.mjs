/**
 * Seed demo account + sample matches, pathway report, and activity for sales demos.
 *
 * Usage (from repo root):
 *   NEXT_PUBLIC_SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... npm run seed:demo-data
 */
import { createClient } from "@supabase/supabase-js";
import { createHash } from "node:crypto";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
let serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

const PROJECT_REF = "nvsxswvdktnphktrrxlg";
const MANAGEMENT_API = "https://api.supabase.com/v1";

async function fetchServiceRoleKey() {
  const accessToken = process.env.SUPABASE_ACCESS_TOKEN;
  if (!accessToken) return null;

  const res = await fetch(`${MANAGEMENT_API}/projects/${PROJECT_REF}/api-keys?reveal=true`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) return null;

  const keys = await res.json();
  const list = Array.isArray(keys) ? keys : keys?.data || [];
  const service =
    list.find((k) => k.name === "service_role") ||
    list.find((k) => k?.api_key?.includes?.("service_role"));
  return service?.api_key ?? null;
}

const DEMO_EMAIL = "demo@careeros.app";
const DEMO_PASSWORD = "careeros-dev-password";
const DEMO_NAME = "Alex Chen (Demo)";

const DEMO_JOBS = [
  {
    slug: "demo-sw-dev-halifax",
    source: "job_bank",
    external_id: "demo-21232-hfx",
    title: "Software Developer",
    company: "Atlantic Tech Solutions",
    city: "Halifax",
    province: "NS",
    url: "https://www.jobbank.gc.ca/jobsearch/jobposting/demo-21232",
    noc_code: "21232",
    teer_level: 1,
    noc_confidence: 0.92,
    wage_offered: 48,
    wage_median_region: 40,
    bilingual_required: false,
    match_score: 78,
    gaps: ["Add one more year of Canadian experience to strengthen PNP points."],
    parsed_requirements: {
      requirements: [
        "3+ years software development experience",
        "React and Node.js",
        "PostgreSQL or similar relational databases",
        "Eligible to work in Canada without LMIA",
      ],
      skills: ["TypeScript", "React", "Node.js", "PostgreSQL", "REST APIs"],
    },
    pathway_flags: {
      ee_eligible: true,
      ee_categories: ["STEM"],
      pnp_streams: ["ns_in_demand"],
      aip_relevant: true,
    },
  },
  {
    slug: "demo-data-analyst-toronto",
    source: "job_bank",
    external_id: "demo-21223-tor",
    title: "Data Analyst",
    company: "Maple Analytics Inc.",
    city: "Toronto",
    province: "ON",
    url: "https://www.jobbank.gc.ca/jobsearch/jobposting/demo-21223",
    noc_code: "21223",
    teer_level: 1,
    noc_confidence: 0.88,
    wage_offered: 42,
    wage_median_region: 38,
    bilingual_required: false,
    match_score: 74,
    gaps: ["Highlight SQL and dashboard projects on your resume."],
    pathway_flags: {
      ee_eligible: true,
      ee_categories: ["STEM"],
      pnp_streams: ["oinp_human_capital"],
      aip_relevant: false,
    },
  },
  {
    slug: "demo-devops-calgary",
    source: "job_bank",
    external_id: "demo-21231-yyc",
    title: "DevOps Engineer",
    company: "Prairie Cloud Co.",
    city: "Calgary",
    province: "AB",
    url: "https://www.jobbank.gc.ca/jobsearch/jobposting/demo-21231-devops",
    noc_code: "21231",
    teer_level: 1,
    noc_confidence: 0.85,
    wage_offered: 52,
    wage_median_region: 45,
    bilingual_required: false,
    match_score: 71,
    gaps: ["AWS certification would improve match score."],
    pathway_flags: {
      ee_eligible: true,
      ee_categories: ["STEM"],
      pnp_streams: ["aaip_tech"],
      aip_relevant: false,
    },
  },
  {
    slug: "demo-ux-vancouver",
    source: "job_bank",
    external_id: "demo-52120-yvr",
    title: "UX Designer",
    company: "Pacific Digital Studio",
    city: "Vancouver",
    province: "BC",
    url: "https://www.jobbank.gc.ca/jobsearch/jobposting/demo-52120",
    noc_code: "52120",
    teer_level: 2,
    noc_confidence: 0.8,
    wage_offered: 36,
    wage_median_region: 34,
    bilingual_required: false,
    match_score: 68,
    gaps: ["Portfolio link recommended for design roles."],
    pathway_flags: {
      ee_eligible: true,
      ee_categories: [],
      pnp_streams: ["bc_pnp_skilled_worker"],
      aip_relevant: false,
    },
  },
  {
    slug: "demo-ba-ottawa",
    source: "job_bank",
    external_id: "demo-11202-yow",
    title: "Business Analyst",
    company: "Capital Policy Group",
    city: "Ottawa",
    province: "ON",
    url: "https://www.jobbank.gc.ca/jobsearch/jobposting/demo-11202",
    noc_code: "11202",
    teer_level: 1,
    noc_confidence: 0.83,
    wage_offered: 40,
    wage_median_region: 39,
    bilingual_required: true,
    match_score: 66,
    gaps: ["French intermediate preferred for bilingual Ottawa roles."],
    pathway_flags: {
      ee_eligible: true,
      ee_categories: [],
      pnp_streams: ["oinp_french_speaking"],
      aip_relevant: false,
    },
  },
];

const DEMO_PATHWAY_REPORT = {
  generated_at: new Date().toISOString(),
  disclaimer:
    "Informational only, based on published program criteria — not immigration advice.",
  profile_summary: {
    status: "pgwp",
    province: "NS",
    permit_expiry: "2027-06-01",
    language_en: "advanced",
    language_fr: "basic",
  },
  canadian_experience: {
    total_months: 14,
    by_noc: { "21232": 14 },
    primary_noc: "21232",
    primary_teer: 1,
  },
  pathway_flags: {
    ee_eligible: true,
    ee_categories: ["STEM"],
    pnp_streams: ["ns_in_demand", "oinp_human_capital"],
    aip_relevant: true,
  },
  ee_teer_eligible: true,
  recommendations: [
    "Target TEER 0–3 NOC 21232 roles in Nova Scotia — strong AIP and NS PNP alignment.",
    "Keep permit expiry in view; prioritize employers open to PGWP-to-PR pathways.",
    "Improve French to intermediate to unlock additional OINP and EE category draws.",
  ],
};

const DEMO_WORK_HISTORY = [
  {
    title: "Software Developer",
    employer: "Maritime Digital Ltd.",
    country: "CA",
    province: "NS",
    start_date: "2024-04-01",
    is_current: true,
    duties_text:
      "Built customer-facing web features with React and Node.js. Shipped weekly releases with QA and product. Maintained PostgreSQL-backed APIs used by 12k monthly users.",
    mapped_noc_code: "21232",
    mapped_teer: 1,
    noc_confirmed: true,
    months_canadian_experience: 14,
    sort_order: 0,
  },
];

const DEMO_ACTIVITY = [
  {
    action: "discovery_completed",
    summary: "Found 5 eligible matches after permit and LMIA filters.",
    metadata: { sources: ["job_bank"], matches: 5, filtered: 12 },
  },
  {
    action: "jobs_filtered",
    summary: "Removed 12 jobs requiring LMIA or security clearance you don't hold.",
    metadata: { filtered_count: 12 },
  },
  {
    action: "pathway_report_generated",
    summary: "Pathway report generated for PGWP profile in Nova Scotia.",
    metadata: { ee_eligible: true },
  },
];

function dedupeHash(slug) {
  return createHash("sha256").update(`careeros-demo:${slug}`).digest("hex");
}

async function main() {
  const supabaseUrl =
    url || process.env.NEXT_PUBLIC_SUPABASE_URL || `https://${PROJECT_REF}.supabase.co`;
  serviceKey = serviceKey || (await fetchServiceRoleKey());

  if (!supabaseUrl || !serviceKey) {
    console.error(
      "Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ACCESS_TOKEN to fetch it)"
    );
    process.exit(1);
  }

  const admin = createClient(supabaseUrl, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  const user = await ensureDemoUser(admin);
  await seedProfile(admin, user.id);
  await seedJobsAndMatches(admin, user.id);
  await seedWorkHistory(admin, user.id);
  await seedPathwayReport(admin, user.id);
  await seedActivity(admin, user.id);
  console.log("\nDemo ready:");
  console.log(`  Email:    ${DEMO_EMAIL}`);
  console.log(`  Password: ${DEMO_PASSWORD}`);
  console.log("  Login at /login → dashboard shows 5 matches + pathway report");
}

async function ensureDemoUser(admin) {
  const { data: listed } = await admin.auth.admin.listUsers({ perPage: 200 });
  let user = listed?.users?.find((u) => u.email === DEMO_EMAIL);

  if (!user) {
    const { data, error } = await admin.auth.admin.createUser({
      email: DEMO_EMAIL,
      password: DEMO_PASSWORD,
      email_confirm: true,
      user_metadata: { full_name: DEMO_NAME },
    });
    if (error) throw new Error(`Create demo user failed: ${error.message}`);
    user = data.user;
    console.log(`Created demo user: ${DEMO_EMAIL}`);
  } else {
    await admin.auth.admin.updateUserById(user.id, {
      password: DEMO_PASSWORD,
      email_confirm: true,
      user_metadata: { full_name: DEMO_NAME },
    });
    console.log(`Updated demo user: ${DEMO_EMAIL}`);
  }

  return user;
}

async function seedProfile(admin, userId) {
  const { error } = await admin.from("profiles").upsert(
    {
      id: userId,
      full_name: DEMO_NAME,
      province: "NS",
      city: "Halifax",
      status: "pgwp",
      permit_expiry: "2027-06-01",
      language_en: "advanced",
      language_fr: "basic",
      target_titles: ["Software Developer", "Data Analyst", "DevOps Engineer"],
      onboarding_completed: true,
      onboarding_step: 5,
      match_score_threshold: 65,
    },
    { onConflict: "id" }
  );
  if (error) throw new Error(`Profile upsert failed: ${error.message}`);
}

async function seedJobsAndMatches(admin, userId) {
  await admin.from("matches").delete().eq("user_id", userId);

  for (const demo of DEMO_JOBS) {
    const hash = dedupeHash(demo.slug);
    const { data: job, error: jobError } = await admin
      .from("jobs")
      .upsert(
        {
          source: demo.source,
          external_id: demo.external_id,
          url: demo.url,
          company: demo.company,
          title: demo.title,
          province: demo.province,
          city: demo.city,
          noc_code: demo.noc_code,
          teer_level: demo.teer_level,
          noc_confidence: demo.noc_confidence,
          wage_offered: demo.wage_offered,
          wage_median_region: demo.wage_median_region,
          bilingual_required: demo.bilingual_required,
          lmia_flag: false,
          clearance_required: "none",
          dedupe_hash: hash,
          parsed_requirements: demo.parsed_requirements || {},
        },
        { onConflict: "dedupe_hash" }
      )
      .select("id")
      .single();

    if (jobError) throw new Error(`Job upsert failed (${demo.title}): ${jobError.message}`);

    const { error: matchError } = await admin.from("matches").insert({
      user_id: userId,
      job_id: job.id,
      match_score: demo.match_score,
      score_breakdown: { gaps: demo.gaps },
      pathway_flags: demo.pathway_flags,
      status: "new",
    });
    if (matchError) throw new Error(`Match insert failed (${demo.title}): ${matchError.message}`);
  }

  console.log(`Seeded ${DEMO_JOBS.length} demo jobs + matches`);
}

async function seedPathwayReport(admin, userId) {
  await admin.from("pathway_reports").delete().eq("user_id", userId);
  const { error } = await admin.from("pathway_reports").insert({
    user_id: userId,
    report_json: DEMO_PATHWAY_REPORT,
  });
  if (error) throw new Error(`Pathway report failed: ${error.message}`);
}

async function seedWorkHistory(admin, userId) {
  await admin.from("work_history").delete().eq("user_id", userId);
  const { error } = await admin.from("work_history").insert(
    DEMO_WORK_HISTORY.map((row) => ({ ...row, user_id: userId }))
  );
  if (error) throw new Error(`Work history failed: ${error.message}`);
}

async function seedActivity(admin, userId) {
  await admin.from("activity_log").delete().eq("user_id", userId);
  const { error } = await admin.from("activity_log").insert(
    DEMO_ACTIVITY.map((row) => ({
      user_id: userId,
      action: row.action,
      summary: row.summary,
      metadata: row.metadata,
    }))
  );
  if (error) throw new Error(`Activity log failed: ${error.message}`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
