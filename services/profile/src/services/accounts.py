import hashlib
import hmac
import os

from ..repositories import store


def register(email, password):
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 << 20
    )
    return store.register(email.casefold(), f"scrypt:{salt.hex()}:{digest.hex()}")


def authenticate(email, password):
    user = store.user(email.casefold())
    if user:
        _, salt, digest = user["hash"].split(":")
        check = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=2**15,
            r=8,
            p=1,
            maxmem=64 << 20,
        )
        if hmac.compare_digest(check.hex(), digest):
            return {"id": user["id"], "email": user["email"]}
    return None
