import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://localhost:8000";

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmt = (n) =>
  n == null ? "—" : new Intl.NumberFormat("id-ID").format(Math.round(n));

const fmtCurrency = (n) =>
  n == null ? "—" : `Rp ${new Intl.NumberFormat("id-ID").format(Math.round(n))}`;

const fmtPct = (n) =>
  n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;

// ── Sub-components ────────────────────────────────────────────────────────────
function Ticker({ stocks }) {
  const items = stocks.filter((s) => !s.error);
  if (!items.length) return null;
  const repeated = [...items, ...items, ...items];
  return (
    <div className="ticker-wrap">
      <div className="ticker-track">
        {repeated.map((s, i) => (
          <span key={i} className="ticker-item">
            <span className="ticker-sym">{s.symbol}</span>
            <span className="ticker-price">{fmt(s.price)}</span>
            <span className={`ticker-chg ${s.change_pct >= 0 ? "up" : "down"}`}>
              {fmtPct(s.change_pct)}
            </span>
            <span className="ticker-sep">·</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StockCard({ stock, selected, onClick }) {
  if (stock.error) {
    return (
      <div className="card card-error" onClick={onClick}>
        <div className="card-sym">{stock.symbol}</div>
        <div className="error-msg">Failed to load</div>
      </div>
    );
  }

  const up = stock.change_pct >= 0;
  const portfolioValue = stock.price * stock.shares;

  return (
    <div className={`card ${selected ? "card-selected" : ""} ${stock.has_alert ? "card-alert" : ""}`} onClick={onClick}>
      {stock.has_alert && <div className="alert-badge">⚡ ALERT</div>}
      <div className="card-header">
        <div>
          <div className="card-sym">{stock.symbol}</div>
          <div className="card-name">{stock.name}</div>
        </div>
        <div className={`card-trend ${up ? "up" : "down"}`}>
          {up ? "▲" : "▼"}
        </div>
      </div>

      <div className="card-price">{fmt(stock.price)}</div>
      <div className={`card-change ${up ? "up" : "down"}`}>
        {fmtPct(stock.change_pct)} &nbsp;
        <span className="card-change-abs">({up ? "+" : ""}{fmt(stock.change)})</span>
      </div>

      <div className="card-divider" />

      <div className="card-stats">
        <div className="stat">
          <span className="stat-label">Shares</span>
          <span className="stat-value">{fmt(stock.shares)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Value</span>
          <span className="stat-value">{fmtCurrency(portfolioValue)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Volume</span>
          <span className="stat-value">{fmt(stock.volume)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Vol Ratio</span>
          <span className={`stat-value ${stock.volume_ratio >= 1.5 ? "warn" : ""}`}>
            {stock.volume_ratio}x
          </span>
        </div>
      </div>

      {stock.alerts?.length > 0 && (
        <div className="alert-list">
          {stock.alerts.map((a, i) => (
            <div key={i} className="alert-item">{a}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewsPanel({ stock }) {
  if (!stock || stock.error) return null;
  const news = stock.news || [];
  return (
    <div className="news-panel">
      <div className="panel-title">📰 Latest News — {stock.symbol}</div>
      {news.length === 0 ? (
        <div className="no-news">No recent news found.</div>
      ) : (
        news.map((n, i) => (
          <a key={i} href={n.link} target="_blank" rel="noreferrer" className="news-item">
            <div className="news-title">{n.title}</div>
            <div className="news-meta">{n.publisher} · {n.published}</div>
          </a>
        ))
      )}
    </div>
  );
}

function EmailModal({ content, onClose }) {
  const emailMatch = content.match(/---EMAIL START---([\s\S]*?)---EMAIL END---/);
  const emailContent = emailMatch ? emailMatch[1].trim() : null;

  const copy = () => {
    navigator.clipboard.writeText(emailContent || content);
    alert("Copied to clipboard!");
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span>✉️ Email Draft</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <pre className="email-content">{emailContent || "No email section found."}</pre>
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={copy}>Copy Email</button>
          <button className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [stocks,      setStocks]      = useState([]);
  const [portfolio,   setPortfolio]   = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [selected,    setSelected]    = useState(null);
  const [analysis,    setAnalysis]    = useState("");
  const [analyzing,   setAnalyzing]   = useState(false);
  const [showEmail,   setShowEmail]   = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const intervalRef = useRef(null);
  const analysisRef = useRef(null);

  const fetchStocks = useCallback(async () => {
    try {
      const res  = await fetch(`${API}/api/stocks`);
      const data = await res.json();
      setStocks(data.stocks);
      setPortfolio(data.portfolio);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError("Cannot connect to backend. Is the server running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStocks();
    intervalRef.current = setInterval(fetchStocks, 60_000); // refresh every 60s
    return () => clearInterval(intervalRef.current);
  }, [fetchStocks]);

  const runAnalysis = async () => {
    if (!stocks.length) return;
    setAnalyzing(true);
    setAnalysis("");
    setShowEmail(false);

    try {
      const res = await fetch(`${API}/api/analyze/stream`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          stocks_data:    stocks,
          recipient_name: "Portfolio Manager",
        }),
      });

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") { setAnalyzing(false); return; }
          try {
            const { text } = JSON.parse(payload);
            setAnalysis((prev) => prev + text);
            if (analysisRef.current) {
              analysisRef.current.scrollTop = analysisRef.current.scrollHeight;
            }
          } catch {}
        }
      }
    } catch (e) {
      setAnalysis("Error connecting to analysis API. Check your ANTHROPIC_API_KEY.");
    } finally {
      setAnalyzing(false);
    }
  };

  const hasEmail = analysis.includes("---EMAIL START---");
  const selectedStock = stocks.find((s) => s.symbol === selected);

  return (
    <>
      <style>{CSS}</style>

      {/* Top bar */}
      <div className="topbar">
        <div className="topbar-left">
          <span className="logo">📊</span>
          <span className="logo-text">IDX<b>Alert</b></span>
          <span className="tagline">Banking Sector Monitor</span>
        </div>
        <div className="topbar-right">
          {lastUpdated && (
            <span className="updated">
              Updated {lastUpdated.toLocaleTimeString("id-ID")}
            </span>
          )}
          <button className="btn btn-refresh" onClick={fetchStocks} disabled={loading}>
            {loading ? "⟳" : "⟳ Refresh"}
          </button>
        </div>
      </div>

      {/* Ticker */}
      {stocks.length > 0 && <Ticker stocks={stocks} />}

      <main className="main">
        {error && <div className="error-banner">{error}</div>}

        {/* Portfolio Summary */}
        {portfolio && (
          <div className="summary-bar">
            <div className="summary-item">
              <span className="summary-label">Portfolio Value</span>
              <span className="summary-value">{fmtCurrency(portfolio.total_value)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Active Alerts</span>
              <span className={`summary-value ${portfolio.alerts_count > 0 ? "warn" : "ok"}`}>
                {portfolio.alerts_count > 0 ? `⚡ ${portfolio.alerts_count}` : "✓ None"}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Market</span>
              <span className="summary-value">IDX · Banking</span>
            </div>
          </div>
        )}

        {/* Stock Cards */}
        <div className="cards-grid">
          {loading
            ? [0, 1, 2].map((i) => <div key={i} className="card card-skeleton" />)
            : stocks.map((s) => (
                <StockCard
                  key={s.symbol}
                  stock={s}
                  selected={selected === s.symbol}
                  onClick={() => setSelected(selected === s.symbol ? null : s.symbol)}
                />
              ))}
        </div>

        {/* News for selected stock */}
        {selectedStock && <NewsPanel stock={selectedStock} />}

        {/* AI Analysis */}
        <div className="analysis-section">
          <div className="analysis-header">
            <div>
              <div className="section-title">🤖 AI Analysis</div>
              <div className="section-sub">Powered by Claude · includes email draft</div>
            </div>
            <div className="analysis-actions">
              {hasEmail && (
                <button className="btn btn-email" onClick={() => setShowEmail(true)}>
                  ✉️ View Email
                </button>
              )}
              <button className="btn btn-primary" onClick={runAnalysis} disabled={analyzing || loading}>
                {analyzing ? (
                  <><span className="spinner" /> Analyzing…</>
                ) : (
                  "▶ Run Analysis"
                )}
              </button>
            </div>
          </div>

          {analysis ? (
            <div className="analysis-box" ref={analysisRef}>
              <pre className="analysis-text">{analysis}</pre>
            </div>
          ) : (
            <div className="analysis-empty">
              Click <b>Run Analysis</b> to get AI-powered insights and a ready-to-send alert email.
            </div>
          )}
        </div>
      </main>

      {showEmail && analysis && (
        <EmailModal content={analysis} onClose={() => setShowEmail(false)} />
      )}
    </>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0b0e14;
    --surface:  #131720;
    --surface2: #1a2030;
    --border:   #252d3d;
    --accent:   #00e5a0;
    --accent2:  #0094ff;
    --up:       #00e5a0;
    --down:     #ff4d6a;
    --warn:     #ffb340;
    --text:     #e8eaf0;
    --muted:    #6b7894;
    --font:     'IBM Plex Sans', sans-serif;
    --mono:     'IBM Plex Mono', monospace;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
  }

  /* Topbar */
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
  }
  .topbar-left { display: flex; align-items: center; gap: 12px; }
  .logo { font-size: 22px; }
  .logo-text { font-size: 18px; font-weight: 300; letter-spacing: 1px; color: var(--text); }
  .logo-text b { color: var(--accent); font-weight: 700; }
  .tagline { font-size: 11px; color: var(--muted); background: var(--surface2);
    padding: 2px 8px; border-radius: 4px; letter-spacing: 1px; text-transform: uppercase; }
  .topbar-right { display: flex; align-items: center; gap: 12px; }
  .updated { font-size: 12px; color: var(--muted); font-family: var(--mono); }

  /* Ticker */
  .ticker-wrap {
    overflow: hidden; background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 6px 0;
  }
  .ticker-track {
    display: inline-flex; white-space: nowrap;
    animation: ticker 30s linear infinite;
  }
  .ticker-wrap:hover .ticker-track { animation-play-state: paused; }
  @keyframes ticker { from { transform: translateX(0); } to { transform: translateX(-33.33%); } }
  .ticker-item { display: inline-flex; align-items: center; gap: 6px; padding: 0 18px; font-family: var(--mono); font-size: 12px; }
  .ticker-sym { color: var(--accent2); font-weight: 600; }
  .ticker-price { color: var(--text); }
  .ticker-chg.up { color: var(--up); }
  .ticker-chg.down { color: var(--down); }
  .ticker-sep { color: var(--border); }

  /* Main */
  .main { max-width: 1100px; margin: 0 auto; padding: 28px 20px; }

  /* Error banner */
  .error-banner {
    background: rgba(255,77,106,0.12); border: 1px solid var(--down);
    color: var(--down); padding: 12px 16px; border-radius: 8px; margin-bottom: 20px;
    font-size: 14px;
  }

  /* Summary bar */
  .summary-bar {
    display: flex; gap: 2px; margin-bottom: 24px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    overflow: hidden;
  }
  .summary-item {
    flex: 1; padding: 14px 20px;
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column; gap: 4px;
  }
  .summary-item:last-child { border-right: none; }
  .summary-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
  .summary-value { font-size: 18px; font-weight: 600; font-family: var(--mono); }
  .summary-value.warn { color: var(--warn); }
  .summary-value.ok  { color: var(--up); }

  /* Cards */
  .cards-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 16px; margin-bottom: 24px;
  }
  @media (max-width: 768px) { .cards-grid { grid-template-columns: 1fr; } }

  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px; cursor: pointer;
    transition: border-color .2s, transform .15s, box-shadow .2s;
    position: relative; overflow: hidden;
  }
  .card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent2), transparent);
    opacity: 0; transition: opacity .2s;
  }
  .card:hover { border-color: var(--accent2); transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,148,255,.12); }
  .card:hover::before { opacity: 1; }
  .card-selected { border-color: var(--accent) !important; box-shadow: 0 0 0 1px var(--accent); }
  .card-alert { border-color: var(--warn) !important; }
  .card-skeleton { height: 220px; background: linear-gradient(90deg, var(--surface) 25%, var(--surface2) 50%, var(--surface) 75%);
    background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 12px; }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
  .card-error { display: flex; flex-direction: column; gap: 8px; align-items: center; justify-content: center; min-height: 120px; }
  .error-msg { color: var(--down); font-size: 13px; }

  .alert-badge {
    position: absolute; top: 10px; right: 10px;
    background: rgba(255,179,64,.15); color: var(--warn);
    font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;
    border: 1px solid rgba(255,179,64,.3); letter-spacing: .5px;
  }
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
  .card-sym { font-size: 20px; font-weight: 700; font-family: var(--mono); color: var(--accent2); }
  .card-name { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .card-trend { font-size: 22px; opacity: .85; }
  .card-trend.up { color: var(--up); }
  .card-trend.down { color: var(--down); }
  .card-price { font-size: 28px; font-weight: 700; font-family: var(--mono); letter-spacing: -1px; }
  .card-change { font-size: 14px; font-weight: 600; font-family: var(--mono); margin-top: 2px; margin-bottom: 14px; }
  .card-change.up { color: var(--up); }
  .card-change.down { color: var(--down); }
  .card-change-abs { font-weight: 400; opacity: .7; }
  .card-divider { height: 1px; background: var(--border); margin: 10px 0; }
  .card-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat { display: flex; flex-direction: column; gap: 1px; }
  .stat-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
  .stat-value { font-size: 13px; font-family: var(--mono); font-weight: 600; }
  .stat-value.warn { color: var(--warn); }
  .alert-list { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
  .alert-item { font-size: 11px; color: var(--warn); background: rgba(255,179,64,.08);
    padding: 4px 8px; border-radius: 4px; border-left: 2px solid var(--warn); }

  /* News */
  .news-panel {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px; margin-bottom: 24px;
  }
  .panel-title { font-size: 13px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px; }
  .no-news { color: var(--muted); font-size: 13px; }
  .news-item { display: block; padding: 10px 0; border-bottom: 1px solid var(--border);
    text-decoration: none; transition: color .15s; }
  .news-item:last-child { border-bottom: none; }
  .news-item:hover .news-title { color: var(--accent2); }
  .news-title { font-size: 14px; color: var(--text); margin-bottom: 3px; }
  .news-meta { font-size: 11px; color: var(--muted); }

  /* Analysis */
  .analysis-section {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; overflow: hidden;
  }
  .analysis-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 20px; border-bottom: 1px solid var(--border);
  }
  .section-title { font-size: 15px; font-weight: 700; }
  .section-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .analysis-actions { display: flex; gap: 10px; }
  .analysis-box { padding: 20px; max-height: 520px; overflow-y: auto; }
  .analysis-text { font-family: var(--mono); font-size: 13px; line-height: 1.7;
    white-space: pre-wrap; color: var(--text); }
  .analysis-empty {
    padding: 40px 20px; text-align: center; color: var(--muted); font-size: 14px; line-height: 1.8;
  }

  /* Buttons */
  .btn {
    font-family: var(--font); font-size: 13px; font-weight: 600;
    padding: 8px 16px; border-radius: 7px; border: none; cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px; transition: .15s;
  }
  .btn:disabled { opacity: .5; cursor: not-allowed; }
  .btn-primary { background: var(--accent); color: #0b0e14; }
  .btn-primary:hover:not(:disabled) { background: #00ffb3; }
  .btn-ghost { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
  .btn-ghost:hover { border-color: var(--accent2); color: var(--accent2); }
  .btn-refresh { background: var(--surface2); color: var(--muted); border: 1px solid var(--border);
    font-size: 13px; padding: 7px 14px; border-radius: 7px; cursor: pointer; }
  .btn-refresh:hover { color: var(--text); }
  .btn-email { background: rgba(0,148,255,.15); color: var(--accent2);
    border: 1px solid rgba(0,148,255,.3); }
  .btn-email:hover { background: rgba(0,148,255,.25); }

  /* Spinner */
  .spinner {
    width: 12px; height: 12px; border: 2px solid rgba(11,14,20,.3);
    border-top-color: #0b0e14; border-radius: 50%;
    animation: spin .7s linear infinite; display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Modal */
  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,.7);
    display: flex; align-items: center; justify-content: center;
    z-index: 200; padding: 20px;
  }
  .modal {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 14px; width: 100%; max-width: 620px;
    max-height: 80vh; display: flex; flex-direction: column;
    box-shadow: 0 24px 80px rgba(0,0,0,.6);
  }
  .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 20px; border-bottom: 1px solid var(--border);
    font-weight: 700;
  }
  .modal-close { background: none; border: none; color: var(--muted);
    font-size: 18px; cursor: pointer; line-height: 1; }
  .modal-close:hover { color: var(--text); }
  .modal-body { flex: 1; overflow-y: auto; padding: 20px; }
  .email-content {
    font-family: var(--mono); font-size: 13px; line-height: 1.7;
    white-space: pre-wrap; color: var(--text);
  }
  .modal-footer {
    display: flex; gap: 10px; justify-content: flex-end;
    padding: 14px 20px; border-top: 1px solid var(--border);
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }

  .up { color: var(--up); }
  .down { color: var(--down); }
`;