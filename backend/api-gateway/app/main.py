from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import emit_audit_event
from app.core.correlation import CorrelationIdMiddleware
from app.core.errors import DomainError, SystemError, ValidationError
from app.core.logging import configure_logging, log_event
from app.core.request_context import set_application_id
from app.db import get_db
from app.models import FarmerReference, LoanApplication, RiskAssessment
from app.services.assessment_orchestrator import AssessmentOrchestrator
from app.services.satellite.connectivity_check import SatelliteConnectivityChecker
from app.services.satellite.feature_extractor import SatelliteFeatureExtractor
from app.services.satellite.models import ConnectivityCheckResult, SatelliteFeatureResult
from app.schemas import (
    AnalyzeFarmRequest,
    AnalyzeFarmResponse,
    ApplicationStatus,
    BankerApplicationItem,
    BankerApplicationsResponse,
    DebtLayerScore,
    DecisionRequest,
    DecisionResponse,
    LayerScore,
    RiskScoreMetadata,
    RiskScoreResponse,
)


app = FastAPI(title="Orbital Credit API Gateway", version="0.1.0")
app.add_middleware(CorrelationIdMiddleware)


@app.on_event("startup")
def on_startup() -> None:
    configure_logging()


def _error_payload(
    request: Request,
    *,
    code: str,
    message: str,
    retryable: bool,
) -> dict[str, dict[str, str | bool | None]]:
    return {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": getattr(request.state, "correlation_id", None),
            "retryable": retryable,
        }
    }


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    log_event(
        level="ERROR",
        event="domain_error",
        payload={
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            request,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
        ),
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    err = ValidationError(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        retryable=False,
    )
    log_event(
        level="ERROR",
        event="request_validation_error",
        payload={"errors": exc.errors(), "path": request.url.path},
    )
    return JSONResponse(
        status_code=err.status_code,
        content=_error_payload(
            request,
            code=err.code,
            message=err.message,
            retryable=err.retryable,
        ),
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    detail = str(exc.detail) if exc.detail else "Request failed"
    log_event(
        level="ERROR",
        event="http_exception",
        payload={"status_code": exc.status_code, "detail": detail, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            request,
            code=f"HTTP_{exc.status_code}",
            message=detail,
            retryable=False,
        ),
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    err = SystemError(code="INTERNAL_ERROR", message="Internal server error")
    log_event(
        level="ERROR",
        event="unhandled_exception",
        payload={"exception_type": type(exc).__name__, "path": request.url.path},
    )
    return JSONResponse(
        status_code=err.status_code,
        content=_error_payload(
            request,
            code=err.code,
            message=err.message,
            retryable=err.retryable,
        ),
    )


def _layer_status(score: int | None) -> str:
    return "available" if score is not None else "pending"


def _satellite_layer_status(assessment: RiskAssessment | None) -> str:
    if assessment is None:
        return "pending"
    if assessment.satellite_provider_status == "failed":
        return "unavailable"
    if assessment.satellite_score is not None:
        return "available"
    return "pending"


def _compute_overall_score(
    satellite_score: int,
    debt_score: int,
    social_score: int,
) -> int:
    return round((0.40 * satellite_score) + (0.35 * debt_score) + (0.25 * social_score))


def _evaluate_zone(payload: DecisionRequest) -> tuple[str, list[str]]:
    reasons: list[str] = []

    # Hard RED rules (highest precedence).
    if payload.satellite_no_crop_history:
        reasons.append("No crop history detected from satellite analysis")
        return "RED", reasons
    if payload.satellite_fire_detected:
        reasons.append("Fire signal detected in satellite analysis")
        return "RED", reasons
    if payload.debt_to_income_ratio > 0.50:
        reasons.append("Debt-to-income ratio exceeds 0.50")
        return "RED", reasons
    if payload.social_verified_references < 2:
        reasons.append("Fewer than 2 verified references")
        return "RED", reasons
    if payload.identity_verification_failed:
        reasons.append("Identity verification failed")
        return "RED", reasons

    # GREEN eligibility gates.
    satellite_green = (
        payload.satellite_score >= 80
        and payload.satellite_data_quality >= 0.80
        and not payload.satellite_fire_detected
    )
    debt_green = (
        payload.debt_to_income_ratio <= 0.30
        and payload.debt_status == "verified"
    )
    social_green = (
        payload.social_score >= 70
        and payload.social_verified_references == 2
    )
    if satellite_green and debt_green and social_green:
        reasons.append("All green eligibility gates satisfied")
        return "GREEN", reasons

    # Default YELLOW with primary reasons.
    if payload.satellite_data_quality < 0.80:
        reasons.append("Satellite data quality below 0.80")
    if payload.debt_status in {"timeout", "provider_unavailable", "consent_pending"}:
        reasons.append("Debt status is not fully verified")
    borderline = (
        (60 <= payload.satellite_score <= 79)
        or (0.31 <= payload.debt_to_income_ratio <= 0.50)
        or (40 <= payload.social_score <= 69)
    )
    if borderline:
        reasons.append("One or more inputs are in borderline range")
    if not reasons:
        reasons.append("Manual review required by safe default rule")
    return "YELLOW", reasons


@app.get("/health")
def healthcheck() -> dict[str, str]:
    log_event(event="healthcheck")
    return {"status": "ok"}


@app.get("/api/v1/satellite/connectivity-check", response_model=ConnectivityCheckResult)
def satellite_connectivity_check(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> ConnectivityCheckResult:
    checker = SatelliteConnectivityChecker()
    return checker.run(latitude=latitude, longitude=longitude)


@app.get("/api/v1/satellite/features", response_model=SatelliteFeatureResult)
def satellite_features(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> SatelliteFeatureResult:
    extractor = SatelliteFeatureExtractor()
    return extractor.extract(latitude=latitude, longitude=longitude)


@app.post("/api/v1/analyze-farm", response_model=AnalyzeFarmResponse, status_code=202)
def analyze_farm(
    payload: AnalyzeFarmRequest,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AnalyzeFarmResponse:
    log_event(
        event="analysis_received",
        payload={
            "banker_id": payload.banker_id,
            "loan_amount": payload.loan_amount,
            "farmer_mobile": payload.farmer_mobile,
            "gps_coordinates": {
                "latitude": payload.gps_coordinates.latitude,
                "longitude": payload.gps_coordinates.longitude,
            },
            "reference_count": len(payload.references),
        },
    )

    if idempotency_key:
        existing = db.execute(
            select(LoanApplication).where(LoanApplication.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing:
            request.state.application_id = str(existing.application_id)
            set_application_id(str(existing.application_id))
            log_event(
                event="analysis_idempotent_hit",
                application_id=str(existing.application_id),
                payload={"idempotency_key_present": True},
            )
            return AnalyzeFarmResponse(
                application_id=existing.application_id,
                status=ApplicationStatus(existing.status),
                message="Application already accepted for processing",
            )

    application = LoanApplication(
        banker_id=payload.banker_id,
        farmer_mobile=payload.farmer_mobile,
        loan_amount=payload.loan_amount,
        latitude=payload.gps_coordinates.latitude,
        longitude=payload.gps_coordinates.longitude,
        status=ApplicationStatus.processing.value,
        idempotency_key=idempotency_key,
    )
    db.add(application)
    db.flush()
    request.state.application_id = str(application.application_id)
    set_application_id(str(application.application_id))

    reference_rows = [
        FarmerReference(
            application_id=application.application_id,
            farmer_mobile=payload.farmer_mobile,
            reference_mobile=reference,
        )
        for reference in payload.references
    ]
    db.add_all(reference_rows)

    assessment = RiskAssessment(
        application_id=application.application_id,
        rationale="Risk assessment queued for satellite, debt, and social analysis",
        satellite_provider_status="pending",
        debt_status="pending",
        debt_provider_status="pending",
    )
    db.add(assessment)
    db.flush()

    orchestrator = AssessmentOrchestrator()
    orchestrator.run_satellite_assessment(
        db=db,
        application=application,
        assessment=assessment,
    )
    orchestrator.run_debt_assessment(
        db=db,
        application=application,
        assessment=assessment,
    )

    emit_audit_event(
        db=db,
        event="application_created",
        actor_type="banker",
        actor_id=payload.banker_id,
        application_id=application.application_id,
        payload={
            "loan_amount": payload.loan_amount,
            "farmer_mobile": payload.farmer_mobile,
            "reference_count": len(payload.references),
            "upstream_dependency": "none",
        },
    )
    db.commit()
    log_event(
        event="analysis_queued",
        application_id=str(application.application_id),
        payload={"status": "processing"},
    )

    return AnalyzeFarmResponse(
        application_id=application.application_id,
        status=ApplicationStatus.processing,
        message="Application accepted for processing",
    )


@app.get("/api/v1/risk-score/{application_id}", response_model=RiskScoreResponse)
def get_risk_score(
    application_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> RiskScoreResponse:
    request.state.application_id = str(application_id)
    set_application_id(str(application_id))
    application = db.get(LoanApplication, application_id)
    if application is None:
        raise ValidationError(
            code="APPLICATION_NOT_FOUND",
            message="Application not found",
            status_code=404,
            retryable=False,
        )

    assessment = db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.application_id == application_id)
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    end_time = assessment.created_at if assessment else datetime.now(timezone.utc)
    processing_seconds = max(0, int((end_time - application.created_at).total_seconds()))
    log_event(
        event="risk_score_requested",
        application_id=str(application_id),
        payload={"processing_time_seconds": processing_seconds},
    )

    if assessment is None:
        return RiskScoreResponse(
            application_id=application.application_id,
            satellite=LayerScore(score=None, status="pending", quality=None, provider_status="pending", flags=[]),
            debt=DebtLayerScore(
                score=None,
                status="pending",
                provider_status="pending",
                flags=[],
                existing_debt=None,
                proposed_debt=None,
                estimated_income=None,
                debt_to_income_ratio=None,
            ),
            social=LayerScore(score=None, status="pending"),
            overall_score=None,
            traffic_light_status=None,
            rationale="Risk assessment is still processing",
            metadata=RiskScoreMetadata(
                created_at=application.created_at,
                processing_time_seconds=processing_seconds,
                data_quality_flags=["assessment_pending"],
            ),
        )

    return RiskScoreResponse(
        application_id=application.application_id,
        satellite=LayerScore(
            score=assessment.satellite_score,
            status=_satellite_layer_status(assessment),
            quality=assessment.satellite_quality,
            provider_status=assessment.satellite_provider_status,
            flags=assessment.satellite_flags or [],
        ),
        debt=DebtLayerScore(
            score=assessment.debt_score,
            status=assessment.debt_status if assessment.debt_status else _layer_status(assessment.debt_score),
            provider_status=assessment.debt_provider_status,
            flags=assessment.debt_flags or [],
            existing_debt=assessment.debt_existing_amount,
            proposed_debt=assessment.debt_proposed_amount,
            estimated_income=assessment.debt_estimated_income,
            debt_to_income_ratio=assessment.debt_to_income_ratio,
        ),
        social=LayerScore(
            score=assessment.social_score,
            status=_layer_status(assessment.social_score),
        ),
        overall_score=assessment.overall_score,
        traffic_light_status=assessment.traffic_light_status,
        rationale=assessment.rationale,
        metadata=RiskScoreMetadata(
            created_at=assessment.created_at,
            processing_time_seconds=processing_seconds,
            data_quality_flags=(
                []
                if (
                    assessment.satellite_score is not None
                    and assessment.debt_score is not None
                    and assessment.social_score is not None
                )
                else (assessment.satellite_flags or []) + ["assessment_incomplete"]
            ),
        ),
    )


@app.get("/api/v1/applications/{banker_id}", response_model=BankerApplicationsResponse)
def get_banker_applications(
    banker_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> BankerApplicationsResponse:
    request.state.application_id = None
    set_application_id(None)
    applications = db.execute(
        select(LoanApplication)
        .where(LoanApplication.banker_id == banker_id)
        .order_by(LoanApplication.created_at.desc())
    ).scalars().all()
    log_event(
        event="banker_applications_requested",
        payload={"banker_id": banker_id, "count": len(applications)},
    )

    response_items: list[BankerApplicationItem] = []
    for application in applications:
        latest_assessment = db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.application_id == application.application_id)
            .order_by(RiskAssessment.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        response_items.append(
            BankerApplicationItem(
                application_id=application.application_id,
                farmer_mobile=application.farmer_mobile,
                loan_amount=application.loan_amount,
                status=application.status,
                created_at=application.created_at,
                overall_score=(
                    latest_assessment.overall_score if latest_assessment else None
                ),
                traffic_light_status=(
                    latest_assessment.traffic_light_status
                    if latest_assessment
                    else None
                ),
            )
        )

    return BankerApplicationsResponse(
        banker_id=banker_id,
        applications=response_items,
    )


@app.post("/api/v1/decisions/{application_id}", response_model=DecisionResponse)
def post_decision(
    application_id: UUID,
    payload: DecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> DecisionResponse:
    request.state.application_id = str(application_id)
    set_application_id(str(application_id))
    application = db.get(LoanApplication, application_id)
    if application is None:
        raise ValidationError(
            code="APPLICATION_NOT_FOUND",
            message="Application not found",
            status_code=404,
            retryable=False,
        )

    overall_score = _compute_overall_score(
        satellite_score=payload.satellite_score,
        debt_score=payload.debt_score,
        social_score=payload.social_score,
    )
    zone, reasons = _evaluate_zone(payload)
    rationale = payload.rationale_override or "; ".join(reasons[:3])

    assessment = db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.application_id == application_id)
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if assessment is None:
        assessment = RiskAssessment(application_id=application_id)
        db.add(assessment)
        db.flush()

    assessment.satellite_score = payload.satellite_score
    assessment.debt_score = payload.debt_score
    assessment.social_score = payload.social_score
    assessment.overall_score = overall_score
    assessment.traffic_light_status = zone
    assessment.rationale = rationale

    application.status = ApplicationStatus.completed.value

    emit_audit_event(
        db=db,
        event="decision_finalized",
        actor_type="service",
        actor_id=payload.actor_id,
        application_id=application_id,
        payload={
            "overall_score": overall_score,
            "traffic_light_status": zone,
            "debt_to_income_ratio": payload.debt_to_income_ratio,
            "debt_status": payload.debt_status.value,
            "reasons": reasons[:3],
            "upstream_dependency": "decision-engine",
        },
    )
    db.commit()
    db.refresh(assessment)
    log_event(
        event="decision_finalized",
        application_id=str(application_id),
        payload={
            "overall_score": overall_score,
            "traffic_light_status": zone,
            "upstream_dependency": "decision-engine",
        },
    )

    return DecisionResponse(
        application_id=application_id,
        assessment_id=assessment.assessment_id,
        overall_score=overall_score,
        traffic_light_status=zone,
        status=ApplicationStatus.completed,
        rationale=rationale,
    )
