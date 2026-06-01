"""Ponto de entrada para hospedagem (Pterodactyl e similares).

O painel Pterodactyl roda `python /home/container/app.py`. Este arquivo sobe a
API FastAPI (que também serve o frontend) usando uvicorn, escutando em
0.0.0.0 na porta fornecida pelo painel (SERVER_PORT) ou pela variável PORT.

Propriedade exclusiva de João Vitor Anunciação Oliveira (snwvlr).
Uso somente com autorização: https://github.com/snwvlr
"""
from __future__ import annotations

import os
import sys

# Garante que o pacote do backend (backend/app) seja importável.
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(HERE, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def _port() -> int:
    for var in ("SERVER_PORT", "PORT", "APP_PORT"):
        val = os.environ.get(var)
        if val and val.isdigit():
            return int(val)
    return 8000


if __name__ == "__main__":
    import uvicorn
    from app.main import app  # backend/app/main.py

    host = os.environ.get("HOST", "0.0.0.0")
    port = _port()
    print(f"[CarePlus] Iniciando em http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)
