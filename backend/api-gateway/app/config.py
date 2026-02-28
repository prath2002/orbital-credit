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


settings = Settings()
