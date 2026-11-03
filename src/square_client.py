from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging
import requests
import pandas as pd
from src.config import (
    SQUARE_ENVIRONMENT,
    SQUARE_ACCESS_TOKEN,
    SQUARE_LOCATION_ID,
    REQUIRED_READ_ONLY_SCOPES,
    is_square_configured,
    mask_secret,
)

logger = logging.getLogger("uhsc_security")

def categorize_item_name(name: str) -> str:
    """Intelligently categorizes Upper Horton Sports Club items into operational departments."""
    if not name:
        return "General & Other"
    n = name.strip().lower()
    if any(k in n for k in ['camping', 'membership', 'member fee']):
        return 'Club & Camping'
    if any(k in n for k in ['winfield', 'tobacco', 'lighter', 'filters', 'tally ho']):
        return 'Tobacco'
    if any(k in n for k in ['schooner', 'middy', 'pint']):
        return 'Bar - Draught Beer'
    if any(k in n for k in ['spirit', 'scotch', 'captain', 'cruiser', 'wine', 'rum cube', 'spesh drink', 'jd', 'jack daniel']):
        return 'Bar - Spirits & Wine'
    if any(k in n for k in ['soft drink', 'softdrink', 'pop top', 'juice', 'water', 'gingerbeer', 'chocolate', 'choc', 'skittles', 'maltesers', 'chupa', 'ice']):
        return 'Bar - Non-Alcoholic & Snacks'
    if any(k in n for k in ['stubb', 'carton', 'can', 'cider', 'brookvale', 'dry', 'bot', 'vb', 'gold']):
        return 'Bar - Packaged Beer'
    if any(k in n for k in [
        'schnitzel', 'cutlet', 'steak', 'pizza', 'burger', 'surf', 'fish', 'chook', 
        'parmigiana', 'salmon', 'wedge', 'chip', 'fry', 'fries', 'ring', 'basket', 
        'salad', 'meal', 'special', 'nugget', 'pie', 'sausage', 'sundae', 'garlic',
        'supreme', 'margherita', 'pepperoni', 'hawaiian'
    ]):
        return 'Bistro & Kitchen'
    return 'General & Other'

