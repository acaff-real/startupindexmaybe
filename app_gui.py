import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta


GREEN_TICKERS = [
    "ACMESOLAR.NS", "ADANIGREEN.NS", "ALPEXSOLAR.NS", "BORORENEW.NS", 
    "EMMVEE.NS", "INOXWIND.NS", "KPIGREEN.NS", "NTPCGREEN.NS", 
    "OSWALPUMPS.NS", "PACEDIGITK.NS", "PREMIERENE.NS", "SHAKTIPUMP.NS", 
    "SOLEX.NS", "SWSOLAR.NS", "SUZLON.NS", "TATAPOWER.NS", 
    "VIKRAMSOLR.NS", "WAAREEENER.NS", "WAAREERTL.NS", "SAATVIKGL.NS", 
    "JSWENERGY.NS", "SOLARWORLD.NS",  "GKENERGY.NS", "OLECTRA.NS", 
    "WEBELSOLAR.NS", "ADVAIT.NS"
]

STARTUP_TICKERS = [
    "OLAELEC.NS", "SHADOWFAX.NS", "AMAGI.NS", "DEVX.NS", 
    "SMARTWORKS.NS", "ARISINFRA.NS", "ZAPPFRESH.BO", "MEESHO.NS",
     "GROWW.BO", "LENSKART.NS", "PINELABS.NS", "URBANCO.NS",
     "WEWORK.NS",  "INDIQUBE.NS", "DELHIVERY.NS", "IDEAFORGE.NS",
    "POLICYBZR.NS", "PWL.BO", "SWIGGY.NS", "IXIGO.NS", 
    "FIRSTCRY.NS", "TBOTEK.NS", "NETWEB.NS", "MOBIKWIK.NS",
    "BLACKBUCK.NS", "JARO.NS", "CAPILLARY.NS", "RATEGAIN.NS",
    "YATRA.NS", "BLUESTONE.NS", "WAKEFIT.NS"
]


BENCHMARK_TICKER = "^NSEI"


st.set_page_config(page_title="Market Analyzer Pro", layout="wide")
st.title("Market Analyzer Pro: Equity Terminal")


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
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    raw_data = yf.download(tickers, start=start_str, end=end_str, threads=False, auto_adjust=False)
    
    if raw_data.empty: return None

    if 'Adj Close' in raw_data.columns.levels[0]:
        prices = raw_data['Adj Close']
    elif 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        prices = raw_data.iloc[:, :len(tickers)]
    
    prices = prices.dropna(axis=1, how='all').ffill().bfill()
    if prices.empty: return None

    common_cols = prices.columns.intersection(shares_series.index)
    market_caps = prices[common_cols].mul(shares_series[common_cols], axis=1)
    total_market_cap = market_caps.sum(axis=1)
    
    if total_market_cap.empty: return None
        
    base_value = total_market_cap.iloc[0]
    index_series = (total_market_cap / base_value) * 100
    
    return index_series

@st.cache_data
def fetch_rich_stats(tickers, end_date):
    """
    Downloads ~1 year of data to calculate 52W High/Low and 30D Change.
    Returns a DataFrame with the latest Snapshot of all metrics.
    """
    
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
            
            if df.empty:
                continue
                
            
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
    """Combines the Rich Market Data with Fundamental Data (Shares, PE)."""
    
    
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
        
        
        with st.spinner(f"Calculating Indices..."):
            g_series = calculate_weighted_index(GREEN_TICKERS, start_date, end_date, st.session_state['green_meta']['shares'])
            s_series = calculate_weighted_index(STARTUP_TICKERS, start_date, end_date, st.session_state['startup_meta']['shares'])
            
            
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
            st.error("No data found.")
        else:
            
            with st.spinner("Fetching Detailed Quote Stats (52W High/Low, Vol, etc.)..."):
                g_rich_stats = fetch_rich_stats(GREEN_TICKERS, end_date)
                s_rich_stats = fetch_rich_stats(STARTUP_TICKERS, end_date)

            
            
            
            g_final = g_series.iloc[-1]
            n_final = n_series.iloc[-1] if n_series is not None else 100
            s_final = s_series.iloc[-1] if s_series is not None else 100

            col1, col2, col3 = st.columns(3)
            col1.metric("Green Index", f"{g_final:.2f}", f"{(g_final-100):.2f}%")
            col2.metric("NIFTY 50", f"{n_final:.2f}", f"{(n_final-100):.2f}%")
            if s_series is not None:
                col3.metric("Startup Index", f"{s_final:.2f}", f"{(s_final-100):.2f}%")

            
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
            
            
            st.caption("Risk Metrics:")
            risk_data = [calculate_risk_metrics(g_series, "Green Energy"), calculate_risk_metrics(n_series, "NIFTY 50")]
            if s_series is not None: risk_data.append(calculate_risk_metrics(s_series, "Startups"))
            st.table(pd.DataFrame(risk_data).set_index("Name"))

            st.divider()

            
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
                if not g_rich_stats.empty:
                    g_table = generate_full_report(g_rich_stats, st.session_state['green_meta'])
                    
                    cols = ["Open", "High", "Low", "LTP", "Chng", "%Chng", "Volume", "Value (Cr)", "52W H", "52W L", "30D %Chng", "Weight (%)", "Mkt Cap (Cr)", "P/E"]
                    
                    cols = [c for c in cols if c in g_table.columns]
                    st.dataframe(g_table[cols], column_config=col_config, use_container_width=True)

            with tab2:
                if not s_rich_stats.empty:
                    s_table = generate_full_report(s_rich_stats, st.session_state['startup_meta'])
                    cols = ["Open", "High", "Low", "LTP", "Chng", "%Chng", "Volume", "Value (Cr)", "52W H", "52W L", "30D %Chng", "Weight (%)", "Mkt Cap (Cr)"]
                    cols = [c for c in cols if c in s_table.columns]
                    st.dataframe(s_table[cols], column_config=col_config, use_container_width=True)
                else:
                    st.warning("No data available for Startups.")
    else:
        st.info("Select dates and click 'Generate Dashboard'.")