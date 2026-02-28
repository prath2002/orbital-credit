# Design Document: Orbital-Credit Autonomous Underwriting Agent (Implementation-Ready)

## 1. Purpose and Scope

Orbital-Credit is an underwriting platform for rural nano-loans (INR 20,000-50,000) where borrowers often lack formal income documents.

This design is implementation-ready and covers:
- Satellite-based farm productivity assessment
- Debt verification through Account Aggregator (AA)
- Social trust validation through 2 references
- Deterministic traffic-light decisioning (GREEN/YELLOW/RED)
- Banker-facing APIs and dashboard integration
- Security, observability, and operational requirements

Out of scope (Phase 1):
- ML-based replacement of core rule engine
- Multi-country compliance expansion

## 2. Architecture

### 2.1 Logical Components

- `api-gateway` (FastAPI): auth, request validation, orchestration, response shaping
- `satellite-service` (FastAPI/Python): Sentinel-2 retrieval, NDVI, crop cycles, volatility, fire signal
- `debt-service` (FastAPI/Python): AA consent + fetch, debt aggregation, debt-to-income ratio
- `social-trust-service` (FastAPI/Python): reference verification, trust score lookup/update, JLG registration
- `decision-engine` (library/service): final rule evaluation and rationale generation
- `dashboard` (Next.js/React): banker workflow UI

### 2.2 Runtime Dependencies

- PostgreSQL: transactional source of truth
- Redis: caching + idempotency keys + short-lived workflow state
- Object storage: optional archival of imagery metadata/derived artifacts
- External APIs: Google Earth Engine, AA provider, SMS/OTP provider

### 2.3 Deployment Pattern

Phase 1 recommendation: modular monolith (single deployable API with clear domain modules) for faster delivery.
Phase 2: split into independent services when load/team boundary requires it.

## 3. Canonical API Contracts

Base path: `/api/v1`

Primary endpoints:
- `POST /analyze-farm`
- `GET /risk-score/{application_id}`
- `GET /applications/{banker_id}`
- `POST /decisions/{application_id}`

Backward-compatible aliases (optional):
- `POST /analyze-farm` -> internally routed to `/api/v1/analyze-farm`
- `GET /risk-score/{application_id}` -> internally routed to `/api/v1/risk-score/{application_id}`

### 3.1 POST /api/v1/analyze-farm

Request fields:
- `gps_coordinates`: `{ latitude: float, longitude: float }`
- `farmer_mobile`: `+91XXXXXXXXXX`
- `loan_amount`: integer (`20000..50000`)
- `references`: list of exactly 2 mobile numbers
- `banker_id`: string

Synchronous response target: within 5 minutes for p95.
If orchestration exceeds timeout, return `202 Accepted` with polling handle.

### 3.2 GET /api/v1/risk-score/{application_id}

Returns:
- per-layer outputs (satellite, debt, social)
- `overall_score` (0-100)
- `traffic_light_status`
- human-readable rationale
- processing metadata (`created_at`, `processing_time_seconds`, `data_quality_flags`)

## 4. Data Model and Persistence

### 4.1 Core Entities

- `loan_applications`
- `risk_assessments`
- `trust_network`
- `farmer_references`
- `audit_events` (new, mandatory)

### 4.2 Mandatory Additions

Add `audit_events`:
- `event_id` UUID PK
- `application_id` UUID nullable
- `actor_type` (`system`,`banker`,`service`)
- `actor_id` string
- `event_type` string
- `payload_json` JSONB
- `created_at` timestamptz default now

Add indexes:
- `loan_applications (banker_id, created_at desc)`
- `risk_assessments (application_id, created_at desc)`
- `farmer_references (farmer_mobile)`
- `audit_events (application_id, created_at desc)`

## 5. End-to-End Processing Flow

1. Validate request schema and invariants (exactly 2 references, loan range, mobile format, GPS bounds).
2. Create application row with `processing` status and idempotency key.
3. Run satellite analysis, debt verification, and social verification concurrently.
4. Normalize each layer into `0..100` score + status flags.
5. Evaluate deterministic decision rules (see decision table file).
6. Persist `risk_assessments` and `audit_events`.
7. Return structured response and banker-facing explanation.

## 6. Layer Logic (Normative)

### 6.1 Satellite Layer

Inputs: GPS coordinates, 3 years of Sentinel-2 imagery.

Required computations:
- NDVI: `(NIR - Red) / (NIR + Red)`
- Crop cycle detection from NDVI peaks
- Volatility score = coefficient of variation
- Fire signal detection
- Data quality score from cloud coverage and missing windows

Classification:
- Single cropping: <= 1.5 peaks/year
- Double cropping: > 1.5 peaks/year

### 6.2 Debt Layer

- Retrieve liabilities from AA using explicit consent.
- Compute:
  - `existing_debt`
  - `proposed_debt = existing_debt + requested_loan_amount`
  - `debt_to_income_ratio = proposed_debt / estimated_income`
- Over-leveraged if `debt_to_income_ratio > 0.50`.

If consent denied/timeouts/provider outage:
- Mark debt status `unverified`
- Route final decision to YELLOW unless an independent RED rule already applies

### 6.3 Social Trust Layer

- Exactly 2 references are required at input validation.
- Both references must pass identity/contact verification for full social score.
- Create/update digital JLG linkages after verification.
- On borrower default event, reduce both references' trust scores and emit audit event.

## 7. Decisioning and Scoring

### 7.1 Score Composition

- Satellite score weight: 40%
- Debt score weight: 35%
- Social score weight: 25%

`overall_score = round(0.40*satellite + 0.35*debt + 0.25*social)`

Score clamped to `0..100`.

### 7.2 Rule Precedence

Rule precedence is strict and deterministic:
1. Hard RED rules
2. GREEN eligibility rules
3. Otherwise YELLOW

Authoritative rule matrix: `decision-rules-table.md`.

## 8. Error Handling and Resilience

- Retries for external dependencies: exponential backoff (1s, 2s, 4s), max 3 attempts
- Circuit breaker per external provider
- Partial-failure behavior:
  - Satellite low quality -> YELLOW
  - AA unavailable -> YELLOW
  - SMS verification outage -> YELLOW
- All failures must emit structured logs and `audit_events`

## 9. Security and Privacy Controls

- TLS for all API traffic
- Encryption at rest for PII columns
- Role-based access (`banker`, `ops_admin`, `system_service`)
- Immutable audit trail for read/write access to farmer data
- Data retention job for timed purge per policy

## 10. Performance and SLOs

- p95 end-to-end analysis <= 5 minutes
- repeated request for same farm served from cache <= 30 seconds
- availability target >= 99% during business hours

Implementation requirements:
- Redis cache key: hash(`coordinates`,`farmer_mobile`,`loan_amount`,`references`)
- idempotency key on POST analyze requests
- async task orchestration with bounded worker pools

## 11. Observability

- Correlation ID per request propagated across modules
- Metrics:
  - `analysis_latency_seconds`
  - `external_api_failures_total`
  - `decision_zone_count{zone}`
  - `data_quality_low_total`
- Logs: structured JSON with PII redaction

## 12. Testing and Verification

- Unit tests for calculators and validators
- Property-based tests for NDVI math and decision exclusivity
- Integration tests with mocked GEE/AA/SMS
- Contract tests for API response schema
- Load tests for p95 SLA and concurrency

## 13. Delivery Plan

- Milestone A: API skeleton, schema validation, persistence
- Milestone B: satellite + debt + social integrations with mocks
- Milestone C: decision engine, audit trail, dashboard APIs
- Milestone D: hardening (security, retries, observability, load tests)
