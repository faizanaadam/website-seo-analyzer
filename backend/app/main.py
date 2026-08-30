import asyncio
import httpx
import logging
import time
import uuid
from typing import Optional
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
    AIAnalysisResultModel,
)
from app.services.fetcher import fetch_website, DEFAULT_HEADERS
from app.services.technical_seo import evaluate_technical_seo
from app.services.content_analysis import analyze_content
from app.services.pagespeed import get_pagespeed_insights
from app.services.ai_insights import generate_ai_insights
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Website SEO & Visibility Analyser API",
    description="Backend API for automated SEO, Content, ICP, PageSpeed, Competitor visibility, and AI-powered recommendations.",
    version="0.6.0",
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
    Phase 6.5: Fetches website, evaluates Technical SEO, performs multi-page Content & CTA Analysis,
    integrates Google PageSpeed Insights, and synthesizes AI-powered business insights.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[Pipeline] request_id={request_id} Starting analysis for url={request.url}")
    total_start = time.monotonic()

    fetch_start = time.monotonic()
    result = await fetch_website(request.url)
    fetch_duration = time.monotonic() - fetch_start
    logger.info(f"[Pipeline] request_id={request_id} Fetch completed in {fetch_duration:.2f}s success={result.success}")

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
            ai_insights=AIAnalysisResultModel(
                status="unavailable",
                reason="Target website could not be reached for analysis.",
            ),
            error=result.error_type,
        )

    # 1. Evaluate technical SEO rules (synchronous)
    tech_start = time.monotonic()
    tech_eval = evaluate_technical_seo(result)
    tech_duration = time.monotonic() - tech_start
    logger.info(f"[Pipeline] request_id={request_id} Technical SEO completed in {tech_duration:.2f}s")

    # 2. Run Content Analysis and PageSpeed Insights concurrently
    # Note: PageSpeed now uses its own client internally, so we don't pass `client` to it.
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, verify=False) as client:
        content_task = analyze_content(result, client=client)
        pagespeed_task = get_pagespeed_insights(result.final_url, request_id=request_id)

        concurrent_start = time.monotonic()
        content_res, pagespeed_res = await asyncio.gather(
            content_task,
            pagespeed_task,
            return_exceptions=True,
        )
        concurrent_duration = time.monotonic() - concurrent_start
        logger.info(f"[Pipeline] request_id={request_id} Concurrent Content+PageSpeed completed in {concurrent_duration:.2f}s")

        # Handle results / fallback if an unexpected exception escaped
        final_content: Optional[ContentAnalysisResultModel] = None
        if isinstance(content_res, ContentAnalysisResultModel):
            final_content = content_res
        elif isinstance(content_res, Exception):
            logger.warning(f"[Pipeline] request_id={request_id} Content task raised exception: {content_res}")
            final_content = None

        final_pagespeed: Optional[PageSpeedResultModel] = None
        if isinstance(pagespeed_res, PageSpeedResultModel):
            final_pagespeed = pagespeed_res
        elif isinstance(pagespeed_res, Exception):
            logger.warning(f"[Pipeline] request_id={request_id} PageSpeed task raised exception: {pagespeed_res}")
            final_pagespeed = PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason="Google PageSpeed API is temporarily unavailable.",
            )

        raw_fetch = RawFetchData(**result.to_dict())
        tech_model = TechnicalSEOResultModel(**tech_eval.to_dict())

        # 3. Evaluate Context Intelligence (Business categorization & audience inference)
        from app.services.context_analysis import evaluate_context_intelligence
        context_intel = evaluate_context_intelligence(
            fetch_data=raw_fetch,
            content_analysis=final_content,
        )

        # 4. Generate AI insights from deterministic facts
        ai_start = time.monotonic()
        try:
            # We explicitly do NOT pass `client=client` to force ai_insights to use its own client
            ai_insights = await generate_ai_insights(
                technical_seo=tech_model,
                content_analysis=final_content,
                pagespeed=final_pagespeed,
                fetch_data=raw_fetch,
                context_intelligence=context_intel,
                request_id=request_id,
            )
        except Exception as ai_err:
            logger.warning(f"[Pipeline] request_id={request_id} Unexpected error in AI insights pipeline: {ai_err}")
            ai_insights = AIAnalysisResultModel(
                status="unavailable",
                reason="Strategic AI analysis could not be generated at this time.",
            )
        ai_duration = time.monotonic() - ai_start
        logger.info(f"[Pipeline] request_id={request_id} AI Insights completed in {ai_duration:.2f}s")
    
    total_duration = time.monotonic() - total_start
    logger.info(f"[Pipeline] request_id={request_id} Full analysis completed in {total_duration:.2f}s")

    return AnalysisResponse(
        status="success",
        message="Website fetched, technical SEO, content, context intelligence, PageSpeed, and AI insights completed successfully.",
        target_url=result.final_url,
        fetch_data=raw_fetch,
        technical_seo=tech_model,
        content_analysis=final_content,
        context_intelligence=context_intel,
        pagespeed=final_pagespeed,
        ai_insights=ai_insights,
    )



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
