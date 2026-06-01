"""Serviço de exames laboratoriais (dados simulados, porém realistas).

Fornece painéis de exames com valores, faixas de referência e classificação
automática (normal / alto / baixo). Serve de base para a interpretação por IA.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from ..schemas import ExamPanel, ExamResult


def _classify(value: float, low: float, high: float) -> str:
    if value < low:
        return "baixo"
    if value > high:
        return "alto"
    return "normal"


def _rand(low: float, high: float, decimals: int = 0):
    """Gera um valor plausível: na maioria das vezes dentro da faixa,
    às vezes um pouco fora (para haver exames alterados de forma realista)."""
    span = high - low
    roll = random.random()
    if roll < 0.7:                      # 70% dentro da faixa
        v = random.uniform(low, high)
    elif roll < 0.85:                   # 15% acima
        v = random.uniform(high, high + span * 0.4)
    else:                               # 15% abaixo
        v = random.uniform(max(0, low - span * 0.4), low)
    return round(v, decimals) if decimals else round(v)


def _r(name: str, low: float, high: float, unit: str, decimals: int = 0) -> ExamResult:
    value = _rand(low, high, decimals)
    return ExamResult(
        name=name, value=value, unit=unit,
        ref_low=low, ref_high=high, status=_classify(value, low, high),
    )


def _build_catalog() -> list[ExamPanel]:
    hoje = date.today()
    return [
        ExamPanel(
            id="hemograma",
            name="Hemograma completo",
            category="Sangue",
            collected_at=(hoje - timedelta(days=4)).isoformat(),
            lab="Lab CarePlus",
            results=[
                _r("Hemoglobina", 13.0, 17.0, "g/dL", 1),
                _r("Hematócrito", 40.0, 52.0, "%", 1),
                _r("Leucócitos", 4000, 11000, "/mm³"),
                _r("Plaquetas", 150000, 450000, "/mm³"),
            ],
        ),
        ExamPanel(
            id="lipidograma",
            name="Lipidograma",
            category="Metabólico",
            collected_at=(hoje - timedelta(days=4)).isoformat(),
            lab="Lab CarePlus",
            results=[
                _r("Colesterol total", 120, 190, "mg/dL"),
                _r("LDL", 60, 130, "mg/dL"),
                _r("HDL", 40, 60, "mg/dL"),
                _r("Triglicerídeos", 50, 150, "mg/dL"),
            ],
        ),
        ExamPanel(
            id="glicemia",
            name="Glicemia e diabetes",
            category="Metabólico",
            collected_at=(hoje - timedelta(days=4)).isoformat(),
            lab="Lab CarePlus",
            results=[
                _r("Glicose em jejum", 70, 99, "mg/dL"),
                _r("Hemoglobina glicada (HbA1c)", 4.0, 5.6, "%", 1),
            ],
        ),
        ExamPanel(
            id="tireoide",
            name="Função tireoidiana",
            category="Hormonal",
            collected_at=(hoje - timedelta(days=18)).isoformat(),
            lab="Lab CarePlus",
            results=[
                _r("TSH", 0.4, 4.0, "mUI/L", 1),
                _r("T4 livre", 0.9, 1.7, "ng/dL", 1),
            ],
        ),
        ExamPanel(
            id="vitaminas",
            name="Vitaminas e minerais",
            category="Nutricional",
            collected_at=(hoje - timedelta(days=18)).isoformat(),
            lab="Lab CarePlus",
            results=[
                _r("Vitamina D (25-OH)", 30, 100, "ng/mL"),
                _r("Vitamina B12", 200, 900, "pg/mL"),
                _r("Ferritina", 30, 400, "ng/mL"),
            ],
        ),
    ]


class ExamService:
    """Mantém o catálogo de exames em memória."""

    def __init__(self) -> None:
        self._panels = {p.id: p for p in _build_catalog()}

    def list_panels(self) -> list[ExamPanel]:
        return list(self._panels.values())

    def add_uploaded(self, filename: str) -> ExamPanel:
        """Registra um PDF de exame enviado pelo paciente (metadados apenas)."""
        from datetime import date as _date
        clean = (filename or "exame.pdf").strip()
        pid = "upload-" + str(len([p for p in self._panels if p.startswith("upload-")]) + 1)
        panel = ExamPanel(
            id=pid,
            name=clean,
            category="Enviado pelo paciente",
            collected_at=_date.today().isoformat(),
            lab="Upload",
            results=[],
            uploaded=True,
        )
        self._panels[pid] = panel
        return panel

    def get_panel(self, panel_id: str) -> ExamPanel | None:
        return self._panels.get(panel_id)

    def summary(self) -> dict:
        """Contagem por status para os cartões de visão geral."""
        total = alterados = 0
        for p in self._panels.values():
            for r in p.results:
                total += 1
                if r.status != "normal":
                    alterados += 1
        return {"paineis": len(self._panels), "marcadores": total, "alterados": alterados}


# Instância única.
exam_service = ExamService()
