"""Rotas de IA (Gemini 2.5 Flash): chat, análise, relatório e prescrição médica."""
# Painel do Médico: rotas de prescrição (draft/assinar) integradas ao histórico.
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..ratelimit import ai_rate_limit
from ..schemas import AnalysisResponse, ChatRequest, ChatResponse, PrescriptionItem
from ..services import clinical
from ..services.gemini_service import gemini_service
from ..services.guardrails import checar_red_flag, resposta_escalada
from ..services.records import records_service
from ..services.twin_state import twin_engine
from ..services.wearables import simulator

# Rate limit aplicado a todas as rotas que conversam com o Gemini.
router = APIRouter(prefix="/api/ai", tags=["ia-gemini"], dependencies=[Depends(ai_rate_limit)])

# ---------------------------------------------------------------------------
# Armazenamento em RAM (Zero-Data Footprint / LGPD)
# A prescrição pendente vive no records_service (memória do processo) para que,
# ao trocar de paciente (regenerate), seja zerada junto do histórico. Nunca em
# disco ou banco; ao reiniciar o servidor, tudo é apagado automaticamente.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Schemas de prescrição
# ---------------------------------------------------------------------------
class TwinSummaryInput(BaseModel):
    mood: str = "alerta"
    health_score: int = 42
    vitals: dict = {}
    alerts: list[str] = []


class PrescricaoDraftRequest(BaseModel):
    twin_summary: TwinSummaryInput
    consulta_notes: str


class PrescricaoMedication(BaseModel):
    name: str
    dosage: str = ""
    frequency: str = ""
    duration: str = ""


class PrescricaoDraftResponse(BaseModel):
    prescription_draft: str  # texto plano (exibição + PDF)
    medications: list[PrescricaoMedication] = []
    guidance: list[str] = []
    return_criteria: list[str] = []
    allergy_note: str = ""
    patient_name: str = ""
    powered_by: str


class AssinarPrescricaoRequest(BaseModel):
    prescription_text: str
    medications: list[PrescricaoMedication] = []
    guidance: list[str] = []
    return_criteria: list[str] = []
    allergy_note: str = ""
    doctor: str = "Dr(a). Especialista CarePlus"
    consulta_notes: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _current_twin():
    return twin_engine.compute_state(simulator.aggregate_vitals())


def _twin_autonomy(message: str, twin) -> list[str]:
    """Dá autonomia ao Gêmeo Digital: ele AGE e conta o que fez.

    Determinístico (funciona em modo demo e com Gemini). Duas ações possíveis:
      • Avisar o médico: ao detectar sintomas/mal-estar, registra o relato (vai
        para o painel do médico) e agrega os sintomas ao perfil.
      • Marcar teleconsulta: se o paciente pede ajuda/consulta (ou está em
        alerta e relata mal-estar), agenda de fato (aparece em Consultas).
    """
    actions: list[str] = []
    syms = clinical.extract_symptoms(message)
    distress = clinical.reports_distress(message)

    if syms or distress:
        records_service.add_patient_report(message, source="paciente")  # idempotente
        if syms:
            merged = list(dict.fromkeys(list(twin_engine.profile.symptoms) + syms))
            twin_engine.update_profile(symptoms=merged)
        actions.append("✓ **Avisei seu médico** — registrei seu relato e ele já aparece no painel clínico dele.")

    if clinical.wants_appointment(message) or (twin.mood == "alerta" and distress):
        appt = records_service.ensure_twin_appointment()
        if appt["created"]:
            actions.append(
                f"✓ **Marquei uma teleconsulta** para você — protocolo {appt['protocol']} "
                f"({appt['when']}). É só aguardar o contato da Care Plus."
            )
        else:
            actions.append(
                f"✓ Sua **teleconsulta já está marcada** — protocolo {appt['protocol']} ({appt['when']})."
            )
    return actions


