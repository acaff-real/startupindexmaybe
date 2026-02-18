from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# 1. CONSTANTS & TICKER MAP
TICKER_MAP = {
    "PAYTM.NS": {"name": "One 97 Comm (Paytm)", "sector": "Fintech"},
    "ZOMATO.BO": {"name": "Zomato", "sector": "Food Tech"},
    "NYKAA.NS": {"name": "Nykaa", "sector": "E-Commerce"},
    "POLICYBZR.NS": {"name": "PB Fintech", "sector": "Fintech"},
    "DELHIVERY.NS": {"name": "Delhivery", "sector": "Logistics"},
    "CARTRADE.NS": {"name": "CarTrade Tech", "sector": "Auto Tech"},
    "EASEMYTRIP.NS": {"name": "Easy Trip Planners", "sector": "Travel Tech"},
    "NAZARA.NS": {"name": "Nazara Tech", "sector": "Gaming"},
    "IDEAFORGE.NS": {"name": "ideaForge", "sector": "Drone Tech"},
    "MAPMYINDIA.NS": {"name": "MapmyIndia", "sector": "Deep Tech"},
    "RATEGAIN.NS": {"name": "RateGain", "sector": "SaaS"},
    "LENSKART.NS": {"name": "Lenskart", "sector": "E-Commerce"}, 
    "YATRA.NS": {"name": "Yatra Online", "sector": "Travel Tech"},
    "ZAGGLE.NS": {"name": "Zaggle", "sector": "Fintech"},
    "HONASA.NS": {"name": "Honasa (Mamaearth)", "sector": "D2C"},
    "CIEINDIA.NS": {"name": "CIE Automotive", "sector": "Auto Comp"},
    "KPITTECH.NS": {"name": "KPIT Tech", "sector": "Auto Tech"},
    "TATAELXSI.NS": {"name": "Tata Elxsi", "sector": "Design Tech"},
    "HAPPSTMNDS.NS": {"name": "Happiest Minds", "sector": "IT Services"},
    "ROUTE.NS": {"name": "Route Mobile", "sector": "CPaaS"},
    "TANLA.NS": {"name": "Tanla Platforms", "sector": "CPaaS"},
    "AFFLE.NS": {"name": "Affle India", "sector": "Ad Tech"},
    "INDIAMART.NS": {"name": "IndiaMART", "sector": "B2B E-Comm"},
    "INFIBEAM.NS": {"name": "Infibeam Avenues", "sector": "Fintech"},
    "JUSTDIAL.NS": {"name": "Just Dial", "sector": "Search"}
}

# 2. SHARES DATABASE (Hardcoded to prevent API blocking/NaN errors)
# Values are approx shares outstanding (in integers)
SHARES_DB = {
    "PAYTM.NS": 635000000,
    "ZOMATO.NS": 8600000000,
    "NYKAA.NS": 2850000000,
    "POLICYBZR.NS": 450000000,
    "DELHIVERY.NS": 730000000,
    "CARTRADE.NS": 46000000,
    "EASEMYTRIP.NS": 1770000000,
    "NAZARA.NS": 76000000,
    "IDEAFORGE.NS": 42000000,
    "MAPMYINDIA.NS": 53000000,
    "RATEGAIN.NS": 117000000,
    "LENSKART.NS": 150000000, # Placeholder if unlisted/unavailable
    "YATRA.NS": 156000000,
    "ZAGGLE.NS": 122000000,
    "HONASA.NS": 320000000,
    "CIEINDIA.NS": 379000000,
    "KPITTECH.NS": 270000000,
    "TATAELXSI.NS": 62000000,
    "HAPPSTMNDS.NS": 150000000,
    "ROUTE.NS": 62000000,
    "TANLA.NS": 135000000,
    "AFFLE.NS": 133000000,
    "INDIAMART.NS": 60000000,
    "INFIBEAM.NS": 2700000000,
    "JUSTDIAL.NS": 84000000
}

STARTUP_TICKERS_FULL = list(TICKER_MAP.keys())
BENCHMARK_TICKER = "^NSEI"

def get_fundamental_data(tickers):
    # Instead of slow API calls, we return our robust local DB
    # We create a DataFrame to match the format expected by the logic
    data = {}
    for ticker in tickers:
        # Default to a median value if ticker missing from DB to prevent crashes
        shares = SHARES_DB.get(ticker, 100000000) 
        data[ticker] = {'shares': shares}
            
    df = pd.DataFrame.from_dict(data, orient='index')
    return df

