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


class NdviSample(BaseModel):
    scene_id: str
    acquired_at: datetime
    ndvi: float
    nbr: float | None = None
    cloud_cover: float | None = None


class SatelliteFeatureResult(BaseModel):
    ndvi_score: int = Field(ge=0, le=100)
    crop_cycle: str
    volatility: float = Field(ge=0.0)
    fire_detected: bool
    fire_signal_score: float = Field(ge=0.0, le=1.0)
    data_quality: float = Field(ge=0.0, le=1.0)
    data_quality_flags: list[str] = Field(default_factory=list)
    provider_degraded: bool = False
    sample_count: int = Field(ge=1)
    peak_count: int = Field(ge=0)
    cycles_per_year: float = Field(ge=0.0)
    latest_scene_id: str
    latest_acquired_at: datetime
    ndvi_series: list[NdviSample]
    processing_latency_ms: float = Field(ge=0.0)
