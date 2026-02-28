from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.core.logging import log_event
from app.services.satellite.exceptions import (
    SatelliteAssetMissingError,
    SatellitePropertyMissingError,
)
from app.services.satellite.models import SentinelScene
from app.services.satellite.transport import SatelliteTransport


class PlanetaryComputerAdapter:
    def __init__(self, transport: SatelliteTransport | None = None) -> None:
        self.transport = transport or SatelliteTransport(
            stac_url=settings.satellite_stac_url,
            collection_id=settings.satellite_collection_id,
            request_timeout_seconds=settings.satellite_request_timeout_seconds,
        )

    def fetch_scene(self, *, latitude: float, longitude: float) -> tuple[SentinelScene, float, float]:
        item, search_latency_ms = self.transport.search_latest_scene(
            latitude=latitude,
            longitude=longitude,
            lookback_days=settings.satellite_search_lookback_days,
            max_cloud_cover=settings.satellite_max_cloud_cover,
        )
        signed_item, sign_latency_ms = self.transport.sign_item_assets(item)

        b04 = signed_item.assets.get("B04")
        b08 = signed_item.assets.get("B08")
        if b04 is None:
            raise SatelliteAssetMissingError("B04")
        if b08 is None:
            raise SatelliteAssetMissingError("B08")

        acquired_at = signed_item.datetime
        if acquired_at is None:
            acquired_at_raw = signed_item.properties.get("datetime")
            if isinstance(acquired_at_raw, str):
                acquired_at = datetime.fromisoformat(acquired_at_raw.replace("Z", "+00:00"))
            else:
                raise SatellitePropertyMissingError("datetime")

        scene = SentinelScene(
            scene_id=signed_item.id,
            acquired_at=acquired_at,
            cloud_cover=self.transport.get_float_property(signed_item, "eo:cloud_cover"),
            bands={
                "B04": str(b04.href),
                "B08": str(b08.href),
            },
        )
        log_event(
            event="satellite_scene_fetched",
            payload={
                "upstream_dependency": "planetary-computer-stac",
                "scene_id": scene.scene_id,
                "cloud_cover": scene.cloud_cover,
                "stac_search_latency_ms": search_latency_ms,
                "sas_sign_latency_ms": sign_latency_ms,
            },
        )
        return scene, search_latency_ms, sign_latency_ms
