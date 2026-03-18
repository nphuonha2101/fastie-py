from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def __hash_password__(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def __verify_password__(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print("Error verifying password:", str(e))
        return False