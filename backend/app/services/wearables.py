"""Simulador de wearables.

Gera dados vitais realistas para diferentes marcas (Apple Watch, Samsung,
Xiaomi e Amazon Fit). Cada marca expõe um conjunto próprio de métricas, como
acontece nos dispositivos reais. Os dados variam suavemente ao longo do tempo
(random walk) para simular um stream contínuo e crível.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from ..schemas import (
    DeviceInfo,
    VitalSigns,
    WearableBrand,
    WearableReading,
)

# Catálogo de dispositivos disponíveis para pareamento.
DEVICE_CATALOG: dict[WearableBrand, DeviceInfo] = {
    WearableBrand.apple_watch: DeviceInfo(
        brand=WearableBrand.apple_watch,
        device_name="Apple Watch Series 9",
        icon="watch",
        color="#a3aab8",
        metrics=["heart_rate", "spo2", "steps", "calories", "sleep_hours",
                 "hrv", "body_temp", "respiratory_rate"],
    ),
    WearableBrand.samsung: DeviceInfo(
        brand=WearableBrand.samsung,
        device_name="Samsung Galaxy Watch 6",
        icon="watch",
        color="#1428a0",
        metrics=["heart_rate", "spo2", "steps", "calories", "sleep_hours",
                 "stress", "body_temp"],
    ),
    WearableBrand.xiaomi: DeviceInfo(
        brand=WearableBrand.xiaomi,
        device_name="Xiaomi Smart Band 8",
        icon="fitness_center",
        color="#ff6900",
        metrics=["heart_rate", "spo2", "steps", "calories", "sleep_hours",
                 "stress"],
    ),
    WearableBrand.amazon_fit: DeviceInfo(
        brand=WearableBrand.amazon_fit,
        device_name="Amazon Halo (Fit)",
        icon="monitor_heart",
        color="#ff9900",
        metrics=["heart_rate", "steps", "calories", "sleep_hours",
                 "body_temp", "respiratory_rate"],
    ),
    WearableBrand.garmin: DeviceInfo(
        brand=WearableBrand.garmin,
        device_name="Garmin Venu 3",
        icon="watch",
        color="#007cc3",
        metrics=["heart_rate", "spo2", "steps", "calories", "sleep_hours",
                 "stress", "hrv", "respiratory_rate"],
    ),
    WearableBrand.fitbit: DeviceInfo(
        brand=WearableBrand.fitbit,
        device_name="Fitbit Charge 6",
        icon="fitness_center",
        color="#00b0b9",
        metrics=["heart_rate", "spo2", "steps", "calories", "sleep_hours",
                 "stress"],
    ),
    WearableBrand.esp32: DeviceInfo(
        brand=WearableBrand.esp32,
        device_name="ESP32 DIY (sensor próprio)",
        icon="developer_board",
        color="#e7352c",
        metrics=["heart_rate", "spo2", "body_temp"],
    ),
}

# Faixas saudáveis usadas como ponto de partida da simulação.
_BASELINE = {
    "heart_rate": (72, 55, 130),          # (base, min, max)
    "spo2": (98, 93, 100),
    "steps": (4200, 0, 18000),
    "calories": (320, 0, 1200),
    "sleep_hours": (7.2, 4.0, 9.5),
    "stress": (30, 5, 95),
    "hrv": (55, 20, 110),
    "body_temp": (36.5, 35.8, 38.5),
    "respiratory_rate": (15, 10, 24),
}


class WearableSimulator:
    """Mantém o estado da simulação e produz leituras contínuas por marca."""

    def __init__(self) -> None:
        # Estado vital "vivo" compartilhado (random walk).
        self._state: dict[str, float] = {k: v[0] for k, v in _BASELINE.items()}
        self._battery: dict[WearableBrand, int] = {
            b: random.randint(60, 100) for b in WearableBrand
        }
        # Conjunto de dispositivos pareados.
        self._paired: set[WearableBrand] = set()

    # ----------------------------- pareamento ----------------------------- #
    def catalog(self) -> list[DeviceInfo]:
        return list(DEVICE_CATALOG.values())

    def pair(self, brand: WearableBrand) -> DeviceInfo:
        self._paired.add(brand)
        return DEVICE_CATALOG[brand]

    def unpair(self, brand: WearableBrand) -> None:
        self._paired.discard(brand)

    def paired_brands(self) -> list[WearableBrand]:
        return list(self._paired)

    # ------------------------------ simulação ----------------------------- #
    # Força de retorno à linha de base, por passo. Faz o random walk "puxar" de
    # volta ao valor saudável, então uma anomalia injetada se dissipa sozinha,
    # devagar, em vez de ficar presa no extremo. Quanto MENOR, mais lenta a
    # recuperação. Com o poll de ~8s da tela do gêmeo, 0.015 deixa o alerta ~1min
    # e a normalização total em ~3min. Aumente para recuperar mais rápido.
    # Para zerar na hora, use reset(). Ver também inject_anomaly().
    _REVERSION = 0.015

    def _step(self) -> None:
        """Avança o estado vital um passo: random walk + retorno à linha de base."""
        for key, (base, lo, hi) in _BASELINE.items():
            current = self._state[key]
            # passo proporcional à amplitude da métrica
            amplitude = (hi - lo) * 0.04
            current += random.uniform(-amplitude, amplitude)
            # mean-reversion: aproxima suavemente do valor saudável de base
            current += (base - current) * self._REVERSION
            self._state[key] = max(lo, min(hi, current))

    def _current_vitals(self) -> VitalSigns:
        return VitalSigns(
            heart_rate=round(self._state["heart_rate"]),
            spo2=round(self._state["spo2"]),
            steps=round(self._state["steps"]),
            calories=round(self._state["calories"]),
            sleep_hours=round(self._state["sleep_hours"], 1),
            stress=round(self._state["stress"]),
            hrv=round(self._state["hrv"]),
            body_temp=round(self._state["body_temp"], 1),
            respiratory_rate=round(self._state["respiratory_rate"]),
        )

    def read(self, brand: WearableBrand) -> WearableReading:
        """Retorna uma nova leitura para a marca informada."""
        self._step()
        info = DEVICE_CATALOG[brand]
        # bateria cai devagar
        self._battery[brand] = max(1, self._battery[brand] - random.choice([0, 0, 1]))
        return WearableReading(
            brand=brand,
            device_name=info.device_name,
            battery=self._battery[brand],
            connected=brand in self._paired,
            timestamp=datetime.now(timezone.utc),
            vitals=self._current_vitals(),
        )

    def read_paired(self) -> list[WearableReading]:
        """Leituras de todos os dispositivos pareados (ou Apple Watch como padrão)."""
        brands = self._paired or {WearableBrand.apple_watch}
        return [self.read(b) for b in brands]

    def aggregate_vitals(self) -> VitalSigns:
        """Sinais vitais consolidados do paciente (estado atual)."""
        self._step()
        return self._current_vitals()

    def inject_anomaly(self, kind: str = "cardiac") -> None:
        """Injeta uma anomalia para demonstrar a detecção do gêmeo digital."""
        if kind == "cardiac":
            self._state["heart_rate"] = 138
            self._state["hrv"] = 18
            self._state["stress"] = 92
            self._state["spo2"] = 94
            self._state["respiratory_rate"] = 22
        elif kind == "respiratory":
            self._state["spo2"] = 89
            self._state["respiratory_rate"] = 24
            self._state["heart_rate"] = 120
        elif kind == "fever":
            self._state["body_temp"] = 39.2
            self._state["heart_rate"] = 118
            self._state["respiratory_rate"] = 22

    def reset(self) -> None:
        """Normaliza os sinais vitais para a linha de base saudável.

        Encerra qualquer anomalia em andamento sem reiniciar o servidor — útil,
        por exemplo, para "voltar ao normal" no meio de uma apresentação.
        """
        self._state = {k: v[0] for k, v in _BASELINE.items()}


# Instância única (singleton) usada pela aplicação.
simulator = WearableSimulator()
