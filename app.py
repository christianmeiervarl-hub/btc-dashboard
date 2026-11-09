import math
import time
import numpy as np
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Kronos Bitcoin Forecasting Engine")

# --- KRONOS SIMULATION ENGINE ---
def run_kronos_simulation(current_price: float, num_paths: int = 100):
    np.random.seed(int(time.time()) % 10000)
    mu = 0.0002
    sigma = 0.015
    
    steps_map = {
        "24h": 24, "48h": 48, "1w": 168,
        "2w": 336, "4w": 672, "8w": 1344, "12w": 2016
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

# --- BÖRSE: LIVE-PREIS, 200D SMA & 50W SMA ---
def get_live_data_and_smas():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        ticker_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCEUR"
        ticker_res = requests.get(ticker_url, headers=headers, timeout=4).json()
        price = float(ticker_res["lastPrice"])
        high_24h = float(ticker_res["highPrice"])
        low_24h = float(ticker_res["lowPrice"])
        
        klines_200d_url = "https://api.binance.com/api/v3/klines?symbol=BTCEUR&interval=1d&limit=200"
        res_2
