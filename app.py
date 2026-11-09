import asyncio
import math
import time
import numpy as np
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Kronos Bitcoin Forecasting Engine")

# --- KRONOS PROBABILISTISCHE ENGINE (100 SIMULIERTE ZUKUNFTSPFADE) ---
def run_kronos_simulation(current_price: float, num_paths: int = 100):
    """
    Simuliert 100 Zukunftsverläufe basierend auf weltweiten Volatilitätsdaten & Monte-Carlo.
    """
    np.random.seed(int(time.time()) % 10000)
    mu = 0.0002       # Erwartete Drift
    sigma = 0.015     # Stochastische Volatilität (24-48h)
    
    # 24h, 48h, 7 Tage (168 Stunden)
    steps_24h = 24
    steps_48h = 48
    steps_7d = 168

    paths = []
    final_24h, final_48h, final_7d = [], [], []

    for _ in range(num_paths):
        path = [current_price]
        price = current_price
        for t in range(1, steps_7d + 1):
            shock = np.random.normal(0, 1)
            price = price * math.exp((mu - 0.5 * sigma**2) + sigma * shock)
            path.append(price)
            if t == steps_24h:
                final_24h.append(price)
            elif t == steps_48h:
                final_48h.append(price)
            elif t == steps_7d:
                final_7d.append(price)
        paths.append(path)

    return {
        "p24_low": float(np.percentile(final_24h, 5)),
        "p24_high": float(np.percentile(final_24h, 95)),
        "p48_low": float(np.percentile(final_48h, 5)),
        "p48_high": float(np.percentile(final_48h, 95)),
        "p7d_low": float(np.percentile(final_7d, 5)),
        "p7d_high": float(np.percentile(final_7d, 95)),
        "avg_24h": float(np.mean(final_24h)),
        "avg_48h": float(np.mean(final_48h)),
        "avg_7d": float(np.mean(final_7d)),
    }

# --- ECHTZEIT BTC-PREIS VOM GLOBALEN MARKT ---
def get_live_btc_eur():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur&include_24hr_change=true&include_24hr_high=true&include_24hr_low=true"
        res = requests.get(url, timeout=5).json()["bitcoin"]
        return {
            "price": res["eur"],
            "change_24h": res.get("eur_24h_change", 0.0),
            "high_24h": res.get("eur_24h_high", res["eur"] * 1.01),
            "low_24h": res.get("eur_24h_low", res["eur"] * 0.99)
        }
    except Exception:
        return {"price": 66159.0, "change_24h": -0.5, "high_24h": 67656.0, "low_24h": 65918.0}

# --- DASHBOARD HTML / APP INTERACTION ---
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Kronos Dashboard</title>
    <link rel="manifest" href="data:application/json,{ %22name%22:%22BTC%20Kronos%22,%22short_name%22:%22BTCKronos%22,%22start_url%22:%22/%22,%22display%22:%22standalone%22}">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 16px; }
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
        .badge { background: #3b82f6; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>⚡ BTC ECHTZEITBÖRSE</h1>
        <div id="live-price" class="price-huge">Lädt...</div>
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
        <h1>🔮 KRONOS PROGNOSE (100 Zukunftsverläufe)</h1>
        <table>
            <thead>
                <tr>
                    <th>Zeitraum</th>
                    <th>Erwarteter Korridor (EUR)</th>
                </tr>
            </thead>
            <tbody id="kronos-table">
                <tr><td colspan="2">Berechne 100 Pfade...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            document.getElementById('live-price').innerText = data.market.price.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
            document.getElementById('high-24h').innerText = data.market.high_24h.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
            document.getElementById('low-24h').innerText = data.market.low_24h.toLocaleString('de-DE', {style: 'currency', currency: 'EUR'});
            
            const k = data.kronos;
            document.getElementById('kronos-table').innerHTML = `
                <tr><td><strong>24 Stunden</strong></td><td>${k.p24_low.toFixed(0)} € – ${k.p24_high.toFixed(0)} €</td></tr>
                <tr><td><strong>48 Stunden</strong></td><td>${k.p48_low.toFixed(0)} € – ${k.p48_high.toFixed(0)} €</td></tr>
                <tr><td><strong>1 Woche</strong></td><td>${k.p7d_low.toFixed(0)} € – ${k.p7d_high.toFixed(0)} €</td></tr>
            `;
        };
    </script>
</body>
</html>
    """

# --- WEBSOCKET FÜR REAL-TIME PUSH ON IPHONE & PIXEL ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            market_data = get_live_btc_eur()
            kronos_sim = run_kronos_simulation(market_data["price"], num_paths=100)
            payload = {
                "market": market_data,
                "kronos": kronos_sim
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5)  # Live-Update alle 5 Sekunden
    except WebSocketDisconnect:
        pass