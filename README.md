# Website SEO & Visibility Analyser

An automated website assessment tool built for small service businesses (dental clinics, garages, home services, etc.) that delivers clear, jargon-free SEO, Content, ICP, and Competitor visibility insights.

---

## 1. Project Overview

- **Frontend**: Mobile app built with **Expo SDK 54 + React Native 0.81 + TypeScript**, designed with an "Answer First" approach, clean visual hierarchy, and accessible indicators. Compatible with current App Store Expo Go.
- **Backend**: **Python + FastAPI** service orchestrating deterministic SEO parsing, multi-page crawling, performance checks, structured AI reasoning, and Google Places API (New) competitor discovery.
- **Security Rule**: Zero API keys or secrets in the mobile app. All external credentials reside securely in the backend.

---

## 2. Technology Stack

- **Mobile Client**: Expo SDK 54, React Native 0.81, React 19.1, TypeScript 5.9.
- **Backend API**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2, `pydantic-settings`.
- **Parsing & HTTP**: `httpx` (async), `BeautifulSoup4`.
- **External APIs**: Google PageSpeed Insights API, Google Places API (New), Google Gemini AI API.
- **Testing**: `pytest`, `fastapi.testclient` (123 automated test cases).

---

## 3. Project Structure

```text
website-seo-analyser/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint with CORS, pipelines & routes
│   │   ├── config.py                # Environment configuration (pydantic-settings)
│   │   ├── models.py                # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── technical_seo.py     # Deterministic Technical SEO evaluator (meta, schema, robots, sitemap)
│   │   │   ├── content_analysis.py  # Multi-page crawl, readability, CTA & contact analysis
│   │   │   ├── context_analysis.py  # Business category detection & ICP alignment
│   │   │   ├── pagespeed.py         # Google PageSpeed Insights with TTL cache & timeout resilience
│   │   │   ├── google_places.py     # Google Places API (New) competitor discovery & ranking
│   │   │   ├── ai_insights.py       # Gemini-powered business synthesis & actionable takeaways
│   │   │   ├── fetcher.py           # Async HTTP fetcher with anti-bot headers & multi-page support
│   │   │   ├── recommendation_engine.py # Priority & Quick Win recommendations engine
│   │   │   └── failure_types.py     # Resilient error classification & partial failure handling
│   │   └── utils/
│   ├── tests/                       # 123 automated pytest test suites
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Placeholder environment configuration
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InputState.tsx       # Target URL input with sample buttons & error simulation toggle
│   │   │   ├── LoadingState.tsx     # Step-by-step audit progress checklist
│   │   │   ├── ResultsState.tsx     # Full results dashboard (Score, Quick Wins, SEO, Speed, Places, AI)
│   │   │   ├── ErrorState.tsx       # User-friendly error recovery screen with retry & back buttons
│   │   │   ├── StatusBadge.tsx      # Accessible status indicators (Good / Warning / Critical)
│   │   │   ├── QuickWinCard.tsx     # High-impact immediate fix card
│   │   │   └── ExpandableCard.tsx   # Collapsible audit category section
│   │   ├── config.ts                # Auto-resolving API Base URL (Localhost / LAN IP / Expo packager)
│   │   ├── constants/
│   │   │   └── theme.ts             # Dark-mode design system and token palette
│   │   ├── data/
│   │   │   └── mockAnalysis.ts      # Offline/testing mock dataset
│   │   ├── services/
│   │   │   └── api.ts               # Backend communication service with timeout handling
│   │   └── types/
│   │       └── analysis.ts          # Shared TypeScript models
│   ├── App.tsx                      # Root screen state coordinator
│   ├── package.json
│   ├── tsconfig.json
│   └── app.json
│
├── docs/                            # Project documentation & notes
├── .gitignore
└── README.md
```

---

## 4. Backend Setup & Run Instructions

### Step 1: Install Dependencies
Open a terminal in the `backend/` directory:
```bash
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Copy the example environment file and add your API keys:
```bash
cp .env.example .env
```
*(Configure `GEMINI_API_KEY`, `PAGESPEED_API_KEY`, and `GOOGLE_PLACES_API_KEY` in `.env`)*

### Step 3: Run the FastAPI Backend
Start the server with live reload enabled and listening on all network interfaces (`0.0.0.0` allows physical phones on the same Wi-Fi to connect):
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Verify Backend Health
Verify the backend is running via browser or curl:
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{
  "status": "ok",
  "message": "Website SEO & Visibility Analyser backend is running"
}
```

### Step 5: Run Automated Tests
```bash
python -m pytest backend/tests
```
*(All 123 tests passing)*

---

## 5. Frontend Setup & Run Instructions

### Step 1: Install Dependencies
Open a terminal in the `frontend/` directory:
```bash
npm install
```

### Step 2: Start Expo (SDK 54)
```bash
npx expo start
```
- **Web**: Press **w** to open in web browser (`http://localhost:8081`).
- **Physical iPhone**: Scan the displayed QR code with your iOS Camera or enter `exp://<YOUR_LOCAL_IP>:8081` in the **Expo Go** app.

---

## 6. Completed Phases & Features

- **Phase 1: Foundation & Connectivity** ✅
  - FastAPI backend with `/health` and `/api/analyse` endpoints.
  - Expo TypeScript frontend with network connectivity and state management.
- **Phase 2: Deterministic Technical SEO Engine** ✅
  - Comprehensive metadata, heading hierarchy, canonical URL, robots.txt, sitemap.xml, OpenGraph, and JSON-LD schema parsing.
- **Phase 3: Multi-Page Content & CTA Analysis** ✅
  - Multi-page crawler, word count metrics, Flesch-Kincaid readability scoring, CTA detection, and contact information extraction.
- **Phase 4: Google PageSpeed Insights Integration** ✅
  - Mobile & desktop performance audit, Core Web Vitals extraction, in-memory TTL caching, and graceful timeout handling.
- **Phase 5: Gemini AI Business Synthesis** ✅
  - Business context extraction, audience classification, and jargon-free recommendations.
- **Phase 6: UI/UX & Reliability Hardening** ✅
  - Dark-mode design system, accessible StatusBadges, expandable audit cards, and partial failure isolation.
- **Phase 7: Google Places API (New) Competitor Intelligence** ✅
  - Upgraded to Google Places API (New), deterministic address extraction, competitor ranking, and rating comparisons.
- **Maintenance: Expo SDK 54 Upgrade** ✅
  - Aligned Expo SDK 54, React Native 0.81, React 19.1, and TypeScript 5.9 for App Store Expo Go compatibility.
