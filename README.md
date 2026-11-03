# Upper Horton Sports Club - Square Sales Reporting Engine

A self-hosted, operational sales reporting dashboard for the **Upper Horton Sports Club**, powered by the Square API, DuckDB, and Streamlit. Built for homelab deployment with zero-maintenance embedded OLAP storage.

---

## Features

- **Executive KPI Overview:** Daily/Weekly Gross Sales, Net Sales, Order Count, Average Order Value (AOV), and Member Discounts.
- **Revenue by Department & Category:** Visual breakdown and contribution tables across Bar (Beer & Cider, Spirits, Wine, Non-Alcoholic), Canteen & Bistro, Events & Gate, and Club Merchandise.
- **End-of-Day (EOD) Reconciliation:** Settlement summaries for Card/EFTPOS vs. Cash, Square processing fees, tips, and refunds.
- **Trading Velocity Heatmap:** Hour-of-day vs. Day-of-week sales heatmap to assist with bar volunteer and staff scheduling for club events.
- **Product Sales & Movement:** Searchable item performance tables with one-click **Excel (.xlsx)** and **CSV** export for the treasurer and committee.
- **Dual-Mode Engine:** Runs in live Square API mode (Sandbox or Production) or instant simulated mock mode for offline testing.

---

## Quick Start (Local)

### 1. Configure Credentials
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your Square Sandbox credentials:
```ini
SQUARE_ENVIRONMENT=sandbox
SQUARE_ACCESS_TOKEN=your_sandbox_access_token_here
SQUARE_LOCATION_ID=your_sandbox_location_id_here
USE_MOCK=false
```

### 2. Run the Dashboard
```bash
# Activate virtual environment
source .venv/bin/activate

# Launch Streamlit
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## Homelab Deployment (Docker Compose)

To run 24/7 on your homelab:

```bash
docker compose up -d
```

- **Web Dashboard:** `http://<homelab-ip>:8501`
- **Data Persistence:** The local DuckDB database is preserved in `./data/club_sales.duckdb`.
- **Logs:** Run `docker compose logs -f` to monitor sync activity.
