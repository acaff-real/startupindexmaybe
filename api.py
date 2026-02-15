from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)
# CORS allows your separate HTML frontend to request data from this Python server
CORS(app)

STARTUP_TICKERS_FULL = [
    "PWL.BO", "PINELABS.NS", "YATRA.NS", "IDEAFORGE.NS", "SHADOWFAX.NS",
    "AMAGI.NS", "GROWW.BO", "LENSKART.NS", "URBANCO.NS", "MEESHO.NS",
    "OLAELEC.NS", "SWIGGY.NS", "FIRSTCRY.NS", "GODIGIT.NS", "HONASA.NS",
    "INDGN.NS", "TBOTEK.NS", "IXIGO.NS", "AWFIS.NS", "ZAGGLE.NS", 
    "ENTERO.NS", "MEDIASSIST.NS", "BLUESTONE.NS", "WEWORK.NS", "BLACKBUCK.NS"
]

BENCHMARK_TICKER = "^NSEI"

# Simple in-memory cache to speed up API responses
APP_CACHE = {
    'startup_meta': None
}

def get_fundamental_data(tickers):
    """Fetches Shares, P/E, and EPS. Uses cache if available."""
    if APP_CACHE['startup_meta'] is not None:
        return APP_CACHE['startup_meta']
        
    data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            data[ticker] = {
                'shares': info.get('sharesOutstanding', np.nan),
                'pe': info.get('trailingPE', np.nan),
                'eps': info.get('trailingEps', np.nan)
            }
        except:
            data[ticker] = {'shares': np.nan, 'pe': np.nan, 'eps': np.nan}
            
    df = pd.DataFrame.from_dict(data, orient='index')
    df['shares'] = df['shares'].fillna(df['shares'].median())
    
    APP_CACHE['startup_meta'] = df
    return df

def calculate_weighted_index(tickers, start_date_str, end_date_str, shares_series):
    """Calculates the index and returns a JSON-friendly dictionary."""
    if not tickers: return None
    
    # Add 1 day to end_date for yfinance exclusivity
    end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
    end_str = end_date_obj.strftime("%Y-%m-%d")
    
    raw_data = yf.download(tickers, start=start_date_str, end=end_str, threads=False, auto_adjust=False, progress=False)
    
    if raw_data.empty: return None

    if 'Adj Close' in raw_data.columns.levels[0]:
        prices = raw_data['Adj Close']
    elif 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        prices = raw_data.iloc[:, :len(tickers)]
    
    prices = prices.dropna(axis=1, how='all').ffill().bfill()
    if prices.empty: return None

    common = prices.columns.intersection(shares_series.index)
    prices = prices[common]
    current_shares = shares_series[common]
    
    market_caps = prices.mul(current_shares, axis=1)
    total_market_cap = market_caps.sum(axis=1)
    
    if total_market_cap.empty or total_market_cap.iloc[0] == 0: 
        return None
    
    index_series = (total_market_cap / total_market_cap.iloc[0]) * 100
    
    # Convert Pandas Series with DatetimeIndex to a standard Dictionary (String Date -> Float Value)
    index_series.index = index_series.index.strftime('%Y-%m-%d')
    return index_series.to_dict()

# --- API ENDPOINTS ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Startup Index API is running! Data available at /api/startups/chart"})
    
@app.route('/api/startups/chart', methods=['GET'])
def startup_chart_data():
    """
    Endpoint to get the time-series data for the Startup Index.
    Usage: GET /api/startups/chart?start=2026-01-01&end=2026-02-15
    """
    # Get dates from the URL, or default to YTD
    start_date = request.args.get('start', '2026-01-01')
    end_date = request.args.get('end', datetime.today().strftime('%Y-%m-%d'))
    
    # 1. Get Meta Data (Shares)
    meta_df = get_fundamental_data(STARTUP_TICKERS_FULL)
    
    # 2. Calculate Startup Index
    startup_data = calculate_weighted_index(STARTUP_TICKERS_FULL, start_date, end_date, meta_df['shares'])
    
    # 3. Calculate NIFTY 50 (Benchmark)
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    nifty_raw = yf.download(BENCHMARK_TICKER, start=start_date, end=end_date_obj.strftime("%Y-%m-%d"), progress=False)
    
    nifty_data = {}
    if not nifty_raw.empty:
        col = 'Adj Close' if 'Adj Close' in nifty_raw else 'Close'
        nifty_series = nifty_raw[col].ffill().bfill()
        
        if isinstance(nifty_series, pd.DataFrame):
            nifty_series = nifty_series[BENCHMARK_TICKER]
            
        nifty_index = (nifty_series / nifty_series.iloc[0]) * 100
        nifty_index.index = nifty_index.index.strftime('%Y-%m-%d')
        nifty_data = nifty_index.to_dict()

    # 4. Package and send to frontend
    if startup_data is None:
        return jsonify({"error": "No data found for the given dates"}), 404
        
    response = {
        "dates": list(startup_data.keys()),
        "startup_index": list(startup_data.values()),
        "nifty_index": [nifty_data.get(date, None) for date in startup_data.keys()],
        "latest_value": list(startup_data.values())[-1]
    }
    
    return jsonify(response)

if __name__ == '__main__':
    # Runs the API on port 5000
    app.run(debug=True, port=5000)