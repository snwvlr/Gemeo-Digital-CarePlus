"""Portão de acesso por senha (para apresentação em domínio público).

Quando AUTH_ENABLED=true, todo o site e a API ficam protegidos por uma senha
definida em SITE_PASSWORD. O fluxo é:

  1. O usuário acessa qualquer página e é redirecionado para /login.
  2. Envia a senha; se confere, o servidor grava um cookie httpOnly com um
     token derivado de HMAC(segredo, hash_da_senha).
  3. O middleware valida esse cookie em cada requisição.

Por que é resistente a XSS: o cookie é httpOnly, então JavaScript (inclusive
script malicioso injetado) NÃO consegue lê-lo nem exfiltrá-lo. A validação é
feita no servidor; o token não é forjável sem o segredo (AUTH_SECRET).
"""
from __future__ import annotations

import hashlib
import hmac

from .config import get_settings

COOKIE_NAME = "cp_gate"


def _password_hash(password: str) -> str:
    return hashlib.sha256(("careplus::" + password).encode("utf-8")).hexdigest()


def expected_token() -> str:
    """Token esperado no cookie, derivado da senha + segredo do servidor."""
    s = get_settings()
    msg = _password_hash(s.site_password).encode("utf-8")
    return hmac.new(s.auth_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def password_ok(password: str) -> bool:
    s = get_settings()
    if not s.site_password:
        return False
    # comparação em tempo constante
    return hmac.compare_digest(password or "", s.site_password)


def token_ok(token: str | None) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token, expected_token())
