# Website SEO & Visibility Analyser

An automated website assessment tool built for small service businesses (dental clinics, garages, home services, etc.) that delivers clear, jargon-free SEO, Content, ICP, and Competitor visibility insights.

---

## 1. Project Overview

- **Frontend**: Mobile app built with **Expo + React Native + TypeScript**, designed with an "Answer First" approach, clean visual hierarchy, and accessible indicators.
- **Backend**: **Python + FastAPI** service orchestrating deterministic SEO parsing, performance checks, structured AI reasoning, and competitor discovery.
- **Security Rule**: Zero API keys or secrets in the mobile app. All external credentials reside securely in the backend.

---

## 2. Technology Stack

- **Mobile Client**: Expo SDK 52, React Native 0.76, TypeScript.
- **Backend API**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2, `pydantic-settings`.
- **Parsing & HTTP**: `httpx` (async), `BeautifulSoup4`.
- **Testing**: `pytest`, `fastapi.testclient`.

---

## 3. Project Structure

```text
website-seo-analyser/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint with CORS & routes
│   │   ├── config.py                # Environment configuration (pydantic-settings)
│   │   ├── models.py                # Pydantic request/response schemas
│   │   └── services/
│   │       └── __init__.py          # Service module package
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py           # Endpoint validation tests
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Placeholder environment configuration
│
├── frontend/
│   ├── src/
│   │   ├── config.ts                # Configurable API Base URL (Localhost / LAN IP)
│   │   ├── types/
│   │   │   └── analysis.ts          # Shared TypeScript interfaces
│   │   └── services/
│   │       └── api.ts               # Backend communication service
│   ├── App.tsx                      # Phase 1 verification screen
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
Copy the example environment file:
```bash
cp .env.example .env
```

### Step 3: Run the FastAPI Backend
Start the server with live reload enabled and listening on all network interfaces (`0.0.0.0` allows physical phones on the same Wi-Fi to connect):
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Verify Backend Health
You can verify the backend is running in your browser or via curl:
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

---

## 5. Frontend Setup & Run Instructions

### Step 1: Install Dependencies
Open a terminal in the `frontend/` directory:
```bash
npm install
```

### Step 2: Configure Backend URL for Your Device

- **Testing on Web or iOS Simulator**: Default `http://localhost:8000` works out of the box.
- **Testing on Android Emulator**: Default `http://10.0.2.2:8000` maps directly to your PC's localhost.
- **Testing on a Physical Phone via Expo Go**:
  1. Find your computer's local IP address (e.g. run `ipconfig` on Windows or `ifconfig` on Mac/Linux, look for IPv4 like `192.168.1.50`).
  2. In the mobile app's text input or in `frontend/src/config.ts`, set the URL to:
     ```
     http://<YOUR_LOCAL_IP>:8000
     ```
  3. Ensure your phone and computer are connected to the same Wi-Fi network.

### Step 3: Start Expo
```bash
npx expo start
```
- Press **w** to open in web browser.
- Scan the displayed QR code with your iOS Camera or Android Expo Go app to launch on a physical phone.

---

## 6. Current Phase Status

- **Phase 1: Foundation & Connectivity** ✅ **COMPLETE**
  - Git repository initialized.
  - Backend FastAPI app with `GET /health` and `POST /api/analyse` placeholder created.
  - Unit tests verifying endpoints and URL normalization passing.
  - Expo TypeScript frontend created with in-app backend health check testing UI.
