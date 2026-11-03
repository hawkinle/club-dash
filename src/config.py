import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def get_config_val(key: str, default: str = "") -> str:
    """Retrieves config from st.secrets (Streamlit Cloud) first if present, then os.getenv, then default."""
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(DATA_DIR, 0o700)
except OSError:
    pass

# Configuration settings
SQUARE_ENVIRONMENT = get_config_val("SQUARE_ENVIRONMENT", "sandbox").lower()
SQUARE_ACCESS_TOKEN = get_config_val("SQUARE_ACCESS_TOKEN", "")
SQUARE_LOCATION_ID = get_config_val("SQUARE_LOCATION_ID", "")

# Optional OAuth 2.0 Scoped Token & Rotation Credentials
SQUARE_APPLICATION_ID = get_config_val("SQUARE_APPLICATION_ID", "")
SQUARE_APPLICATION_SECRET = get_config_val("SQUARE_APPLICATION_SECRET", "")
SQUARE_REFRESH_TOKEN = get_config_val("SQUARE_REFRESH_TOKEN", "")

# Database paths
DATABASE_PATH = get_config_val("DATABASE_PATH", str(DATA_DIR / "club_sales.duckdb"))
CLUB_NAME = get_config_val("CLUB_NAME", "Upper Horton Sports Club")

# Mock data toggle
USE_MOCK = get_config_val("USE_MOCK", "false").lower() in ("true", "1", "yes")

# Required Read-Only OAuth Scopes for Least-Privilege Operation
REQUIRED_READ_ONLY_SCOPES = (
    "MERCHANT_PROFILE_READ",
    "ITEMS_READ",
    "ORDERS_READ",
    "PAYMENTS_READ",
)


def is_square_configured() -> bool:
    """Check if Square access token is configured."""
    return bool(SQUARE_ACCESS_TOKEN and not SQUARE_ACCESS_TOKEN.startswith("your_"))


def mask_secret(secret: str) -> str:
    """Masks sensitive API or OAuth tokens so they are never exposed in UI or logs."""
    if not secret or len(secret) < 10:
        return "••••••••"
    return f"{secret[:4]}••••••••{secret[-4:]}"
