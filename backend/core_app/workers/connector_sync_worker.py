"""Connector sync worker utilities.

Polls queued connector sync jobs and executes them via ConnectorRuntimeService.
"""
from __future__ import annotations

import logging
import uuid

from core_app.db.session import get_db_session_ctx
from core_app.services.connector_runtime_service import ConnectorRuntimeService

logger = logging.getLogger(__name__)


def process_connector_sync_batch(
    *,
    limit: int = 10,
    actor_user_id: uuid.UUID | None = None,
) -> int:
    """Process a bounded batch of queued connector sync jobs."""

    with get_db_session_ctx() as db:
        svc = ConnectorRuntimeService(db)
        processed = svc.process_queued_jobs(limit=limit, actor_user_id=actor_user_id)
        if processed:
            logger.info("connector_sync_worker_processed_jobs count=%d", processed)
        return processed
