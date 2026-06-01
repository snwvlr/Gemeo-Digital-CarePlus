"""Configuração central da aplicação.

Carrega variáveis de ambiente (arquivo .env) usando pydantic-settings.
Nenhum segredo é escrito no código; a chave da API vem sempre do ambiente.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do projeto (… / Dash_Avatar_CarePlus)
BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"


class Settings(BaseSettings):
    """Configurações lidas de variáveis de ambiente / arquivo .env."""

    # Lê variáveis do ambiente e, se existirem, de um .env na raiz ou em backend/.
    # (No Pterodactyl é mais fácil criar /home/container/.env.)
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Aplicação ---
    app_name: str = "CarePlus Gêmeo Digital API"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- Google Gemini ---
    # Obtenha a chave em https://aistudio.google.com/apikey
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.7
    gemini_max_output_tokens: int = 2048

    # --- CORS ---
    cors_origins: list[str] = ["*"]

    # --- Proteção da API de IA (anti-abuso) ---
    # Limita quantas chamadas que falam com o Gemini um mesmo IP pode fazer.
    ai_rate_max: int = 20            # requisições
    ai_rate_window_seconds: int = 60  # por janela de tempo

    # --- Portão de acesso ao site (para apresentação em domínio público) ---
    # Quando AUTH_ENABLED=true, o site pede senha (SITE_PASSWORD) antes de abrir.
    # A senha vira um token via hash + segredo, guardado em cookie httpOnly
    # (não acessível por JavaScript, resistente a XSS).
    auth_enabled: bool = False
    site_password: str = ""
    auth_secret: str = "careplus-altere-este-segredo"

    @property
    def gemini_enabled(self) -> bool:
        """True quando há chave configurada (caso contrário roda em modo demo)."""
        return bool(self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância única (cacheada) das configurações."""
    return Settings()
