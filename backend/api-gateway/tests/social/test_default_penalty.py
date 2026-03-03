from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.models import AuditEvent, JlgLinkage, LoanApplication, TrustNetwork
from app.services.social.penalty import SocialPenaltyService


class _FakeQuery:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def all(self) -> list[object]:
        return self._items


class _FakeDB:
    def __init__(
        self,
        *,
        trust_rows: list[TrustNetwork],
        linkages: list[JlgLinkage],
    ) -> None:
        self.trust_rows = trust_rows
        self.linkages = linkages
        self.items: list[object] = []

    def add(self, obj: object) -> None:
        self.items.append(obj)
        if isinstance(obj, TrustNetwork):
            self.trust_rows.append(obj)

    def query(self, model: object) -> _FakeQuery:
        if model is TrustNetwork:
            return _FakeQuery(self.trust_rows)  # type: ignore[arg-type]
        if model is JlgLinkage:
            return _FakeQuery(self.linkages)  # type: ignore[arg-type]
        return _FakeQuery([])


def test_default_penalty_updates_farmer_references_and_linkages() -> None:
    application = LoanApplication(
        application_id=uuid.uuid4(),
        banker_id="BANKER-1",
        farmer_mobile="+919999999990",
        loan_amount=30000,
        latitude=28.6139,
        longitude=77.2090,
        status="completed",
    )
    trust_rows = [
        TrustNetwork(farmer_mobile=application.farmer_mobile, trust_score=60),
        TrustNetwork(farmer_mobile="+919111111112", trust_score=50),
        TrustNetwork(farmer_mobile="+919222222229", trust_score=20),
    ]
    linkages = [
        JlgLinkage(
            linkage_id=uuid.uuid4(),
            application_id=application.application_id,
            farmer_mobile=application.farmer_mobile,
            reference_mobile="+919111111112",
            linkage_status="active",
            linked_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        JlgLinkage(
            linkage_id=uuid.uuid4(),
            application_id=application.application_id,
            farmer_mobile=application.farmer_mobile,
            reference_mobile="+919222222229",
            linkage_status="pending",
            linked_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    db = _FakeDB(trust_rows=trust_rows, linkages=linkages)
    service = SocialPenaltyService()

    result = service.apply_default_event_penalty(db=db, application=application)

    assert result.farmer_trust_before == 60
    assert result.farmer_trust_after == 48
    assert len(result.impacted_references) == 2
    ref_after = {row.farmer_mobile: row.trust_score for row in db.trust_rows}
    assert ref_after["+919111111112"] == 42
    assert ref_after["+919222222229"] == 12
    assert all(linkage.linkage_status == "default_impacted" for linkage in db.linkages)
    assert any(
        isinstance(item, AuditEvent) and item.event_type == "social_default_penalty_applied"
        for item in db.items
    )

