import os
import threading
import uuid
import duckdb
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from src.config import DATABASE_PATH

_DB_LOCK = threading.RLock()
_SCHEMA_INITIALIZED = set()


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH
        # Ensure parent folder exists with restricted permissions
        parent_dir = Path(self.db_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        if self.db_path not in _SCHEMA_INITIALIZED or not os.path.exists(self.db_path):
            try:
                os.chmod(parent_dir, 0o700)
            except OSError:
                pass
            self.init_schema()
            _SCHEMA_INITIALIZED.add(self.db_path)
            try:
                if os.path.exists(self.db_path):
                    os.chmod(self.db_path, 0o600)
            except OSError:
                pass

    @contextmanager
    def get_connection(self, read_only: bool = True):
        """
        Returns a thread-safe connection to the DuckDB instance.
        Defaults to read_only=True (SEC-03) so analytical queries can never mutate or lock the ledger.
        """
        with _DB_LOCK:
            # If the database file does not exist yet, DuckDB requires read_only=False to create it
            effective_ro = read_only and os.path.exists(self.db_path)
            con = duckdb.connect(self.db_path, read_only=effective_ro)
            try:
                yield con
            finally:
                con.close()

    def init_schema(self):
        """Initializes tables, security columns, and audit logs if they do not exist."""
        with self.get_connection(read_only=False) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    location_id VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    status VARCHAR,
                    currency VARCHAR DEFAULT 'AUD',
                    address VARCHAR
                );

                CREATE TABLE IF NOT EXISTS categories (
                    category_id VARCHAR PRIMARY KEY,
                    name VARCHAR
                );

                CREATE TABLE IF NOT EXISTS catalog_items (
                    item_id VARCHAR PRIMARY KEY,
                    category_id VARCHAR,
                    category_name VARCHAR,
                    name VARCHAR
                );

                CREATE TABLE IF NOT EXISTS orders (
                    order_id VARCHAR PRIMARY KEY,
                    location_id VARCHAR,
                    created_at TIMESTAMP,
                    closed_at TIMESTAMP,
                    state VARCHAR,
                    total_money DOUBLE,
                    tax_money DOUBLE,
                    discount_money DOUBLE,
                    tip_money DOUBLE,
                    net_money DOUBLE
                );

                CREATE TABLE IF NOT EXISTS order_line_items (
                    line_item_id VARCHAR PRIMARY KEY,
                    order_id VARCHAR,
                    name VARCHAR,
                    catalog_object_id VARCHAR,
                    category_name VARCHAR,
                    quantity DOUBLE,
                    gross_sales_money DOUBLE,
                    total_discount_money DOUBLE,
                    net_sales_money DOUBLE,
                    created_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS payments (
                    payment_id VARCHAR PRIMARY KEY,
                    order_id VARCHAR,
                    location_id VARCHAR,
                    created_at TIMESTAMP,
                    status VARCHAR,
                    amount_money DOUBLE,
                    tip_money DOUBLE,
                    processing_fee_money DOUBLE,
                    payment_method VARCHAR,
                    card_brand VARCHAR,
                    entry_mode VARCHAR
                );

                CREATE TABLE IF NOT EXISTS refunds (
                    refund_id VARCHAR PRIMARY KEY,
                    payment_id VARCHAR,
                    order_id VARCHAR,
                    location_id VARCHAR,
                    created_at TIMESTAMP,
                    amount_money DOUBLE,
                    status VARCHAR,
                    reason VARCHAR
                );

                CREATE TABLE IF NOT EXISTS sync_log (
                    sync_id VARCHAR PRIMARY KEY,
                    synced_at TIMESTAMP,
                    status VARCHAR,
                    orders_synced INTEGER,
                    payments_synced INTEGER,
                    message VARCHAR
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR PRIMARY KEY,
                    username VARCHAR UNIQUE NOT NULL,
                    full_name VARCHAR NOT NULL,
                    email VARCHAR,
                    role VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    salt VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    must_change_password BOOLEAN DEFAULT FALSE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id VARCHAR PRIMARY KEY,
                    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actor_username VARCHAR,
                    event_type VARCHAR,
                    target_entity VARCHAR,
                    details VARCHAR
                );
            """)

            # Ensure security columns exist on existing users table (non-destructive migration)
            con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0;")
            con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;")
            con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;")

            # Auto-seed initial default Super Admin if users table is empty
            user_count = con.execute("SELECT count(*) FROM users").fetchone()[0]
            if user_count == 0:
                from src.auth import hash_password
                initial_pw = os.getenv("INITIAL_ADMIN_PASSWORD", "admin")
                pwd_hash, salt = hash_password(initial_pw)
                must_change = (initial_pw == "admin")
                con.execute("""
                    INSERT INTO users (
                        user_id, username, full_name, email, role,
                        password_hash, salt, status, failed_attempts, must_change_password
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 0, ?)
                """, [
                    str(uuid.uuid4()), "leith", "Leith",
                    "leith@upperhortonsportsclub.com.au", "Super Admin",
                    pwd_hash, salt, must_change
                ])

    def log_audit_event(self, actor_username: str, event_type: str, target_entity: str, details: str):
        """Records immutable security and governance events in the audit_logs table."""
        with self.get_connection(read_only=False) as con:
            con.execute("""
                INSERT INTO audit_logs (log_id, event_time, actor_username, event_type, target_entity, details)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
            """, [str(uuid.uuid4()), actor_username, event_type, target_entity, details])

    def get_audit_logs(self, limit: int = 50) -> pd.DataFrame:
        """Returns recent security and administrative governance audit logs (Read-Only)."""
        with self.get_connection(read_only=True) as con:
            return con.execute("""
                SELECT
                    STRFTIME(event_time, '%d %b %Y %H:%M:%S') AS timestamp_str,
                    actor_username AS actor,
                    event_type AS event,
                    target_entity AS target,
                    details
                FROM audit_logs
                ORDER BY event_time DESC
                LIMIT ?
            """, [limit]).fetchdf()

    # ------------------ Ingestion Helpers (Write Mode) ------------------

    def upsert_locations(self, df: pd.DataFrame):
        if df.empty:
            return
        with self.get_connection(read_only=False) as con:
            con.register("df_loc", df)
            con.execute("""
                INSERT OR REPLACE INTO locations
                SELECT * FROM df_loc
            """)

    def upsert_catalog(self, df_cat: pd.DataFrame, df_items: pd.DataFrame):
        with self.get_connection(read_only=False) as con:
            if not df_cat.empty:
                con.register("df_c", df_cat)
                con.execute("INSERT OR REPLACE INTO categories SELECT * FROM df_c")
            if not df_items.empty:
                con.register("df_i", df_items)
                con.execute("INSERT OR REPLACE INTO catalog_items SELECT * FROM df_i")

    def upsert_orders(self, df_orders: pd.DataFrame, df_items: pd.DataFrame):
        with self.get_connection(read_only=False) as con:
            if not df_orders.empty:
                con.register("df_ord", df_orders)
                con.execute("INSERT OR REPLACE INTO orders SELECT * FROM df_ord")
            if not df_items.empty:
                con.register("df_lines", df_items)
                con.execute("INSERT OR REPLACE INTO order_line_items SELECT * FROM df_lines")

    def upsert_payments(self, df_payments: pd.DataFrame):
        if df_payments.empty:
            return
        with self.get_connection(read_only=False) as con:
            con.register("df_pay", df_payments)
            con.execute("INSERT OR REPLACE INTO payments SELECT * FROM df_pay")

    def upsert_refunds(self, df_refunds: pd.DataFrame):
        if df_refunds.empty:
            return
        with self.get_connection(read_only=False) as con:
            con.register("df_ref", df_refunds)
            con.execute("INSERT OR REPLACE INTO refunds SELECT * FROM df_ref")

    def log_sync(self, status: str, orders_count: int, payments_count: int, message: str):
        sync_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        now = datetime.utcnow()
        with self.get_connection(read_only=False) as con:
            con.execute("""
                INSERT INTO sync_log (sync_id, synced_at, status, orders_synced, payments_synced, message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [sync_id, now, status, orders_count, payments_count, message])

    # ------------------ User Administration & RBAC ------------------

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verifies credentials with constant-time anti-enumeration (SEC-05)
        and 5-strike / 15-minute brute-force lockout protection (SEC-06).
        """
        from src.auth import verify_password, dummy_verify, hash_password, is_legacy_hash

        clean_user = (username or "").strip().lower()
        if not clean_user or not password:
            dummy_verify(password or "empty")
            return None

        with self.get_connection(read_only=True) as con:
            res = con.execute("SELECT * FROM users WHERE LOWER(username) = ?", [clean_user]).fetchdf()

        if res.empty:
            # SEC-05: Execute full 600k PBKDF2 dummy hash to neutralize timing attacks
            dummy_verify(password)
            self.log_audit_event(clean_user, "LOGIN_FAILED", clean_user, "Unknown username attempt")
            return None

        user = res.iloc[0].to_dict()
        now = datetime.now()

        # Check brute-force lockout window (SEC-06)
        locked_until = user.get("locked_until")
        if pd.notna(locked_until) and locked_until is not None:
            if isinstance(locked_until, pd.Timestamp):
                locked_until = locked_until.to_pydatetime().replace(tzinfo=None)
            if locked_until > now:
                dummy_verify(password)
                mins_left = max(1, int((locked_until - now).total_seconds() // 60) + 1)
                return {"error": "LOCKED", "minutes_remaining": mins_left}

        # Verify password in constant time
        if not verify_password(password, user["password_hash"], user["salt"]):
            failed_count = int(user.get("failed_attempts") or 0) + 1
            with self.get_connection(read_only=False) as con:
                if failed_count >= 5:
                    lock_time = now + timedelta(minutes=15)
                    con.execute(
                        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE user_id = ?",
                        [failed_count, lock_time, user["user_id"]]
                    )
                    self.log_audit_event(clean_user, "ACCOUNT_LOCKED", clean_user, "Locked for 15m after 5 failed attempts")
                    return {"error": "LOCKED", "minutes_remaining": 15}
                else:
                    con.execute(
                        "UPDATE users SET failed_attempts = ? WHERE user_id = ?",
                        [failed_count, user["user_id"]]
                    )
            self.log_audit_event(clean_user, "LOGIN_FAILED", clean_user, f"Invalid password (attempt {failed_count}/5)")
            return None

        # SEC-05: Check account suspension status ONLY AFTER valid password verification
        if user.get("status") == "SUSPENDED":
            self.log_audit_event(clean_user, "LOGIN_BLOCKED_SUSPENDED", clean_user, "Suspended user attempted sign-in")
            return {"error": "SUSPENDED"}

        # Transparent upgrade of legacy 100k hashes to OWASP 600k iterations (SEC-05)
        must_change = bool(user.get("must_change_password")) or (password == "admin")
        with self.get_connection(read_only=False) as con:
            if is_legacy_hash(user["password_hash"]):
                new_hash, new_salt = hash_password(password)
                con.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP, failed_attempts = 0, locked_until = NULL, password_hash = ?, salt = ?, must_change_password = ? WHERE user_id = ?",
                    [new_hash, new_salt, must_change, user["user_id"]]
                )
            else:
                con.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP, failed_attempts = 0, locked_until = NULL, must_change_password = ? WHERE user_id = ?",
                    [must_change, user["user_id"]]
                )

        self.log_audit_event(clean_user, "LOGIN_SUCCESS", clean_user, f"Signed in ({user.get('role')})")
        user["must_change_password"] = must_change
        user.pop("password_hash", None)
        user.pop("salt", None)
        return user

    def get_users(self) -> pd.DataFrame:
        """Returns all club users and board members (Read-Only)."""
        with self.get_connection(read_only=True) as con:
            return con.execute("""
                SELECT 
                    user_id, 
                    username, 
                    full_name, 
                    email, 
                    role, 
                    status, 
                    STRFTIME(created_at, '%d %b %Y') as created_date,
                    CASE WHEN last_login IS NOT NULL THEN STRFTIME(last_login, '%d %b %Y %H:%M') ELSE 'Never' END as last_login_str
                FROM users 
                ORDER BY created_at ASC
            """).fetchdf()

    def create_user(self, username: str, full_name: str, email: str, role: str, password: str, actor: str = "admin") -> Tuple[bool, str]:
        """Creates a new board member or staff user with salted 600k PBKDF2 password."""
        from src.auth import hash_password, validate_password_strength

        clean_user = (username or "").strip().lower()
        if not clean_user or not full_name.strip() or not password:
            return False, "Username, Full Name, and Password are required."

        valid_pw, pw_msg = validate_password_strength(password)
        if not valid_pw:
            return False, pw_msg

        with self.get_connection(read_only=False) as con:
            existing = con.execute("SELECT count(*) FROM users WHERE LOWER(username) = ?", [clean_user]).fetchone()[0]
            if existing > 0:
                return False, f"Username '{clean_user}' is already taken."

            pwd_hash, salt = hash_password(password)
            con.execute("""
                INSERT INTO users (user_id, username, full_name, email, role, password_hash, salt, status, failed_attempts, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 0, FALSE)
            """, [str(uuid.uuid4()), clean_user, full_name.strip(), email.strip(), role, pwd_hash, salt])

        self.log_audit_event(actor, "USER_CREATED", clean_user, f"Provisioned role: {role}")
        return True, f"User '{clean_user}' created successfully."

    def update_user_status(self, user_id: str, new_status: str, actor: str = "admin") -> Tuple[bool, str]:
        """Suspends or reactivates access for board members with sole-Super-Admin protection (SEC-07)."""
        with self.get_connection(read_only=False) as con:
            target = con.execute("SELECT username, role FROM users WHERE user_id = ?", [user_id]).fetchone()
            if not target:
                return False, "User account not found."
            target_username, target_role = target[0], target[1]

            if new_status != "ACTIVE" and target_role == "Super Admin":
                other_admins = con.execute(
                    "SELECT count(*) FROM users WHERE role = 'Super Admin' AND status = 'ACTIVE' AND user_id != ?",
                    [user_id]
                ).fetchone()[0]
                if other_admins == 0:
                    return False, "Governance Lockout Protection: Cannot suspend the sole active Super Admin."

            con.execute("UPDATE users SET status = ?, failed_attempts = 0, locked_until = NULL WHERE user_id = ?", [new_status, user_id])
        self.log_audit_event(actor, f"USER_STATUS_{new_status}", target_username, f"Status changed to {new_status}")
        return True, f"Account @{target_username} status updated to {new_status}."

    def reset_user_password(self, user_id: str, new_password: str, actor: str = "admin") -> Tuple[bool, str]:
        """Resets a user's password with fresh salt and complexity verification (SEC-05 & SEC-06)."""
        from src.auth import hash_password, validate_password_strength

        valid_pw, pw_msg = validate_password_strength(new_password)
        if not valid_pw:
            return False, pw_msg

        pwd_hash, salt = hash_password(new_password)
        with self.get_connection(read_only=False) as con:
            target = con.execute("SELECT username FROM users WHERE user_id = ?", [user_id]).fetchone()
            target_username = target[0] if target else user_id
            con.execute(
                "UPDATE users SET password_hash = ?, salt = ?, failed_attempts = 0, locked_until = NULL, must_change_password = FALSE WHERE user_id = ?",
                [pwd_hash, salt, user_id]
            )
        self.log_audit_event(actor, "PASSWORD_RESET", target_username, "Password updated with 600k PBKDF2-SHA256")
        return True, "Password updated successfully."

    def update_user_role(self, user_id: str, new_role: str, actor: str = "admin") -> Tuple[bool, str]:
        """Updates user's role with sole-Super-Admin demotion protection (SEC-07)."""
        with self.get_connection(read_only=False) as con:
            target = con.execute("SELECT username, role FROM users WHERE user_id = ?", [user_id]).fetchone()
            if not target:
                return False, "User account not found."
            target_username, current_role = target[0], target[1]

            if current_role == "Super Admin" and new_role != "Super Admin":
                other_admins = con.execute(
                    "SELECT count(*) FROM users WHERE role = 'Super Admin' AND status = 'ACTIVE' AND user_id != ?",
                    [user_id]
                ).fetchone()[0]
                if other_admins == 0:
                    return False, "Governance Lockout Protection: Cannot demote the sole active Super Admin."

            con.execute("UPDATE users SET role = ? WHERE user_id = ?", [new_role, user_id])
        self.log_audit_event(actor, "ROLE_CHANGED", target_username, f"Role changed from {current_role} to {new_role}")
        return True, f"Updated @{target_username} role to {new_role}."

    def delete_user(self, user_id: str, actor: str = "admin") -> Tuple[bool, str]:
        """Permanently removes a board member or user account with sole-Super-Admin protection (SEC-07)."""
        with self.get_connection(read_only=False) as con:
            target = con.execute("SELECT username, role FROM users WHERE user_id = ?", [user_id]).fetchone()
            if not target:
                return False, "User account not found."
            target_username, target_role = target[0], target[1]

            if target_role == "Super Admin":
                other_admins = con.execute(
                    "SELECT count(*) FROM users WHERE role = 'Super Admin' AND status = 'ACTIVE' AND user_id != ?",
                    [user_id]
                ).fetchone()[0]
                if other_admins == 0:
                    return False, "Governance Lockout Protection: Cannot delete the sole active Super Admin."

            con.execute("DELETE FROM users WHERE user_id = ?", [user_id])
        self.log_audit_event(actor, "USER_DELETED", target_username, "Account permanently removed")
        return True, f"User @{target_username} permanently deleted."

    # ------------------ Reporting Queries ------------------

    def get_kpis(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates executive headline KPIs for the date range with previous period comparisons."""
        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                COALESCE(SUM(total_money), 0.0) AS gross_sales,
                COALESCE(SUM(net_money), 0.0) AS net_sales,
                COALESCE(SUM(discount_money), 0.0) AS total_discounts,
                COALESCE(SUM(tip_money), 0.0) AS total_tips,
                COUNT(order_id) AS total_orders,
                CASE WHEN COUNT(order_id) > 0 
                     THEN COALESCE(SUM(net_money), 0.0) / COUNT(order_id) 
                     ELSE 0.0 
                END AS avg_order_value
            FROM orders
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
              AND state IN ('COMPLETED', 'OPEN')
              {loc_filter}
        """

        refund_query = f"""
            SELECT COALESCE(SUM(amount_money), 0.0) AS total_refunds
            FROM refunds
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
              {loc_filter}
        """

        with self.get_connection() as con:
            res_orders = con.execute(query, params).fetchdf()
            res_refunds = con.execute(refund_query, params).fetchdf()

        kpi_data = res_orders.iloc[0].to_dict() if not res_orders.empty else {}
        kpi_data["total_refunds"] = res_refunds.iloc[0]["total_refunds"] if not res_refunds.empty else 0.0

        # Calculate previous period for PoP comparison
        try:
            curr_start = pd.to_datetime(start_date)
            curr_end = pd.to_datetime(end_date)
            period_len = curr_end - curr_start
            prev_end = curr_start
            prev_start = prev_end - period_len

            prev_params = [prev_start.strftime("%Y-%m-%d %H:%M:%S"), prev_end.strftime("%Y-%m-%d %H:%M:%S")]
            if loc_filter:
                prev_params.append(location_id)

            with self.get_connection() as con:
                res_prev = con.execute(query, prev_params).fetchdf()
            
            if not res_prev.empty and res_prev.iloc[0]["net_sales"] > 0:
                prev_net = res_prev.iloc[0]["net_sales"]
                prev_orders = res_prev.iloc[0]["total_orders"]
                curr_net = kpi_data.get("net_sales", 0.0)
                curr_orders = kpi_data.get("total_orders", 0)
                
                kpi_data["net_sales_pop_pct"] = round(((curr_net - prev_net) / prev_net) * 100.0, 1)
                kpi_data["orders_pop_pct"] = round(((curr_orders - prev_orders) / max(prev_orders, 1)) * 100.0, 1)
                kpi_data["prev_net_sales"] = float(prev_net)
                kpi_data["prev_orders"] = int(prev_orders)
            else:
                kpi_data["net_sales_pop_pct"] = None
                kpi_data["orders_pop_pct"] = None
                kpi_data["prev_net_sales"] = 0.0
                kpi_data["prev_orders"] = 0
        except Exception:
            kpi_data["net_sales_pop_pct"] = None
            kpi_data["orders_pop_pct"] = None
            kpi_data["prev_net_sales"] = 0.0
            kpi_data["prev_orders"] = 0

        # Calculate Year-over-Year (YoY) comparison (same calendar window 1 year prior)
        try:
            curr_start = pd.to_datetime(start_date)
            curr_end = pd.to_datetime(end_date)
            yoy_start = curr_start - pd.DateOffset(years=1)
            yoy_end = curr_end - pd.DateOffset(years=1)

            yoy_params = [yoy_start.strftime("%Y-%m-%d %H:%M:%S"), yoy_end.strftime("%Y-%m-%d %H:%M:%S")]
            if loc_filter:
                yoy_params.append(location_id)

            with self.get_connection() as con:
                res_yoy = con.execute(query, yoy_params).fetchdf()

            if not res_yoy.empty and res_yoy.iloc[0]["net_sales"] > 0:
                yoy_net = res_yoy.iloc[0]["net_sales"]
                yoy_orders = res_yoy.iloc[0]["total_orders"]
                curr_net = kpi_data.get("net_sales", 0.0)
                curr_orders = kpi_data.get("total_orders", 0)

                kpi_data["yoy_sales_pct"] = round(((curr_net - yoy_net) / yoy_net) * 100.0, 1)
                kpi_data["yoy_orders_pct"] = round(((curr_orders - yoy_orders) / max(yoy_orders, 1)) * 100.0, 1)
                kpi_data["yoy_net_sales"] = float(yoy_net)
                kpi_data["yoy_orders"] = int(yoy_orders)
            else:
                kpi_data["yoy_sales_pct"] = None
                kpi_data["yoy_orders_pct"] = None
                kpi_data["yoy_net_sales"] = 0.0
                kpi_data["yoy_orders"] = 0
        except Exception:
            kpi_data["yoy_sales_pct"] = None
            kpi_data["yoy_orders_pct"] = None
            kpi_data["yoy_net_sales"] = 0.0
            kpi_data["yoy_orders"] = 0

        return kpi_data

    def get_bank_settlement_bridge(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> Dict[str, float]:
        """Calculates the accountant's bank settlement bridge from gross takings to net bank deposit."""
        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                COALESCE(SUM(total_money), 0.0) AS gross_sales,
                COALESCE(SUM(discount_money), 0.0) AS discounts,
                COALESCE(SUM(net_money), 0.0) AS net_sales
            FROM orders
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
              AND state IN ('COMPLETED', 'OPEN')
              {loc_filter}
        """

        pay_query = f"""
            SELECT
                COALESCE(SUM(CASE WHEN payment_method = 'CASH' THEN amount_money ELSE 0.0 END), 0.0) AS cash_takings,
                COALESCE(SUM(CASE WHEN payment_method != 'CASH' THEN amount_money ELSE 0.0 END), 0.0) AS card_takings,
                COALESCE(SUM(processing_fee_money), 0.0) AS square_fees,
                COALESCE(SUM(amount_money - processing_fee_money), 0.0) AS net_settlement
            FROM payments
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
              AND status = 'COMPLETED'
              {loc_filter}
        """

        with self.get_connection() as con:
            ord_res = con.execute(query, params).fetchdf()
            pay_res = con.execute(pay_query, params).fetchdf()

        ord_dict = ord_res.iloc[0].to_dict() if not ord_res.empty else {}
        pay_dict = pay_res.iloc[0].to_dict() if not pay_res.empty else {}

        return {
            "gross_sales": ord_dict.get("gross_sales", 0.0),
            "discounts": ord_dict.get("discounts", 0.0),
            "net_sales": ord_dict.get("net_sales", 0.0),
            "cash_takings": pay_dict.get("cash_takings", 0.0),
            "card_takings": pay_dict.get("card_takings", 0.0),
            "square_fees": pay_dict.get("square_fees", 0.0),
            "net_settlement": pay_dict.get("net_settlement", 0.0),
        }

    def get_gl_export(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> pd.DataFrame:
        """
        Generates general ledger journal entries in the exact Xero Manual Journal import format.
        Headers: Narration, Date, Description, AccountCode, TaxType, Debit, Credit
        """
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                COALESCE(li.category_name, 'General Sales') AS department,
                COALESCE(SUM(li.net_sales_money), 0.0) AS credit_amount
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1
        """

        bridge = self.get_bank_settlement_bridge(start_date, end_date, location_id)

        with self.get_connection() as con:
            dept_df = con.execute(query, params).fetchdf()

        gl_rows = []
        date_formatted = pd.to_datetime(end_date).strftime("%d/%m/%Y")
        narration_text = f"Square POS Trading {start_date[:10]} to {end_date[:10]}"

        # Standard Australian Xero Chart of Accounts mapping for Sports Clubs
        xero_account_map = {
            "Bar - Draught Beer": ("201", "Bar Sales - Draught Beer", "GST on Income"),
            "Bar - Packaged Beer": ("202", "Bar Sales - Packaged Beer & Cider", "GST on Income"),
            "Bar - Spirits & Wine": ("203", "Bar Sales - Spirits, RTDs & Wine", "GST on Income"),
            "Bar - Non-Alcoholic & Snacks": ("204", "Bar Sales - Soft Drink & Confectionery", "GST on Income"),
            "Bar - Beer & Cider": ("201", "Bar Sales - Beer & Cider", "GST on Income"),
            "Bar - Non-Alcoholic": ("204", "Bar Sales - Soft Drink & Water", "GST on Income"),
            "Bistro & Kitchen": ("210", "Bistro & Kitchen Food Takings", "GST on Income"),
            "Canteen & Bistro": ("210", "Bistro & Canteen Takings", "GST on Income"),
            "Tobacco": ("220", "Tobacco & Cigarette Sales", "GST on Income"),
            "Club & Camping": ("230", "Camping Fees & Club Memberships", "GST on Income"),
            "Events & Gate": ("240", "Events, Gate & Admissions", "GST on Income"),
            "Club Merchandise": ("250", "Club Merchandise Sales", "GST on Income"),
            "General & Other": ("200", "General Bar & Counter Sales", "GST on Income"),
        }

        # 1. Revenue Credits (Income Accounts)
        for _, row in dept_df.iterrows():
            dept = row["department"]
            amt = round(float(row["credit_amount"]), 2)
            code, desc_name, tax = xero_account_map.get(dept, ("200", f"Sales - {dept}", "GST on Income"))
            
            gl_rows.append({
                "*Narration": narration_text,
                "*Date": date_formatted,
                "*Description": f"{desc_name} ({start_date[:10]} - {end_date[:10]})",
                "*AccountCode": code,
                "*TaxType": tax,
                "Debit": "",
                "Credit": f"{amt:.2f}"
            })

        # 2. Square Processing Fees (Expense Account - 404 Merchant Fees)
        if bridge["square_fees"] > 0:
            gl_rows.append({
                "*Narration": narration_text,
                "*Date": date_formatted,
                "*Description": "Square Merchant Processing Fees",
                "*AccountCode": "404",
                "*TaxType": "GST on Expenses",
                "Debit": f"{bridge['square_fees']:.2f}",
                "Credit": ""
            })

        # 3. Cash on Hand (Asset Account - 801 Undeposited Cash / Safe Clearing)
        if bridge["cash_takings"] > 0:
            gl_rows.append({
                "*Narration": narration_text,
                "*Date": date_formatted,
                "*Description": "Physical Cash Collected for Safe / Bank Deposit",
                "*AccountCode": "801",
                "*TaxType": "BAS Excluded",
                "Debit": f"{bridge['cash_takings']:.2f}",
                "Credit": ""
            })

        # 4. Square Clearing Account (Asset Account - 802 Square Electronic Clearing)
        net_card = round(bridge["card_takings"] - bridge["square_fees"], 2)
        if net_card > 0:
            gl_rows.append({
                "*Narration": narration_text,
                "*Date": date_formatted,
                "*Description": "Net EFTPOS Settlement Expected in Main Bank Account",
                "*AccountCode": "802",
                "*TaxType": "BAS Excluded",
                "Debit": f"{net_card:.2f}",
                "Credit": ""
            })

        return pd.DataFrame(gl_rows)

    def get_sales_timeseries(self, start_date: str, end_date: str, freq: str = "D", location_id: Optional[str] = None) -> pd.DataFrame:
        """Returns daily or hourly sales trend."""
        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""
        date_trunc = "day" if freq == "D" else "hour"

        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                DATE_TRUNC('{date_trunc}', created_at) AS period,
                COALESCE(SUM(net_money), 0.0) AS net_sales,
                COALESCE(SUM(gross_sales_money), 0.0) AS gross_sales,
                COUNT(DISTINCT order_id) AS order_count
            FROM (
                SELECT 
                    o.order_id,
                    o.created_at,
                    o.net_money,
                    o.total_money AS gross_sales_money
                FROM orders o
                WHERE o.created_at >= CAST(? AS TIMESTAMP)
                  AND o.created_at <= CAST(? AS TIMESTAMP)
                  AND o.state IN ('COMPLETED', 'OPEN')
                  {loc_filter}
            )
            GROUP BY 1
            ORDER BY 1 ASC
        """
        with self.get_connection() as con:
            return con.execute(query, params).fetchdf()
    def get_department_breakdown(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> pd.DataFrame:
        """Returns revenue and item count breakdown by category / department."""
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                COALESCE(li.category_name, 'Uncategorized') AS category,
                COALESCE(SUM(li.quantity), 0) AS units_sold,
                COALESCE(SUM(li.gross_sales_money), 0.0) AS gross_sales,
                COALESCE(SUM(li.total_discount_money), 0.0) AS discounts,
                COALESCE(SUM(li.net_sales_money), 0.0) AS net_sales,
                ROUND(COALESCE(SUM(li.net_sales_money), 0.0) * 100.0 / NULLIF(SUM(SUM(li.net_sales_money)) OVER(), 0), 2) AS percentage_of_sales
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1
            ORDER BY net_sales DESC
        """
        with self.get_connection() as con:
            return con.execute(query, params).fetchdf()
    def get_tender_breakdown(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> pd.DataFrame:
        """Returns breakdown of payments by tender type (Card, Cash, etc)."""
        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                COALESCE(payment_method, 'CARD') AS payment_method,
                COALESCE(card_brand, 'Other/None') AS card_brand,
                COUNT(payment_id) AS transaction_count,
                COALESCE(SUM(amount_money), 0.0) AS total_amount,
                COALESCE(SUM(tip_money), 0.0) AS total_tips,
                COALESCE(SUM(processing_fee_money), 0.0) AS est_processing_fees,
                COALESCE(SUM(amount_money - processing_fee_money), 0.0) AS net_deposit
            FROM payments
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
              AND status = 'COMPLETED'
              {loc_filter}
            GROUP BY 1, 2
            ORDER BY total_amount DESC
        """
        with self.get_connection() as con:
            return con.execute(query, params).fetchdf()
    def get_trading_heatmap(self, start_date: str, end_date: str, location_id: Optional[str] = None, min_hour: int = 12, max_hour: int = 24) -> pd.DataFrame:
        """Returns sales activity grouped by Day of Week and Hour of Day, filtered to club trading hours (default 12:00 to 24:00 Midday-Midnight)."""
        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date, min_hour, max_hour]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                DAYOFWEEK(created_at) AS day_num, -- 1=Sunday, 2=Monday, ..., 7=Saturday
                STRFTIME(created_at, '%A') AS day_name,
                HOUR(created_at) AS hour_of_day,
                COUNT(order_id) AS order_count,
                COALESCE(SUM(net_money), 0.0) AS total_sales
            FROM orders
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
              AND HOUR(created_at) >= ?
              AND HOUR(created_at) < ?
              AND state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1, 2, 3
            ORDER BY day_num ASC, hour_of_day ASC
        """
        with self.get_connection() as con:
            return con.execute(query, params).fetchdf()
    def get_top_items(self, start_date: str, end_date: str, limit: int = 50, category: Optional[str] = None, location_id: Optional[str] = None) -> pd.DataFrame:
        """Returns top performing menu items / products."""
        filters = ["o.created_at >= CAST(? AS TIMESTAMP)", "o.created_at <= CAST(? AS TIMESTAMP)", "o.state IN ('COMPLETED', 'OPEN')"]
        params: List[Any] = [start_date, end_date]

        if category and category != "ALL":
            filters.append("li.category_name = ?")
            params.append(category)

        if location_id and location_id != "ALL":
            filters.append("o.location_id = ?")
            params.append(location_id)

        where_clause = " AND ".join(filters)
        params.append(limit)

        query = f"""
            SELECT
                li.name AS item_name,
                COALESCE(li.category_name, 'Uncategorized') AS category,
                COALESCE(SUM(li.quantity), 0) AS total_qty_sold,
                COALESCE(SUM(li.gross_sales_money), 0.0) AS gross_sales,
                COALESCE(SUM(li.total_discount_money), 0.0) AS discounts,
                COALESCE(SUM(li.net_sales_money), 0.0) AS net_sales,
                ROUND(CASE WHEN SUM(li.quantity) > 0 
                     THEN SUM(li.net_sales_money) / SUM(li.quantity) 
                     ELSE 0.0 END, 2) AS avg_unit_price
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE {where_clause}
            GROUP BY 1, 2
            ORDER BY net_sales DESC
            LIMIT ?
        """
        with self.get_connection() as con:
            return con.execute(query, params).fetchdf()
    def reset_transactions(self, actor: str = "admin"):
        """Clears all orders, line items, payments, and refunds for a clean production import."""
        with self.get_connection(read_only=False) as con:
            con.execute("DELETE FROM order_line_items;")
            con.execute("DELETE FROM orders;")
            con.execute("DELETE FROM payments;")
            con.execute("DELETE FROM refunds;")
            con.execute("DELETE FROM sync_log;")
        self.log_audit_event(actor, "DATABASE_PURGED", "ALL_TABLES", "Cleared transactions for fresh sync")

    def get_sync_history(self, limit: int = 10) -> pd.DataFrame:
        """Returns recent sync audit logs."""
        with self.get_connection() as con:
            return con.execute("""
                SELECT 
                    synced_at,
                    status,
                    orders_synced,
                    payments_synced,
                    message
                FROM sync_log
                ORDER BY synced_at DESC
                LIMIT ?
            """, [limit]).fetchdf()

    def get_available_locations(self) -> List[Dict[str, str]]:
        """Returns all distinct locations stored in the database."""
        with self.get_connection() as con:
            df = con.execute("SELECT location_id, name FROM locations").fetchdf()
            if df.empty:
                return []
            return df.to_dict(orient="records")

    def get_available_categories(self) -> List[str]:
        """Returns distinct category names."""
        with self.get_connection() as con:
            df = con.execute("""
                SELECT DISTINCT category_name 
                FROM order_line_items 
                WHERE category_name IS NOT NULL
                ORDER BY 1
            """).fetchdf()
            if df.empty:
                return []
            return df["category_name"].tolist()

    def get_mtd_comparative_analysis(self, location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates Month-to-Date (MTD) performance with dual executive comparisons:
        1. vs. Prior Month (MoM) comparable day-range and full month total
        2. vs. Same Month Last Year (YoY / SMLY) comparable day-range and full month total
        Also returns a daily cumulative tracking DataFrame for high-end spline plotting.
        """
        import calendar
        from datetime import timedelta

        now = datetime.now()
        # Current month
        m_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        curr_day = now.day
        
        # Prior month
        first_of_curr = now.replace(day=1)
        prev_month_last_day = first_of_curr - timedelta(days=1)
        prev_month_start = prev_month_last_day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_comp_end = prev_month_start + timedelta(days=min(curr_day, prev_month_last_day.day) - 1, hours=23, minutes=59, seconds=59)
        prev_month_full_end = prev_month_last_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Same month last year
        try:
            last_year_start = m_start.replace(year=now.year - 1)
        except ValueError:
            last_year_start = m_start.replace(year=now.year - 1, day=28)
            
        days_in_last_year_month = calendar.monthrange(now.year - 1, now.month)[1]
        last_year_comp_end = last_year_start + timedelta(days=min(curr_day, days_in_last_year_month) - 1, hours=23, minutes=59, seconds=59)
        last_year_full_end = last_year_start.replace(day=days_in_last_year_month, hour=23, minute=59, second=59, microsecond=999999)

        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""

        def fetch_metrics(start_dt, end_dt):
            params = [start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")]
            if loc_filter:
                params.append(location_id)
            q = f"""
                SELECT
                    COALESCE(SUM(total_money), 0.0) AS gross_sales,
                    COALESCE(SUM(net_money), 0.0) AS net_sales,
                    COALESCE(SUM(discount_money), 0.0) AS total_discounts,
                    COUNT(order_id) AS total_orders,
                    CASE WHEN COUNT(order_id) > 0 THEN COALESCE(SUM(net_money), 0.0) / COUNT(order_id) ELSE 0.0 END AS aov
                FROM orders
                WHERE created_at >= CAST(? AS TIMESTAMP)
                  AND created_at <= CAST(? AS TIMESTAMP)
                  AND state IN ('COMPLETED', 'OPEN')
                  {loc_filter}
            """
            with self.get_connection() as con:
                res = con.execute(q, params).fetchdf()
            return res.iloc[0].to_dict() if not res.empty else {"gross_sales": 0, "net_sales": 0, "total_discounts": 0, "total_orders": 0, "aov": 0}

        curr_mtd = fetch_metrics(m_start, now)
        prior_mo_comp = fetch_metrics(prev_month_start, prev_month_comp_end)
        prior_mo_full = fetch_metrics(prev_month_start, prev_month_full_end)
        last_yr_comp = fetch_metrics(last_year_start, last_year_comp_end)
        last_yr_full = fetch_metrics(last_year_start, last_year_full_end)

        def calc_pct(current, baseline):
            if baseline > 0:
                return round(((current - baseline) / baseline) * 100.0, 1)
            return None

        mom_sales_pct = calc_pct(curr_mtd["net_sales"], prior_mo_comp["net_sales"])
        mom_orders_pct = calc_pct(curr_mtd["total_orders"], prior_mo_comp["total_orders"])
        yoy_sales_pct = calc_pct(curr_mtd["net_sales"], last_yr_comp["net_sales"])
        yoy_orders_pct = calc_pct(curr_mtd["total_orders"], last_yr_comp["total_orders"])

        def fetch_daily_series(start_dt, end_dt):
            params = [start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")]
            if loc_filter:
                params.append(location_id)
            q = f"""
                SELECT
                    DAY(created_at) AS day_num,
                    COALESCE(SUM(net_money), 0.0) AS daily_sales
                FROM orders
                WHERE created_at >= CAST(? AS TIMESTAMP)
                  AND created_at <= CAST(? AS TIMESTAMP)
                  AND state IN ('COMPLETED', 'OPEN')
                  {loc_filter}
                GROUP BY 1
                ORDER BY 1 ASC
            """
            with self.get_connection() as con:
                return con.execute(q, params).fetchdf()

        df_curr_days = fetch_daily_series(m_start, now)
        df_prior_days = fetch_daily_series(prev_month_start, prev_month_full_end)
        df_last_yr_days = fetch_daily_series(last_year_start, last_year_full_end)

        days_range = list(range(1, 32))
        curr_map = dict(zip(df_curr_days["day_num"], df_curr_days["daily_sales"])) if not df_curr_days.empty else {}
        prior_map = dict(zip(df_prior_days["day_num"], df_prior_days["daily_sales"])) if not df_prior_days.empty else {}
        last_yr_map = dict(zip(df_last_yr_days["day_num"], df_last_yr_days["daily_sales"])) if not df_last_yr_days.empty else {}

        tracking_rows = []
        c_cum, p_cum, ly_cum = 0.0, 0.0, 0.0
        for d in days_range:
            c_val = curr_map.get(d, 0.0)
            if d <= curr_day:
                c_cum += c_val
                curr_cum_val = round(c_cum, 2)
            else:
                curr_cum_val = None

            p_val = prior_map.get(d, 0.0)
            p_cum += p_val
            
            ly_val = last_yr_map.get(d, 0.0)
            ly_cum += ly_val

            tracking_rows.append({
                "day_num": d,
                "current_month_cum": curr_cum_val,
                "prior_month_cum": round(p_cum, 2),
                "same_month_last_year_cum": round(ly_cum, 2)
            })

        return {
            "current_month_name": now.strftime("%B %Y"),
            "prior_month_name": prev_month_start.strftime("%B %Y"),
            "last_year_month_name": last_year_start.strftime("%B %Y"),
            "current_day": curr_day,
            "curr_mtd": curr_mtd,
            "prior_mo_comp": prior_mo_comp,
            "prior_mo_full": prior_mo_full,
            "last_yr_comp": last_yr_comp,
            "last_yr_full": last_yr_full,
            "mom_sales_pct": mom_sales_pct,
            "mom_orders_pct": mom_orders_pct,
            "yoy_sales_pct": yoy_sales_pct,
            "yoy_orders_pct": yoy_orders_pct,
            "df_cumulative": pd.DataFrame(tracking_rows)
        }

    def get_ytd_performance(self, location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates 2026 Year-to-Date (YTD) performance with 2025 comparative benchmark:
        1. Monthly progression (Jan through Oct) comparing 2026 Net Takings vs 2025 Net Takings.
        2. Cumulative running sums across both calendar years.
        3. Annual headline metrics: 2026 YTD net sales, 2025 YTD net sales, overall YoY growth %.
        """
        now = datetime.now()
        curr_year = now.year

        loc_filter = "AND location_id = ?" if location_id and location_id != "ALL" else ""
        params_26 = [f"{curr_year}-01-01 00:00:00", f"{curr_year}-12-31 23:59:59"]
        params_25 = [f"{curr_year-1}-01-01 00:00:00", f"{curr_year-1}-12-31 23:59:59"]
        if loc_filter:
            params_26.append(location_id)
            params_25.append(location_id)

        query = f"""
            WITH m26 AS (
                SELECT 
                    MONTH(created_at) AS mo,
                    COALESCE(SUM(net_money), 0.0) AS net_26,
                    COALESCE(SUM(total_money), 0.0) AS gross_26,
                    COUNT(order_id) AS orders_26
                FROM orders
                WHERE created_at >= CAST(? AS TIMESTAMP)
                  AND created_at <= CAST(? AS TIMESTAMP)
                  AND state IN ('COMPLETED', 'OPEN')
                  {loc_filter}
                GROUP BY 1
            ),
            m25 AS (
                SELECT 
                    MONTH(created_at) AS mo,
                    COALESCE(SUM(net_money), 0.0) AS net_25,
                    COALESCE(SUM(total_money), 0.0) AS gross_25,
                    COUNT(order_id) AS orders_25
                FROM orders
                WHERE created_at >= CAST(? AS TIMESTAMP)
                  AND created_at <= CAST(? AS TIMESTAMP)
                  AND state IN ('COMPLETED', 'OPEN')
                  {loc_filter}
                GROUP BY 1
            )
            SELECT 
                m26.mo AS month_num,
                m26.net_26,
                m26.gross_26,
                m26.orders_26,
                COALESCE(m25.net_25, 0.0) AS net_25,
                COALESCE(m25.gross_25, 0.0) AS gross_25,
                COALESCE(m25.orders_25, 0) AS orders_25
            FROM m26
            LEFT JOIN m25 ON m26.mo = m25.mo
            ORDER BY month_num ASC
        """
        all_params = params_26 + params_25
        with self.get_connection() as con:
            df_months = con.execute(query, all_params).fetchdf()

        if df_months.empty:
            return {
                "ytd_net_2026": 0.0,
                "ytd_net_2025": 0.0,
                "ytd_yoy_growth_pct": None,
                "ytd_orders_2026": 0,
                "ytd_orders_2025": 0,
                "avg_monthly_sales_2026": 0.0,
                "peak_month_label": "N/A",
                "peak_month_sales": 0.0,
                "df_ytd": pd.DataFrame()
            }

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_months["month_label"] = df_months["month_num"].apply(lambda m: month_names[int(m) - 1])
        df_months["cum_net_2026"] = df_months["net_26"].cumsum()
        df_months["cum_net_2025"] = df_months["net_25"].cumsum()
        df_months["yoy_growth_pct"] = df_months.apply(
            lambda r: round(((r["net_26"] - r["net_25"]) / r["net_25"]) * 100.0, 1) if r["net_25"] > 0 else None,
            axis=1
        )

        ytd_net_26 = float(df_months["net_26"].sum())
        ytd_net_25 = float(df_months["net_25"].sum())
        ytd_orders_26 = int(df_months["orders_26"].sum())
        ytd_orders_25 = int(df_months["orders_25"].sum())
        overall_yoy = round(((ytd_net_26 - ytd_net_25) / ytd_net_25) * 100.0, 1) if ytd_net_25 > 0 else None

        num_months = len(df_months)
        avg_mo_26 = ytd_net_26 / max(1, num_months)
        peak_row = df_months.loc[df_months["net_26"].idxmax()]

        return {
            "ytd_net_2026": ytd_net_26,
            "ytd_net_2025": ytd_net_25,
            "ytd_yoy_growth_pct": overall_yoy,
            "ytd_orders_2026": ytd_orders_26,
            "ytd_orders_2025": ytd_orders_25,
            "avg_monthly_sales_2026": avg_mo_26,
            "peak_month_label": peak_row["month_label"],
            "peak_month_sales": float(peak_row["net_26"]),
            "df_ytd": df_months
        }

    # -------------------------------------------------------------
    # Bar Manager Analytical Queries (What's Selling & What's Not)
    # -------------------------------------------------------------

    def get_bar_manager_kpis(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates Bar Operations KPIs: Tap Kegs, Cartons, Draught vs Packaged split."""
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                -- Tap / Draught (Schooner items)
                COALESCE(SUM(CASE WHEN li.category_name = 'Bar - Draught Beer' OR LOWER(li.name) LIKE '%schooner%' OR LOWER(li.name) LIKE '%tap%' OR LOWER(li.name) LIKE '%draught%' OR LOWER(li.name) LIKE '%middy%' OR LOWER(li.name) LIKE '%pint%' THEN li.quantity ELSE 0 END), 0) AS tap_units,
                COALESCE(SUM(CASE WHEN li.category_name = 'Bar - Draught Beer' OR LOWER(li.name) LIKE '%schooner%' OR LOWER(li.name) LIKE '%tap%' OR LOWER(li.name) LIKE '%draught%' OR LOWER(li.name) LIKE '%middy%' OR LOWER(li.name) LIKE '%pint%' THEN li.net_sales_money ELSE 0 END), 0.0) AS tap_sales,
                -- Packaged (Cans, Stubbies, Bottles, RTDs)
                COALESCE(SUM(CASE WHEN li.category_name = 'Bar - Packaged Beer' OR (li.category_name = 'Bar - Spirits & Wine' AND (LOWER(li.name) LIKE '%can%' OR LOWER(li.name) LIKE '%stubby%' OR LOWER(li.name) LIKE '%bottle%' OR LOWER(li.name) LIKE '%pk%')) OR LOWER(li.name) LIKE '%can%' OR LOWER(li.name) LIKE '%stubby%' OR LOWER(li.name) LIKE '%bottle%' THEN li.quantity ELSE 0 END), 0) AS packaged_units,
                COALESCE(SUM(CASE WHEN li.category_name = 'Bar - Packaged Beer' OR (li.category_name = 'Bar - Spirits & Wine' AND (LOWER(li.name) LIKE '%can%' OR LOWER(li.name) LIKE '%stubby%' OR LOWER(li.name) LIKE '%bottle%' OR LOWER(li.name) LIKE '%pk%')) OR LOWER(li.name) LIKE '%can%' OR LOWER(li.name) LIKE '%stubby%' OR LOWER(li.name) LIKE '%bottle%' THEN li.net_sales_money ELSE 0 END), 0.0) AS packaged_sales,
                -- Overall Bar
                COALESCE(SUM(CASE WHEN li.category_name LIKE 'Bar%' THEN li.quantity ELSE 0 END), 0) AS total_bar_units,
                COALESCE(SUM(CASE WHEN li.category_name LIKE 'Bar%' THEN li.net_sales_money ELSE 0 END), 0.0) AS total_bar_sales
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND (li.category_name LIKE 'Bar%' OR LOWER(li.name) LIKE '%schooner%' OR LOWER(li.name) LIKE '%stubby%' OR LOWER(li.name) LIKE '%spirit%')
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
        """

        with self.get_connection() as con:
            df = con.execute(query, params).fetchdf()

        data = df.iloc[0].to_dict() if not df.empty else {}
        tap_units = data.get("tap_units", 0)
        packaged_units = data.get("packaged_units", 0)
        total_units = data.get("total_bar_units", 0)

        # Standard Australian conversions:
        # 1 standard 50L commercial beer keg yields approx 118 schooners (425ml) allowing for head/spillage
        # 1 carton/case = 24 stubbies or cans
        data["est_50l_kegs"] = round(tap_units / 118.0, 1) if tap_units > 0 else 0.0
        data["est_cartons"] = round(packaged_units / 24.0, 1) if packaged_units > 0 else 0.0
        data["tap_ratio_pct"] = round((tap_units / total_units) * 100.0, 1) if total_units > 0 else 0.0
        data["packaged_ratio_pct"] = round((packaged_units / total_units) * 100.0, 1) if total_units > 0 else 0.0

        return data

    def get_bar_movement_matrix(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Returns two DataFrames:
        1. Top Movers (What's Selling / Flying): High-velocity bar items ranked by volume and revenue.
        2. Dead Stock / Slow Movers (What's NOT Selling): Bar items with low velocity, tying up cool room capital.
        """
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                li.name AS item_name,
                li.category_name AS category,
                COALESCE(SUM(li.quantity), 0) AS units_sold,
                COALESCE(SUM(li.net_sales_money), 0.0) AS net_revenue,
                ROUND(CASE WHEN SUM(li.quantity) > 0 THEN SUM(li.net_sales_money) / SUM(li.quantity) ELSE 0.0 END, 2) AS avg_unit_price,
                ROUND(COALESCE(SUM(li.net_sales_money), 0.0) * 100.0 / NULLIF(SUM(SUM(li.net_sales_money)) OVER(), 0), 1) AS revenue_share_pct
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND (li.category_name LIKE 'Bar%' OR li.category_name IN ('Bar - Beer & Cider', 'Bar - Spirits & Wine', 'Bar - Non-Alcoholic'))
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1, 2
            ORDER BY units_sold DESC
        """

        with self.get_connection() as con:
            df = con.execute(query, params).fetchdf()

        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Top Movers (High Volume in selected trading window)
        df_top = df.head(10).copy()
        df_top["velocity_badge"] = "🔥 Fast Mover"

        # Slow Movers / Dead Stock: Evaluated on a 6-Month (180-day) trailing basis
        now = datetime.now()
        six_mo_start = now - timedelta(days=180)
        dead_stock_params = [six_mo_start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")]
        if loc_filter:
            dead_stock_params.append(location_id)

        dead_query = f"""
            SELECT
                li.name AS item_name,
                li.category_name AS category,
                COALESCE(SUM(li.quantity), 0) AS units_sold,
                COALESCE(SUM(li.net_sales_money), 0.0) AS net_revenue,
                ROUND(CASE WHEN SUM(li.quantity) > 0 THEN SUM(li.net_sales_money) / SUM(li.quantity) ELSE 0.0 END, 2) AS avg_unit_price,
                STRFTIME(MAX(o.created_at), '%d %b %Y') AS last_sold_str
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND (li.category_name LIKE 'Bar%' OR li.category_name IN ('Bar - Beer & Cider', 'Bar - Spirits & Wine', 'Bar - Non-Alcoholic'))
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1, 2
            HAVING SUM(li.quantity) <= 12
            ORDER BY units_sold ASC, net_revenue ASC
        """
        with self.get_connection() as con:
            df_slow = con.execute(dead_query, dead_stock_params).fetchdf()

        if not df_slow.empty:
            df_slow["recommendation"] = df_slow["units_sold"].apply(
                lambda u: "🛑 Raffle Prize / Clear Out" if u <= 2 else ("⚠️ Discontinue / Delist Line" if u <= 6 else "📉 Reduce Reorder Par-Level")
            )
        else:
            df_slow = pd.DataFrame()

        return df_top, df_slow

    def get_bar_shift_category_mix(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> pd.DataFrame:
        """Returns beverage category velocity across days of the week."""
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                STRFTIME(o.created_at, '%A') AS day_name,
                DAYOFWEEK(o.created_at) AS day_num,
                li.category_name AS category,
                COALESCE(SUM(li.quantity), 0) AS units_sold,
                COALESCE(SUM(li.net_sales_money), 0.0) AS net_sales
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND (li.category_name LIKE 'Bar%' OR li.category_name IN ('Bar - Beer & Cider', 'Bar - Spirits & Wine', 'Bar - Non-Alcoholic'))
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1, 2, 3
            ORDER BY day_num ASC, net_sales DESC
        """
        with self.get_connection() as con:
            return con.execute(query, params).fetchdf()

    # -------------------------------------------------------------
    # Bistro & Kitchen Analytical Queries
    # -------------------------------------------------------------

    def get_kitchen_kpis(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates Bistro & Kitchen Operations KPIs: Meals Served, Food Revenue, Average Check, Lunch vs Dinner split."""
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        # 1. Total Food Revenue, Line Items, and Total Food Orders
        query_totals = f"""
            SELECT
                COUNT(DISTINCT o.order_id) AS food_orders_count,
                COALESCE(SUM(li.quantity), 0) AS total_food_items,
                COALESCE(SUM(li.net_sales_money), 0.0) AS total_kitchen_revenue,
                -- Main Meals count (Mains + Pizzas + Burgers + Steaks + Specials, excluding small sides)
                COALESCE(SUM(CASE 
                    WHEN LOWER(li.name) LIKE '%schnitzel%' 
                      OR LOWER(li.name) LIKE '%steak%' 
                      OR LOWER(li.name) LIKE '%cutlet%' 
                      OR LOWER(li.name) LIKE '%pizza%' 
                      OR LOWER(li.name) LIKE '%burger%' 
                      OR LOWER(li.name) LIKE '%meal%' 
                      OR LOWER(li.name) LIKE '%parmi%' 
                      OR LOWER(li.name) LIKE '%fish%' 
                      OR LOWER(li.name) LIKE '%salmon%' 
                      OR LOWER(li.name) LIKE '%basket%' 
                      OR LOWER(li.name) LIKE '%chook%' 
                      OR LOWER(li.name) LIKE '%special%' 
                      OR LOWER(li.name) LIKE '%salad%' 
                      OR LOWER(li.name) LIKE '%nugget%'
                    THEN li.quantity ELSE 0 END), 0) AS meals_served,
                -- Sides and Starters
                COALESCE(SUM(CASE 
                    WHEN LOWER(li.name) LIKE '%bread%' 
                      OR LOWER(li.name) LIKE '%chip%' 
                      OR LOWER(li.name) LIKE '%wedge%' 
                      OR LOWER(li.name) LIKE '%ring%' 
                      OR LOWER(li.name) LIKE '%fry%' 
                      OR LOWER(li.name) LIKE '%fries%'
                      OR LOWER(li.name) LIKE '%pie%'
                      OR LOWER(li.name) LIKE '%sausage%'
                      OR LOWER(li.name) LIKE '%sundae%'
                    THEN li.quantity ELSE 0 END), 0) AS sides_served
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND li.category_name = 'Bistro & Kitchen'
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
        """

        # 2. Service Window: Lunch (11:30 - 15:00) vs Dinner (17:00 - 21:30)
        query_service = f"""
            SELECT
                CASE 
                    WHEN HOUR(o.created_at) >= 11 AND HOUR(o.created_at) < 16 THEN 'Lunch'
                    WHEN HOUR(o.created_at) >= 17 AND HOUR(o.created_at) < 22 THEN 'Dinner'
                    ELSE 'Other'
                END AS service_window,
                COUNT(DISTINCT o.order_id) AS orders,
                COALESCE(SUM(li.quantity), 0) AS items,
                COALESCE(SUM(li.net_sales_money), 0.0) AS sales
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND li.category_name = 'Bistro & Kitchen'
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1
        """

        with self.get_connection() as con:
            df_tot = con.execute(query_totals, params).fetchdf()
            df_srv = con.execute(query_service, params).fetchdf()

        data = df_tot.iloc[0].to_dict() if not df_tot.empty else {}
        food_rev = data.get("total_kitchen_revenue", 0.0)
        food_orders = data.get("food_orders_count", 0)
        meals_served = data.get("meals_served", 0)

        data["avg_check"] = round(food_rev / food_orders, 2) if food_orders > 0 else 0.0
        data["avg_meal_price"] = round(food_rev / meals_served, 2) if meals_served > 0 else 0.0

        lunch_sales = 0.0
        dinner_sales = 0.0
        lunch_meals = 0
        dinner_meals = 0
        for _, r in df_srv.iterrows():
            if r["service_window"] == "Lunch":
                lunch_sales = float(r["sales"])
                lunch_meals = int(r["items"])
            elif r["service_window"] == "Dinner":
                dinner_sales = float(r["sales"])
                dinner_meals = int(r["items"])

        data["lunch_sales"] = lunch_sales
        data["dinner_sales"] = dinner_sales
        data["lunch_meals"] = lunch_meals
        data["dinner_meals"] = dinner_meals
        tot_srv = lunch_sales + dinner_sales
        data["dinner_pct"] = round((dinner_sales / tot_srv) * 100.0, 1) if tot_srv > 0 else 0.0
        data["lunch_pct"] = round((lunch_sales / tot_srv) * 100.0, 1) if tot_srv > 0 else 0.0

        return data

    def get_kitchen_movement_matrix(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Returns top kitchen food sellers and menu subcategory performance."""
        loc_filter = "AND o.location_id = ?" if location_id and location_id != "ALL" else ""
        params = [start_date, end_date]
        if loc_filter:
            params.append(location_id)

        query = f"""
            SELECT
                li.name AS dish_name,
                CASE 
                    WHEN LOWER(li.name) LIKE '%pizza%' THEN 'Pizza'
                    WHEN LOWER(li.name) LIKE '%burger%' THEN 'Burgers'
                    WHEN LOWER(li.name) LIKE '%schnitzel%' OR LOWER(li.name) LIKE '%parmi%' THEN 'Schnitzels & Poultry'
                    WHEN LOWER(li.name) LIKE '%steak%' OR LOWER(li.name) LIKE '%cutlet%' OR LOWER(li.name) LIKE '%meat fest%' THEN 'Steaks & Meats'
                    WHEN LOWER(li.name) LIKE '%fish%' OR LOWER(li.name) LIKE '%salmon%' OR LOWER(li.name) LIKE '%basket%' OR LOWER(li.name) LIKE '%surf%' THEN 'Seafood'
                    WHEN LOWER(li.name) LIKE '%special%' OR LOWER(li.name) LIKE '%$%' THEN 'Blackboard Specials'
                    WHEN LOWER(li.name) LIKE '%kid%' OR LOWER(li.name) LIKE '%nugget%' THEN 'Kids Meals'
                    ELSE 'Sides, Starters & Snacks'
                END AS course_type,
                COALESCE(SUM(li.quantity), 0) AS qty_sold,
                COALESCE(SUM(li.net_sales_money), 0.0) AS net_revenue,
                ROUND(CASE WHEN SUM(li.quantity) > 0 THEN SUM(li.net_sales_money) / SUM(li.quantity) ELSE 0.0 END, 2) AS avg_price,
                ROUND(COALESCE(SUM(li.net_sales_money), 0.0) * 100.0 / NULLIF(SUM(SUM(li.net_sales_money)) OVER(), 0), 1) AS revenue_share_pct
            FROM order_line_items li
            JOIN orders o ON li.order_id = o.order_id
            WHERE o.created_at >= CAST(? AS TIMESTAMP)
              AND o.created_at <= CAST(? AS TIMESTAMP)
              AND li.category_name = 'Bistro & Kitchen'
              AND o.state IN ('COMPLETED', 'OPEN')
              {loc_filter}
            GROUP BY 1, 2
            ORDER BY qty_sold DESC
        """

        with self.get_connection() as con:
            df = con.execute(query, params).fetchdf()

        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        df_course = df.groupby("course_type").agg(
            dishes_sold=("qty_sold", "sum"),
            revenue=("net_revenue", "sum")
        ).reset_index().sort_values("revenue", ascending=False)
        df_course["revenue_pct"] = round((df_course["revenue"] / df_course["revenue"].sum()) * 100.0, 1)

        return df, df_course
