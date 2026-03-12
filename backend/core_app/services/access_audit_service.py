from __future__ import annotations

import logging
import uuid

from sqlalchemy import text

from core_app.db.session import get_db_session_ctx
from core_app.models.access_audit_log import AccessAuditLog, AccessDecision

logger = logging.getLogger(__name__)


class AccessAuditService:
    """Write-once access audit entries.

    This is intentionally isolated from request transaction state so that
    access denials are still persisted even when the request is rejected.
    """

    def log_access(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_role: str,
        required_role: str,
        path: str,
        method: str,
        decision: AccessDecision,
        reason: str | None,
        correlation_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        try:
            with get_db_session_ctx() as db:
                # Enforce RLS scope for this write.
                db.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": str(tenant_id)},
                )
                db.add(
                    AccessAuditLog(
                        tenant_id=tenant_id,
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        required_role=required_role,
                        path=path[:512],
                        method=method[:16],
                        decision=decision.value,
                        reason=reason[:255] if reason else None,
                        correlation_id=correlation_id[:64] if correlation_id else None,
                        ip_address=ip_address[:64] if ip_address else None,
                        user_agent=user_agent[:255] if user_agent else None,
                    )
                )
                db.commit()
        except Exception:
            # Never break request flow due to audit write failure.
            logger.exception(
                "access_audit_log_write_failed tenant_id=%s actor_user_id=%s path=%s",
                str(tenant_id),
                str(actor_user_id),
                path,
            )
