<div align="center">
  <img src="frontend/public/icons.svg" alt="Rakshak AI Logo" width="120" />
  
  # Rakshak AI 🛡️
  **Strategic Energy Intelligence & Supply Chain Resilience Dashboard**

  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
  [![Vite](https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E)](https://vitejs.dev/)
  [![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
</div>

<br />

**Rakshak AI** is an advanced, multi-layered strategic intelligence platform designed to preemptively detect geopolitical disruptions at critical global maritime choke points, accurately model their downstream macroeconomic impacts on the Indian economy, and dynamically generate optimized, alternative crude oil sourcing strategies.

Built to transform reactive crisis management into proactive energy security.

---

## ✨ Key Features & The 3-Layer Architecture

Rakshak AI is built on a robust, autonomous three-layer pipeline:

### 📡 Layer 1: Watch (Signal Fusion)
Monitors critical global maritime corridors (Strait of Hormuz, Red Sea, Suez Canal, Strait of Malacca).
- **Rules-Based Keyword Evidence:** Extracts breaking intelligence from global news streams via **GDELT**.
- **Sanctions Tracking:** Monitors real-time US **OFAC** Specially Designated Nationals (SDN) updates.
- **Market Sentiment:** Ingests live **Polymarket** prediction market probabilities for geopolitical escalation.
- *Outputs a fused, weighted severity score (0-100) per corridor.*

### 📈 Layer 2: Model (Economic Impact)
Translates geopolitical risk scores into quantifiable macroeconomic projections.
- **Monte Carlo Simulations:** Runs 200+ statistical iterations to generate 10th and 90th percentile confidence bounds for Brent Crude trajectory forecasts.
- **Macro Impact:** Calculates dynamic INR/USD depreciation, domestic retail fuel price shocks, and precise state-by-state economic stress indices.
- **National Security:** Tracks projected Strategic Petroleum Reserve (SPR) drawdown multipliers and days of remaining cover based on disruption severity.

### 🗺️ Layer 3: Act (Strategic Sourcing)
Generates actionable, optimized procurement rerouting recommendations when primary supply lines are compromised.
- **Multi-factor Ranking Engine:** Evaluates alternative suppliers (US Gulf Coast, West Africa, Brazil, etc.) based on spot price differentials, physical transit lead times (nautical miles & tanker class), port congestion, and geopolitical diversification value.
- **Visual Intelligence:** Plots optimal alternative shipping routes dynamically on an interactive Leaflet map interface.

---

## 🚀 Quick Start (Local Development)

The project is split into a Python FastAPI backend and a React (Vite) frontend.

### 1. Start the Backend API
The backend requires Python 3.10+.

```bash
# Clone the repository
git clone https://github.com/immortalfoodie/Rakshak-AI.git
cd Rakshak-AI

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python integration/api.py
```
*The API will run on `http://127.0.0.1:8000`*

### 2. Start the Frontend Dashboard
The frontend requires Node.js 18+.

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
*The UI will run on `http://localhost:5173`. Open this in your browser.*

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, Requests
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React (Icons)
- **Data Visualization:** Recharts, React-Leaflet
- **Data Sources:** GDELT Project (News), OFAC API (Sanctions), Polymarket (Sentiment)

---

## 🎮 Hackathon Demo Mode ("Simulate Crisis")

For demonstration and judging purposes, the dashboard includes a **"Simulate Crisis"** toggle. 

Given that the global maritime environment may be relatively calm on the day of the presentation (resulting in low live GDELT/OFAC scores), enabling this toggle instructs the backend to seamlessly inject deterministic, high-severity mock scores (e.g., 95.5) for the selected corridors. This ensures you can fully demonstrate the Monte Carlo modeling and Layer 3 alternative routing engine on demand without waiting for a real-world black swan event.

---

## 📂 Project Structure

```text
Rakshak-AI/
├── frontend/                 # React + Vite Dashboard
│   ├── src/components/       # Reusable UI components
│   └── src/App.tsx           # Main application logic
├── integration/
│   └── api.py                # FastAPI endpoints & orchestrator
├── layer1-watch/             # Geopolitical signal extraction
│   └── scoring/              # Signal fusion logic
├── layer2-model/             # Economic impact & Monte Carlo engine
├── layer3-act/               # Sourcing optimization logic
├── shared/                   # Shared schemas and historical replay JSONs
└── requirements.txt          # Python dependencies
```

---

<div align="center">
  <i>Built for energy security. Built for resilience.</i>
</div>
