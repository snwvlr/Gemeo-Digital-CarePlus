"""Rotas de consultas, prescrições e histórico."""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas import Appointment, AppointmentCreate, HistoryItem, Prescription
from ..services.records import records_service
from ..services.twin_state import twin_engine
from ..services.wearables import simulator

router = APIRouter(prefix="/api", tags=["registros"])


@router.post("/appointments", response_model=Appointment)
def create_appointment(data: AppointmentCreate) -> Appointment:
    return records_service.create_appointment(data)


@router.get("/appointments", response_model=list[Appointment])
def list_appointments() -> list[Appointment]:
    return records_service.list_appointments()


@router.post("/prescriptions", response_model=Prescription)
def create_prescription(doctor: str = "Equipe médica Care Plus") -> Prescription:
    """Emite uma prescrição (simulada) após a teleconsulta.

    A IA não prescreve: a prescrição é atribuída ao médico e baseada nos
    medicamentos de uso contínuo do paciente. Integra-se ao histórico.
    """
    meds = twin_engine.profile.medications
    return records_service.create_prescription(doctor, meds)


@router.get("/prescriptions", response_model=list[Prescription])
def list_prescriptions() -> list[Prescription]:
    return records_service.list_prescriptions()


@router.get("/history", response_model=list[HistoryItem])
def history() -> list[HistoryItem]:
    twin = twin_engine.compute_state(simulator.aggregate_vitals())
    return records_service.history(ia_alerts=twin.alerts)


@router.get("/medications/check")
def check_interactions(name: str) -> dict:
    """Verifica interações do novo medicamento com os de uso contínuo (simulado)."""
    avisos = records_service.check_interactions(name, twin_engine.profile.medications)
    return {"name": name, "has_warning": bool(avisos), "warnings": avisos,
            "checked_against": twin_engine.profile.medications}
