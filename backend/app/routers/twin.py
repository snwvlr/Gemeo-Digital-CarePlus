"""Rotas do Gêmeo Digital: estado atual e perfil do paciente."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..schemas import PatientProfile, TwinState
from ..services import clinical
from ..services.records import records_service
from ..services.twin_state import twin_engine
from ..services.wearables import simulator

router = APIRouter(prefix="/api/twin", tags=["gemeo-digital"])


class RelatoInput(BaseModel):
    message: str
    source: str = "paciente"  # "paciente" (chat) ou "medico" (inserido no painel)


@router.get("/state", response_model=TwinState)
def twin_state() -> TwinState:
    """Estado atual do gêmeo digital, derivado dos sinais vitais."""
    vitals = simulator.aggregate_vitals()
    return twin_engine.compute_state(vitals)


@router.get("/emergency")
def emergency() -> dict:
    """Avaliação inteligente de emergência (pronto-socorro vs telemedicina)."""
    vitals = simulator.aggregate_vitals()
    assessment = twin_engine.emergency_assessment(vitals, twin_engine.profile.symptoms)
    return assessment


@router.post("/telemedicine")
def request_telemedicine() -> dict:
    """Solicita uma teleconsulta (simulada)."""
    import random
    return {
        "success": True,
        "protocol": f"TLM-{random.randint(10000, 99999)}",
        "wait_minutes": random.choice([2, 3, 5]),
        "message": "Teleconsulta solicitada. Um médico da Care Plus vai te chamar em instantes.",
    }


@router.post("/regenerate", response_model=PatientProfile)
def regenerate_profile() -> PatientProfile:
    """Gera um novo paciente de demonstração e ZERA os registros do anterior.

    Sem isto, ao trocar de paciente (Ctrl+F5), o histórico, a prescrição
    pendente e os relatos do paciente anterior continuavam aparecendo até
    reiniciar o servidor. Tudo em RAM (Zero-Data Footprint).
    """
    profile = twin_engine.randomize()
    records_service.reset()
    return profile


@router.get("/profile", response_model=PatientProfile)
def get_profile() -> PatientProfile:
    return twin_engine.profile


@router.post("/relato")
def add_relato(req: RelatoInput) -> dict:
    """Registra em RAM o que o paciente relatou à IA, para o médico ver.

    Além de guardar o texto (do jeito que o paciente escreveu), extrai os
    sintomas e os agrega ao perfil — assim eles aparecem no campo "Sintomas"
    do Painel do Médico. Também serve para o médico inserir um relato recebido
    por fora (source="medico"). Zero-Data Footprint: tudo em RAM.
    """
    records_service.add_patient_report(req.message, source=req.source)
    sintomas = clinical.extract_symptoms(req.message)
    if sintomas:
        merged = list(dict.fromkeys(list(twin_engine.profile.symptoms) + sintomas))
        twin_engine.update_profile(symptoms=merged)
    return {"ok": True, "symptoms": sintomas}


@router.get("/relato")
def get_relato() -> dict:
    """Lista os relatos do paciente (consumido pelo Painel do Médico)."""
    return {"reports": records_service.get_patient_reports()}


@router.put("/profile", response_model=PatientProfile)
def update_profile(profile: PatientProfile) -> PatientProfile:
    """Atualiza o perfil clínico (alergias, sintomas, medicamentos, etc.)."""
    return twin_engine.update_profile(**profile.model_dump())
