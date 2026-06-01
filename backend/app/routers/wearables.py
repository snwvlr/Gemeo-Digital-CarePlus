"""Rotas de wearables: catálogo, pareamento e stream de sinais vitais."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import (
    DeviceInfo,
    PairRequest,
    PairResponse,
    WearableBrand,
    WearableReading,
)
from ..services.wearables import simulator

router = APIRouter(prefix="/api/wearables", tags=["wearables"])


@router.get("/catalog", response_model=list[DeviceInfo])
def list_devices() -> list[DeviceInfo]:
    """Lista os dispositivos disponíveis para pareamento."""
    return simulator.catalog()


@router.get("/paired", response_model=list[WearableBrand])
def list_paired() -> list[WearableBrand]:
    """Marcas atualmente pareadas."""
    return simulator.paired_brands()


@router.post("/pair", response_model=PairResponse)
def pair_device(req: PairRequest) -> PairResponse:
    """Pareia (conecta) um wearable."""
    info = simulator.pair(req.brand)
    return PairResponse(
        success=True,
        brand=req.brand,
        device_name=info.device_name,
        message=f"{info.device_name} pareado com sucesso.",
    )


@router.post("/unpair", response_model=PairResponse)
def unpair_device(req: PairRequest) -> PairResponse:
    """Desconecta um wearable."""
    info = simulator.catalog()
    name = next((d.device_name for d in info if d.brand == req.brand), req.brand.value)
    simulator.unpair(req.brand)
    return PairResponse(success=True, brand=req.brand, device_name=name,
                        message=f"{name} desconectado.")


@router.get("/reading/{brand}", response_model=WearableReading)
def read_device(brand: WearableBrand) -> WearableReading:
    """Uma nova leitura simulada de um dispositivo específico."""
    return simulator.read(brand)


@router.get("/stream", response_model=list[WearableReading])
def stream_paired() -> list[WearableReading]:
    """Leituras de todos os dispositivos pareados (para polling do frontend)."""
    return simulator.read_paired()


@router.post("/simulate/{kind}")
def inject(kind: str) -> dict:
    """Injeta uma anomalia (cardiac|respiratory|fever) para demonstração."""
    if kind not in {"cardiac", "respiratory", "fever"}:
        raise HTTPException(status_code=400, detail="Tipo de anomalia inválido.")
    simulator.inject_anomaly(kind)
    return {"success": True, "injected": kind}


@router.post("/reset")
def reset_vitals() -> dict:
    """Normaliza os sinais vitais (encerra a simulação de anomalia)."""
    simulator.reset()
    return {"success": True, "reset": True}
