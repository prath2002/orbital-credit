from __future__ import annotations

from app.core.logging import log_event
from app.services.satellite.models import BandDownloadProbe, ConnectivityCheckResult
from app.services.satellite.planetary_adapter import PlanetaryComputerAdapter


class SatelliteConnectivityChecker:
    def __init__(self, adapter: PlanetaryComputerAdapter | None = None) -> None:
        self.adapter = adapter or PlanetaryComputerAdapter()

    def fetch_scene(self, latitude: float, longitude: float) -> dict[str, object]:
        scene, _, _ = self.adapter.fetch_scene(latitude=latitude, longitude=longitude)
        return scene.model_dump(mode="json")

    def run(self, *, latitude: float, longitude: float) -> ConnectivityCheckResult:
        scene, stac_search_latency_ms, sas_sign_latency_ms = self.adapter.fetch_scene(
            latitude=latitude,
            longitude=longitude,
        )

        probes: list[BandDownloadProbe] = []
        for band_name in ("B04", "B08"):
            band_url = str(scene.bands[band_name])
            bytes_downloaded, latency_ms = self.adapter.transport.probe_download(url=band_url)
            probes.append(
                BandDownloadProbe(
                    band=band_name,
                    bytes_downloaded=bytes_downloaded,
                    latency_ms=latency_ms,
                )
            )

        result = ConnectivityCheckResult(
            scene=scene,
            stac_search_latency_ms=stac_search_latency_ms,
            sas_sign_latency_ms=sas_sign_latency_ms,
            download_probes=probes,
        )
        log_event(
            event="satellite_connectivity_check_succeeded",
            payload={
                "upstream_dependency": "planetary-computer",
                "scene_id": scene.scene_id,
                "stac_search_latency_ms": stac_search_latency_ms,
                "sas_sign_latency_ms": sas_sign_latency_ms,
                "download_probe_count": len(probes),
                "download_latencies_ms": [probe.latency_ms for probe in probes],
            },
        )
        return result


def fetch_scene(latitude: float, longitude: float) -> dict[str, object]:
    """Core Phase 2A function required by execution plan."""
    checker = SatelliteConnectivityChecker()
    return checker.fetch_scene(latitude=latitude, longitude=longitude)
