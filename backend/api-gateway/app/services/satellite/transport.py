from __future__ import annotations

from datetime import date, timedelta
import random
from time import perf_counter, sleep
from typing import Any, Callable

import planetary_computer
import rasterio
import requests
from pystac import Item
from pystac_client import Client
from rasterio.warp import transform

from app.config import settings
from app.core.logging import log_event
from app.services.satellite.exceptions import (
    SatelliteCircuitOpenError,
    SatelliteSceneNotFoundError,
    SatelliteServiceError,
)
from app.services.satellite.resilience import CircuitBreaker


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
        self._breakers: dict[str, CircuitBreaker] = {}

    def _breaker_for(self, operation: str) -> CircuitBreaker:
        breaker = self._breakers.get(operation)
        if breaker is None:
            breaker = CircuitBreaker(
                failure_threshold=settings.satellite_circuit_breaker_failure_threshold,
                reset_seconds=settings.satellite_circuit_breaker_reset_seconds,
            )
            self._breakers[operation] = breaker
        return breaker

    def _execute_with_resilience(self, operation: str, fn: Callable[[], Any]) -> Any:
        breaker = self._breaker_for(operation)
        if not breaker.allow_request():
            log_event(
                level="ERROR",
                event="satellite_circuit_open",
                payload={"operation": operation, "failure_count": breaker.failure_count},
            )
            raise SatelliteCircuitOpenError(operation)

        delay = settings.satellite_retry_base_delay_seconds
        attempts = max(1, settings.satellite_retry_attempts)
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = fn()
                breaker.record_success()
                if attempt > 1:
                    log_event(
                        event="satellite_retry_recovered",
                        payload={"operation": operation, "attempt": attempt},
                    )
                return result
            except Exception as exc:  # pragma: no cover - resilience path
                last_exc = exc
                breaker.record_failure(type(exc).__name__)
                log_event(
                    level="ERROR",
                    event="satellite_operation_failed",
                    payload={
                        "operation": operation,
                        "attempt": attempt,
                        "max_attempts": attempts,
                        "error": type(exc).__name__,
                        "circuit_state": breaker.state,
                        "failure_count": breaker.failure_count,
                    },
                )
                if attempt >= attempts:
                    break
                jitter = random.uniform(0.0, 0.25)
                sleep(delay + jitter)
                delay *= 2
        raise SatelliteServiceError(
            message=f"{operation} failed after retries: {type(last_exc).__name__ if last_exc else 'unknown'}",
            code="SATELLITE_PROVIDER_RETRY_EXHAUSTED",
            retryable=True,
        ) from last_exc

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
            items = self._execute_with_resilience(
                "stac_search_latest",
                lambda: list(
                    self._catalog.search(
                        collections=[self.collection_id],
                        intersects={"type": "Point", "coordinates": [longitude, latitude]},
                        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
                        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
                    ).items()
                ),
            )
        except SatelliteServiceError:
            raise
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"STAC search failed: {type(exc).__name__}",
                code="SATELLITE_STAC_SEARCH_FAILED",
                retryable=True,
            ) from exc

        latency_ms = round((perf_counter() - start) * 1000, 2)
        if not items:
            raise SatelliteSceneNotFoundError()

        latest_item = max(items, key=lambda item: item.properties.get("datetime", ""))
        return latest_item, latency_ms

    def search_scene_series(
        self,
        *,
        latitude: float,
        longitude: float,
        history_years: int = 3,
        max_cloud_cover: float = 40.0,
        limit: int = 18,
    ) -> tuple[list[Item], float]:
        start = perf_counter()
        end_date = date.today()
        start_date = end_date - timedelta(days=max(1, history_years) * 365)
        try:
            items = self._execute_with_resilience(
                "stac_search_series",
                lambda: list(
                    self._catalog.search(
                        collections=[self.collection_id],
                        intersects={"type": "Point", "coordinates": [longitude, latitude]},
                        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
                        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
                    ).items()
                ),
            )
        except SatelliteServiceError:
            raise
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"STAC series search failed: {type(exc).__name__}",
                code="SATELLITE_STAC_SERIES_SEARCH_FAILED",
                retryable=True,
            ) from exc

        latency_ms = round((perf_counter() - start) * 1000, 2)
        if not items:
            raise SatelliteSceneNotFoundError(
                "No Sentinel-2 historical scenes found for location/time window"
            )

        sorted_items = sorted(items, key=lambda item: item.properties.get("datetime", ""))
        if len(sorted_items) > limit:
            sorted_items = sorted_items[-limit:]
        return sorted_items, latency_ms

    def sign_item_assets(self, item: Item) -> tuple[Item, float]:
        start = perf_counter()
        try:
            signed = self._execute_with_resilience(
                "sas_sign_item",
                lambda: planetary_computer.sign(item),
            )
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

        def _download() -> int:
            response = requests.get(url, stream=True, timeout=self.request_timeout_seconds)
            response.raise_for_status()
            downloaded_inner = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                downloaded_inner += len(chunk)
                if downloaded_inner >= max_bytes:
                    break
            response.close()
            return downloaded_inner

        try:
            downloaded = self._execute_with_resilience("band_probe_download", _download)
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"Band download probe failed: {type(exc).__name__}",
                code="SATELLITE_BAND_DOWNLOAD_FAILED",
                retryable=True,
            ) from exc
        latency_ms = round((perf_counter() - start) * 1000, 2)
        return downloaded, latency_ms

    def sample_band_values_at_point(
        self,
        *,
        band_urls: dict[str, str],
        latitude: float,
        longitude: float,
    ) -> tuple[dict[str, float], float]:
        start = perf_counter()

        def _sample() -> dict[str, float]:
            output: dict[str, float] = {}
            with rasterio.Env():
                for band_name, band_url in band_urls.items():
                    with rasterio.open(band_url) as ds:
                        xs, ys = transform(
                            "EPSG:4326",
                            ds.crs.to_string(),
                            [longitude],
                            [latitude],
                        )
                        point = [(xs[0], ys[0])]
                        output[band_name] = float(next(ds.sample(point))[0])
            return output

        try:
            values = self._execute_with_resilience("band_value_sampling", _sample)
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"Band value sampling failed: {type(exc).__name__}",
                code="SATELLITE_BAND_VALUE_SAMPLING_FAILED",
                retryable=True,
            ) from exc
        latency_ms = round((perf_counter() - start) * 1000, 2)
        return values, latency_ms

    def sample_ndvi_at_point(
        self,
        *,
        b04_url: str,
        b08_url: str,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float]:
        start = perf_counter()
        try:
            samples, _ = self.sample_band_values_at_point(
                band_urls={"B04": b04_url, "B08": b08_url},
                latitude=latitude,
                longitude=longitude,
            )
            red_sample = samples["B04"]
            nir_sample = samples["B08"]
        except Exception as exc:  # pragma: no cover - external service path
            raise SatelliteServiceError(
                message=f"NDVI sampling failed: {type(exc).__name__}",
                code="SATELLITE_NDVI_SAMPLING_FAILED",
                retryable=True,
            ) from exc

        if red_sample < 0 or nir_sample < 0:
            raise SatelliteServiceError(
                message="Invalid negative reflectance values encountered during NDVI sampling",
                code="SATELLITE_INVALID_REFLECTANCE",
                retryable=False,
            )
        denominator = float(nir_sample + red_sample)
        if denominator == 0:
            raise SatelliteServiceError(
                message="Cannot compute NDVI due to zero denominator",
                code="SATELLITE_NDVI_ZERO_DENOMINATOR",
                retryable=False,
            )
        ndvi = float((nir_sample - red_sample) / denominator)
        ndvi = max(-1.0, min(1.0, ndvi))
        latency_ms = round((perf_counter() - start) * 1000, 2)
        return ndvi, latency_ms

    @staticmethod
    def get_float_property(item: Item, key: str) -> float | None:
        raw: Any = item.properties.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
