import math
import time
import numpy as np
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Kronos Bitcoin Forecasting & Signal Engine")

# --- KRONOS SIMULATION (KERN-KORRIDOR VS. EXTREMWERTE) ---
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
            # Realistischer Kern-Bereich (68% Wahrscheinlichkeit / 1-Sigma: 16. bis 84. Perzentil)
            "core_low": float(np.percentile(arr, 16)),
            "core_high": float(np.percentile(arr, 84)),
            # Extreme Ausreißer (90% Spanne / Bären- vs. Bullen-Extrem)
            "extreme_low": float(np.percentile(arr, 5)),
            "extreme_high": float(np.percentile(arr, 95)),
            "up_prob": int(np.sum(arr > current_price))
        }

    return output

# --- LIVE PREIS & 200-TAGE-DURCHSCHNITT (200 SMA) ---
def get_live_data_and_sma200():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 1. Aktueller Preis
        ticker_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
        ticker_res = requests.get(ticker_url, headers=headers, timeout=4).json()
        price = float(ticker_res["lastPrice"])
        high_24h = float(ticker_res["highPrice"])
        low_24h = float(ticker_res["lowPrice"])
        
        # 2. 200 Tageskerzen für 200 SMA
        klines_url = "https://api.binance.com/api/v3/klines?symbol=BTCEUR&interval=1d&limit=200"
        klines_res = requests.get(klines_url, headers=headers, timeout=5).json()
        closes = [float(candle[4]) for candle in klines_res]
        sma200 = sum(closes) / len(closes) if len(closes) > 0 else price * 0.92
        
    except Exception:
        price = 66159.0
        high_24h = 67656.0
        low_24h = 65918.0
        sma200 = 61200.0  # Fallback

    # --- KAUFEMPFEHLUNG EVALUATION ---
    ratio = price / sma200
    if ratio < 0.98:
        signal = "STARKER KAUF 🟢"
        signal_color = "#10b981"
        signal_text = "Der Kurs liegt UNTER dem 200-Tage-Durchschnitt. Historisch eine exzellente Kaufzone."
    elif 0.98 <= ratio <= 1.12:
        signal = "IDEALER EINSTIEG (DCA) 🟡"
        signal_color = "#f59e0b"
        signal_text = "Der Kurs konsolidiert nahe der 200-Tage-Linie. Ideal für Tranchenkäufe (Sparplan/DCA)."
    else:
        signal = "ABWARTEN / WARNUNG 🔴"
        signal_color = "#ef4444"
        signal_text = "Der Kurs ist überhitzt und liegt weit über dem 200-Tage-Durchschnitt. Erhöhtes Rücksetzer-Risiko."

    return {
        "price": price,
        "high_24h": high_24h,
        "low_24h": low_24h,
        "sma200": sma200,
        "signal": signal,
        "signal_color": signal_color,
        "signal_text": signal_text
    }

# --- REST API ---
@app.get("/api/data")
def get_dashboard_data():
    market_data = get_live_data_and_sma200()
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
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
        .stat-box { background: #0f172a; padding: 10px; border-radius: 8px; text-align: center; }
        .stat-title { font-size: 0.75rem; color: #94a3b8; }
        .stat-val { font-size: 0.95rem; font-weight: bold; }
        
        /* Signal Card */
        .signal-card { border-left: 6px solid #f59e0b; }
        .signal-title { font-size: 1.3rem; font-weight: bold; margin-bottom: 4px; }
        .signal-desc { font-size: 0.85rem; color: #cbd5e1; }

        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #334155; font-size: 0.8rem; }
        th { color: #94a3b8; font-size: 0.75rem; }
        .badge-up { background: #065f46; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
        .sub-text { font-size: 0.7rem; color: #64748b; display: block; }
    </style>
</head>
<body>
    <div class="card">
        <h1>⚡ BTC MARKTLAGE & 200 SMA</h1>
        <div id="live-price" class="price-huge">Lade Daten...</div>
        <div class="grid">
            <div class="stat-box">
                <div class="stat-title">200-Tage-Ø (200 SMA)</div>
                <div id="sma200" class="stat-val" style="color: #38bdf8;">-</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">24h Hoch / Tief</div>
                <div id="range-24h" class="stat-val">-</div>
            </div>
        </div>
    </div>

    <!-- Kaufempfehlung Card -->
    <div class="card signal-card" id="signal-card-bg">
        <div class="stat-title">KRONOS KI-KAUFEMPFEHLUNG</div>
        <div id="signal-title" class="signal-title">Analyse läuft...</div>
        <div id="signal-desc" class="signal-desc">-</div>
    </div>

    <div class="card">
        <h1>🔮 KRONOS PROGNOSE (Realistischer Kern vs. Extremwert)</h1>
        <table>
            <thead>
                <tr>
                    <th>Zeitraum</th>
                    <th>Realistischer Kern (68%)</th>
                    <th>Extrem-Spanne (90%)</th>
                    <th>Chance</th>
                </tr>
            </thead>
            <tbody id="kronos-table">
                <tr><td colspan="4">Berechne Modell...</td></tr>
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
                document.getElementById('sma200').innerText = m.sma200.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                document.getElementById('range-24h').innerText = `${m.high_24h.toFixed(0)} / ${m.low_24h.toFixed(0)} €`;

                // Signal-Update
                const sigCard = document.getElementById('signal-card-bg');
                sigCard.style.borderLeftColor = m.signal_color;
                
                const sigTitle = document.getElementById('signal-title');
                sigTitle.innerText = m.signal;
                sigTitle.style.color = m.signal_color;
                document.getElementById('signal-desc').innerText = m.signal_text;
                
                // Tabellen-Update
                const k = data.kronos;
                let rowsHtml = '';
                
                for (const [key, label] of Object.entries(labels)) {
                    if (k[key]) {
                        rowsHtml += `
                            <tr>
                                <td><strong>${label}</strong></td>
                                <td><strong style="color: #f1f5f9;">${k[key].core_low.toFixed(0)} € – ${k[key].core_high.toFixed(0)} €</strong></td>
                                <td><span class="sub-text">${k[key].extreme_low.toFixed(0)} € – ${k[key].extreme_high.toFixed(0)} €</span></td>
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
