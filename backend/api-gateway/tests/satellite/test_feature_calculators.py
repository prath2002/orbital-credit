from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.satellite.exceptions import SatelliteComputationError
from app.services.satellite.feature_extractor import (
    _classify_crop_cycle,
    _compute_data_quality,
    _compute_index,
    _count_peaks,
    _cycles_per_year,
    _detect_fire_signal,
    _to_ndvi_score,
)
from app.services.satellite.models import NdviSample


def _sample(days: int, ndvi: float, nbr: float | None = None, cloud: float = 0.5) -> NdviSample:
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return NdviSample(
        scene_id=f"scene-{days}",
        acquired_at=base + timedelta(days=days),
        ndvi=ndvi,
        nbr=nbr,
        cloud_cover=cloud,
    )


def test_to_ndvi_score_bounds_and_midpoint() -> None:
    assert _to_ndvi_score(-1.0) == 0
    assert _to_ndvi_score(0.0) == 50
    assert _to_ndvi_score(1.0) == 100


def test_compute_index_validates_inputs() -> None:
    assert _compute_index(0.4, 0.2) == pytest.approx(0.3333333, rel=1e-5)
    with pytest.raises(SatelliteComputationError):
        _compute_index(-0.1, 0.2)
    with pytest.raises(SatelliteComputationError):
        _compute_index(0.0, 0.0)


def test_peak_cycle_and_classification_detect_double_cycle() -> None:
    samples = [
        _sample(0, 0.10),
        _sample(60, 0.52),
        _sample(120, 0.15),
        _sample(190, 0.58),
        _sample(260, 0.18),
        _sample(330, 0.20),
    ]
    peak_count = _count_peaks(samples=samples, min_ndvi=0.35, min_gap_days=45)
    cycles = _cycles_per_year(samples=samples, peak_count=peak_count)
    cycle_label = _classify_crop_cycle(
        cycles_per_year=cycles,
        ndvi_values=[s.ndvi for s in samples],
    )
    assert peak_count == 2
    assert cycles >= 1.5
    assert cycle_label == "double"


def test_detect_fire_signal_flags_fire_when_nbr_low_and_ndvi_drops() -> None:
    samples = [
        _sample(0, 0.62, 0.40),
        _sample(30, 0.58, 0.35),
        _sample(60, 0.51, 0.30),
        _sample(90, 0.18, 0.02),
    ]
    fire_detected, fire_signal_score = _detect_fire_signal(samples=samples)
    assert fire_detected is True
    assert 0.0 <= fire_signal_score <= 1.0


def test_compute_data_quality_adds_expected_flags() -> None:
    samples = [
        _sample(0, 0.20, 0.15, cloud=35.0),
        _sample(20, 0.19, 0.12, cloud=30.0),
        _sample(40, 0.21, 0.10, cloud=32.0),
    ]
    quality, flags = _compute_data_quality(
        samples=samples,
        requested_scene_count=10,
        failed_samples=3,
        missing_fire_band=4,
        base_flags={"sampling_failure"},
    )
    assert 0.0 <= quality <= 1.0
    assert "sampling_failure" in flags
    assert "low_sample_count" in flags
    assert "high_cloud_cover" in flags
    assert "provider_sampling_partial_failure" in flags
    assert "missing_fire_band_b12" in flags
