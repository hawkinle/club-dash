#!/usr/bin/env python3
"""
Upper Horton Sports Club — Nightly 02:00 AM Atomic Batch Ledger Sync
====================================================================
Executes a trailing 3-day Square POS reconciliation into an isolated staging DuckDB
file and performs an atomic OS file swap (os.replace) so the running Streamlit web
server never experiences file lock contention (SEC-03).

Supports two modes:
  1. One-shot CLI / Cron:  python scripts/nightly_sync.py --days 3
  2. Docker Daemon Mode:   python scripts/nightly_sync.py --daemon (runs daily at 02:00 AM NSW time)
"""
import argparse
from datetime import datetime, timedelta
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.database import Database
from src.sync_engine import SyncEngine

SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def run_once(days: int = 3) -> bool:
    now_syd = datetime.now(SYDNEY_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{now_syd}] Starting UHSC Nightly Atomic Sync (trailing {days} days)...", flush=True)

    from src.config import is_square_configured
    if not is_square_configured():
        print("[ERROR] SQUARE_ACCESS_TOKEN is not set or empty! Please add SQUARE_ACCESS_TOKEN under GitHub Repository Settings -> Secrets and variables -> Actions.", flush=True)
        return False

    db = Database()
    engine = SyncEngine(db=db)
    res = engine.run_sync(days_back=days, atomic_staging=True)

    status = res.get("status", "UNKNOWN")
    msg = res.get("message", "")
    done_syd = datetime.now(SYDNEY_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{done_syd}] Sync Status: {status} — {msg}", flush=True)
    return status == "SUCCESS"


def run_daemon(days: int = 3):
    print(f"[{datetime.now(SYDNEY_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}] UHSC Nightly Sync Daemon initialized (Target: 02:00 AM Australia/Sydney).", flush=True)
    while True:
        now = datetime.now(SYDNEY_TZ)
        target = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = max(10, int((target - now).total_seconds()))
        print(
            f"[{now.strftime('%Y-%m-%d %H:%M:%S %Z')}] Next reconciliation scheduled for {target.strftime('%Y-%m-%d %H:%M:%S %Z')} (in {wait_seconds // 3600}h {(wait_seconds % 3600) // 60}m).",
            flush=True,
        )
        time.sleep(wait_seconds)
        try:
            run_once(days=days)
        except Exception as exc:
            print(f"[ERROR] Nightly daemon sync exception: {type(exc).__name__}", flush=True)
        time.sleep(65)


def main():
    parser = argparse.ArgumentParser(description="UHSC Nightly Atomic Batch Sync")
    parser.add_argument("--days", type=int, default=3, help="Trailing days to reconcile (default: 3)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously, triggering every night at 02:00 AM Australia/Sydney")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(days=args.days)
    else:
        ok = run_once(days=args.days)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
