/**
 * Generated from Supabase schema via `npm run db:types`.
 * Placeholder types for Phase 1 — regenerate after `supabase db reset`.
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          full_name: string | null;
          province: string | null;
          city: string | null;
          status: ImmigrationStatus;
          permit_expiry: string | null;
          language_en: LanguageProficiency;
          language_fr: LanguageProficiency;
          target_titles: string[];
          salary_min: number | null;
          remote_pref: RemotePreference;
          daily_send_cap: number;
          locale: string;
          onboarding_completed: boolean;
          onboarding_step: number;
          match_score_threshold: number;
          created_at: string;
          updated_at: string;
        };
        Insert: Partial<Database["public"]["Tables"]["profiles"]["Row"]> & { id: string };
        Update: Partial<Database["public"]["Tables"]["profiles"]["Row"]>;
      };
      work_history: {
        Row: {
          id: string;
          user_id: string;
          title: string;
          employer: string | null;
          country: string;
          province: string | null;
          start_date: string | null;
          end_date: string | null;
          is_current: boolean;
          duties_text: string | null;
          mapped_noc_code: string | null;
          mapped_teer: number | null;
          noc_confirmed: boolean;
          months_canadian_experience: number;
          sort_order: number;
          created_at: string;
          updated_at: string;
        };
      };
      jobs: {
        Row: {
          id: string;
          source: string;
          external_id: string | null;
          url: string;
          company: string | null;
          title: string;
          province: string | null;
          city: string | null;
          remote: boolean;
          posted_at: string | null;
          noc_code: string | null;
          teer_level: number | null;
          noc_confidence: number | null;
          pathway_flags: Json;
        };
      };
      matches: {
        Row: {
          id: string;
          user_id: string;
          job_id: string;
          match_score: number;
          score_breakdown: Json;
          pathway_flags: Json;
          status: MatchStatus;
        };
      };
    };
    Functions: {
      data_export: { Returns: Json };
      delete_user_account: { Returns: undefined };
    };
  };
}

export type ImmigrationStatus =
  | "citizen"
  | "pr"
  | "pgwp"
  | "closed_permit"
  | "open_permit"
  | "outside_canada";

export type LanguageProficiency =
  | "none"
  | "basic"
  | "intermediate"
  | "advanced"
  | "native";

export type RemotePreference = "onsite" | "hybrid" | "remote" | "any";

export type MatchStatus = "new" | "queued" | "approved" | "rejected" | "expired";
