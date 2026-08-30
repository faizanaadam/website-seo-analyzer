import asyncio
import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    HealthResponse,
    AnalysisRequest,
    AnalysisResponse,
    RawFetchData,
    TechnicalSEOResultModel,
    ContentAnalysisResultModel,
    PageSpeedResultModel,
)
from app.services.fetcher import fetch_website, DEFAULT_HEADERS
from app.services.technical_seo import evaluate_technical_seo
from app.services.content_analysis import analyze_content
from app.services.pagespeed import get_pagespeed_insights
from app.config import settings

app = FastAPI(
    title="Website SEO & Visibility Analyser API",
    description="Backend API for automated SEO, Content, ICP, PageSpeed, and Competitor visibility assessment.",
    version="0.5.0",
)

# Enable CORS for mobile and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """Health check endpoint for checking backend availability."""
    return HealthResponse(
        status="ok",
        message="Website SEO & Visibility Analyser backend is running",
    )


@app.post("/api/analyse", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyse_site(request: AnalysisRequest) -> AnalysisResponse:
    """
    Phase 5: Fetches website, evaluates Technical SEO, performs multi-page Content & CTA Analysis,
    and integrates Google PageSpeed Insights concurrently.
    """
    result = await fetch_website(request.url)

    if not result.success:
        if result.error_type == "invalid_url":
            raise HTTPException(
                status_code=422,
                detail=result.error_message or "Invalid website URL provided.",
            )

        # Run technical SEO evaluation on failed fetch to return clean finding structure
        tech_eval = evaluate_technical_seo(result)

        return AnalysisResponse(
            status="error",
            message=result.error_message or "Failed to fetch website.",
            target_url=request.url,
            fetch_data=RawFetchData(**result.to_dict()),
            technical_seo=TechnicalSEOResultModel(**tech_eval.to_dict()),
            content_analysis=None,
            pagespeed=PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason="Target website could not be fetched.",
            ),
            error=result.error_type,
        )

    # 1. Evaluate technical SEO rules (synchronous)
    tech_eval = evaluate_technical_seo(result)

    # 2. Run Content Analysis and PageSpeed Insights concurrently
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, verify=False) as client:
        content_task = analyze_content(result, client=client)
        pagespeed_task = get_pagespeed_insights(result.final_url, client=client)

        content_res, pagespeed_res = await asyncio.gather(
            content_task,
            pagespeed_task,
            return_exceptions=True,
        )

    # Handle results / fallback if an unexpected exception escaped
    final_content: Optional[ContentAnalysisResultModel] = None
    if isinstance(content_res, ContentAnalysisResultModel):
        final_content = content_res
    elif isinstance(content_res, Exception):
        final_content = None

    final_pagespeed: Optional[PageSpeedResultModel] = None
    if isinstance(pagespeed_res, PageSpeedResultModel):
        final_pagespeed = pagespeed_res
    elif isinstance(pagespeed_res, Exception):
        final_pagespeed = PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason=f"PageSpeed analysis error: {str(pagespeed_res)}",
        )

    return AnalysisResponse(
        status="success",
        message="Website fetched, technical SEO, content, and PageSpeed analysis completed successfully.",
        target_url=result.final_url,
        fetch_data=RawFetchData(**result.to_dict()),
        technical_seo=TechnicalSEOResultModel(**tech_eval.to_dict()),
        content_analysis=final_content,
        pagespeed=final_pagespeed,
    )



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
