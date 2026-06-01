"""Registros do paciente: consultas, prescrições e histórico agregado.

Mantém em memória (sessão única de demonstração) as consultas agendadas e as
prescrições emitidas. O histórico é montado a partir desses registros somados
aos exames, para que as páginas conversem entre si: uma consulta agendada em
Consultas aparece no Histórico; um exame aparece no Histórico; e a prescrição
emitida após a teleconsulta também.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from ..schemas import (
    Appointment,
    AppointmentCreate,
    HistoryItem,
    Prescription,
    PrescriptionItem,
)
from .exams import exam_service


class RecordsService:
    def __init__(self) -> None:
        self._appointments: list[Appointment] = []
        self._prescriptions: list[Prescription] = []
        self._pending_rx: dict | None = None          # prescrição entregue ao paciente (RAM)
        self._patient_reports: list[dict] = []         # relatos do paciente à IA (RAM)
        self._seed()

    def reset(self) -> None:
        """Zera os registros (usado quando um novo paciente é gerado).

        Garante que, ao trocar de paciente (Ctrl+F5 -> /api/twin/regenerate),
        o histórico, a prescrição pendente e os relatos não vazem entre pacientes.
        Tudo em RAM (Zero-Data Footprint).
        """
        self._appointments = []
        self._prescriptions = []
        self._pending_rx = None
        self._patient_reports = []
        self._seed()

    # --------------------- prescrição pendente (Exames) ------------------- #
    def set_pending_prescription(self, texto: str, medico: str, structured: dict | None = None) -> dict:
        self._pending_rx = {
            "texto": texto,
            "medico": medico,
            "data": datetime.now(timezone.utc).isoformat(),
            "lida": False,
            "structured": structured or {},
        }
        return self._pending_rx

    def get_pending_prescription(self) -> dict | None:
        return self._pending_rx

    def mark_pending_read(self) -> None:
        if self._pending_rx:
            self._pending_rx["lida"] = True

    # ----------------------- relato do paciente (IA) ---------------------- #
    def add_patient_report(self, text: str, source: str = "paciente") -> None:
        """Guarda um relato (do paciente ou inserido pelo médico).

        Dedupe simples: ignora se o texto for idêntico ao último relato — assim
        o app pode registrar o mesmo relato por dois caminhos (chat + endpoint)
        sem duplicar na tela do médico. Tudo em RAM (Zero-Data Footprint).
        """
        text = (text or "").strip()
        if not text:
            return
        if self._patient_reports and self._patient_reports[0]["text"] == text:
            return
        self._patient_reports.insert(0, {
            "text": text,
            "at": datetime.now(timezone.utc).isoformat(),
            "source": source or "paciente",
        })
        self._patient_reports = self._patient_reports[:12]

    def get_patient_reports(self) -> list[dict]:
        return self._patient_reports

    # --------------- teleconsulta automática (autonomia da IA) ------------ #
    def ensure_twin_appointment(self) -> dict:
        """Garante UMA teleconsulta agendada pelo Gêmeo Digital (sem spam).

        Usado quando o paciente relata sintomas/pede ajuda no chat: o gêmeo
        marca de fato a consulta (aparece em Consultas e no Histórico) e avisa.
        Se já existir uma marcada por ele, apenas a devolve.
        """
        for a in self._appointments:
            if "gêmeo digital" in (a.doctor or "").lower():
                return {"created": False, "protocol": a.protocol,
                        "when": self._fmt_when(a.date, a.time)}
        d = date.today() + timedelta(days=1)
        appt = self.create_appointment(AppointmentCreate(
            type="Telemedicina",
            specialty="Clínica Geral",
            doctor="Teleconsulta · Gêmeo Digital",
            date=d.isoformat(),
            time="09:00",
            reason="Teleconsulta agendada automaticamente após relato de sintomas ao Gêmeo Digital.",
        ))
        return {"created": True, "protocol": appt.protocol, "when": self._fmt_when(appt.date, appt.time)}

    @staticmethod
    def _fmt_when(iso_date: str, time: str) -> str:
        try:
            d = datetime.strptime(iso_date, "%Y-%m-%d")
            return f"{d.strftime('%d/%m')} às {time}"
        except Exception:
            return f"{iso_date} {time}"

    def _seed(self) -> None:
        """Cria um registro inicial para o histórico não nascer vazio."""
        hoje = date.today()
        self._prescriptions.append(
            Prescription(
                id="presc-seed",
                doctor="Dr. Ricardo Silva",
                date=hoje.isoformat(),
                items=[PrescriptionItem(name="Losartana 50mg", instruction="1 comprimido pela manhã")],
                notes="Renovação de uso contínuo. Reavaliar a pressão em 30 dias.",
            )
        )

    # ------------------------------ consultas ----------------------------- #
    def create_appointment(self, data: AppointmentCreate) -> Appointment:
        appt = Appointment(
            id=f"appt-{len(self._appointments) + 1}",
            protocol=f"AG-{random.randint(10000, 99999)}",
            created_at=datetime.now(timezone.utc).isoformat(),
            **data.model_dump(),
        )
        self._appointments.insert(0, appt)
        return appt

    def list_appointments(self) -> list[Appointment]:
        return self._appointments

    # ----------------------------- prescrições ---------------------------- #
    def create_prescription(self, doctor: str, medications: list[str], notes: str = "") -> Prescription:
        items = [PrescriptionItem(name=m, instruction="Conforme orientação médica") for m in medications] or \
                [PrescriptionItem(name="Sem medicação prescrita", instruction="Manter acompanhamento")]
        presc = Prescription(
            id=f"presc-{len(self._prescriptions) + 1}",
            doctor=doctor or "Equipe médica Care Plus",
            date=date.today().isoformat(),
            items=items,
            notes=notes or "Prescrição emitida após teleconsulta e validada pelo médico.",
        )
        self._prescriptions.insert(0, presc)
        return presc

    def add_signed_prescription(
        self,
        doctor: str,
        items: list[PrescriptionItem],
        notes: str = "",
    ) -> Prescription:
        """Registra uma prescrição JÁ revisada e assinada pelo médico no painel.

        Diferente de create_prescription (que monta itens a partir do uso
        contínuo), aqui recebemos os itens estruturados que o médico revisou
        — com dosagem, frequência e duração na instrução — para que o
        Histórico e os PDFs fiquem fiéis ao que foi assinado.
        """
        items = items or [
            PrescriptionItem(name="Sem medicação prescrita", instruction="Manter acompanhamento")
        ]
        presc = Prescription(
            id=f"presc-{len(self._prescriptions) + 1}",
            doctor=doctor or "Equipe médica Care Plus",
            date=date.today().isoformat(),
            items=items,
            notes=notes or "Prescrição revisada e assinada pelo médico após teleconsulta.",
        )
        self._prescriptions.insert(0, presc)
        return presc

    def list_prescriptions(self) -> list[Prescription]:
        return self._prescriptions

    # -------------------- interações medicamentosas ---------------------- #
    # Regras simuladas (ferramenta verificar_interacoes_medicamentosas).
    _RULES = [
        (["ibuprofeno", "diclofenaco", "nimesulida", "naproxeno", "anti-inflam", "aine"],
         ["losartana", "enalapril", "captopril", "valsartana", "anti-hipert"],
         "Risco de redução do efeito anti-hipertensivo."),
        (["ibuprofeno", "diclofenaco", "naproxeno", "aine"],
         ["aas", "aspirina", "varfarina", "clopidogrel"],
         "Aumento do risco de sangramento gastrointestinal."),
        (["sertralina", "fluoxetina", "escitalopram", "paroxetina"],
         ["tramadol", "amitriptilina", "sumatriptana"],
         "Risco de síndrome serotoninérgica."),
        (["omeprazol", "pantoprazol"],
         ["clopidogrel"],
         "Pode reduzir o efeito do clopidogrel."),
        (["metformina"],
         ["álcool", "alcool"],
         "Risco aumentado de acidose lática."),
    ]

    def check_interactions(self, new_med: str, current_meds: list[str]) -> list[str]:
        n = (new_med or "").lower()
        atuais = " | ".join(m.lower() for m in current_meds)
        avisos: list[str] = []
        for grupo_a, grupo_b, msg in self._RULES:
            in_a = any(t in n for t in grupo_a)
            in_b = any(t in n for t in grupo_b)
            cur_a = any(t in atuais for t in grupo_a)
            cur_b = any(t in atuais for t in grupo_b)
            if (in_a and cur_b) or (in_b and cur_a):
                if msg not in avisos:
                    avisos.append(msg)
        return avisos

    # ------------------------------ histórico ----------------------------- #
    def history(self, ia_alerts: list[str] | None = None) -> list[HistoryItem]:
        items: list[HistoryItem] = []

        for a in self._appointments:
            items.append(HistoryItem(
                kind="consulta",
                actor="medico",
                title=f"Consulta de {a.specialty}",
                subtitle=f"{a.doctor} · {a.type}",
                date=a.date,
                detail=a.reason or "Consulta agendada pela plataforma.",
                badge="ação médica",
                badge_kind="ok",
            ))

        for p in self._prescriptions:
            nomes = ", ".join(i.name for i in p.items)
            items.append(HistoryItem(
                kind="prescricao",
                actor="medico",
                title="Prescrição validada e assinada",
                subtitle=f"{p.doctor}",
                date=p.date,
                detail=nomes,
                badge="ação médica",
                badge_kind="ok",
            ))

        for panel in exam_service.list_panels():
            alterados = [r for r in panel.results if r.status != "normal"]
            items.append(HistoryItem(
                kind="exame",
                actor="sistema",
                title=panel.name,
                subtitle=panel.lab,
                date=panel.collected_at,
                detail=("Resultados normais" if not alterados
                        else f"{len(alterados)} marcador(es) fora da faixa"),
                badge=("normal" if not alterados else "atenção"),
                badge_kind=("ok" if not alterados else "warn"),
            ))

        # Ações da IA (monitoramento): registra alertas detectados pelo gêmeo.
        for al in (ia_alerts or [])[:3]:
            items.append(HistoryItem(
                kind="alerta",
                actor="ia",
                title="Alerta detectado pelo Gêmeo Digital",
                subtitle="Monitoramento por IA",
                date=date.today().isoformat(),
                detail=al,
                badge="ação IA",
                badge_kind="warn",
            ))

        # ordena por data desc (string ISO ordena bem; consultas usam AAAA-MM-DD)
        items.sort(key=lambda i: i.date, reverse=True)
        return items


records_service = RecordsService()
