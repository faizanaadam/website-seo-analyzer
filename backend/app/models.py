from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.utils.url_helpers import normalize_url


class HealthResponse(BaseModel):
    status: str = "ok"
    message: str = "Website SEO & Visibility Analyser backend is running"


class AnalysisRequest(BaseModel):
    url: str

    def get_normalized_url(self) -> str:
        return normalize_url(self.url)


class MissingAltImageModel(BaseModel):
    src: str
    raw_src: Optional[str] = None


class ParsedHTMLModel(BaseModel):
    title: Optional[str] = None
    title_length: int = 0
    meta_description: Optional[str] = None
    meta_description_length: int = 0
    canonical_url: Optional[str] = None
    viewport_meta: Optional[str] = None
    h1_tags: List[str] = Field(default_factory=list)
    h1_count: int = 0
    h2_tags: List[str] = Field(default_factory=list)
    h2_count: int = 0
    h3_tags: List[str] = Field(default_factory=list)
    h3_count: int = 0
    total_images: int = 0
    missing_alt_count: int = 0
    images_missing_alt: List[Dict[str, str]] = Field(default_factory=list)
    structured_data_types: List[str] = Field(default_factory=list)
    structured_data_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    internal_links_count: int = 0
    internal_links: List[str] = Field(default_factory=list)
    key_subpages: Dict[str, List[str]] = Field(default_factory=dict)
    visible_word_count: int = 0
    visible_text_snippet: str = ""
    is_javascript_heavy: bool = False
    javascript_rendering_note: Optional[str] = None
    detected_ctas: Dict[str, List[str]] = Field(default_factory=dict)


class RawFetchData(BaseModel):
    success: bool
    initial_url: str
    final_url: str
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    content_type: Optional[str] = None
    redirect_chain: List[str] = Field(default_factory=list)
    robots_txt_present: bool = False
    sitemap_xml_present: bool = False
    parsed_data: Optional[ParsedHTMLModel] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class TechnicalFindingModel(BaseModel):
    id: str
    title: str
    status: str  # 'pass' | 'needs_attention' | 'fail'
    summary: str
    why_it_matters: str
    evidence_found: str
    suggested_action: str
    affected_urls: List[str] = Field(default_factory=list)


class TechnicalSEOSummaryModel(BaseModel):
    passed_count: int
    needs_attention_count: int
    issues_count: int
    total_checks: int
    health_score: int
    summary_text: str


class TechnicalSEOResultModel(BaseModel):
    summary: TechnicalSEOSummaryModel
    findings: List[TechnicalFindingModel] = Field(default_factory=list)
    inferred_category: str = "general"


class AnalysisResponse(BaseModel):
    status: str
    message: str
    target_url: str
    fetch_data: Optional[RawFetchData] = None
    technical_seo: Optional[TechnicalSEOResultModel] = None
    error: Optional[str] = None
