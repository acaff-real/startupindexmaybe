import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import plotly.express as px

# --- CONSTANTS (Full Universe) ---
GREEN_TICKERS_FULL = [
    "ACMESOLAR.NS", "ADANIGREEN.NS", "ALPEXSOLAR.NS", "BORORENEW.NS", 
    "EMMVEE.NS", "INOXWIND.NS", "KPIGREEN.NS", "NTPCGREEN.NS", 
    "OSWALPUMPS.NS", "PACEDIGITK.NS", "PREMIERENE.NS", "SHAKTIPUMP.NS", 
    "SOLEX.NS", "SWSOLAR.NS", "SUZLON.NS", "TATAPOWER.NS", 
    "VIKRAMSOLR.NS", "WAAREEENER.NS", "WAAREERTL.NS", "SAATVIKGL.NS", 
    "JSWENERGY.NS", "SOLARWORLD.NS",  "GKENERGY.NS", "OLECTRA.NS", 
    "WEBELSOLAR.NS", "ADVAIT.NS"
]

STARTUP_TICKERS_FULL = [
    "PWL.BO", "PINELABS.NS", "YATRA.NS", "IDEAFORGE.NS", "SHADOWFAX.NS",
    "AMAGI.NS", "GROWW.BO", "LENSKART.NS", "URBANCO.NS", "MEESHO.NS",
    "OLAELEC.NS", "SWIGGY.NS", "FIRSTCRY.NS", "GODIGIT.NS", "HONASA.NS",
    "INDGN.NS", "TBOTEK.NS", "IXIGO.NS", "AWFIS.NS", "ZAGGLE.NS", 
    "ENTERO.NS", "MEDIASSIST.NS", "BLUESTONE.NS", "WEWORK.NS", "BLACKBUCK.NS"
]

BENCHMARK_TICKER = "^NSEI"

st.set_page_config(page_title="Market Analyzer Pro", layout="wide")
st.title("Market Analyzer Pro: Equity Terminal")