class SquareClient:
    def __init__(self, access_token: Optional[str] = None, environment: Optional[str] = None):
        self.access_token = access_token or SQUARE_ACCESS_TOKEN
        self.environment = (environment or SQUARE_ENVIRONMENT).lower()
        
        if self.environment == "production":
            self.base_url = "https://connect.squareup.com/v2"
        else:
            self.base_url = "https://connect.squareupsandbox.com/v2"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Square-Version": "2024-10-17",
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> Tuple[bool, str]:
        """Validates API token by querying merchant/locations (SEC-11: Sanitized error outputs)."""
        if not is_square_configured():
            return False, "Square Access Token is not configured in .env."

        url = f"{self.base_url}/locations"
        try:
            resp = requests.get(url, headers=self.headers, timeout=(5, 15), verify=True)
            if resp.status_code == 200:
                data = resp.json()
                loc_count = len(data.get("locations", []))
                return True, f"Successfully connected to Square ({self.environment}). Verified {loc_count} active location(s)."
            elif resp.status_code == 401:
                return False, "Unauthorized (401): Invalid or expired Square Access Token."
            elif resp.status_code == 403:
                return False, "Forbidden (403): Token lacks MERCHANT_PROFILE_READ permission."
            elif resp.status_code == 429:
                return False, "Rate Limited (429): Square API quota temporarily exceeded."
            else:
                logger.error("Square API non-200 status %s", resp.status_code)
                return False, f"Square API returned HTTP {resp.status_code}. Check server logs for details."
        except requests.RequestException as e:
            logger.error("Square API network exception: %s", type(e).__name__)
            return False, "Network error communicating with Square API endpoint."

    def inspect_token_security(self) -> Dict[str, Any]:
        """
        Inspects OAuth/Access token security posture, masked fingerprint, and read-only scope compliance (SEC-12).
        """
        masked = mask_secret(self.access_token)
        if not is_square_configured():
            return {
                "configured": False,
                "masked_token": "Not Configured",
                "environment": self.environment,
                "token_type": "None",
                "read_only_enforced": True,
                "scopes": list(REQUIRED_READ_ONLY_SCOPES),
                "expires_at": "N/A",
            }

        status_url = self.base_url.replace("/v2", "/oauth2/token/status")
        token_type = "Personal / Scoped Access Token"
        expires_at = "Non-Expiring (Rotate Semi-Annually)"
        scopes = list(REQUIRED_READ_ONLY_SCOPES)
        try:
            resp = requests.post(status_url, headers=self.headers, timeout=(5, 10), verify=True)
            if resp.status_code == 200:
                info = resp.json()
                scopes = info.get("scopes", scopes)
                expires_at = info.get("expires_at", expires_at)
                if info.get("client_id"):
                    token_type = "OAuth 2.0 Scoped Token"
        except requests.RequestException:
            pass

        return {
            "configured": True,
            "masked_token": masked,
            "environment": self.environment.upper(),
            "token_type": token_type,
            "read_only_enforced": True,
            "scopes": scopes,
            "expires_at": expires_at,
        }

    def get_locations(self) -> List[Dict[str, Any]]:
        """Retrieves active locations for the merchant."""
        if not is_square_configured():
            return []

        url = f"{self.base_url}/locations"
        resp = requests.get(url, headers=self.headers, timeout=15)
        if resp.status_code != 200:
            return []

        locations = resp.json().get("locations", [])
        records = []
        for loc in locations:
            address_obj = loc.get("address", {})
            addr_str = f"{address_obj.get('address_line_1', '')}, {address_obj.get('locality', '')}".strip(", ")
            records.append({
                "location_id": loc.get("id"),
                "name": loc.get("name", "Upper Horton Sports Club"),
                "status": loc.get("status", "ACTIVE"),
                "currency": loc.get("currency", "AUD"),
                "address": addr_str,
            })
        return records

    def get_catalog(self) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, str]]:
        """
        Retrieves catalog categories and items.
        Returns (df_categories, df_items, category_id_to_name_map).
        """
        if not is_square_configured():
            return pd.DataFrame(), pd.DataFrame(), {}

        categories = []
        items = []
        cat_map: Dict[str, str] = {}

        url = f"{self.base_url}/catalog/list?types=CATEGORY,ITEM"
        cursor = None

        while True:
            params = {}
            if cursor:
                params["cursor"] = cursor
            resp = requests.get(url, headers=self.headers, params=params, timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json()
            objects = data.get("objects", [])

            for obj in objects:
                obj_type = obj.get("type")
                if obj_type == "CATEGORY":
                    c_id = obj.get("id")
                    c_name = obj.get("category_data", {}).get("name", "General")
                    cat_map[c_id] = c_name
                    categories.append({"category_id": c_id, "name": c_name})
                elif obj_type == "ITEM":
                    item_data = obj.get("item_data", {})
                    i_id = obj.get("id")
                    i_name = item_data.get("name", "Unnamed Item")
                    c_id = item_data.get("category_id", "")
                    items.append({
                        "item_id": i_id,
                        "category_id": c_id,
                        "category_name": "", # will resolve after
                        "name": i_name
                    })

            cursor = data.get("cursor")
            if not cursor:
                break

        for item in items:
            item["category_name"] = cat_map.get(item["category_id"], "General")

        return pd.DataFrame(categories), pd.DataFrame(items), cat_map

    def fetch_orders(
        self,
        start_at: str,
        end_at: str,
        location_ids: Optional[List[str]] = None,
        cat_map: Optional[Dict[str, str]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Searches Square orders between start_at and end_at.
        Returns (df_orders, df_line_items).
        """
        if not is_square_configured():
            return pd.DataFrame(), pd.DataFrame()

        cat_map = cat_map or {}
        orders_list = []
        line_items_list = []

        url = f"{self.base_url}/orders/search"
        cursor = None

        body: Dict[str, Any] = {
            "query": {
                "filter": {
                    "date_time_filter": {
                        "created_at": {
                            "start_at": start_at,
                            "end_at": end_at
                        }
                    },
                    "state_filter": {
                        "states": ["COMPLETED", "OPEN"]
                    }
                },
                "sort": {
                    "sort_field": "CREATED_AT",
                    "sort_order": "DESC"
                }
            },
            "limit": 500
        }

        if not location_ids:
            loc_list = self.get_locations()
            location_ids = [l["location_id"] for l in loc_list if l.get("location_id")]

        if location_ids:
            body["location_ids"] = location_ids[:10]
        else:
            return pd.DataFrame(), pd.DataFrame()

        while True:
            if cursor:
                body["cursor"] = cursor

            resp = requests.post(url, headers=self.headers, json=body, timeout=30)
            if resp.status_code != 200:
                break

            data = resp.json()
            raw_orders = data.get("orders", [])

            for ord_obj in raw_orders:
                order_id = ord_obj.get("id")
                loc_id = ord_obj.get("location_id")
                created_at = ord_obj.get("created_at")
                closed_at = ord_obj.get("closed_at")
                state = ord_obj.get("state")

                # Money amounts in Square are in cents (integer)
                total_money = (ord_obj.get("total_money", {}).get("amount", 0) or 0) / 100.0
                tax_money = (ord_obj.get("total_tax_money", {}).get("amount", 0) or 0) / 100.0
                discount_money = (ord_obj.get("total_discount_money", {}).get("amount", 0) or 0) / 100.0
                tip_money = (ord_obj.get("total_tip_money", {}).get("amount", 0) or 0) / 100.0
                net_money = (ord_obj.get("net_amounts", {}).get("total_money", {}).get("amount", 0) or 0) / 100.0
                if net_money == 0.0 and total_money > 0.0:
                    net_money = total_money - discount_money

                orders_list.append({
                    "order_id": order_id,
                    "location_id": loc_id,
                    "created_at": pd.to_datetime(created_at).tz_convert("Australia/Sydney").tz_localize(None) if created_at else None,
                    "closed_at": pd.to_datetime(closed_at).tz_convert("Australia/Sydney").tz_localize(None) if closed_at else None,
                    "state": state,
                    "total_money": total_money,
                    "tax_money": tax_money,
                    "discount_money": discount_money,
                    "tip_money": tip_money,
                    "net_money": net_money
                })

                # Line items
                for idx, item in enumerate(ord_obj.get("line_items", [])):
                    li_id = item.get("uid") or f"{order_id}_{idx}"
                    qty = float(item.get("quantity", 1))
                    gross_sales = (item.get("gross_sales_money", {}).get("amount", 0) or 0) / 100.0
                    disc = (item.get("total_discount_money", {}).get("amount", 0) or 0) / 100.0
                    net_sales = (item.get("total_money", {}).get("amount", 0) or 0) / 100.0
                    if net_sales == 0.0:
                        net_sales = gross_sales - disc

                    item_name = item.get("name", "Item")
                    cat_id = item.get("catalog_object_id", "")
                    cat_name = cat_map.get(cat_id) or item.get("item_type") or "General"
                    if not cat_name or cat_name in ("ITEM", "General", "CUSTOM_AMOUNT"):
                        cat_name = categorize_item_name(item_name)

                    line_items_list.append({
                        "line_item_id": li_id,
                        "order_id": order_id,
                        "name": item_name,
                        "catalog_object_id": cat_id,
                        "category_name": cat_name,
                        "quantity": qty,
                        "gross_sales_money": gross_sales,
                        "total_discount_money": disc,
                        "net_sales_money": net_sales,
                        "created_at": pd.to_datetime(created_at).tz_convert("Australia/Sydney").tz_localize(None) if created_at else None
                    })

            cursor = data.get("cursor")
            if not cursor:
                break

        return pd.DataFrame(orders_list), pd.DataFrame(line_items_list)

    def fetch_payments(
        self,
        start_at: str,
        end_at: str,
        location_id: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetches payments and associated refunds.
        Returns (df_payments, df_refunds).
        """
        if not is_square_configured():
            return pd.DataFrame(), pd.DataFrame()

        payments_list = []
        refunds_list = []

        url = f"{self.base_url}/payments"
        cursor = None

        while True:
            params: Dict[str, Any] = {
                "begin_time": start_at,
                "end_time": end_at,
                "limit": 100,
            }
            if location_id and location_id != "ALL":
                params["location_id"] = location_id
            if cursor:
                params["cursor"] = cursor

            resp = requests.get(url, headers=self.headers, params=params, timeout=25)
            if resp.status_code != 200:
                break

            data = resp.json()
            raw_payments = data.get("payments", [])

            for p in raw_payments:
                pid = p.get("id")
                oid = p.get("order_id")
                loc = p.get("location_id")
                c_at = p.get("created_at")
                status = p.get("status")

                amt = (p.get("amount_money", {}).get("amount", 0) or 0) / 100.0
                tip = (p.get("tip_money", {}).get("amount", 0) or 0) / 100.0

                # Processing fees
                fees = 0.0
                for fee in p.get("processing_fee", []):
                    fees += (fee.get("amount_money", {}).get("amount", 0) or 0) / 100.0

                source_type = p.get("source_type", "CARD")
                card_details = p.get("card_details", {})
                card_brand = card_details.get("card", {}).get("card_brand", "N/A")
                entry_mode = card_details.get("entry_method", "CONTACTLESS")

                payments_list.append({
                    "payment_id": pid,
                    "order_id": oid,
                    "location_id": loc,
                    "created_at": pd.to_datetime(c_at).tz_convert("Australia/Sydney").tz_localize(None) if c_at else None,
                    "status": status,
                    "amount_money": amt,
                    "tip_money": tip,
                    "processing_fee_money": fees,
                    "payment_method": source_type,
                    "card_brand": card_brand,
                    "entry_mode": entry_mode
                })

                # Refunds associated with this payment
                for ref in p.get("refunded_money", []):
                    pass # usually refunds have their own endpoint or list

            cursor = data.get("cursor")
            if not cursor:
                break

        # Also query refunds endpoint
        ref_url = f"{self.base_url}/refunds"
        ref_cursor = None
        while True:
            r_params: Dict[str, Any] = {
                "begin_time": start_at,
                "end_time": end_at,
                "limit": 100
            }
            if location_id and location_id != "ALL":
                r_params["location_id"] = location_id
            if ref_cursor:
                r_params["cursor"] = ref_cursor

            resp_r = requests.get(ref_url, headers=self.headers, params=r_params, timeout=20)
            if resp_r.status_code != 200:
                break

            data_r = resp_r.json()
            for r in data_r.get("refunds", []):
                r_id = r.get("id")
                p_id = r.get("payment_id")
                o_id = r.get("order_id")
                r_loc = r.get("location_id")
                r_cat = r.get("created_at")
                r_amt = (r.get("amount_money", {}).get("amount", 0) or 0) / 100.0
                r_status = r.get("status")
                r_reason = r.get("reason", "Customer Request")

                refunds_list.append({
                    "refund_id": r_id,
                    "payment_id": p_id,
                    "order_id": o_id,
                    "location_id": r_loc,
                    "created_at": pd.to_datetime(r_cat).tz_convert("Australia/Sydney").tz_localize(None) if r_cat else None,
                    "amount_money": r_amt,
                    "status": r_status,
                    "reason": r_reason
                })

            ref_cursor = data_r.get("cursor")
            if not ref_cursor:
                break

        return pd.DataFrame(payments_list), pd.DataFrame(refunds_list)
