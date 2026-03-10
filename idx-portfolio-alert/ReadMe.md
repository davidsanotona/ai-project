# IDX Alert — Real-Time Banking Stock Monitor

A real-time AI-powered dashboard for monitoring your IDX banking stock portfolio (BBCA, BMRI, BBRI), with Claude-powered analysis and email alert drafting.

![Tech Stack](https://img.shields.io/badge/Stack-FastAPI_+_React_+_Claude-00e5a0?style=flat-square)
![IDX](https://img.shields.io/badge/Market-IDX_Banking-0094ff?style=flat-square)

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────┐
│  React Frontend │────▶│      FastAPI Backend          │
│  (Vite + JSX)   │◀────│                              │
│                 │     │  ┌────────────┐  ┌─────────┐ │
│  • Price cards  │     │  │ yfinance   │  │ Claude  │ │
│  • News feed    │     │  │ (IDX data) │  │   API   │ │
│  • AI analysis  │     │  └────────────┘  └─────────┘ │
│  • Email draft  │     │                              │
└─────────────────┘     └──────────────────────────────┘
```

**Data flow:**
1. Backend fetches live prices + news from Yahoo Finance (IDX `.JK` tickers)
2. Detects alerts: price moves ≥ 2% or volume spike ≥ 1.5x avg
3. Claude analyzes the data and streams back insights + a ready-to-send email
4. Frontend polls every 60s for fresh data

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Anthropic API Key](https://console.anthropic.com)

### 1. Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run
python main.py
# → http://localhost:8000
```

### 2. Frontend

```bash
cd frontend

npm install
npm run dev
# → http://localhost:5173
```

---

## Docker (Full Stack)

```bash
# 1. Set your API key
cp backend/.env.example backend/.env
echo "ANTHROPIC_API_KEY=sk-ant-..." > backend/.env

# 2. Build and run
docker-compose up --build

# Dashboard → http://localhost:5173
# API docs  → http://localhost:8000/docs
```

---

## Configuration

Edit `backend/main.py` to customize your portfolio:

```python
PORTFOLIO = {
    "BBCA": {"ticker": "BBCA.JK", "name": "Bank Central Asia", "shares": 100},
    "BMRI": {"ticker": "BMRI.JK", "name": "Bank Mandiri",      "shares": 200},
    "BBRI": {"ticker": "BBRI.JK", "name": "Bank BRI",          "shares": 150},
}

ALERT_THRESHOLDS = {
    "price_change_pct": 2.0,   # alert if ±2% daily move
    "volume_spike":     1.5,   # alert if volume > 1.5x avg
}
```

Add any `.JK` ticker from IDX to the portfolio.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stocks` | Fetch all portfolio data + alerts |
| POST | `/api/analyze/stream` | Stream Claude analysis + email (SSE) |
| GET | `/api/health` | Health check |

---

## Claude Integration

The `/api/analyze/stream` endpoint uses **Server-Sent Events (SSE)** to stream Claude's response in real time. Claude receives:
- Live price data with % changes
- Volume analysis
- Alert triggers

And produces:
1. **Market Summary** — portfolio overview
2. **Per-stock Analysis** — key insights per ticker
3. **Email Draft** — professional alert email, ready to copy and send

---

## Potential Extensions

- [ ] Add email sending via SendGrid/SES
- [ ] Telegram/WhatsApp bot integration
- [ ] Add more IDX sectors (TLKM, ASII, UNVR)
- [ ] Historical chart with recharts
- [ ] Scheduled cron job for daily digest
- [ ] Fine-tuned alert thresholds per stock
- [ ] Watchlist management UI

---

## Project Structure

```
idx-alert/
├── backend/
│   ├── main.py              # FastAPI app + Claude integration
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main dashboard component
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Disclaimer

This tool is for **educational and informational purposes only**. It is not financial advice. Always do your own research before making investment decisions.