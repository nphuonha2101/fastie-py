"""Password hashing helpers backed by pwdlib's recommended Argon2 setup."""

import logging

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

logger = logging.getLogger(__name__)
# Argon2 is the only supported password hash for new applications.
password_hash = PasswordHash((Argon2Hasher(),))


def __hash_password__(password: str) -> str:
    """Hash a user password with Argon2."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    if not password:
        raise ValueError("Password cannot be empty")
    return password_hash.hash(password)


def __verify_password__(plain_password: str, hashed_password: str) -> bool:
    """Verify a password without leaking hash parsing details to callers."""
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (TypeError, ValueError, UnknownHashError):
        logger.warning("Password verification failed for an unsupported hash")
        return False


def verify_password_and_upgrade(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Verify a password and return a stronger replacement hash when needed."""
    try:
        return password_hash.verify_and_update(plain_password, hashed_password)
    except (TypeError, ValueError, UnknownHashError):
        logger.warning("Password verification failed for an unsupported hash")
        return False, None
