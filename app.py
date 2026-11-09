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
            # Realistischer Kernbereich (68% Wahrscheinlichkeit / 1-Sigma: 16. bis 84. Perzentil)
            "core_low": float(np.percentile(arr, 16)),
            "core_high": float(np.percentile(arr, 84)),
            # Bärenmarkt-Extrem (5. Perzentil -> Nur 5% Chance für noch tiefere Kurse)
            "bear_extreme": float(np.percentile(arr, 5)),
            # Bullenmarkt-Extrem (95. Perzentil -> Nur 5% Chance für noch höhere Kurse)
            "bull_extreme": float(np.percentile(arr, 95)),
            # Anstiegswahrscheinlichkeit (Prozentualer Anteil steigender Pfade)
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

    # --- KI-KAUFEMPFEHLUNG FÜR DAS DASHBOARD ---
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
        signal_
