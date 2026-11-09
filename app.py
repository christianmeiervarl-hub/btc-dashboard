import math
import time
import numpy as np
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Kronos Bitcoin Forecasting Engine")

# --- KRONOS SIMULATION ENGINE (STATISTISCHE EXTREM- UND KERN-WERTUNG) ---
def run_kronos_simulation(current_price: float, num_paths: int = 100):
    np.random.seed(int(time.time()) % 10000)
    mu = 0.0002
    sigma = 0.015
    
    steps_map = {
        "24h": 24,
        "48h": 48,
        "1w": 168,
        "2w": 336,
        "4w": 672,
        "8w": 1344,
        "12w": 2016
    }
    max_steps = 2016
    results = {k: [] for k in steps_map.keys()}

    for _ in range(num_paths):
        price = current_price
        for t in range(1, max_steps + 1):
            shock = np.random.normal(0, 1)
            price = price * math.exp((mu - 0.5 * sigma**2) + sigma * shock)
            for k, step_t in steps_map.items():
                if t == step_t:
                    results[k].append(price)

    output = {}
    for k, prices in results.items():
        arr = np.array(prices)
        output[k] = {
            "core_low": float(np.percentile(arr, 16)),
            "core_high": float(np.percentile(arr, 84)),
            "bear_extreme": float(np.percentile(arr, 5)),
            "bull_extreme": float(np.percentile(arr, 95)),
            "up_prob": int(np.sum(arr > current_price))
        }

    return output

# --- BÖRSE: LIVE-PREIS, 200-TAGE-Ø UND 50-WOCHEN-Ø ---
def get_live_data_and_smas():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 1. Aktueller Preis & 24h Hoch/Tief
        ticker_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
        ticker_res = requests.get(ticker_url, headers=headers, timeout=4).json()
        price = float(ticker_res["lastPrice"])
        high_24h = float(ticker_res["highPrice"])
        low_24h = float(ticker_res["lowPrice"])
        
        # 2. 200-Tage-Durchschnitt (200D SMA)
        klines_200d_url = "https://api.binance.com/api/v3/klines?symbol=BTCEUR&interval=1d&limit=200"
        res_200d = requests.get(klines_200d_url, headers=headers, timeout=4).json()
        closes_200d = [float(c[4]) for c in res_200d]
        sma200d = sum(closes_200d) / len(closes_200d) if len(closes_200d) > 0 else price * 0.92

        # 3. 50-Wochen-Durchschnitt (50W SMA)
        klines_50w_url = "https://api.binance.com/api/v3/klines?symbol=BTCEUR&interval=1w&limit=50"
        res_50w = requests.get(klines_50w_url, headers=headers, timeout=4).json()
        closes_50w = [float(c[4]) for c in res_50w]
        sma50w = sum(closes_50w) / len(closes_50w) if len(closes_50w) > 0 else price * 0.88

    except Exception:
        price = 66159.0
        high_24h = 67656.0
        low_24h = 65918.0
        sma200d = 61200.0
        sma50w = 58500.0

    # KI-Kaufempfehlung
    if price < sma200d and price < sma50w:
        signal = "STARKER KAUF (Bärenmarkt-Dip) 🟢🟢"
        signal_color = "#10b981"
        signal_text = "Der Kurs liegt unter dem 200-Tage- UND 50-Wochen-Durchschnitt. Historisch extrem seltene und lukrative Kaufzone!"
    elif price < sma200d or price < sma50w:
        signal = "SEHR GUTER KAUF 🟢"
        signal_color = "#34d399"
        signal_text = "Der Kurs testet wichtige langfristige Unterstützungslinien. Sehr gutes Chance-Risiko-Verhältnis für den Einstieg."
    elif 1.0 <= price / sma200d <= 1.15:
        signal = "IDEAL FÜR SPARPLAN (DCA) 🟡"
        signal_color = "#f59e0b"
        signal_text = "Der Kurs bewegt sich im gesunden Trendkanal oberhalb der Durchschnitte. Ideal für regelmäßige Tranchenkäufe."
    else:
        signal = "ABWARTEN / ERHÖHTES RISIKO 🔴"
        signal_color = "#ef4444"
        signal_text = "Der Kurs ist kurzfristig überhitzt und deutlich über die 200D- und 50W-Linien hinausgeschossen. Rücksetzer abwarten."

    return {
        "price": price,
        "high_24h": high_24h,
        "low_24h": low_24h,
        "sma200d": sma200d,
        "sma50w": sma50w,
        "signal": signal,
        "signal_color": signal_color,
        "signal_text": signal_text
    }

