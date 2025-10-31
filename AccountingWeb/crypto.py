import base64, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import Type, hash_secret_raw

# Tunables chosen for server-side derivation security; adjust per your hardware
_ARGON_T = 3          # iterations
_ARGON_M = 64 * 1024  # memory in KiB (64 MB)
_ARGON_P = 1          # parallelism
_KEK_LEN = 32

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode('ascii')

def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode('ascii'))

def new_salt(n=16) -> str:
    return b64e(os.urandom(n))

def new_dek() -> bytes:
    return os.urandom(32)  # 256-bit DEK

def derive_kek_from_password(password: str, salt_b64: str) -> bytes:
    # Argon2id (tweak params for your infra if needed)
    salt = b64d(salt_b64)
    return hash_secret_raw(
        password.encode('utf-8'), salt,
        time_cost=2, memory_cost=102400, parallelism=8,
        hash_len=32, type=Type.ID
    )

def aesgcm_encrypt(key: bytes, plaintext: bytes) -> tuple[str, str]:
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, plaintext, None)
    return b64e(ct), b64e(iv)

def aesgcm_decrypt(key: bytes, ct_b64: str, iv_b64: str) -> bytes:
    return AESGCM(key).decrypt(b64d(iv_b64), b64d(ct_b64), None)

# Tiny field helpers
def enc_str(dek: bytes, s: str | None):
    if s is None:
        return None, None
    return aesgcm_encrypt(dek, s.encode('utf-8'))

def dec_str(dek: bytes, ct_b64: str | None, iv_b64: str | None) -> str | None:
    if not ct_b64 or not iv_b64:
        return None
    return aesgcm_decrypt(dek, ct_b64, iv_b64).decode('utf-8')

def enc_decimal(dek: bytes, d) -> tuple[str|None, str|None]:
    if d is None:
        return None, None
    # store canonical string (so we keep exact cents) and encrypt
    s = str(d)
    return aesgcm_encrypt(dek, s.encode("utf-8"))

def dec_decimal(dek: bytes, ct_b64: str | None, iv_b64: str | None):
    if not ct_b64 or not iv_b64:
        return None
    from decimal import Decimal
    s = aesgcm_decrypt(dek, ct_b64, iv_b64).decode("utf-8")
    return Decimal(s)

def decrypt_tx(tx, dek: bytes):
    if tx.description_ct and tx.description_iv:
        tx.description = dec_str(dek, tx.description_ct, tx.description_iv) or ''
    if tx.dollar_amount_ct and tx.dollar_amount_iv:
        tx.dollar_amount = dec_decimal(dek, tx.dollar_amount_ct, tx.dollar_amount_iv)
    return tx
