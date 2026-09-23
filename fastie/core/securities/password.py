import logging

import bcrypt

logger = logging.getLogger(__name__)


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password cannot exceed 72 UTF-8 bytes")
    return encoded


def __hash_password__(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")

def __verify_password__(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password),
            hashed_password.encode("ascii"),
        )
    except Exception:
        logger.exception("Password verification failed")
        return False
