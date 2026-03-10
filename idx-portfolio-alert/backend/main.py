"""
IDX Stock Alert Backend
Fetches live IDX stock data, news, runs Claude analysis, drafts alert email
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

import yfinance as yf
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="IDX Stock Alert API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Config ────────────────────────────────────────────────────────────────────
PORTFOLIO = {
    "BBCA": {"ticker": "BBCA.JK", "name": "Bank Central Asia", "shares": 100},
    "BMRI": {"ticker": "BMRI.JK", "name": "Bank Mandiri",      "shares": 200},
    "BBRI": {"ticker": "BBRI.JK", "name": "Bank BRI",          "shares": 150},
}

ALERT_THRESHOLDS = {
    "price_change_pct": 2.0,   # alert if ±2% daily move
    "volume_spike":     1.5,   # alert if volume > 1.5x avg
}

# ── Models ────────────────────────────────────────────────────────────────────
class EmailRequest(BaseModel):
    stocks_data: list
    recipient_name: Optional[str] = "Investor"

# ── Stock Data ────────────────────────────────────────────────────────────────
def fetch_stock_data(ticker_symbol: str, stock_info: dict) -> dict:
    """Fetch current price, change, volume from Yahoo Finance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist   = ticker.history(period="5d", interval="1d")
        info   = ticker.info

        if hist.empty:
            raise ValueError(f"No data for {ticker_symbol}")

        latest    = hist.iloc[-1]
        prev      = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]

        price         = round(float(latest["Close"]), 2)
        prev_close    = round(float(prev["Close"]), 2)
        change        = round(price - prev_close, 2)
        change_pct    = round((change / prev_close) * 100, 2) if prev_close else 0
        volume        = int(latest["Volume"])
        avg_volume    = int(hist["Volume"].mean())
        volume_ratio  = round(volume / avg_volume, 2) if avg_volume else 1.0

        # Determine alert type
        alerts = []
        if abs(change_pct) >= ALERT_THRESHOLDS["price_change_pct"]:
            direction = "📈 UP" if change_pct > 0 else "📉 DOWN"
            alerts.append(f"Price moved {direction} {abs(change_pct)}%")
        if volume_ratio >= ALERT_THRESHOLDS["volume_spike"]:
            alerts.append(f"🔊 Volume spike: {volume_ratio}x avg")

        return {
            "symbol":      stock_info["ticker"].replace(".JK", ""),
            "name":        stock_info["name"],
            "price":       price,
            "prev_close":  prev_close,
            "change":      change,
            "change_pct":  change_pct,
            "volume":      volume,
            "avg_volume":  avg_volume,
            "volume_ratio":volume_ratio,
            "shares":      stock_info["shares"],
            "market_cap":  info.get("marketCap"),
            "pe_ratio":    info.get("trailingPE"),
            "alerts":      alerts,
            "has_alert":   len(alerts) > 0,
            "fetched_at":  datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "symbol":    stock_info["ticker"].replace(".JK", ""),
            "name":      stock_info["name"],
            "error":     str(e),
            "has_alert": False,
            "fetched_at":datetime.now().isoformat(),
        }


def fetch_news(symbol: str) -> list[dict]:
    """Fetch recent news headlines for a stock."""
    try:
        ticker = yf.Ticker(f"{symbol}.JK")
        news   = ticker.news or []
        results = []
        for item in news[:3]:
            results.append({
                "title":     item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link":      item.get("link", ""),
                "published": datetime.fromtimestamp(
                    item.get("providerPublishTime", 0)
                ).strftime("%Y-%m-%d %H:%M") if item.get("providerPublishTime") else "",
            })
        return results
    except Exception:
        return []

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/api/stocks")
async def get_stocks():
    """Fetch all portfolio stocks in parallel."""
    loop   = asyncio.get_event_loop()
    tasks  = [
        loop.run_in_executor(None, fetch_stock_data, info["ticker"], info)
        for info in PORTFOLIO.values()
    ]
    stocks = await asyncio.gather(*tasks)

    # Attach news
    for stock in stocks:
        if "error" not in stock:
            stock["news"] = fetch_news(stock["symbol"])

    # Portfolio summary
    total_value = sum(
        s["price"] * s["shares"]
        for s in stocks if "error" not in s
    )
    alerts_count = sum(1 for s in stocks if s.get("has_alert"))

    return {
        "stocks":       list(stocks),
        "portfolio": {
            "total_value":   round(total_value, 2),
            "alerts_count":  alerts_count,
            "last_updated":  datetime.now().isoformat(),
        }
    }


@app.post("/api/analyze/stream")
async def stream_analysis(request: EmailRequest):
    """Stream Claude analysis + email draft via SSE."""

    stocks_summary = json.dumps(request.stocks_data, indent=2)
    today          = datetime.now().strftime("%A, %d %B %Y")
    alerted        = [s for s in request.stocks_data if s.get("has_alert")]

    prompt = f"""You are an equity analyst covering Indonesian banking stocks on IDX.

Today is {today}.

Here is the latest portfolio data:
{stocks_summary}

Please do the following in your response:

## 1. Market Summary
Brief 2-3 sentence overview of today's portfolio performance.

## 2. Stock Analysis
For each stock (BBCA, BMRI, BBRI), provide:
- Key price action insight
- Any notable alerts and what they might signal
- Short-term outlook (1-2 sentences)

## 3. Portfolio Alert Email
Draft a clean, professional portfolio alert email for {request.recipient_name}. 

Format the email exactly like this:
---EMAIL START---
Subject: [subject line]

[email body]
---EMAIL END---

Keep the email concise (under 200 words), professional, actionable, and in English.
End with a standard disclaimer that this is not financial advice.
"""

    def generate():
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                # SSE format
                data = json.dumps({"text": text})
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)