# --- HELPER FUNCTIONS ---
def plot_weight_distribution(rich_stats_df, title):
    if rich_stats_df.empty: return None
    
    df = rich_stats_df.sort_values(by="Weight (%)", ascending=False)
    
    top_10 = df.head(10).copy()
    others_weight = df.iloc[10:]['Weight (%)'].sum()
    
    if others_weight > 0:
        new_row = pd.DataFrame({"Weight (%)": [others_weight]}, index=["Others"])
        top_10 = pd.concat([top_10, new_row])
    
    top_10 = top_10.reset_index().rename(columns={"index": "Ticker"})
    
    fig = px.pie(
        top_10, 
        values='Weight (%)', 
        names='Ticker', 
        title=title,
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

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

@st.cache_data
def calculate_weighted_index(tickers, start_date, end_date, shares_series):
    if not tickers: return None
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    raw_data = yf.download(tickers, start=start_str, end=end_str, threads=False, auto_adjust=False)
    
    if raw_data.empty: return None

    # Handle single ticker vs multiple tickers return structure
    if len(tickers) == 1:
        ticker = tickers[0]
        # Try to find the correct column
        if 'Adj Close' in raw_data.columns:
            prices = raw_data[['Adj Close']].rename(columns={'Adj Close': ticker})
        elif 'Close' in raw_data.columns:
            prices = raw_data[['Close']].rename(columns={'Close': ticker})
        else:
            return None
    else:
        if 'Adj Close' in raw_data.columns.levels[0]:
            prices = raw_data['Adj Close']
        elif 'Close' in raw_data.columns.levels[0]:
            prices = raw_data['Close']
        else:
            prices = raw_data.iloc[:, :len(tickers)]
    
    prices = prices.dropna(axis=1, how='all').ffill().bfill()
    if prices.empty: return None

    # Filter shares series to match current selection
    # Use intersection to be safe against tickers that failed download
    common = prices.columns.intersection(shares_series.index)
    prices = prices[common]
    current_shares = shares_series[common]
    
    market_caps = prices.mul(current_shares, axis=1)
    total_market_cap = market_caps.sum(axis=1)
    
    if total_market_cap.empty: return None
        
    base_value = total_market_cap.iloc[0]
    if base_value == 0: return None
    
    index_series = (total_market_cap / base_value) * 100
    return index_series

@st.cache_data
def fetch_rich_stats(tickers, end_date):
    if not tickers: return pd.DataFrame()
    
    start_lookback = end_date - timedelta(days=370)
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    data = yf.download(tickers, start=start_lookback, end=end_str, group_by='ticker', threads=False, auto_adjust=False)
    
    stats = []
    
    for ticker in tickers:
        try:
            if len(tickers) > 1:
                df = data[ticker].copy()
            else:
                df = data.copy() 
            
            df = df.dropna(how='all')
            if df.empty: continue
                
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            ltp = latest['Close'] if 'Close' in latest else latest['Adj Close']
            prev_close = prev['Close'] if 'Close' in prev else prev['Adj Close']
            change = ltp - prev_close
            pct_change = (change / prev_close) * 100
            
            last_year = df.tail(252)
            high_52 = last_year['High'].max()
            low_52 = last_year['Low'].min()
            
            if len(df) > 21:
                price_30d_ago = df.iloc[-21]['Close']
                chng_30d = ((ltp - price_30d_ago) / price_30d_ago) * 100
            else:
                chng_30d = np.nan

            vol = latest['Volume']
            val_cr = (ltp * vol) / 10000000 

            stats.append({
                "Ticker": ticker,
                "Open": latest['Open'],
                "High": latest['High'],
                "Low": latest['Low'],
                "LTP": ltp,
                "Chng": change,
                "%Chng": pct_change,
                "Volume": vol,
                "Value (Cr)": val_cr,
                "52W H": high_52,
                "52W L": low_52,
                "30D %Chng": chng_30d
            })
        except Exception:
            pass 
            
    return pd.DataFrame(stats).set_index("Ticker")

def generate_full_report(rich_stats_df, metadata_df):
    valid_tickers = rich_stats_df.index.intersection(metadata_df.index)
    stats = rich_stats_df.loc[valid_tickers]
    meta = metadata_df.loc[valid_tickers]
    
    mkt_cap = stats['LTP'] * meta['shares']
    total_mkt_cap = mkt_cap.sum()
    
    weights = (mkt_cap / total_mkt_cap) * 100 if total_mkt_cap != 0 else 0
    
    final_df = stats.copy()
    final_df['Weight (%)'] = weights
    final_df['Mkt Cap (Cr)'] = mkt_cap / 10000000
    final_df['P/E'] = meta['pe']
    final_df['EPS'] = meta['eps']
    
    return final_df

def calculate_risk_metrics(series, name):
    if series is None or len(series) < 2:
        return {"Name": name, "Volatility": np.nan, "Max Drawdown": np.nan}
    daily_ret = series.pct_change().dropna()
    volatility = daily_ret.std() * np.sqrt(252) * 100
    cumulative = (1 + daily_ret).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min() * 100
    return {"Name": name, "Volatility (Ann.)": f"{volatility:.2f}%", "Max Drawdown": f"{max_drawdown:.2f}%"}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Configuration")
start_date = st.sidebar.date_input("Start Date", value=datetime(2026, 1, 1))
end_date = st.sidebar.date_input("End Date", value=datetime.today())

st.sidebar.divider()
st.sidebar.subheader("🎛️ Index Filters")

# --- NEW: CHECKBOX LOGIC ---
selected_green = []
with st.sidebar.expander(" Green Energy Constituents", expanded=False):
    st.caption("Uncheck to exclude from index:")
    for ticker in GREEN_TICKERS_FULL:
        # Default=True means everything is selected at start
        if st.checkbox(ticker, value=True, key=f"g_{ticker}"):
            selected_green.append(ticker)

selected_startup = []
with st.sidebar.expander(" Startup Constituents", expanded=False):
    st.caption("Uncheck to exclude from index:")
    for ticker in STARTUP_TICKERS_FULL:
        if st.checkbox(ticker, value=True, key=f"s_{ticker}"):
            selected_startup.append(ticker)

if start_date > end_date:
    st.sidebar.error("Error: Start Date must be before End Date.")
else:
    if st.sidebar.button("Generate Dashboard"):
        # 1. Fetch Fundamentals (Use Full List to populate cache initially)
        if 'green_meta' not in st.session_state:
            with st.spinner("Fetching Fundamentals..."):
                st.session_state['green_meta'] = fetch_fundamental_data(GREEN_TICKERS_FULL)
        if 'startup_meta' not in st.session_state:
            with st.spinner("Fetching Fundamentals..."):
                st.session_state['startup_meta'] = fetch_fundamental_data(STARTUP_TICKERS_FULL)
        
        # 2. Calculate Indices (Using SELECTED Tickers)
        with st.spinner(f"Calculating Indices..."):
            g_series = calculate_weighted_index(selected_green, start_date, end_date, st.session_state['green_meta']['shares'])
            s_series = calculate_weighted_index(selected_startup, start_date, end_date, st.session_state['startup_meta']['shares'])
            
            end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
            nifty_data = yf.download(BENCHMARK_TICKER, start=start_date, end=end_str, threads=False, auto_adjust=False)
            if not nifty_data.empty:
                try:
                    bench = nifty_data['Adj Close'][BENCHMARK_TICKER]
                except:
                    bench = nifty_data['Adj Close']
                bench = bench.ffill().bfill()
                n_series = (bench / bench.iloc[0]) * 100
            else:
                n_series = None

        if g_series is None:
            st.error("No data found. Please select at least one ticker.")
        else:
            # 3. Fetch Rich Stats (For SELECTED Tickers)
            with st.spinner("Fetching Detailed Quote Stats..."):
                g_rich_stats = fetch_rich_stats(selected_green, end_date)
                s_rich_stats = fetch_rich_stats(selected_startup, end_date)

            # Generate Tables
            g_table = pd.DataFrame()
            s_table = pd.DataFrame()

            if not g_rich_stats.empty:
                g_table = generate_full_report(g_rich_stats, st.session_state['green_meta'])
            
            if not s_rich_stats.empty:
                s_table = generate_full_report(s_rich_stats, st.session_state['startup_meta'])

            # --- METRICS ---
            g_final = g_series.iloc[-1]
            n_final = n_series.iloc[-1] if n_series is not None else 100
            s_final = s_series.iloc[-1] if s_series is not None else 100

            col1, col2, col3 = st.columns(3)
            col1.metric("Green Index", f"{g_final:.2f}", f"{(g_final-100):.2f}%")
            col2.metric("NIFTY 50", f"{n_final:.2f}", f"{(n_final-100):.2f}%")
            if s_series is not None:
                col3.metric("Startup Index", f"{s_final:.2f}", f"{(s_final-100):.2f}%")

            # --- CHART ---
            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(g_series.index, g_series, label='Green Energy', color='#2ca02c', linewidth=2.5)
            if s_series is not None:
                ax.plot(s_series.index, s_series, label='Startups', color='#9467bd', linewidth=2.5)
            if n_series is not None:
                ax.plot(n_series.index, n_series, label='NIFTY 50', color='#7f7f7f', linestyle='--', linewidth=1)
            ax.axhline(y=100, color='black', alpha=0.3)
            ax.legend()
            ax.grid(True, alpha=0.2)
            st.pyplot(fig)
            
            st.divider()

            # --- CONCENTRATION ---
            st.subheader("⚖️ Index Composition & Concentration")
            col_A, col_B = st.columns(2)

            with col_A:
                if not g_table.empty:
                    fig_g = plot_weight_distribution(g_table, "Green Index Weights")
                    if fig_g: st.plotly_chart(fig_g, use_container_width=True)

            with col_B:
                if not s_table.empty:
                    fig_s = plot_weight_distribution(s_table, "Startup Index Weights")
                    if fig_s: st.plotly_chart(fig_s, use_container_width=True)
            
            # --- RISK METRICS ---
            st.caption("Risk Metrics:")
            risk_data = [calculate_risk_metrics(g_series, "Green Energy"), calculate_risk_metrics(n_series, "NIFTY 50")]
            if s_series is not None: risk_data.append(calculate_risk_metrics(s_series, "Startups"))
            st.table(pd.DataFrame(risk_data).set_index("Name"))

            st.divider()

            # --- TABLES ---
            st.subheader("📊 Comprehensive Market Data")
            tab1, tab2 = st.tabs(["Green Energy", "Startups"])

            col_config = {
                "LTP": st.column_config.NumberColumn("LTP", format="%.2f"),
                "Chng": st.column_config.NumberColumn("Chng", format="%.2f"),
                "%Chng": st.column_config.NumberColumn("%Chng", format="%.2f%%"),
                "Volume": st.column_config.NumberColumn("Volume", format="%d"),
                "Value (Cr)": st.column_config.NumberColumn("Value (Cr)", format="%.2f"),
                "Weight (%)": st.column_config.ProgressColumn("Weight", format="%.1f%%", min_value=0, max_value=100),
                "52W H": st.column_config.NumberColumn("52W High", format="%.2f"),
                "52W L": st.column_config.NumberColumn("52W Low", format="%.2f"),
                "30D %Chng": st.column_config.NumberColumn("30D %", format="%.2f%%"),
                "Mkt Cap (Cr)": st.column_config.NumberColumn("Mkt Cap (Cr)", format="%.0f"),
            }

            with tab1:
                if not g_table.empty:
                    cols = ["Open", "High", "Low", "LTP", "Chng", "%Chng", "Volume", "Value (Cr)", "52W H", "52W L", "30D %Chng", "Weight (%)", "Mkt Cap (Cr)", "P/E"]
                    cols = [c for c in cols if c in g_table.columns]
                    st.dataframe(g_table[cols], column_config=col_config, use_container_width=True)

            with tab2:
                if not s_table.empty:
                    cols = ["Open", "High", "Low", "LTP", "Chng", "%Chng", "Volume", "Value (Cr)", "52W H", "52W L", "30D %Chng", "Weight (%)", "Mkt Cap (Cr)"]
                    cols = [c for c in cols if c in s_table.columns]
                    st.dataframe(s_table[cols], column_config=col_config, use_container_width=True)
                else:
                    st.warning("No data available for Startups.")
    else:
        st.info("Select dates and click 'Generate Dashboard'.")