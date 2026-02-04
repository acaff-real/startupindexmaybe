import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# --- CONFIGURATION ---
GREEN_TICKERS = [
    "ACMESOLAR.NS", "ADANIGREEN.NS", "ALPEXSOLAR.NS", "BORORENEW.NS", 
    "EMMVEE.NS", "INOXWIND.NS", "KPIGREEN.NS", "NTPCGREEN.NS", 
    "OSWALPUMPS.NS", "PACEDIGITK.NS", "PREMIERENE.NS", "SHAKTIPUMP.NS", 
    "SOLEX.NS", "SWSOLAR.NS", "SUZLON.NS", "TATAPOWER.NS", 
    "VIKRAMSOLR.NS", "WAAREEENER.NS", "WAAREERTL.NS"
]

# Validated tickers from your uploaded image
STARTUP_TICKERS = [
    "OLAELEC.NS",    # Ola Electric
    "SHADOWFAX.NS",  # Shadowfax Technologies
    "AMAGI.NS",      # Amagi Media Labs
    "DEVX.NS",       # Dev Accelerator
    "SMARTWORKS.NS", # Smartworks Coworking
    "ARISINFRA.NS",  # ArisInfra Solutions
    "ZAPPFRESH.NS"   # Zappfresh (DSM Fresh Foods)
]

BENCHMARK_TICKER = "^NSEI"

# --- APP SETUP ---
st.set_page_config(page_title="Market Dashboard", layout="wide")
st.title("📈 Market Dashboard: Green Sector vs. Startups")

# --- BACKEND LOGIC ---
@st.cache_data
def fetch_share_counts(tickers):
    """Fetches share counts once and caches them."""
    shares_data = {}
    progress_bar = st.progress(0)
    
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        try:
            stock = yf.Ticker(ticker)
            shares = stock.info.get('sharesOutstanding')
            shares_data[ticker] = shares if shares else np.nan
        except:
            shares_data[ticker] = np.nan
        progress_bar.progress((i + 1) / total)
            
    progress_bar.empty()
    s = pd.Series(shares_data)
    return s.fillna(s.median())

def calculate_weighted_index(tickers, start_date, shares_series):
    """Generic function to calculate any Market Cap Weighted Index."""
    start_str = start_date.strftime('%Y-%m-%d')
    
    # 1. Download
    raw_data = yf.download(tickers, start=start_str, threads=False, auto_adjust=False)
    
    if raw_data.empty:
        return None

    # 2. Extract Prices
    if 'Adj Close' in raw_data.columns.levels[0]:
        prices = raw_data['Adj Close']
    elif 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        prices = raw_data.iloc[:, :len(tickers)]
    
    # 3. Clean & Backfill (Crucial for new IPOs)
    # We use bfill() here so if a stock lists on Jan 5, we assume Jan 1-4 was the IPO price.
    prices = prices.dropna(axis=1, how='all').ffill().bfill()
    
    # 4. Calculate Market Cap
    common_cols = prices.columns.intersection(shares_series.index)
    market_caps = prices[common_cols].mul(shares_series[common_cols], axis=1)
    total_market_cap = market_caps.sum(axis=1)
    
    if total_market_cap.empty:
        return None
        
    # 5. Normalize to 100
    base_value = total_market_cap.iloc[0]
    return (total_market_cap / base_value) * 100

@st.cache_data
def get_all_indices(start_date, _green_shares, _startup_shares):
    """Orchestrates the data fetching for all three lines."""
    
    # 1. Green Index
    green_idx = calculate_weighted_index(GREEN_TICKERS, start_date, _green_shares)
    
    # 2. Startup Index
    startup_idx = calculate_weighted_index(STARTUP_TICKERS, start_date, _startup_shares)
    
    # 3. NIFTY 50 Benchmark
    nifty_data = yf.download(BENCHMARK_TICKER, start=start_date, threads=False, auto_adjust=False)
    if not nifty_data.empty:
        # Handle different yfinance return formats
        try:
            bench_prices = nifty_data['Adj Close'][BENCHMARK_TICKER]
        except KeyError:
            bench_prices = nifty_data['Adj Close'] if 'Adj Close' in nifty_data else nifty_data['Close']
            
        bench_prices = bench_prices.ffill().bfill()
        nifty_idx = (bench_prices / bench_prices.iloc[0]) * 100
    else:
        nifty_idx = None
        
    return green_idx, startup_idx, nifty_idx

# --- SIDEBAR INPUTS ---
st.sidebar.header("Configuration")
start_date = st.sidebar.date_input("Start Date", value=datetime(2026, 1, 1))

if st.sidebar.button("Generate Dashboard"):
    # 1. Fetch Metadata (Cached)
    if 'green_shares' not in st.session_state:
        st.info("Initializing Green Sector metadata...")
        st.session_state['green_shares'] = fetch_share_counts(GREEN_TICKERS)
        
    if 'startup_shares' not in st.session_state:
        st.info("Initializing Startup metadata...")
        st.session_state['startup_shares'] = fetch_share_counts(STARTUP_TICKERS)
    
    # 2. Compute Indices
    with st.spinner("Crunching numbers..."):
        green_series, startup_series, nifty_series = get_all_indices(
            start_date, 
            st.session_state['green_shares'],
            st.session_state['startup_shares']
        )
    
    if green_series is None:
        st.error("Failed to generate indices. Check data availability.")
    else:
        # --- METRICS ROW ---
        # Align all series to the same dates (intersection)
        common_idx = green_series.index.intersection(nifty_series.index)
        if startup_series is not None:
            common_idx = common_idx.intersection(startup_series.index)
            
        g_val = green_series.loc[common_idx][-1]
        s_val = startup_series.loc[common_idx][-1] if startup_series is not None else 0
        n_val = nifty_series.loc[common_idx][-1]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Green Index", f"{g_val:.2f}", f"{g_val-100:.2f}%")
        col2.metric("NIFTY 50", f"{n_val:.2f}", f"{n_val-100:.2f}%")
        col3.metric("Startup Index", f"{s_val:.2f}", f"{s_val-100:.2f}%")

        # --- MAIN CHART ---
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 1. Green Index (Green)
        ax.plot(green_series.index, green_series, 
                label='Green Energy', color='#2ca02c', linewidth=2.5)
        
        # 2. Startup Index (Purple)
        if startup_series is not None:
            ax.plot(startup_series.index, startup_series, 
                    label='Startups', color='#9467bd', linewidth=2.5)
        
        # 3. Benchmark (Grey Dashed)
        ax.plot(nifty_series.index, nifty_series, 
                label='NIFTY 50', color='#7f7f7f', linestyle='--', linewidth=1.5)
        
        # Styling
        ax.axhline(y=100, color='black', linewidth=0.5, alpha=0.5)
        ax.set_title("Sector Performance Comparison", fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        fig.autofmt_xdate()
        
        st.pyplot(fig)
        
        st.caption("Note: 'Startup Index' includes only publicly listed entities from the provided list (Ola, Shadowfax, Amagi, DevX, etc). Private unicorns (Meesho, Groww) are excluded.")

else:
    st.info("👈 Click 'Generate Dashboard' to visualize the market data.")