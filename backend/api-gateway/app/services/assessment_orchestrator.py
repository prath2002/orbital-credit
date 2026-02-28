from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.audit import emit_audit_event
from app.core.logging import log_event
from app.models import LoanApplication, RiskAssessment
from app.services.satellite.feature_extractor import SatelliteFeatureExtractor


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _compute_satellite_score(
    *,
    ndvi_score: int,
    volatility: float,
    fire_detected: bool,
    fire_signal_score: float,
    data_quality: float,
) -> int:
    score = float(ndvi_score)
    score -= min(25.0, volatility * 25.0)
    score -= min(30.0, fire_signal_score * 30.0)
    if fire_detected:
        score = min(score, 20.0)
    if data_quality < 0.8:
        score -= min(20.0, (0.8 - data_quality) * 100.0 * 0.2)
    return _clamp_score(round(score))


class AssessmentOrchestrator:
    def __init__(self, extractor: SatelliteFeatureExtractor | None = None) -> None:
        self.extractor = extractor or SatelliteFeatureExtractor()

    def run_satellite_assessment(
        self,
        *,
        db: Session,
        application: LoanApplication,
        assessment: RiskAssessment,
    ) -> None:
        try:
            features = self.extractor.extract(
                latitude=application.latitude,
                longitude=application.longitude,
            )
            satellite_score = _compute_satellite_score(
                ndvi_score=features.ndvi_score,
                volatility=features.volatility,
                fire_detected=features.fire_detected,
                fire_signal_score=features.fire_signal_score,
                data_quality=features.data_quality,
            )
            flags = list(features.data_quality_flags)
            flags.append(f"crop_cycle:{features.crop_cycle}")
            if features.fire_detected:
                flags.append("fire_detected")
            if features.provider_degraded:
                flags.append("provider_degraded")
            flags = sorted(set(flags))

            assessment.satellite_score = satellite_score
            assessment.satellite_quality = features.data_quality
            assessment.satellite_flags = flags
            assessment.satellite_provider_status = (
                "degraded" if features.provider_degraded else "available"
            )
            assessment.satellite_computed_at = datetime.now(timezone.utc)

            emit_audit_event(
                db=db,
                event="satellite_assessment_completed",
                actor_type="service",
                actor_id="SATELLITE-SERVICE",
                application_id=application.application_id,
                payload={
                    "satellite_score": satellite_score,
                    "satellite_quality": features.data_quality,
                    "satellite_provider_status": assessment.satellite_provider_status,
                    "flags": flags,
                    "fire_detected": features.fire_detected,
                    "upstream_dependency": "planetary-computer",
                },
            )
            log_event(
                event="assessment_satellite_persisted",
                application_id=str(application.application_id),
                payload={
                    "satellite_score": satellite_score,
                    "satellite_quality": features.data_quality,
                    "satellite_provider_status": assessment.satellite_provider_status,
                    "flag_count": len(flags),
                },
            )
        except Exception as exc:  # pragma: no cover - provider failure path
            assessment.satellite_score = None
            assessment.satellite_quality = 0.0
            assessment.satellite_flags = [f"satellite_error:{type(exc).__name__}"]
            assessment.satellite_provider_status = "failed"
            assessment.satellite_computed_at = datetime.now(timezone.utc)
            emit_audit_event(
                db=db,
                event="satellite_assessment_failed",
                actor_type="service",
                actor_id="SATELLITE-SERVICE",
                application_id=application.application_id,
                payload={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "upstream_dependency": "planetary-computer",
                },
            )
            log_event(
                level="ERROR",
                event="assessment_satellite_failed",
                application_id=str(application.application_id),
                payload={"error_type": type(exc).__name__},
            )
