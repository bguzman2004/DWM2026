"""Contraseñas con hash (PBKDF2-HMAC-SHA256 con sal) para el Authentication Service.

Para agregar un usuario, genera su hash con:  python auth_passwords.py
y pega el resultado en USERS (auth-service.py).
"""
import hashlib
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000


def hash_password(password: str, sal: bytes | None = None, iteraciones: int = ITERACIONES) -> str:
    sal = sal if sal is not None else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, iteraciones)
    return f"{ALGORITMO}${iteraciones}${sal.hex()}${digest.hex()}"


def verify_password(password: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones, sal_hex, digest_hex = guardado.split("$")
        if algoritmo != ALGORITMO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(sal_hex), int(iteraciones)
        )
        esperado = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(digest, esperado)


if __name__ == "__main__":
    import getpass

    print(hash_password(getpass.getpass("Contraseña: ")))
