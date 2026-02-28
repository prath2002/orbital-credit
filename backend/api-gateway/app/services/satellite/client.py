from __future__ import annotations

from app.services.satellite.models import SentinelScene
from app.services.satellite.planetary_adapter import PlanetaryComputerAdapter


class SatelliteClient:
    """Compatibility wrapper for the new Planetary Computer adapter."""

    def __init__(self, adapter: PlanetaryComputerAdapter | None = None) -> None:
        self.adapter = adapter or PlanetaryComputerAdapter()

    def fetch_scene(self, *, latitude: float, longitude: float) -> SentinelScene:
        scene, _, _ = self.adapter.fetch_scene(latitude=latitude, longitude=longitude)
        return scene
