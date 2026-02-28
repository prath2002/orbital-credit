from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class SatelliteResult(BaseModel):
    """Legacy placeholder scoring model retained for compatibility."""

    ndvi_score: int = Field(ge=0, le=100)
    crop_cycle: str
    volatility: float = Field(ge=0.0)
    fire_flag: bool
    data_quality: float = Field(ge=0.0, le=1.0)


class SentinelScene(BaseModel):
    scene_id: str
    acquired_at: datetime
    cloud_cover: float | None = None
    bands: dict[str, HttpUrl]


class BandDownloadProbe(BaseModel):
    band: str
    bytes_downloaded: int
    latency_ms: float


class ConnectivityCheckResult(BaseModel):
    scene: SentinelScene
    stac_search_latency_ms: float
    sas_sign_latency_ms: float
    download_probes: list[BandDownloadProbe]
