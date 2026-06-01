"""Rate limiting simples (anti-abuso) para os endpoints que chamam o Gemini.

Objetivo: evitar que a API que se comunica com o Gemini seja abusada (muitas
chamadas em sequência consumindo a cota/custo da chave). NÃO é uma trava no
conteúdo do chat, e sim um limite de frequência por IP, em janela fixa.

Implementação em memória (suficiente para um protótipo). Em produção, o ideal
seria um backend compartilhado (ex.: Redis) e autenticação por usuário.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from .config import get_settings

_hits: dict[str, list[float]] = defaultdict(list)


def ai_rate_limit(request: Request) -> None:
    """Dependency: limita chamadas à IA por IP. Lança 429 se exceder."""
    settings = get_settings()
    ip = request.client.host if request.client else "anon"
    now = time.time()
    janela = settings.ai_rate_window_seconds

    recentes = [t for t in _hits[ip] if now - t < janela]
    if len(recentes) >= settings.ai_rate_max:
        espera = int(janela - (now - recentes[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=(f"Limite de uso da IA atingido ({settings.ai_rate_max} por "
                    f"{janela}s). Aguarde {espera}s e tente novamente."),
            headers={"Retry-After": str(espera)},
        )
    recentes.append(now)
    _hits[ip] = recentes
