"""Rotas do portão de acesso (login por senha)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from ..auth import COOKIE_NAME, expected_token, password_ok
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["acesso"])


class LoginRequest(BaseModel):
    password: str


@router.get("/status")
def auth_status() -> dict:
    return {"enabled": get_settings().auth_enabled and bool(get_settings().site_password)}


@router.post("/login")
def login(req: LoginRequest, response: Response) -> dict:
    if not password_ok(req.password):
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    # Cookie httpOnly: JavaScript não consegue ler (resistente a XSS).
    response.set_cookie(
        key=COOKIE_NAME,
        value=expected_token(),
        httponly=True,
        samesite="strict",
        max_age=60 * 60 * 8,  # 8 horas
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
