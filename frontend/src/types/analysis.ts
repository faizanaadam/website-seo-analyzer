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

export interface TechnicalFindingItem {
  id: string;
  title: string;
  status: CheckStatus;
  summary: string;
  why_it_matters: string;
  evidence_found: string;
  suggested_action: string;
  affected_urls?: string[];
  is_inconclusive?: boolean;
}

export interface TechnicalSEOResultData {
  summary: {
    passed_count: number;
    needs_attention_count: number;
    issues_count: number;
    total_checks: number;
    health_score: number;
    summary_text: string;
    is_content_blocked?: boolean;
    reliability_notice?: string | null;
  };
  findings: TechnicalFindingItem[];
  inferred_category?: string;
}

export interface RawFetchDataPayload {
  success: boolean;
  initial_url: string;
  final_url: string;
  status_code?: number | null;
  response_time_ms?: number | null;
  content_type?: string | null;
  redirect_chain?: string[];
  robots_txt_present?: boolean;
  sitemap_xml_present?: boolean;
  content_accessible?: boolean;
  content_reliability?: string;
  parsed_data?: {
    title?: string | null;
    meta_description?: string | null;
    h1_tags?: string[];
    h2_tags?: string[];
    h3_tags?: string[];
    visible_word_count?: number;
    internal_links?: string[];
    detected_ctas?: Record<string, string[]>;
  } | null;
  error_type?: string | null;
  error_message?: string | null;
}

export interface AIRecommendationItemData {
  title: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  category: 'technical_seo' | 'content' | 'performance' | 'visibility' | 'conversion';
  explanation: string;
  business_impact: string;
  recommended_action: string;
  estimated_effort: 'quick' | 'moderate' | 'significant';
  anchor_finding_id?: string | null;
}

export interface AIAnalysisResultData {
  status: 'available' | 'unavailable' | 'partial';
  overall_assessment?: 'excellent' | 'good' | 'moderate' | 'needs_improvement' | 'critical' | null;
  executive_summary?: string | null;
  top_priorities: AIRecommendationItemData[];
  quick_wins: string[];
  strengths: string[];
  limitations: string[];
  reason?: string | null;
}

export interface AnalysisApiResponse {
  status: 'success' | 'error';
  message: string;
  target_url: string;
  fetch_data?: RawFetchDataPayload | null;
  technical_seo?: TechnicalSEOResultData | null;
  content_analysis?: ContentAnalysisResultData | null;
  pagespeed?: PageSpeedResultData | null;
  ai_insights?: AIAnalysisResultData | null;
  error?: string | null;
}

export interface AnalysisReportData {
  targetUrl: string;
  businessName: string;
  completedAt: string;
  isAccessBlocked?: boolean;
  reliabilityNotice?: string | null;
  overall: {
    passedCount: number;
    needsAttentionCount: number;
    issuesCount: number;
    summaryText: string;
    healthScore?: number;
  };
  quickWins: QuickWinItem[];
  technicalChecks: TechnicalCheckItem[];
  content: {
    servicesDetected: string[];
    dedicatedServicePages: boolean;
    homepageWordCount: number;
    callToActionDetected: string[];
    notes: string;
    contactInfo?: ContactInfoData | null;
    is_inconclusive?: boolean;
    inconclusive_reason?: string | null;
  };
  pagespeed?: PageSpeedResultData | null;
  ai_insights?: AIAnalysisResultData | null;
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
  content_depth: 'Thin' | 'Moderate' | 'Comprehensive' | 'Inconclusive';
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
  is_inconclusive?: boolean;
  inconclusive_reason?: string | null;
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

