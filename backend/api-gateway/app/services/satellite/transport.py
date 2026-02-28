from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter
from typing import Any

import planetary_computer
import requests
from pystac import Item
from pystac_client import Client

from app.services.satellite.exceptions import SatelliteSceneNotFoundError, SatelliteServiceError


DEFAULT_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
DEFAULT_SENTINEL_COLLECTION = "sentinel-2-l2a"


class SatelliteTransport:
    def __init__(
        self,
        *,
        stac_url: str = DEFAULT_STAC_URL,
        collection_id: str = DEFAULT_SENTINEL_COLLECTION,
        request_timeout_seconds: float = 30.0,
    ) -> None:
        self.stac_url = stac_url
        self.collection_id = collection_id
        self.request_timeout_seconds = request_timeout_seconds
        self._catalog = Client.open(stac_url)

    def search_latest_scene(
        self,
        *,
        latitude: float,
        longitude: float,
        lookback_days: int = 60,
        max_cloud_cover: float = 40.0,
    ) -> tuple[Item, float]:
        start = perf_counter()
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        try:
            search = self._catalog.search(
                collections=[self.collection_id],
                intersects={
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
                query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            )
            items = list(search.items())
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"STAC search failed: {type(exc).__name__}",
                code="SATELLITE_STAC_SEARCH_FAILED",
                retryable=True,
            ) from exc

        latency_ms = round((perf_counter() - start) * 1000, 2)
        if not items:
            raise SatelliteSceneNotFoundError()

        latest_item = max(
            items,
            key=lambda item: item.properties.get("datetime", ""),
        )
        return latest_item, latency_ms

    def sign_item_assets(self, item: Item) -> tuple[Item, float]:
        start = perf_counter()
        try:
            signed = planetary_computer.sign(item)
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"SAS signing failed: {type(exc).__name__}",
                code="SATELLITE_SAS_SIGN_FAILED",
                retryable=True,
            ) from exc
        latency_ms = round((perf_counter() - start) * 1000, 2)
        return signed, latency_ms

    def probe_download(self, *, url: str, max_bytes: int = 65536) -> tuple[int, float]:
        start = perf_counter()
        try:
            response = requests.get(
                url,
                stream=True,
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded >= max_bytes:
                    break
            response.close()
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"Band download probe failed: {type(exc).__name__}",
                code="SATELLITE_BAND_DOWNLOAD_FAILED",
                retryable=True,
            ) from exc
        latency_ms = round((perf_counter() - start) * 1000, 2)
        return downloaded, latency_ms

    @staticmethod
    def get_float_property(item: Item, key: str) -> float | None:
        raw: Any = item.properties.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
