export type AppState = 'input' | 'loading' | 'results' | 'error';

export type CheckStatus = 'pass' | 'needs_attention' | 'fail';

export type EpistemicStatus = 'fact' | 'inference' | 'unknown';

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'none';

export interface HealthResponse {
  status: string;
  message: string;
}

export interface AnalysisRequest {
  url: string;
}

export interface AnalysisResponse {
  status: string;
  message: string;
  target_url: string;
}

export interface TechnicalCheckItem {
  id: string;
  name: string;
  status: CheckStatus;
  summary: string;
  whyItMatters: string;
  evidence: string;
  suggestedAction: string;
}

export interface QuickWinItem {
  id: string;
  title: string;
  impact: 'High' | 'Medium' | 'Low';
  timeEstimate: string;
  why: string;
}

export interface ContentFindingItem {
  label: string;
  value: string;
  detail?: string;
  status?: CheckStatus;
}

export interface ICPFindingItem {
  category: string;
  value: string;
  status: EpistemicStatus;
  confidence?: ConfidenceLevel;
  evidence?: string;
}

export interface CompetitorItem {
  name: string;
  rating: number;
  reviewCount: number;
  highlight: string;
}

export interface ProjectItem {
  id: string;
  title: string;
  impact: 'High' | 'Medium' | 'Low';
  estimatedEffort: string;
  why: string;
}

export interface AnalysisReportData {
  targetUrl: string;
  businessName: string;
  completedAt: string;
  overall: {
    passedCount: number;
    needsAttentionCount: number;
    issuesCount: number;
    summaryText: string;
  };
  quickWins: QuickWinItem[];
  technicalChecks: TechnicalCheckItem[];
  content: {
    servicesDetected: string[];
    dedicatedServicePages: boolean;
    homepageWordCount: number;
    callToActionDetected: string[];
    notes: string;
  };
  icp: {
    summary: string;
    items: ICPFindingItem[];
  };
  competitors: {
    disclaimer: string;
    items: CompetitorItem[];
    strengths: string[];
    opportunities: string[];
  };
  biggerProjects: ProjectItem[];
}

export interface PageContentItemData {
  url: string;
  page_name: string;
  word_count: number;
  content_depth: 'Thin' | 'Moderate' | 'Comprehensive';
  headings: string[];
  is_service_page: boolean;
}

export interface ContactInfoData {
  phones: string[];
  emails: string[];
  address?: string | null;
  opening_hours?: string[] | null;
}

export interface CTAData {
  phones: string[];
  emails: string[];
  whatsapp: string[];
  booking_links: string[];
  booking_providers: string[];
}

export interface ServiceStructureData {
  has_dedicated_service_pages: boolean;
  services_mainly_on_homepage: boolean;
  service_pages_count: number;
  detected_services: string[];
  service_details: Array<{ name: string; source: string; url?: string }>;
}

export interface ContentAnalysisResultData {
  pages_analyzed: PageContentItemData[];
  total_pages_analyzed: number;
  homepage_word_count: number;
  average_word_count: number;
  contact_info: ContactInfoData;
  ctas: CTAData;
  services_structure: ServiceStructureData;
  summary: string;
}

export interface PageSpeedMetricsData {
  fcp?: string | null;
  lcp?: string | null;
  cls?: number | null;
  inp?: string | null;
  tbt?: string | null;
}

export interface PageSpeedResultData {
  status: 'available' | 'unavailable';
  performance_score?: number | null;
  metrics?: PageSpeedMetricsData | null;
  reason?: string | null;
}

