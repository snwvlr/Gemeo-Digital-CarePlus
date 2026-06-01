"""Rotas de exames: listagem, detalhe e interpretação por IA."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..ratelimit import ai_rate_limit
from ..schemas import ExamInterpretation, ExamPanel, ExamUpload
from ..services.exams import exam_service
from ..services.gemini_service import gemini_service
from ..services.twin_state import twin_engine

router = APIRouter(prefix="/api/exams", tags=["exames"])


@router.get("", response_model=list[ExamPanel])
def list_exams() -> list[ExamPanel]:
    return exam_service.list_panels()


@router.post("/upload", response_model=ExamPanel)
def upload_exam(payload: ExamUpload) -> ExamPanel:
    """Registra um PDF de exame enviado pelo paciente (apenas metadados)."""
    return exam_service.add_uploaded(payload.filename)


@router.get("/summary")
def exams_summary() -> dict:
    return exam_service.summary()


@router.get("/{panel_id}", response_model=ExamPanel)
def get_exam(panel_id: str) -> ExamPanel:
    panel = exam_service.get_panel(panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Exame não encontrado.")
    return panel


@router.post("/{panel_id}/interpret", response_model=ExamInterpretation,
             dependencies=[Depends(ai_rate_limit)])
def interpret_exam(panel_id: str) -> ExamInterpretation:
    panel = exam_service.get_panel(panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Exame não encontrado.")
    text = gemini_service.interpret_exam(twin_engine.profile, panel)
    return ExamInterpretation(interpretation=text, powered_by=gemini_service.label)
