import math
import time
import numpy as np
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Kronos Bitcoin Forecasting Engine")

# --- KRONOS PROGNOSE ENGINE (100 PFADE BIS ZU 12 WOCHEN) ---
def run_kronos_simulation(current_price: float, num_paths: int = 100):
    np.random.seed(int(time.time()) % 10000)
    mu = 0.0002
    sigma = 0.015
    
    # Zeitschritte in Stunden (bis zu 12 Wochen = 2016 Std)
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
            "low": float(np.percentile(arr, 5)),
            "high": float(np.percentile(arr, 95)),
            "up_prob": int(np.sum(arr > current_price))
        }

    return output

# --- ECHTZEIT BTC-PREIS (BINANCE MIT FALLBACK) ---
def get_live_btc_eur():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
        res = requests.get(url, headers=headers, timeout=4).json()
        return {
            "price": float(res["lastPrice"]),
            "high_24h": float(res["highPrice"]),
            "low_24h": float(res["lowPrice"])
        }
    except Exception:
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur&include_24hr_high=true&include_24hr_low=true"
            res = requests.get(url, headers=headers, timeout=4).json()["bitcoin"]
            return {
                "price": float(res["eur"]),
                "high_24h": float(res["eur_24h_high"]),
                "low_24h": float(res["eur_24h_low"])
            }
        except Exception:
            return {"price": 66159.0, "high_24h": 67656.0, "low_24h": 65918.0}

# --- REST API ENDPUNKT ---
@app.get("/api/data")
def get_dashboard_data():
    market_data = get_live_btc_eur()
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
        h1 { font-size: 1.25rem; color: #f59e0b; margin-top: 0; }
        .price-huge { font-size: 2rem; font-weight: bold; color: #10b981; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
        .stat-box { background: #0f172a; padding: 10px; border-radius: 8px; text-align: center; }
        .stat-title { font-size: 0.75rem; color: #94a3b8; }
        .stat-val { font-size: 1rem; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #334155; font-size: 0.85rem; }
        th { color: #94a3b8; }
        .badge-up { background: #065f46; color: #34d399; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>⚡ BTC ECHTZEITBÖRSE</h1>
        <div id="live-price" class="price-huge">Lade Daten...</div>
        <div class="grid">
            <div class="stat-box">
                <div class="stat-title">24h Hoch</div>
                <div id="high-24h" class="stat-val">-</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">24h Tief</div>
                <div id="low-24h" class="stat-val">-</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h1>🔮 KRONOS PROGNOSE (100 Pfade bis 12 Wochen)</h1>
        <table>
            <thead>
                <tr>
                    <th>Zeitraum</th>
                    <th>90% Korridor (EUR)</th>
                    <th>Chance auf Anstieg</th>
                </tr>
            </thead>
            <tbody id="kronos-table">
                <tr><td colspan="3">Berechne Wahrscheinlichkeiten...</td></tr>
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
                
                document.getElementById('live-price').innerText = data.market.price.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                document.getElementById('high-24h').innerText = data.market.high_24h.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                document.getElementById('low-24h').innerText = data.market.low_24h.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
                
                const k = data.kronos;
                let rowsHtml = '';
                
                for (const [key, label] of Object.entries(labels)) {
                    if (k[key]) {
                        rowsHtml += `
                            <tr>
                                <td><strong>${label}</strong></td>
                                <td>${k[key].low.toFixed(0)} € – ${k[key].high.toFixed(0)} €</td>
                                <td><span class="badge-up">🟢 ${k[key].up_prob}%</span></td>
                            </tr>
                        `;
                    }
                }
                
                document.getElementById('kronos-table').innerHTML = rowsHtml;
            } catch (err) {
                console.error("Fehler beim Abrufen der Daten:", err);
            }
        }

        fetchDashboardData();
        setInterval(fetchDashboardData, 3000);
    </script>
</body>
</html>
    """
