"""Genera el hash argon2 de la contraseña del usuario y una clave para firmar los JWT.

Uso: python backend/scripts/hash_password.py
La contraseña se pide de forma oculta y no queda en ningún archivo ni en el historial.
"""

import secrets
from getpass import getpass

from argon2 import PasswordHasher

password = getpass("Contraseña: ")
if password != getpass("Repita la contraseña: "):
    raise SystemExit("Las contraseñas no coinciden.")

print(f"AUTH_PASSWORD_HASH='{PasswordHasher().hash(password)}'")
print(f"JWT_SECRET='{secrets.token_urlsafe(48)}'")
