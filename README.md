# Startup Equity Terminal (SVF Index)

A real-time dashboard tracking the performance of India's new-age technology stocks. Built with **Flask (Python)** and **Vanilla JS**.

## 🛠️ Prerequisites

* **Python 3.8+** installed.
* 

### 1. Clone the Repository
```bash
git clone https://github.com/acaff-real/startupindexmaybe
cd startupindexmaybe
```
### 2. Set up Python Environment (Recommended)

It is best practice to use a virtual environment to keep dependencies isolated.

# Windows
```
python -m venv venv
venv\Scripts\activate
```
# Mac/Linux
```
python3 -m venv venv
source venv/bin/activate
```
### 3. Install Backend Dependencies

This installs Flask, Pandas, yfinance, and the Gunicorn server.

```
pip install -r requirements.txt
```

### 4. Frontend Dependencies
This project currently uses CDNs for libraries like Chart.js.
No npm install is required for this version. The frontend is ready to go out of the box.
Access the terminal at: http://127.0.0.1:5000

If deploying to Render, Heroku, or a VPS, Ensure the Procfile is present in the root directory. If the app says "Delisted" or data is missing, the API might be rate-limiting you. Restarting the server usually fixes this.
