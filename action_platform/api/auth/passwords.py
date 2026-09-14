import hashlib
import hmac
import secrets
import unicodedata

N, R, P, LENGTH = 16384, 16, 1, 64
MAXMEM = 128 * N * R * 2


def _key(password: str, salt: str) -> str:
    normalized = unicodedata.normalize("NFKC", password).encode()
    return hashlib.scrypt(
        normalized, salt=salt.encode(), n=N, r=R, p=P, dklen=LENGTH, maxmem=MAXMEM
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}:{_key(password, salt)}"


def verify_password(stored: str | None, password: str) -> bool:
    salt, sep, key = (stored or "").partition(":")
    if not sep or not salt or not key:
        return False
    return hmac.compare_digest(_key(password, salt), key)
