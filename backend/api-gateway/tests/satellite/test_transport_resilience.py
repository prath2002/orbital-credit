from __future__ import annotations

import pytest

from app.services.satellite.exceptions import SatelliteServiceError
from app.services.satellite.transport import SatelliteTransport


class _FailingCatalog:
    def search(self, **_: object) -> object:
        raise RuntimeError("simulated_provider_failure")


def test_transport_retries_then_opens_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.satellite import transport as transport_module

    monkeypatch.setattr(transport_module.Client, "open", lambda *_args, **_kwargs: _FailingCatalog())
    monkeypatch.setattr(transport_module, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(transport_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    monkeypatch.setattr(transport_module.settings, "satellite_retry_attempts", 2)
    monkeypatch.setattr(transport_module.settings, "satellite_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(transport_module.settings, "satellite_circuit_breaker_failure_threshold", 2)
    monkeypatch.setattr(transport_module.settings, "satellite_circuit_breaker_reset_seconds", 60)

    transport = SatelliteTransport(stac_url="https://planetarycomputer.microsoft.com/api/stac/v1")

    with pytest.raises(SatelliteServiceError) as first_exc:
        transport.search_latest_scene(latitude=23.0, longitude=72.0)
    assert first_exc.value.code == "SATELLITE_PROVIDER_RETRY_EXHAUSTED"

    with pytest.raises(SatelliteServiceError) as second_exc:
        transport.search_latest_scene(latitude=23.0, longitude=72.0)
    assert second_exc.value.code == "SATELLITE_PROVIDER_CIRCUIT_OPEN"
