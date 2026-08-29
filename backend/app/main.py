from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.models import HealthResponse, AnalysisRequest, AnalysisResponse
from app.config import settings

app = FastAPI(
    title="Website SEO & Visibility Analyser API",
    description="Backend API for automated SEO, Content, ICP, and Competitor visibility assessment.",
    version="0.1.0",
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
    Initial analysis endpoint placeholder for Phase 1.
    Accepts target URL and verifies connectivity.
    """
    return AnalysisResponse(
        status="connected",
        message="Endpoint connected successfully. Full analysis engine will be activated in subsequent phases.",
        target_url=request.url,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
