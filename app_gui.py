import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# --- CONFIGURATION ---
GREEN_TICKERS = [
    "ACMESOLAR.NS", "ADANIGREEN.NS", "ALPEXSOLAR.NS", "BORORENEW.NS", 
    "EMMVEE.NS", "INOXWIND.NS", "KPIGREEN.NS", "NTPCGREEN.NS", 
    "OSWALPUMPS.NS", "PACEDIGITK.NS", "PREMIERENE.NS", "SHAKTIPUMP.NS", 
    "SOLEX.NS", "SWSOLAR.NS", "SUZLON.NS", "TATAPOWER.NS", 
    "VIKRAMSOLR.NS", "WAAREEENER.NS", "WAAREERTL.NS", "SAATVIKGL.NS", 
    "JSWENERGY.NS", "SOLARWORLD.NS",  "GKENERGY.NS", "OLECTRA.NS", 
    "WEBSOLAR.NS", "ADVAIT.NS"
]

STARTUP_TICKERS = [
    "OLAELEC.NS", "SHADOWFAX.NS", "AMAGI.NS", "DEVX.NS", 
    "SMARTWORKS.NS", "ARISINFRA.NS", "ZAPPFRESH.BO", "MEESHO.NS",
     "GROWW.BO", "LENSKART.NS", "PINELABS.NS", "URBANCO.NS",
     "WEWORK.NS",  "INDIQUBE.NS"   
]

BENCHMARK_TICKER = "^NSEI"

# --- APP SETUP ---
st.set_page_config(page_title="Market Analyzer Pro", layout="wide")
st.title("Market Analyzer Pro: Fundamentals & Technicals")

# --- BACKEND LOGIC ---
@st.cache_data
def fetch_fundamental_data(tickers):
    """Fetches Shares, P/E, and EPS in one go and caches it."""
    data = {}
    progress_bar = st.progress(0)
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
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
        progress_bar.progress((i + 1) / total)
            
    progress_bar.empty()
    df = pd.DataFrame.from_dict(data, orient='index')
    df['shares'] = df['shares'].fillna(df['shares'].median())
    return df

def calculate_weighted_index(tickers, start_date, end_date, shares_series):
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    raw_data = yf.download(tickers, start=start_str, end=end_str, threads=False, auto_adjust=False)
    
    if raw_data.empty: return None, None

    if 'Adj Close' in raw_data.columns.levels[0]:
        prices = raw_data['Adj Close']
    elif 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        prices = raw_data.iloc[:, :len(tickers)]
    
    prices = prices.dropna(axis=1, how='all').ffill().bfill()
    if prices.empty: return None, None

    common_cols = prices.columns.intersection(shares_series.index)
    market_caps = prices[common_cols].mul(shares_series[common_cols], axis=1)
    total_market_cap = market_caps.sum(axis=1)
    
    if total_market_cap.empty: return None, None
        
    base_value = total_market_cap.iloc[0]
    index_series = (total_market_cap / base_value) * 100
    
    return index_series, prices

@st.cache_data
def get_dashboard_data(start_date, end_date, _green_meta, _startup_meta):
    green_shares = _green_meta['shares']
    startup_shares = _startup_meta['shares']
    
    green_idx, green_prices = calculate_weighted_index(GREEN_TICKERS, start_date, end_date, green_shares)
    startup_idx, startup_prices = calculate_weighted_index(STARTUP_TICKERS, start_date, end_date, startup_shares)
    
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    nifty_data = yf.download(BENCHMARK_TICKER, start=start_date, end=end_str, threads=False, auto_adjust=False)
    
    if not nifty_data.empty:
        try:
            bench_prices = nifty_data['Adj Close'][BENCHMARK_TICKER]
        except KeyError:
            bench_prices = nifty_data['Adj Close'] if 'Adj Close' in nifty_data else nifty_data['Close']
        bench_prices = bench_prices.ffill().bfill()
        nifty_idx = (bench_prices / bench_prices.iloc[0]) * 100
    else:
        nifty_idx = None
        
    return green_idx, green_prices, startup_idx, startup_prices, nifty_idx

def generate_transparency_table(prices_df, metadata_df):
    valid_tickers = prices_df.columns.intersection(metadata_df.index)
    aligned_prices = prices_df[valid_tickers]
    aligned_meta = metadata_df.loc[valid_tickers]
    latest_prices = aligned_prices.iloc[-1]
    
    market_caps_raw = latest_prices * aligned_meta['shares']
    total_cap = market_caps_raw.sum()
    
    weights = (market_caps_raw / total_cap) * 100 if total_cap != 0 else pd.Series(0, index=valid_tickers)
    
    if len(aligned_prices) >= 6:
        week_ago_prices = aligned_prices.iloc[-6]
        weekly_returns = ((latest_prices - week_ago_prices) / week_ago_prices) * 100
    else:
        start_prices = aligned_prices.iloc[0]
        weekly_returns = np.where(start_prices == 0, 0, ((latest_prices - start_prices) / start_prices) * 100)

    display_df = pd.DataFrame({
        "Ticker": valid_tickers,
        "Price (INR)": latest_prices.values,
        "Weight (%)": weights.values,
        "Weekly Return (%)": weekly_returns,
        "Mkt Cap (Cr)": (market_caps_raw / 10000000).values, 
        "P/E Ratio": aligned_meta['pe'].values,
        "EPS (INR)": aligned_meta['eps'].values
    })
    
    display_df = display_df.set_index("Ticker")
    display_df = display_df.sort_values(by="Weight (%)", ascending=False)
    return display_df

