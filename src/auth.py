import hashlib
import hmac
import re
import secrets
from typing import Tuple

# OWASP 2025/2026 Password Storage Standard for PBKDF2-HMAC-SHA256
PBKDF2_ITERATIONS = 600_000
LEGACY_ITERATIONS = 100_000

# Precomputed dummy salt & hash for constant-time timing-attack defense when username is unknown
_DUMMY_SALT = secrets.token_hex(16)
_DUMMY_HASH = hashlib.pbkdf2_hmac(
    "sha256",
    b"uhsc_constant_time_dummy_secret",
    _DUMMY_SALT.encode("utf-8"),
    PBKDF2_ITERATIONS,
).hex()


def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """Generates a secure PBKDF2-HMAC-SHA256 salted hash with 600,000 iterations (stored as v2$600000$<hex>)."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"v2${PBKDF2_ITERATIONS}${dk.hex()}", salt


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    """
    Verifies password using constant-time comparison.
    Supports both OWASP v2 (600,000 iterations) and legacy (100,000 iterations) hashes.
    """
    if not password or not expected_hash or not salt:
        dummy_verify(password or "invalid")
        return False

    if expected_hash.startswith("v2$"):
        parts = expected_hash.split("$")
        if len(parts) == 3:
            try:
                iterations = int(parts[1])
                raw_expected = parts[2]
            except ValueError:
                dummy_verify(password)
                return False
        else:
            dummy_verify(password)
            return False
    else:
        iterations = LEGACY_ITERATIONS
        raw_expected = expected_hash

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(dk.hex(), raw_expected)


def is_legacy_hash(expected_hash: str) -> bool:
    """Returns True if the stored password hash uses legacy (<600k) iterations."""
    return not (expected_hash and expected_hash.startswith(f"v2${PBKDF2_ITERATIONS}$"))


def dummy_verify(password: str = "dummy_input") -> bool:
    """Executes a full 600,000-iteration PBKDF2 calculation to prevent username enumeration via timing attacks."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _DUMMY_SALT.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(dk.hex(), _DUMMY_HASH)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Enforces minimum password complexity standards for club governance accounts."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if password.strip().lower() in ("admin", "password", "12345678", "upperhorton", "qwertyui"):
        return False, "Password is too common. Please choose a stronger passphrase."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
        return False, "Password must contain both letters and at least one number or symbol."
    return True, "Valid password."
