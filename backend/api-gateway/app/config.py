from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = (
        "postgresql+psycopg://orbital_user:orbital_pass@localhost:5432/orbital_credit"
    )
    satellite_stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    satellite_collection_id: str = "sentinel-2-l2a"
    satellite_search_lookback_days: int = 60
    satellite_max_cloud_cover: float = 40.0
    satellite_request_timeout_seconds: float = 30.0
    satellite_feature_history_years: int = 3
    satellite_feature_max_scenes: int = 18
    satellite_peak_min_ndvi: float = 0.35
    satellite_peak_min_gap_days: int = 45
    satellite_fire_nbr_threshold: float = 0.10
    satellite_fire_ndvi_drop_threshold: float = 0.20
    satellite_retry_attempts: int = 3
    satellite_retry_base_delay_seconds: float = 0.5
    satellite_circuit_breaker_failure_threshold: int = 5
    satellite_circuit_breaker_reset_seconds: int = 60
    debt_provider_mode: str = "mock"
    debt_request_timeout_seconds: float = 5.0
    debt_retry_attempts: int = 2
    debt_retry_base_delay_seconds: float = 0.25
    debt_circuit_breaker_failure_threshold: int = 3
    debt_circuit_breaker_reset_seconds: int = 60
    social_provider_mode: str = "mock"
    social_request_timeout_seconds: float = 5.0
    social_retry_attempts: int = 2
    social_retry_base_delay_seconds: float = 0.25
    social_circuit_breaker_failure_threshold: int = 3
    social_circuit_breaker_reset_seconds: int = 60
    social_default_penalty_farmer_points: int = 12
    social_default_penalty_reference_points: int = 8
    decision_rule_version: str = "decision-rules-v1.0.0"


settings = Settings()
