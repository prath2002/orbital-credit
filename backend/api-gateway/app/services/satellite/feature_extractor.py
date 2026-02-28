from __future__ import annotations

from datetime import datetime
from statistics import mean, pstdev
from time import perf_counter

from app.config import settings
from app.core.logging import log_event
from app.services.satellite.exceptions import (
    SatelliteAssetMissingError,
    SatelliteComputationError,
)
from app.services.satellite.models import NdviSample, SatelliteFeatureResult
from app.services.satellite.transport import SatelliteTransport


class SatelliteFeatureExtractor:
    def __init__(self, transport: SatelliteTransport | None = None) -> None:
        self.transport = transport or SatelliteTransport(
            stac_url=settings.satellite_stac_url,
            collection_id=settings.satellite_collection_id,
            request_timeout_seconds=settings.satellite_request_timeout_seconds,
        )

    def extract(self, *, latitude: float, longitude: float) -> SatelliteFeatureResult:
        start = perf_counter()
        scenes, search_latency_ms = self.transport.search_scene_series(
            latitude=latitude,
            longitude=longitude,
            history_years=settings.satellite_feature_history_years,
            max_cloud_cover=settings.satellite_max_cloud_cover,
            limit=settings.satellite_feature_max_scenes,
        )

        samples: list[NdviSample] = []
        signing_latency_ms = 0.0
        sampling_latency_ms = 0.0
        skipped_assets = 0
        failed_samples = 0
        missing_fire_band = 0
        quality_flags: set[str] = set()

        for scene in scenes:
            signed, sign_latency = self.transport.sign_item_assets(scene)
            signing_latency_ms += sign_latency
            b04 = signed.assets.get("B04")
            b08 = signed.assets.get("B08")
            if b04 is None or b08 is None:
                skipped_assets += 1
                quality_flags.add("missing_primary_bands")
                continue
            acquired_at = signed.datetime or _parse_dt(signed.properties.get("datetime"))
            if acquired_at is None:
                skipped_assets += 1
                quality_flags.add("missing_scene_datetime")
                continue

            band_urls: dict[str, str] = {"B04": str(b04.href), "B08": str(b08.href)}
            b12 = signed.assets.get("B12")
            if b12 is not None:
                band_urls["B12"] = str(b12.href)
            else:
                missing_fire_band += 1

            try:
                band_values, sample_latency = self.transport.sample_band_values_at_point(
                    band_urls=band_urls,
                    latitude=latitude,
                    longitude=longitude,
                )
            except Exception:
                failed_samples += 1
                quality_flags.add("sampling_failure")
                continue
            sampling_latency_ms += sample_latency

            ndvi = _compute_index(band_values["B08"], band_values["B04"])
            nbr: float | None = None
            if "B12" in band_values:
                nbr = _compute_index(band_values["B08"], band_values["B12"])
            samples.append(
                NdviSample(
                    scene_id=signed.id,
                    acquired_at=acquired_at,
                    ndvi=round(ndvi, 5),
                    nbr=round(nbr, 5) if nbr is not None else None,
                    cloud_cover=self.transport.get_float_property(signed, "eo:cloud_cover"),
                )
            )

        if not samples:
            if skipped_assets > 0:
                raise SatelliteAssetMissingError("B04/B08")
            raise SatelliteComputationError("No NDVI samples available for feature extraction")

        samples.sort(key=lambda s: s.acquired_at)
        ndvi_values = [s.ndvi for s in samples]
        latest = samples[-1]
        ndvi_score = _to_ndvi_score(latest.ndvi)

        volatility = _compute_volatility(ndvi_values)
        peak_count = _count_peaks(
            samples=samples,
            min_ndvi=settings.satellite_peak_min_ndvi,
            min_gap_days=settings.satellite_peak_min_gap_days,
        )
        cycles_per_year = _cycles_per_year(samples=samples, peak_count=peak_count)
        crop_cycle = _classify_crop_cycle(cycles_per_year=cycles_per_year, ndvi_values=ndvi_values)
        fire_detected, fire_signal_score = _detect_fire_signal(samples=samples)
        data_quality, quality_flag_list = _compute_data_quality(
            samples=samples,
            requested_scene_count=len(scenes),
            failed_samples=failed_samples,
            missing_fire_band=missing_fire_band,
            base_flags=quality_flags,
        )
        provider_degraded = failed_samples > 0 or skipped_assets > 0
        total_latency_ms = round((perf_counter() - start) * 1000, 2)

        result = SatelliteFeatureResult(
            ndvi_score=ndvi_score,
            crop_cycle=crop_cycle,
            volatility=round(volatility, 5),
            fire_detected=fire_detected,
            fire_signal_score=round(fire_signal_score, 5),
            data_quality=round(data_quality, 5),
            data_quality_flags=quality_flag_list,
            provider_degraded=provider_degraded,
            sample_count=len(samples),
            peak_count=peak_count,
            cycles_per_year=round(cycles_per_year, 4),
            latest_scene_id=latest.scene_id,
            latest_acquired_at=latest.acquired_at,
            ndvi_series=samples,
            processing_latency_ms=total_latency_ms,
        )
        log_event(
            event="satellite_features_computed",
            payload={
                "upstream_dependency": "planetary-computer",
                "sample_count": len(samples),
                "ndvi_score": ndvi_score,
                "crop_cycle": crop_cycle,
                "volatility": result.volatility,
                "fire_detected": fire_detected,
                "fire_signal_score": result.fire_signal_score,
                "data_quality": result.data_quality,
                "data_quality_flags": result.data_quality_flags,
                "provider_degraded": provider_degraded,
                "peak_count": peak_count,
                "cycles_per_year": result.cycles_per_year,
                "failed_samples": failed_samples,
                "missing_fire_band": missing_fire_band,
                "search_latency_ms": search_latency_ms,
                "signing_latency_ms": round(signing_latency_ms, 2),
                "sampling_latency_ms": round(sampling_latency_ms, 2),
                "processing_latency_ms": total_latency_ms,
            },
        )
        return result


