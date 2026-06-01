"""Modelos Pydantic (contratos de entrada e saída da API)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Wearables
# --------------------------------------------------------------------------- #
class WearableBrand(str, Enum):
    """Marcas de wearables suportadas na simulação."""

    apple_watch = "apple_watch"
    samsung = "samsung"
    xiaomi = "xiaomi"
    amazon_fit = "amazon_fit"
    garmin = "garmin"
    fitbit = "fitbit"
    esp32 = "esp32"


class VitalSigns(BaseModel):
    """Snapshot de sinais vitais coletados de um wearable."""

    heart_rate: int = Field(..., description="Frequência cardíaca (bpm)")
    spo2: int = Field(..., description="Saturação de oxigênio (%)")
    steps: int = Field(..., description="Passos acumulados no dia")
    calories: int = Field(..., description="Calorias gastas (kcal)")
    sleep_hours: float = Field(..., description="Horas de sono na última noite")
    stress: int = Field(..., description="Índice de estresse (0-100)")
    hrv: int = Field(..., description="Variabilidade da freq. cardíaca (ms)")
    body_temp: float = Field(..., description="Temperatura corporal (°C)")
    respiratory_rate: int = Field(..., description="Freq. respiratória (rpm)")


class WearableReading(BaseModel):
    """Leitura completa de um dispositivo em um instante."""

    brand: WearableBrand
    device_name: str
    battery: int = Field(..., ge=0, le=100)
    connected: bool = True
    timestamp: datetime
    vitals: VitalSigns


class DeviceInfo(BaseModel):
    """Metadados de um dispositivo disponível para pareamento."""

    brand: WearableBrand
    device_name: str
    icon: str
    color: str
    metrics: list[str]


class PairRequest(BaseModel):
    brand: WearableBrand


class PairResponse(BaseModel):
    success: bool
    brand: WearableBrand
    device_name: str
    message: str


# --------------------------------------------------------------------------- #
# Paciente / Gêmeo Digital
# --------------------------------------------------------------------------- #
class PatientProfile(BaseModel):
    """Perfil clínico básico do paciente (alimenta o gêmeo digital)."""

    name: str = "Paciente CarePlus"
    age: int = 34
    sex: str = "Não informado"
    height_cm: int = 172
    weight_kg: float = 70.0
    allergies: list[str] = Field(default_factory=lambda: ["Dipirona", "Poeira"])
    conditions: list[str] = Field(default_factory=lambda: ["Pré-hipertensão"])
    medications: list[str] = Field(default_factory=lambda: ["Losartana 50mg"])
    symptoms: list[str] = Field(default_factory=list)


class TwinState(BaseModel):
    """Estado do gêmeo digital: espelha como o paciente está agora."""

    mood: str = Field(..., description="Estado geral: ótimo, bem, atenção, alerta")
    health_score: int = Field(..., ge=0, le=100)
    summary: str
    color: str
    vitals: VitalSigns
    alerts: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# IA (Gemini)
# --------------------------------------------------------------------------- #
class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' ou 'model'")
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    powered_by: str
    twin_mood: Optional[str] = None
    escalate: bool = False
    escalation_type: Optional[str] = None  # 'emergencia' | 'saude_mental'
    actions: list[str] = Field(default_factory=list)  # ações autônomas do gêmeo (avisou médico, agendou…)


class AnalysisResponse(BaseModel):
    analysis: str
    risk_level: str
    recommendations: list[str]
    powered_by: str


# --------------------------------------------------------------------------- #
# Exames
# --------------------------------------------------------------------------- #
class ExamResult(BaseModel):
    """Um marcador de exame com sua faixa de referência e classificação."""

    name: str
    value: float
    unit: str
    ref_low: float
    ref_high: float
    status: str = Field(..., description="normal | alto | baixo")


class ExamPanel(BaseModel):
    """Um painel/exame com vários marcadores."""

    id: str
    name: str
    category: str
    collected_at: str
    lab: str
    results: list[ExamResult]
    uploaded: bool = False


class ExamUpload(BaseModel):
    filename: str


class ExamInterpretation(BaseModel):
    interpretation: str
    powered_by: str


# --------------------------------------------------------------------------- #
# Consultas, prescrições e histórico
# --------------------------------------------------------------------------- #
class AppointmentCreate(BaseModel):
    type: str = Field(..., description="Telemedicina | Presencial")
    specialty: str
    doctor: str
    date: str
    time: str
    reason: str = ""


class Appointment(AppointmentCreate):
    id: str
    protocol: str
    status: str = "agendada"
    created_at: str


class PrescriptionItem(BaseModel):
    name: str
    instruction: str


class Prescription(BaseModel):
    id: str
    doctor: str
    date: str
    items: list[PrescriptionItem]
    notes: str = ""


class HistoryItem(BaseModel):
    kind: str = Field(..., description="consulta | exame | prescricao | alerta")
    actor: str = Field("sistema", description="ia | medico | sistema")
    title: str
    subtitle: str
    date: str
    detail: str = ""
    badge: str = ""
    badge_kind: str = "muted"  # ok | warn | bad | muted
