export type ResumeExperience = {
  title: string;
  employer: string;
  dates?: string;
  location?: string;
  bullets: string[];
};

export type BaseResume = {
  full_name: string;
  contact?: Record<string, string>;
  summary: string;
  experience: ResumeExperience[];
  education?: Array<{ institution: string; degree: string; dates?: string }>;
  skills?: string[];
};

export type TailoredResume = BaseResume & {
  changes_made: Array<{ section: string; reason: string }>;
};

export type CoverLetterResult = {
  full_text: string;
  word_count: number;
};