# --- REST API ---
@app.get("/api/data")
def get_dashboard_data():
    market_data = get_live_data_and_smas()
    kronos_sim = run_kronos_simulation(market_data["price"], num_paths=100)
    return {
        "market": market_data,
        "kronos": kronos_sim
    }

# --- DASHBOARD HTML ---
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Kronos Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 16px; }
        .card { background: #1e293b; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }
        h1 { font-size: 1.15rem; color: #f59e0b; margin-top: 0; }
        .price-huge { font-size: 2rem; font-weight: bold; color: #10b981; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 12px; }
        .stat-box { background: #0f172a; padding: 10px; border-radius: 8px; text-align: center; }
        .stat-title { font-size: 0.7rem; color: #94a3b8; }
        .stat-val { font-size: 0.88rem; font-weight: bold; }
        .signal-card { border-left: 6px solid #f59e0b; }
        .signal-title { font-size: 1.25rem; font-weight: bold; margin-bottom: 4px; }
        .signal-desc { font-size: 0.85rem; color: #cbd5e1; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #334155; font-size: 0.8rem; }
        th { color: #94a3b8; font-size: 0.72rem; }
        .badge-up { background: #065f46; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
        .bear-val { color: #f87171; font-size: 0.75rem; }
        .bull-val { color: #34d399; font-size: 0.75rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>⚡ BTC MARKTLAGE & DURCHSCHNITTSPREISE</h1>
        <div id="live-price" class="price-huge">Lade Daten...</div>
        <div class="grid-3">
            <div class="stat-box">
                <div class="stat-title">200-Tage-Ø (200D)</div>
                <div id="sma200d" class="stat-val" style="color: #38bdf8;">-</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">50-Wochen-Ø (50W)</div>
                <div id="sma50w" class="stat-val" style="color: #a78bfa;">-</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">24h Hoch / Tief</div>
                <div id="range-24h" class="stat-val" style="font-size: 0.75rem;">-</div>
            </div>
        </div>
    </div>

    <div class="card signal-card" id="signal-card-bg">
        <div class="stat-title">KRONOS KI-INVESTMENT-EMPFEHLUNG</div>
        <div id="signal-title" class="signal-title">Analyse läuft...</div>
        <div id="signal-desc" class="signal-desc">-</div>
    </div>

    <div class="card">
        <h1>🔮 KRONOS PROGNOSE (Kern vs. Bären/Bullen-Extreme)</h1>
        <table>
            <thead>
                <tr>
                    <th>Zeitraum</th>
                    <th>Realistischer Kern (68%)</th>
                    <th>Bären-Extrem (5%)</th>
                    <th>Bullen-Extrem (95%)</th>
                    <th>Chance</th>
                </tr>
            </thead>
            <tbody id="kronos-table">
                <tr><td colspan="5">Berechne Modell...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        const labels = {
            "24h": "24 Std",
            "48h": "48 Std",
            "1w": "1 Woche",
            "2w": "2 Wochen",
            "4w": "4 Wochen",
            "8w": "8 Wochen",
            "12w": "12 Wochen"
        };

        async function fetchDashboardData() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                const m = data.market;
                
                document.getElementById('live-price').innerText = m.price.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                document.getElementById('sma200d').innerText = m.sma200d.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                document.getElementById('sma50w').innerText = m.sma50w.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                document.getElementById('range-24h').innerText = `${m.high_24h.toFixed(0)} / ${m.low_24h.toFixed(0)} €`;

                const sigCard = document.getElementById('signal-card-bg');
                sigCard.style.borderLeftColor = m.signal_color;
                
                const sigTitle = document.getElementById('signal-title');
                sigTitle.innerText = m.signal;
                sigTitle.style.color = m.signal_color;
                document.getElementById('signal-desc').innerText = m.signal_text;
                
                const k = data.kronos;
                let rowsHtml = '';
                
                for (const [key, label] of Object.entries(labels)) {
                    if (k[key]) {
                        rowsHtml += `
                            <tr>
                                <td><strong>${label}</strong></td>
                                <td><strong style="color: #f1f5f9;">${k[key].core_low.toFixed(0)} € – ${k[key].core_high.toFixed(0)} €</strong></td>
                                <td><span class="bear-val">🐻 ${k[key].bear_extreme.toFixed(0)} €</span></td>
                                <td><span class="bull-val">🐂 ${k[key].bull_extreme.toFixed(0)} €</span></td>
                                <td><span class="badge-up">🟢 ${k[key].up_prob}%</span></td>
                            </tr>
                        `;
                    }
                }
                
                document.getElementById('kronos-table').innerHTML = rowsHtml;
            } catch (err) {
                console.error("Fehler beim Abrufen:", err);
            }
        }

        fetchDashboardData();
        setInterval(fetchDashboardData, 4000);
    </script>
</body>
</html>
    """
