import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from action_platform.api.auth.secrets import Secrets

LEGACY_SALT = b"action-platform:source-host"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class Sealer:
    """AES-256-GCM over the `source-host` subkey, in the `v2.iv.tag.data` shape the web app writes; `v1` (scrypt key) is still readable."""

    def __init__(self, secrets: Secrets) -> None:
        self.key = secrets.subkey("source-host")
        self.secret = secrets.secret

    def seal(self, plain: str) -> str:
        iv = os.urandom(12)
        sealed = AESGCM(self.key).encrypt(iv, plain.encode(), None)

        return ".".join(["v2", _b64(iv), _b64(sealed[-16:]), _b64(sealed[:-16])])

    def open(self, sealed: str) -> str:
        version, iv, tag, data = sealed.split(".")

        if version == "v1":
            key = hashlib.scrypt(
                self.secret, salt=LEGACY_SALT, n=16384, r=8, p=1, dklen=32
            )
        elif version == "v2":
            key = self.key
        else:
            raise ValueError("unknown ciphertext version")

        return (
            AESGCM(key).decrypt(_unb64(iv), _unb64(data) + _unb64(tag), None).decode()
        )