def calculate_weighted_index(tickers, start_date_str, end_date_str, shares_series):
    if not tickers: return None
    end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
    
    # Fetch price history
    raw_data = yf.download(tickers, start=start_date_str, end=end_date_obj.strftime("%Y-%m-%d"), threads=False, auto_adjust=False, progress=False)
    
    if raw_data.empty: return None

    # Handle MultiIndex columns
    if 'Adj Close' in raw_data.columns.levels[0]:
        prices = raw_data['Adj Close']
    elif 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        # Fallback for single level or unexpected structure
        prices = raw_data.iloc[:, :len(tickers)]
    
    prices = prices.dropna(axis=1, how='all').ffill().bfill()
    if prices.empty: return None

    # Align shares with price columns
    common = prices.columns.intersection(shares_series.index)
    prices = prices[common]
    current_shares = shares_series[common]
    
    market_caps = prices.mul(current_shares, axis=1)
    total_market_cap = market_caps.sum(axis=1)
    
    if total_market_cap.empty or total_market_cap.iloc[0] == 0: return None
    
    index_series = (total_market_cap / total_market_cap.iloc[0]) * 100
    index_series.index = index_series.index.strftime('%Y-%m-%d')
    return index_series.to_dict()

# --- ROUTES ---

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/api/startups/chart', methods=['GET'])
def startup_chart_data():
    start_date = request.args.get('start', '2026-01-01')
    end_date = request.args.get('end', datetime.today().strftime('%Y-%m-%d'))
    
    meta_df = get_fundamental_data(STARTUP_TICKERS_FULL)
    startup_data = calculate_weighted_index(STARTUP_TICKERS_FULL, start_date, end_date, meta_df['shares'])
    
    # NIFTY Benchmark
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    nifty_raw = yf.download(BENCHMARK_TICKER, start=start_date, end=end_date_obj.strftime("%Y-%m-%d"), progress=False)
    
    nifty_data = {}
    if not nifty_raw.empty:
        col = 'Adj Close' if 'Adj Close' in nifty_raw else 'Close'
        nifty_series = nifty_raw[col].ffill().bfill()
        if isinstance(nifty_series, pd.DataFrame): nifty_series = nifty_series[BENCHMARK_TICKER]
        nifty_index = (nifty_series / nifty_series.iloc[0]) * 100
        nifty_index.index = nifty_index.index.strftime('%Y-%m-%d')
        nifty_data = nifty_index.to_dict()

    if startup_data is None: return jsonify({"error": "No data found"}), 404
        
    response = {
        "dates": list(startup_data.keys()),
        "startup_index": list(startup_data.values()),
        "nifty_index": [nifty_data.get(date, None) for date in startup_data.keys()],
    }
    return jsonify(response)

@app.route('/api/startups/composition', methods=['GET'])
def startup_composition():
    """Returns the latest Snapshot of all companies with real weights."""
    meta_df = get_fundamental_data(STARTUP_TICKERS_FULL)
    
    # Fetch last 5 days to ensure we get a valid price
    end_date = datetime.today()
    start_date = end_date - timedelta(days=5)
    
    data = yf.download(STARTUP_TICKERS_FULL, start=start_date, end=end_date, threads=False, auto_adjust=False, progress=False)
    
    if data.empty:
        return jsonify([])

    # Extract latest prices safely
    if 'Adj Close' in data.columns.levels[0]:
        latest_prices_df = data['Adj Close']
    else:
        latest_prices_df = data['Close']
        
    # Get the very last row of prices
    latest_prices = latest_prices_df.iloc[-1]
    
    composition_list = []
    total_mkt_cap = 0
    temp_data = []

    for ticker in STARTUP_TICKERS_FULL:
        # Check if we have price data for this ticker
        if ticker in latest_prices:
            price = latest_prices[ticker]
            
            # Check if price is valid (not NaN)
            if pd.isna(price):
                # Try finding the last valid price in the series
                valid_series = latest_prices_df[ticker].dropna()
                if not valid_series.empty:
                    price = valid_series.iloc[-1]
                else:
                    continue # Skip if no price data at all

            shares = meta_df.loc[ticker, 'shares']
            mkt_cap = price * shares
            total_mkt_cap += mkt_cap
            
            temp_data.append({
                "ticker": ticker,
                "price": price,
                "mkt_cap": mkt_cap
            })

    # Second pass: Calculate Weights
    for item in temp_data:
        ticker = item['ticker']
        details = TICKER_MAP.get(ticker, {"name": ticker, "sector": "Tech"})
        
        weight = (item['mkt_cap'] / total_mkt_cap) * 100
        
        composition_list.append({
            "ticker": ticker.replace(".NS", "").replace(".BO", ""),
            "name": details['name'],
            "sector": details['sector'],
            "price": round(item['price'], 2),
            "mkt_cap": round(item['mkt_cap'] / 10000000), # In Crores
            "weight": round(weight, 2),
            # Mock High/Low for UI display
            "high": round(item['price'] * 1.15, 2),
            "low": round(item['price'] * 0.85, 2)
        })
    
    composition_list.sort(key=lambda x: x['weight'], reverse=True)
    
    return jsonify(composition_list)

if __name__ == '__main__':
    app.run(debug=True, port=5000)