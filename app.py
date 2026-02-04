import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


tickers = [
    "ACMESOLAR.NS", "ADANIGREEN.NS", "ALPEXSOLAR.NS", "BORORENEW.NS", 
    "EMMVEE.NS", "INOXWIND.NS", "KPIGREEN.NS", "NTPCGREEN.NS", 
    "OSWALPUMPS.NS", "PACEDIGITK.NS", "PREMIERENE.NS", "SHAKTIPUMP.NS", 
    "SOLEX.NS", "SWSOLAR.NS", "SUZLON.NS", "TATAPOWER.NS", 
    "VIKRAMSOLR.NS", "WAAREEENER.NS", "WAAREERTL.NS"
]
start_date = "2026-01-01"

print("--- Step 1: Downloading Historical Prices (Safe Mode) ---")
raw_data = yf.download(tickers, start=start_date, threads=False, auto_adjust=False)

if raw_data.empty:
    print("CRITICAL: No data downloaded.")
    exit()

# Safely extract 'Adj Close' or 'Close'
if 'Adj Close' in raw_data.columns.levels[0]:
    prices = raw_data['Adj Close']
elif 'Close' in raw_data.columns.levels[0]:
    prices = raw_data['Close']
else:
    prices = raw_data.iloc[:, :len(tickers)]

# Clean Data
prices = prices.dropna(axis=1, how='all').ffill()
print(f"Loaded prices for {len(prices.columns)} companies.")

print("\n--- Step 2: Fetching Shares Outstanding ---")
shares_data = {}
for ticker in prices.columns:
    try:
        stock = yf.Ticker(ticker)
        shares = stock.info.get('sharesOutstanding')
        if shares is None:
            shares_data[ticker] = np.nan
        else:
            shares_data[ticker] = shares
            # Print minimal info to keep terminal clean
            # print(f"  [ok] {ticker}") 
    except Exception:
        shares_data[ticker] = np.nan

# Impute Missing Shares
shares_series = pd.Series(shares_data)
shares_series.fillna(shares_series.median(), inplace=True)

print("\n--- Step 3: Calculating Market Cap Weighted Index ---")
market_caps = prices.mul(shares_series, axis=1)
total_market_cap = market_caps.sum(axis=1)

# Normalize to 100
base_value = total_market_cap.iloc[0]
green_index_mcap = (total_market_cap / base_value) * 100
print(f"Current Index Value: {green_index_mcap.iloc[-1]:.2f}")

print("\n--- Step 4: Generating Chart ---")
plt.figure(figsize=(12, 6))

# Plot the Index
plt.plot(green_index_mcap.index, green_index_mcap, label='Green Index (Market Cap Wtd)', color='#2ca02c', linewidth=2.5)

# Add Reference Line (100)
plt.axhline(y=100, color='red', linestyle='--', alpha=0.5, label='Base (Jan 1 = 100)')

# Styling
plt.title(f'India Green Energy Index (YTD 2026)', fontsize=16, fontweight='bold')
plt.ylabel('Index Value', fontsize=12)
plt.xlabel('Date', fontsize=12)
plt.grid(True, alpha=0.3)
plt.legend(loc='lower left')

# Format Dates nicely
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
plt.gcf().autofmt_xdate()

# Save and Show
filename = "green_index_chart.png"
plt.savefig(filename, dpi=300)
print(f"Chart saved as {filename}")
plt.show()