# --- NEW: RISK CALCULATOR ---
def calculate_risk_metrics(series, name):
    if series is None or len(series) < 2:
        return {"Name": name, "Volatility": np.nan, "Max Drawdown": np.nan}
    
    # Daily Returns
    daily_ret = series.pct_change().dropna()
    
    # 1. Annualized Volatility (Standard Deviation * sqrt(252 trading days))
    volatility = daily_ret.std() * np.sqrt(252) * 100
    
    # 2. Max Drawdown (Peak to Trough)
    cumulative = (1 + daily_ret).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min() * 100
    
    return {
        "Name": name, 
        "Volatility (Ann.)": f"{volatility:.2f}%", 
        "Max Drawdown": f"{max_drawdown:.2f}%"
    }

# --- SIDEBAR ---
st.sidebar.header("Configuration")
start_date = st.sidebar.date_input("Start Date", value=datetime(2026, 1, 1))
end_date = st.sidebar.date_input("End Date", value=datetime.today())

if start_date > end_date:
    st.sidebar.error("Error: Start Date must be before End Date.")
else:
    if st.sidebar.button("Generate Dashboard"):
        if 'green_meta' not in st.session_state:
            with st.spinner("Fetching Fundamentals..."):
                st.session_state['green_meta'] = fetch_fundamental_data(GREEN_TICKERS)
        if 'startup_meta' not in st.session_state:
            with st.spinner("Fetching Fundamentals..."):
                st.session_state['startup_meta'] = fetch_fundamental_data(STARTUP_TICKERS)
        
        with st.spinner(f"Crunching numbers..."):
            g_series, g_prices, s_series, s_prices, n_series = get_dashboard_data(
                start_date, end_date, st.session_state['green_meta'], st.session_state['startup_meta']
            )
        
        if g_series is None:
            st.error("No data found.")
        else:
            # --- 1. EXPORT BUTTON (Sidebar) ---
            # Create a combined CSV for download
            export_df = pd.DataFrame({"Green Index": g_series, "NIFTY 50": n_series})
            if s_series is not None: export_df["Startup Index"] = s_series
            
            csv = export_df.to_csv().encode('utf-8')
            st.sidebar.download_button(
                label="📥 Download Index Data (CSV)",
                data=csv,
                file_name=f"market_data_{start_date}_{end_date}.csv",
                mime='text/csv',
            )

            # --- 2. TOP METRICS ---
            st.subheader(f"Performance Overview ({start_date} to {end_date})")
            g_final = g_series.iloc[-1]
            n_final = n_series.iloc[-1] if n_series is not None else 100
            s_final = s_series.iloc[-1] if s_series is not None else 100

            col1, col2, col3 = st.columns(3)
            col1.metric("Green Index", f"{g_final:.2f}", f"{(g_final-100):.2f}%")
            col2.metric("NIFTY 50", f"{n_final:.2f}", f"{(n_final-100):.2f}%")
            if s_series is not None:
                col3.metric("Startup Index", f"{s_final:.2f}", f"{(s_final-100):.2f}%")

            # --- 3. CHART ---
            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(g_series.index, g_series, label='Green Energy', color='#2ca02c', linewidth=2.5)
            if s_series is not None:
                ax.plot(s_series.index, s_series, label='Startups', color='#9467bd', linewidth=2.5)
            if n_series is not None:
                ax.plot(n_series.index, n_series, label='NIFTY 50', color='#7f7f7f', linestyle='--', linewidth=1)
            ax.axhline(y=100, color='black', alpha=0.3)
            ax.legend()
            ax.grid(True, alpha=0.2)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            st.pyplot(fig)

            with st.expander("How is this Score Calculated?"):
                st.markdown("We use a **Market-Cap Weighted** formula, normalized to 100 on the start date.")
            
            st.divider()

            # --- 4. RISK METRICS SECTION ---
            st.subheader("⚠️ Risk Analysis")
            st.caption("Volatility measures how wild the price swings are. Max Drawdown measures the worst possible loss from a peak.")
            
            risk_data = [
                calculate_risk_metrics(g_series, "Green Energy"),
                calculate_risk_metrics(n_series, "NIFTY 50"),
                calculate_risk_metrics(s_series, "Startups")
            ]
            risk_df = pd.DataFrame(risk_data).set_index("Name")
            st.table(risk_df)

            st.divider()

            # --- 5. TRANSPARENCY SECTION ---
            st.subheader("Index Transparency & Fundamentals")
            tab1, tab2 = st.tabs(["Green Energy", "Startups"])
            
            column_config = {
                "Price (INR)": st.column_config.NumberColumn(format="INR %.2f"),
                "Weight (%)": st.column_config.ProgressColumn("Impact", format="%.1f%%", min_value=0, max_value=100),
                "Weekly Return (%)": st.column_config.NumberColumn("Weekly Trend", format="%.2f%%"),
                "Mkt Cap (Cr)": st.column_config.NumberColumn("Market Cap (Cr)", format="INR %d Cr"),
                "P/E Ratio": st.column_config.NumberColumn("P/E Ratio", format="%.1f"),
                "EPS (INR)": st.column_config.NumberColumn("EPS", format="INR %.2f")
            }

            with tab1:
                g_table = generate_transparency_table(g_prices, st.session_state['green_meta'])
                st.dataframe(g_table, column_config=column_config, use_container_width=True)

            with tab2:
                if s_prices is not None:
                    s_table = generate_transparency_table(s_prices, st.session_state['startup_meta'])
                    st.dataframe(s_table, column_config=column_config, use_container_width=True)
                else:
                    st.warning("Insufficient data.")
    else:
        st.info("Select dates and click 'Generate Dashboard'.")