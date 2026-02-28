from __future__ import annotations

from app.services.satellite.client import SatelliteClient
from app.services.satellite.models import SentinelScene


class SatelliteAdapter:
    def __init__(self, client: SatelliteClient) -> None:
        self.client = client

    def fetch_scene(self, *, latitude: float, longitude: float) -> SentinelScene:
        return self.client.fetch_scene(latitude=latitude, longitude=longitude)
