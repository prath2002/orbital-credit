from __future__ import annotations

from app.config import settings
from app.core.logging import configure_logging, log_event
from app.db import SessionLocal
from app.services.retention import RetentionService


def main() -> None:
    configure_logging()
    db = SessionLocal()
    try:
        service = RetentionService(db)
        result = service.purge_older_than(retention_days=settings.data_retention_days)
        log_event(event="retention_purge_completed", payload=result)
    finally:
        db.close()


if __name__ == "__main__":
    main()