def _parse_dt(raw: object) -> datetime | None:
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _to_ndvi_score(ndvi: float) -> int:
    score = ((ndvi + 1.0) / 2.0) * 100.0
    return max(0, min(100, round(score)))


def _compute_volatility(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    if abs(avg) < 1e-9:
        return 1.0
    return pstdev(values) / abs(avg)


def _count_peaks(*, samples: list[NdviSample], min_ndvi: float, min_gap_days: int) -> int:
    if len(samples) < 3:
        return 0
    peak_indices: list[int] = []
    for idx in range(1, len(samples) - 1):
        prev_ndvi = samples[idx - 1].ndvi
        curr_ndvi = samples[idx].ndvi
        next_ndvi = samples[idx + 1].ndvi
        if curr_ndvi < min_ndvi:
            continue
        if curr_ndvi > prev_ndvi and curr_ndvi > next_ndvi:
            if not peak_indices:
                peak_indices.append(idx)
                continue
            last_peak_time = samples[peak_indices[-1]].acquired_at
            delta_days = (samples[idx].acquired_at - last_peak_time).days
            if delta_days >= min_gap_days:
                peak_indices.append(idx)
    return len(peak_indices)


def _cycles_per_year(*, samples: list[NdviSample], peak_count: int) -> float:
    if peak_count == 0 or len(samples) < 2:
        return 0.0
    days = max(1, (samples[-1].acquired_at - samples[0].acquired_at).days)
    years = max(1.0 / 12.0, days / 365.25)
    return peak_count / years


def _classify_crop_cycle(*, cycles_per_year: float, ndvi_values: list[float]) -> str:
    avg_ndvi = mean(ndvi_values)
    if avg_ndvi < 0.2 and cycles_per_year == 0:
        return "none"
    if cycles_per_year >= 1.5:
        return "double"
    if cycles_per_year >= 0.5:
        return "single"
    return "uncertain"


def _compute_index(high_band: float, low_band: float) -> float:
    if high_band < 0 or low_band < 0:
        raise SatelliteComputationError("Negative reflectance encountered", retryable=False)
    denominator = high_band + low_band
    if denominator == 0:
        raise SatelliteComputationError("Index denominator is zero", retryable=False)
    value = (high_band - low_band) / denominator
    return max(-1.0, min(1.0, float(value)))


def _detect_fire_signal(*, samples: list[NdviSample]) -> tuple[bool, float]:
    nbr_values = [sample.nbr for sample in samples if sample.nbr is not None]
    if not nbr_values:
        return False, 0.0
    latest = samples[-1]
    latest_nbr = latest.nbr if latest.nbr is not None else nbr_values[-1]
    previous_ndvi = [sample.ndvi for sample in samples[:-1]]
    baseline_ndvi = mean(previous_ndvi) if previous_ndvi else latest.ndvi
    ndvi_drop = max(0.0, baseline_ndvi - latest.ndvi)
    low_nbr_signal = max(0.0, (settings.satellite_fire_nbr_threshold - latest_nbr) / 0.25)
    ndvi_drop_signal = max(0.0, ndvi_drop / max(0.05, settings.satellite_fire_ndvi_drop_threshold))
    signal = min(1.0, 0.6 * low_nbr_signal + 0.4 * min(1.0, ndvi_drop_signal))
    fire_detected = latest_nbr <= settings.satellite_fire_nbr_threshold and ndvi_drop >= settings.satellite_fire_ndvi_drop_threshold
    return fire_detected, signal


def _compute_data_quality(
    *,
    samples: list[NdviSample],
    requested_scene_count: int,
    failed_samples: int,
    missing_fire_band: int,
    base_flags: set[str],
) -> tuple[float, list[str]]:
    score = 1.0
    flags = set(base_flags)
    sample_count = len(samples)
    if sample_count < 6:
        score -= 0.30
        flags.add("low_sample_count")
    elif sample_count < 10:
        score -= 0.15
        flags.add("moderate_sample_count")

    cloud_values = [s.cloud_cover for s in samples if s.cloud_cover is not None]
    avg_cloud = mean(cloud_values) if cloud_values else 100.0
    cloud_penalty = min(0.40, (avg_cloud / 100.0) * 0.40)
    score -= cloud_penalty
    if avg_cloud > 20:
        flags.add("high_cloud_cover")

    total_requested = max(1, requested_scene_count)
    failure_ratio = failed_samples / total_requested
    if failure_ratio > 0:
        score -= min(0.35, failure_ratio * 0.35)
        flags.add("provider_sampling_partial_failure")

    missing_fire_ratio = missing_fire_band / total_requested
    if missing_fire_ratio > 0:
        score -= min(0.15, missing_fire_ratio * 0.15)
        flags.add("missing_fire_band_b12")

    ndvi_values = [s.ndvi for s in samples]
    if len(ndvi_values) > 1:
        if (max(ndvi_values) - min(ndvi_values)) < 0.03:
            score -= 0.10
            flags.add("low_temporal_variation")
    else:
        score -= 0.20
        flags.add("single_sample")

    return max(0.0, min(1.0, score)), sorted(flags)
