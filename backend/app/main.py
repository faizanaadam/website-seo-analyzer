from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.models import HealthResponse, AnalysisRequest, AnalysisResponse, RawFetchData
from app.services.fetcher import fetch_website
from app.config import settings

app = FastAPI(
    title="Website SEO & Visibility Analyser API",
    description="Backend API for automated SEO, Content, ICP, and Competitor visibility assessment.",
    version="0.3.0",
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
    Phase 3: Fetches, normalizes, and extracts structured raw website data.
    """
    result = await fetch_website(request.url)

    if not result.success:
        if result.error_type == "invalid_url":
            raise HTTPException(
                status_code=422,
                detail=result.error_message or "Invalid website URL provided.",
            )

        return AnalysisResponse(
            status="error",
            message=result.error_message or "Failed to fetch website.",
            target_url=request.url,
            fetch_data=RawFetchData(**result.to_dict()),
            error=result.error_type,
        )

    return AnalysisResponse(
        status="success",
        message="Website fetched and parsed successfully.",
        target_url=result.final_url,
        fetch_data=RawFetchData(**result.to_dict()),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
