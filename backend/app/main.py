"""Ponto de entrada da API CarePlus - Gemeo Digital.

Cria a aplicacao FastAPI, configura CORS, registra as rotas e serve o frontend
estatico (HTML/CSS/JS) a partir da pasta ../frontend.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .auth import COOKIE_NAME, token_ok
from .config import FRONTEND_DIR, get_settings
from .routers import ai, auth, exams, records, twin, wearables

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

API_DESCRIPTION = """
API do **CarePlus Gemeo Digital**: plataforma de cuidado remoto com check-up
digital, gemeo digital com IA (Google Gemini 2.5 Flash), simulacao de wearables,
exames, consultas e prescricao integrada ao historico.

**Limites de seguranca**
- A IA orienta e alerta, mas **nao diagnostica nem prescreve**.
- Guardrails deterministicos escalam emergencias (SAMU 192 / CVV 188).
- Os endpoints que falam com o Gemini tem **rate limit por IP** (anti-abuso).
- Privacidade: a plataforma nao coleta nem armazena dados de saude do usuario.
"""

OPENAPI_TAGS = [
    {"name": "sistema", "description": "Saude do servico e status geral."},
    {"name": "gemeo-digital", "description": "Estado do gemeo, perfil e emergencia."},
    {"name": "wearables", "description": "Pareamento e leitura de dispositivos (simulado)."},
    {"name": "ia-gemini", "description": "Chat, analise e relatorio (com rate limit anti-abuso)."},
    {"name": "exames", "description": "Paineis laboratoriais e interpretacao por IA."},
    {"name": "registros", "description": "Consultas, prescricoes e historico agregado."},
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    docs_url=None,   # desativa o Swagger padrao; usamos o Scalar em /docs
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Portão de acesso (senha via .env) ---
# Quando habilitado, bloqueia site e API até o login. Cookie httpOnly (anti-XSS).
@app.middleware("http")
async def auth_gate(request: Request, call_next):
    s = get_settings()
    if not (s.auth_enabled and s.site_password):
        return await call_next(request)
    path = request.url.path
    liberado = (
        path == "/login"
        or path.startswith("/api/auth/")
        or path in ("/openapi.json", "/favicon.ico")
    )
    if liberado or token_ok(request.cookies.get(COOKIE_NAME)):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Acesso restrito. Faça login."}, status_code=401)
    return RedirectResponse(url="/login", status_code=302)


# --- Rotas da API ---
app.include_router(auth.router)
app.include_router(wearables.router)
app.include_router(twin.router)
app.include_router(ai.router)
app.include_router(exams.router)
app.include_router(records.router)


_SCALAR_HTML = """<!doctype html>
<html><head>
  <title>CarePlus API · Documentação</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link rel="icon" href="data:,"/>
  <style> body { margin: 0; } </style>
</head>
<body>
  <script id="api-reference" data-url="/openapi.json"></script>
  <script>
    document.getElementById("api-reference").dataset.configuration = JSON.stringify({
      theme: "purple",
      layout: "modern",
      hideDownloadButton: false,
      metaData: { title: "CarePlus Gemeo Digital - API" }
    });
  </script>
  <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
</body></html>"""


@app.get("/docs", include_in_schema=False)
def docs_scalar() -> HTMLResponse:
    """Documentação interativa da API com o visual do Scalar (em /docs)."""
    return HTMLResponse(content=_SCALAR_HTML)


@app.get("/scalar", include_in_schema=False)
def scalar_alias() -> HTMLResponse:
    """Alias de /docs."""
    return HTMLResponse(content=_SCALAR_HTML)


_LOGIN_HTML = """<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>CarePlus · Acesso</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap" rel="stylesheet"/>
<style>
  *{box-sizing:border-box;font-family:'Inter',sans-serif}
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b1120;color:#e2e8f0}
  .card{width:100%;max-width:360px;background:#0f172a;border:1px solid rgba(148,163,184,.18);border-radius:18px;padding:28px;box-shadow:0 30px 60px -30px rgba(17,82,212,.6)}
  .brand{display:flex;align-items:center;gap:.5rem;color:#3b82f6;font-weight:800;margin-bottom:.2rem}
  h1{font-size:1.2rem;margin:.4rem 0 .2rem}
  p{color:#94a3b8;font-size:.85rem;margin:0 0 1.2rem}
  label{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8}
  input{width:100%;margin-top:.4rem;padding:.7rem .9rem;border-radius:.7rem;background:#1e293b;border:1px solid #334155;color:#fff;font-size:.95rem}
  input:focus{outline:none;border-color:#1152d4}
  button{width:100%;margin-top:1rem;padding:.8rem;border:0;border-radius:.7rem;background:#1152d4;color:#fff;font-weight:800;font-size:.9rem;cursor:pointer}
  button:hover{background:#0e44b0}
  .err{color:#f87171;font-size:.8rem;margin-top:.7rem;min-height:1rem}
</style></head>
<body>
  <form class="card" id="f">
    <div class="brand"><span style="font-size:20px">＋</span> CarePlus</div>
    <h1>Acesso restrito</h1>
    <p>Esta demonstração é privada. Digite a senha para continuar.</p>
    <label for="pw">Senha</label>
    <input id="pw" type="password" autocomplete="current-password" autofocus/>
    <button type="submit">Entrar</button>
    <div class="err" id="err"></div>
  </form>
  <script>
    document.getElementById("f").addEventListener("submit", async function(e){
      e.preventDefault();
      const err = document.getElementById("err"); err.textContent = "";
      try {
        const r = await fetch("/api/auth/login", {method:"POST",headers:{"Content-Type":"application/json"},
          body: JSON.stringify({password: document.getElementById("pw").value})});
        if (r.ok) { window.location.href = "/"; }
        else { err.textContent = "Senha incorreta."; }
      } catch (e) { err.textContent = "Erro ao conectar."; }
    });
  </script>
</body></html>"""


@app.get("/login", include_in_schema=False)
def login_page() -> HTMLResponse:
    return HTMLResponse(content=_LOGIN_HTML)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    # Evita o 404 do favicon (o navegador pede automaticamente).
    return Response(status_code=204)


@app.get("/api/health", tags=["sistema"])
def health_check() -> dict:
    """Verificacao de saude do servico."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "gemini_enabled": settings.gemini_enabled,
        "model": settings.gemini_model,
    }


# --- Frontend estatico ---
# Montado na RAIZ (por ultimo) para que os caminhos relativos do frontend
# (assets/css, assets/js, *.html) resolvam corretamente. As rotas /api e /docs
# sao registradas antes e tem prioridade na resolucao.
_frontend_ready = FRONTEND_DIR.exists()
if _frontend_ready:
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    logging.warning("Pasta frontend nao encontrada em %s", FRONTEND_DIR)

# fim do modulo