# ---------------------------------------------------------------------------
# Rotas existentes
# ---------------------------------------------------------------------------
@router.get("/status")
def ai_status() -> dict:
    """Indica se a IA está ativa e qual modelo está em uso."""
    return {"enabled": gemini_service.enabled, "model": gemini_service.label}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Conversa com o gêmeo digital (responde em primeira pessoa).

    Guardrail determinístico: se a mensagem contém red flag clínica ou ideação
    suicida, escalamos imediatamente (sem passar pelo LLM).
    """
    twin = _current_twin()

    rf = checar_red_flag(req.message)
    if rf["detectado"]:
        return ChatResponse(
            reply=resposta_escalada(rf["tipo"]),
            powered_by="Guardrail de segurança",
            twin_mood=twin.mood,
            escalate=True,
            escalation_type=rf["tipo"],
        )

    reply = gemini_service.chat(req.message, req.history, twin_engine.profile, twin)

    # Autonomia: o gêmeo age (avisa o médico / marca consulta) e relata ao paciente.
    actions = _twin_autonomy(req.message, twin)
    if actions:
        reply = reply.rstrip() + "\n\n" + "\n".join(actions)

    return ChatResponse(
        reply=reply, powered_by=gemini_service.label, twin_mood=twin.mood, actions=actions
    )


@router.post("/analyze", response_model=AnalysisResponse)
def analyze() -> AnalysisResponse:
    """Análise dos sinais vitais e perfil pela IA."""
    twin = _current_twin()
    data = gemini_service.analyze(twin_engine.profile, twin)
    return AnalysisResponse(powered_by=gemini_service.label, **data)


@router.post("/report")
def report() -> dict:
    """Relatório de saúde gerado pela IA para o médico.

    Inclui os sintomas e o relato do paciente (nas palavras dele) e sai limpo,
    sem markdown/asteriscos.
    """
    twin = _current_twin()
    relatos = [r["text"] for r in records_service.get_patient_reports()[:3]]
    return {
        "report": gemini_service.report(twin_engine.profile, twin, relatos=relatos),
        "powered_by": gemini_service.label,
    }


# ---------------------------------------------------------------------------
# Rotas de prescrição médica (Painel do Médico)
# ---------------------------------------------------------------------------
@router.post("/prescricao-draft", response_model=PrescricaoDraftResponse)
def prescricao_draft(req: PrescricaoDraftRequest) -> PrescricaoDraftResponse:
    """Gera rascunho de prescrição via IA para revisão do médico.

    Recebe os dados do Gêmeo Digital e as anotações da teleconsulta.
    A IA age como assistente médico — o texto gerado é apenas um rascunho
    para o médico revisar e assinar. Nunca substitui a decisão clínica.

    Zero-Data Footprint: nenhuma informação é armazenada em disco.
    """
    draft = gemini_service.generate_prescription_draft(
        twin_summary=req.twin_summary.model_dump(),
        consulta_notes=req.consulta_notes,
        profile=twin_engine.profile,
    )
    return PrescricaoDraftResponse(
        prescription_draft=draft["text"],
        medications=[PrescricaoMedication(**m) for m in draft.get("medications", [])],
        guidance=draft.get("guidance", []),
        return_criteria=draft.get("return_criteria", []),
        allergy_note=draft.get("allergy_note", ""),
        patient_name=twin_engine.profile.name,
        powered_by=gemini_service.label,
    )


@router.post("/prescricao-assinar")
def prescricao_assinar(req: AssinarPrescricaoRequest) -> dict:
    """Assina a prescrição e a entrega ao paciente em TRÊS lugares:

    1. Aviso no Dashboard — via prescrição pendente em RAM (Zero-Data Footprint).
    2. Histórico — cria um registro de "Prescrição assinada" (records_service).
    3. Medicamentos — adiciona os itens prescritos ao perfil do paciente.

    Zero-Data Footprint: tudo vive APENAS na memória do processo Python. Ao
    reiniciar o servidor, é apagado. Sem banco de dados, sem disco.
    """
    # 1) Itens estruturados (com dose/frequência/duração) para Histórico/Medicamentos.
    items: list[PrescriptionItem] = []
    med_labels: list[str] = []
    for m in req.medications:
        detalhe = " · ".join(p for p in (m.frequency, m.duration) if p) or "Conforme orientação médica"
        items.append(PrescriptionItem(
            name=(f"{m.name} — {m.dosage}".strip(" —") if m.dosage else m.name),
            instruction=detalhe,
        ))
        # Rótulo curto para a lista de Medicamentos do paciente.
        sufixo = " · ".join(p for p in (m.frequency, m.duration) if p)
        med_labels.append(f"{m.name} ({sufixo})" if sufixo else m.name)

    # 2) Prescrição pendente em RAM (a tela do paciente lê isto).
    #    Guarda também o conteúdo estruturado para o paciente ver cards bonitos.
    structured = {
        "medications": [m.model_dump() for m in req.medications],
        "guidance": req.guidance,
        "return_criteria": req.return_criteria,
        "allergy_note": req.allergy_note,
    }
    records_service.set_pending_prescription(
        texto=req.prescription_text, medico=req.doctor, structured=structured
    )

    # 3) Registro no Histórico (records_service).
    prescricao = records_service.add_signed_prescription(
        doctor=req.doctor,
        items=items,
        notes=(req.consulta_notes.strip() or "Prescrição revisada e assinada pelo médico após teleconsulta."),
    )

    # 4) Adiciona ao perfil (Medicamentos), sem duplicar pelo nome do princípio.
    if med_labels:
        atuais = list(twin_engine.profile.medications)
        existentes = " | ".join(a.lower() for a in atuais)
        for label, m in zip(med_labels, req.medications):
            chave = (m.name.split()[0] if m.name else label).lower()
            if chave and chave not in existentes:
                atuais.append(label)
                existentes += " | " + label.lower()
        twin_engine.update_profile(medications=atuais)

    return {
        "ok": True,
        "message": "Prescrição assinada e entregue ao paciente (Dashboard + Histórico + Medicamentos).",
        "prescription_id": prescricao.id,
        "added_to_medications": med_labels,
    }


@router.get("/prescricao")
def prescricao_consultar() -> dict:
    """Retorna a prescrição pendente (se houver) para o paciente.

    Chamado pelo frontend do paciente (polling ou on-load).
    Zero-Data Footprint: apenas leitura da memória em RAM.
    """
    pend = records_service.get_pending_prescription()
    if pend is None:
        return {"pendente": False, "prescricao": None}
    return {"pendente": True, "prescricao": pend}


@router.post("/prescricao-marcar-lida")
def prescricao_marcar_lida() -> dict:
    """Marca a prescrição como lida pelo paciente."""
    records_service.mark_pending_read()
    return {"ok": True}
