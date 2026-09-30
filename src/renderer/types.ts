export interface Vacancy {
  id: string;
  title: string;
  employer: string;
  url: string;
  salary: string;
  is_remote: boolean | number;
  role_category: string;
  full_description: string;
  cover_letter: string;
  list_name: 'backlog' | 'approved' | 'applied' | 'interview' | 'archive';
  selected_resume_id: string;
  selected_materials: string[];
  has_questionnaire: boolean | number;
  manual_review_note?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SearchQueryItem {
  id: string;
  name: string;
  query: string;
  resume_key: string;
  salary_min: number;
  schedule: string;
  enabled: boolean;
}

export interface PortfolioLink {
  id: string;
  title: string;
  url: string;
  category?: string;
}

export interface AppSettings {
  hh_token: string;
  hh_xsrf: string;
  llm_provider: string;
  llm_api_key: string;
  llm_model: string;
  llm_key_gemini?: string;
  llm_key_deepseek?: string;
  llm_key_openrouter?: string;
  llm_key_groq?: string;
  llm_model_gemini?: string;
  llm_model_deepseek?: string;
  llm_model_openrouter?: string;
  llm_model_groq?: string;
  scan_time: string;
  check_interval_min: string;
  search_queries: string;
  custom_contacts?: string;
  custom_portfolio_links?: string;
  agent_system_prompt?: string;
  last_scan_date?: string;
  last_scan_time?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'error' | 'success' | 'hh';
  message: string;
}

declare global {
  interface Window {
    electronAPI: {
      getVacancies: (listName?: string) => Promise<{ success: boolean; vacancies?: Vacancy[]; error?: string }>;
      moveVacancy: (vacancyId: string, newList: string) => Promise<{ success: boolean }>;
      updateCustomization: (vacancyId: string, resumeId: string, materials: string[], coverLetter: string) => Promise<{ success: boolean }>;
      applyVacancy: (vacancyId: string) => Promise<{ success: boolean; error?: string; message?: string }>;
      runScan: () => Promise<{ success: boolean; scan_result?: any; error?: string }>;
      checkNegotiations: () => Promise<{ success: boolean; negotiations_result?: any; error?: string }>;
      clearArchive: () => Promise<{ success: boolean; cleared?: number; error?: string }>;
      getSettings: () => Promise<{ success: boolean; settings?: Record<string, string> }>;
      setSetting: (key: string, value: string) => Promise<{ success: boolean }>;
      checkHhAuth: () => Promise<{ authenticated: boolean; user?: string; status?: string; error?: string }>;
      startHhAuth: () => Promise<any>;
      getKnowledge: (name: string) => Promise<{ success: boolean; content: string }>;
      saveKnowledge: (name: string, content: string) => Promise<{ success: boolean }>;
      migratePlanka: () => Promise<{ success: boolean; imported_count?: number; error?: string }>;
      generateLetter: (vacancyId: string) => Promise<{ success: boolean; cover_letter?: string; error?: string }>;
      applyApproved: () => Promise<{ success: boolean; total?: number; sent?: number; errors?: string[]; error?: string }>;
      refetchVacancy: (vacancyId: string) => Promise<{ success: boolean; vacancy?: Vacancy; error?: string }>;
      onNegotiationUpdate: (callback: (data: any) => void) => void;
      onEngineLog: (callback: (log: LogEntry) => void) => void;
    };
  }
}
