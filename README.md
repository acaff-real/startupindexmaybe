
A professional financial dashboard tracking the performance of India's Green Energy sector and emerging startups against the broad market (NIFTY 50).

## Overview

This tool was built to analyze sector-specific trends that general market indices often miss. It generates custom, dynamic indices in real-time using live market data.

**Key Features:**
* **Green Energy Index:** Tracks ~19 key players (Adani Green, Tata Power, Suzlon, etc.).
* **Startup Index:** Tracks publicly listed tech companies (Ola Electric, Zappfresh, MapMyIndia, etc.).
* **Market Benchmark:** Real-time comparison against the NIFTY 50 to calculate Alpha (outperformance).
* **Professional Weighting:** Uses **Market-Cap Weighting** (not simple averages) to accurately reflect sector movement.

---

##  Installation Guide

### Prerequisites
* Python 3.8 or higher
* Internet connection (for live data fetching)

### Step 1: Set up the Project
Unzip the project folder and open your terminal (Command Prompt or PowerShell) inside this folder.

### Step 2: Install Dependencies
Run the following command to install the required financial libraries:

pip install -r requirements.txt

### How to Run

To launch the dashboard, run this command in your terminal:
```
streamlit run app.py
```
Unlike basic price trackers, this tool constructs Market-Cap Weighted Indices.

The Formula:

    Index Value = (Current Total Market Cap / Base Total Market Cap) × 100

Why this matters:

    A 5% move in a giant like Tata Power affects the index more than a 5% move in a smaller player like Solex Energy.

    This matches the methodology used by professional indices like S&P 500 and NIFTY 50.

    Data Source: Live data is fetched via the Yahoo Finance API (yfinance).

    Rebalancing: The index dynamically handles missing data for recently listed IPOs (e.g., automatically backfilling pre-IPO prices to prevent index crashes).

## Troubleshooting

###Issue: "OperationalError: database is locked"

    Cause: The data downloader was interrupted during a previous run.

    Fix: Close the terminal. Delete the hidden yfinance cache folder on your computer, or simply restart your computer and run the script again.

###Issue: "No Data Found"

    Cause: Markets might be closed, or the start date is set to a holiday/weekend.

    Fix: Try moving the "Start Date" slider back by 1-2 days.

This tool is for informational and analytical purposes only. It does not constitute financial advice.
