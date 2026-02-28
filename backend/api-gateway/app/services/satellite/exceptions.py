from __future__ import annotations

from app.core.errors import ProviderError


class SatelliteServiceError(ProviderError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "SATELLITE_SERVICE_ERROR",
        retryable: bool = True,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=502,
            retryable=retryable,
        )


class SatelliteSceneNotFoundError(SatelliteServiceError):
    def __init__(self, message: str = "No Sentinel-2 scene found for location/time window") -> None:
        super().__init__(message=message, code="SATELLITE_SCENE_NOT_FOUND", retryable=False)


class SatelliteAssetMissingError(SatelliteServiceError):
    def __init__(self, band: str) -> None:
        super().__init__(
            message=f"Required satellite asset missing for band {band}",
            code="SATELLITE_ASSET_MISSING",
            retryable=False,
        )


class SatellitePropertyMissingError(SatelliteServiceError):
    def __init__(self, prop: str) -> None:
        super().__init__(
            message=f"Required satellite property missing: {prop}",
            code="SATELLITE_PROPERTY_MISSING",
            retryable=False,
        )
