from datetime import datetime, timezone, timedelta
import logging
import os
import shutil
import threading
from typing import Dict, Any, Optional
import pandas as pd
from src.config import USE_MOCK, is_square_configured, SQUARE_LOCATION_ID, DATABASE_PATH
from src.database import Database
from src.square_client import SquareClient
from src.mock_data import generate_mock_club_data

logger = logging.getLogger("uhsc_security")
_SYNC_MUTEX = threading.Lock()


class SyncEngine:
    def __init__(self, db: Optional[Database] = None, client: Optional[SquareClient] = None):
        self.db = db or Database()
        self.client = client or SquareClient()

    def run_sync(
        self,
        force_mock: bool = False,
        days_back: int = 3,
        clear_existing: bool = False,
        atomic_staging: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a thread-safe sync cycle:
        - Uses _SYNC_MUTEX so overlapping syncs cannot trigger Square 429 rate-limits.
        - If atomic_staging=True (used by the 2:00 AM nightly cron), writes to a staging DuckDB file
          and performs an atomic OS file swap (os.replace) to prevent multi-process DuckDB lock contention (SEC-03).
        """
        if not _SYNC_MUTEX.acquire(blocking=False):
            return {
                "status": "BUSY",
                "mode": "LOCKED",
                "message": "A ledger synchronization is already in progress.",
            }

        try:
            target_db = self.db
            staging_path = None
            live_path = self.db.db_path or DATABASE_PATH

            if atomic_staging and os.path.exists(live_path):
                staging_path = f"{live_path}.staging"
                shutil.copy2(live_path, staging_path)
                try:
                    os.chmod(staging_path, 0o600)
                except OSError:
                    pass
                target_db = Database(db_path=staging_path)

            if clear_existing:
                target_db.reset_transactions()

            if force_mock or USE_MOCK or not is_square_configured():
                res = self._sync_mock_data(target_db)
            else:
                res = self._sync_live_square(target_db, days_back=days_back)

            if atomic_staging and staging_path and os.path.exists(staging_path):
                if res.get("status") == "SUCCESS":
                    try:
                        os.chmod(staging_path, 0o600)
                    except OSError:
                        pass
                    os.replace(staging_path, live_path)
                else:
                    try:
                        os.remove(staging_path)
                    except OSError:
                        pass

            return res
        finally:
            _SYNC_MUTEX.release()

    def _sync_mock_data(self, target_db: Database) -> Dict[str, Any]:
        """Loads simulated Upper Horton Sports Club data into DuckDB."""
        try:
            (
                df_locations,
                df_categories,
                df_items,
                df_orders,
                df_line_items,
                df_payments,
                df_refunds,
            ) = generate_mock_club_data()

            target_db.upsert_locations(df_locations)
            target_db.upsert_catalog(df_categories, df_items)
            target_db.upsert_orders(df_orders, df_line_items)
            target_db.upsert_payments(df_payments)
            target_db.upsert_refunds(df_refunds)

            msg = f"Loaded {len(df_orders)} mock orders and {len(df_payments)} payments across 45 trading days."
            target_db.log_sync("SUCCESS (MOCK)", len(df_orders), len(df_payments), msg)

            return {
                "status": "SUCCESS",
                "mode": "MOCK",
                "message": msg,
                "orders_count": len(df_orders),
                "payments_count": len(df_payments),
            }
        except Exception as e:
            logger.error("Mock sync failure: %s", type(e).__name__)
            err_msg = "Mock synchronization failed. Check server logs."
            target_db.log_sync("ERROR", 0, 0, err_msg)
            return {"status": "ERROR", "mode": "MOCK", "message": err_msg}

    def _sync_live_square(self, target_db: Database, days_back: int = 3) -> Dict[str, Any]:
        """Syncs live data from Square API into DuckDB."""
        try:
            # 1. Test connection
            ok, msg = self.client.test_connection()
            if not ok:
                target_db.log_sync("FAILED", 0, 0, msg)
                return {"status": "ERROR", "mode": "LIVE", "message": msg}

            # 2. Sync Locations
            loc_list = self.client.get_locations()
            if loc_list:
                df_loc = pd.DataFrame(loc_list)
                target_db.upsert_locations(df_loc)

            # 3. Sync Catalog & Categories
            df_cat, df_items, cat_map = self.client.get_catalog()
            target_db.upsert_catalog(df_cat, df_items)

            # 4. Determine Date Window
            now_utc = datetime.now(timezone.utc)
            start_utc = now_utc - timedelta(days=days_back)
            start_str = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Locations filter
            location_ids = [SQUARE_LOCATION_ID] if SQUARE_LOCATION_ID else None

            # 5. Sync Orders
            df_orders, df_lines = self.client.fetch_orders(
                start_at=start_str,
                end_at=end_str,
                location_ids=location_ids,
                cat_map=cat_map,
            )
            target_db.upsert_orders(df_orders, df_lines)

            # 6. Sync Payments & Refunds
            df_pay, df_ref = self.client.fetch_payments(
                start_at=start_str,
                end_at=end_str,
                location_id=SQUARE_LOCATION_ID or "ALL",
            )
            target_db.upsert_payments(df_pay)
            target_db.upsert_refunds(df_ref)

            summary_msg = f"Synced {len(df_orders)} orders and {len(df_pay)} payments ({days_back}-day trailing window)."
            target_db.log_sync("SUCCESS", len(df_orders), len(df_pay), summary_msg)

            return {
                "status": "SUCCESS",
                "mode": "LIVE",
                "message": summary_msg,
                "orders_count": len(df_orders),
                "payments_count": len(df_pay),
            }
        except Exception as e:
            logger.error("Square live sync error: %s", type(e).__name__)
            err_msg = "Square synchronization encountered an unexpected error. Check server logs."
            target_db.log_sync("ERROR", 0, 0, err_msg)
            return {"status": "ERROR", "mode": "LIVE", "message": err_msg}
