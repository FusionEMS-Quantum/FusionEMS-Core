"""AI Use-Case Registry Service — inventory, version, audit every AI feature."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.ai_platform import (
    AIDomainCopilot,
    AIPromptTemplate,
    AIUseCase,
    AIUseCaseAuditEvent,
    AIUseCaseVersion,
)
from core_app.schemas.ai_platform import (
    AIPromptTemplateCreate,
    AIPromptTemplateUpdate,
    AIUseCaseCreate,
    AIUseCaseUpdate,
)
from core_app.schemas.auth import CurrentUser


class AIRegistryService:

    def __init__(self, db: Session, user: CurrentUser) -> None:
        self._db = db
        self._user = user

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_use_cases(self, *, domain: str | None = None) -> Sequence[AIUseCase]:
        q = self._db.query(AIUseCase).filter(
            AIUseCase.tenant_id == self._user.tenant_id
        )
        if domain:
            q = q.filter(AIUseCase.domain == domain)
        return q.order_by(AIUseCase.name).all()

    def get_use_case(self, use_case_id: uuid.UUID) -> AIUseCase:
        uc = (
            self._db.query(AIUseCase)
            .filter(
                AIUseCase.id == use_case_id,
                AIUseCase.tenant_id == self._user.tenant_id,
            )
            .first()
        )
        if not uc:
            raise AppError(status_code=404, code="AI_USE_CASE_NOT_FOUND", message="AI use case not found.")
        return uc

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_use_case(self, payload: AIUseCaseCreate) -> AIUseCase:
        if not payload.owner:
            raise AppError(
                status_code=400,
                code="AI_OWNER_REQUIRED",
                message="Every AI use case must have an explicit owner.",
            )

        uc = AIUseCase(
            tenant_id=self._user.tenant_id,
            name=payload.name,
            domain=payload.domain,
            purpose=payload.purpose,
            model_provider=payload.model_provider,
            prompt_template_id=payload.prompt_template_id,
            risk_tier=payload.risk_tier.value,
            fallback_behavior=payload.fallback_behavior,
            owner=payload.owner,
            allowed_data_scope=payload.allowed_data_scope,
            human_override_behavior=payload.human_override_behavior,
            is_enabled=True,
        )
        self._db.add(uc)
        self._db.flush()

        self._audit(uc.id, "CREATED", {"name": uc.name, "risk_tier": uc.risk_tier})
        self._db.commit()
        self._db.refresh(uc)
        return uc

    def update_use_case(self, use_case_id: uuid.UUID, payload: AIUseCaseUpdate) -> AIUseCase:
        uc = self.get_use_case(use_case_id)

        # Snapshot before change
        self._snapshot_version(uc, payload.change_reason)

        if payload.name is not None:
            uc.name = payload.name
        if payload.purpose is not None:
            uc.purpose = payload.purpose
        if payload.risk_tier is not None:
            uc.risk_tier = payload.risk_tier.value
        if payload.is_enabled is not None:
            uc.is_enabled = payload.is_enabled
        if payload.fallback_behavior is not None:
            uc.fallback_behavior = payload.fallback_behavior
        if payload.owner is not None:
            uc.owner = payload.owner

        uc.last_review_date = datetime.now(UTC)
        self._audit(uc.id, "UPDATED", {"change_reason": payload.change_reason})
        self._db.commit()
        self._db.refresh(uc)
        return uc

    def disable_use_case(self, use_case_id: uuid.UUID, reason: str) -> AIUseCase:
        uc = self.get_use_case(use_case_id)
        uc.is_enabled = False
        self._audit(uc.id, "DISABLED", {"reason": reason})
        self._db.commit()
        self._db.refresh(uc)
        return uc

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _audit(self, use_case_id: uuid.UUID, action: str, detail: dict) -> None:
        evt = AIUseCaseAuditEvent(
            tenant_id=self._user.tenant_id,
            use_case_id=use_case_id,
            actor_id=self._user.user_id,
            action=action,
            detail=detail,
        )
        self._db.add(evt)

    def _snapshot_version(self, uc: AIUseCase, change_reason: str) -> None:
        # Count existing versions for this use case
        last_version = (
            self._db.query(AIUseCaseVersion)
            .filter(AIUseCaseVersion.use_case_id == uc.id)
            .count()
        )
        v = AIUseCaseVersion(
            tenant_id=self._user.tenant_id,
            use_case_id=uc.id,
            version_number=last_version + 1,
            changed_by=str(self._user.user_id),
            change_reason=change_reason,
            snapshot={
                "name": uc.name,
                "domain": uc.domain,
                "risk_tier": uc.risk_tier,
                "is_enabled": uc.is_enabled,
                "owner": uc.owner,
                "fallback_behavior": uc.fallback_behavior,
            },
        )
        self._db.add(v)

    # ── Prompt Templates ──────────────────────────────────────────────────────

    def list_prompt_templates(self, *, domain: str | None = None) -> Sequence[AIPromptTemplate]:
        q = self._db.query(AIPromptTemplate).filter(
            AIPromptTemplate.tenant_id == self._user.tenant_id
        )
        if domain:
            q = q.filter(AIPromptTemplate.domain == domain)
        return q.order_by(AIPromptTemplate.template_key).all()

    def create_prompt_template(self, payload: AIPromptTemplateCreate) -> AIPromptTemplate:
        tpl = AIPromptTemplate(
            tenant_id=self._user.tenant_id,
            template_key=payload.template_key,
            domain=payload.domain,
            system_prompt=payload.system_prompt,
            user_prompt_template=payload.user_prompt_template,
            version=1,
            is_active=True,
        )
        self._db.add(tpl)
        self._db.commit()
        self._db.refresh(tpl)
        return tpl

    # ── Domain Copilots ─────────────────────────────────────────────────────

    def list_copilots(self, domain: str | None = None) -> list[AIDomainCopilot]:
        """Return domain copilots, optionally filtered by domain."""
        q = self._db.query(AIDomainCopilot).filter(
            AIDomainCopilot.tenant_id == self._user.tenant_id,
        )
        if domain:
            q = q.filter(AIDomainCopilot.domain == domain)
        return q.order_by(AIDomainCopilot.domain, AIDomainCopilot.name).all()

    def update_prompt_template(
        self, template_id: uuid.UUID, payload: AIPromptTemplateUpdate
    ) -> AIPromptTemplate:
        tpl = (
            self._db.query(AIPromptTemplate)
            .filter(
                AIPromptTemplate.id == template_id,
                AIPromptTemplate.tenant_id == self._user.tenant_id,
            )
            .first()
        )
        if not tpl:
            raise AppError(
                status_code=404,
                code="AI_PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt template not found.",
            )

        if payload.system_prompt is not None:
            tpl.system_prompt = payload.system_prompt
        if payload.user_prompt_template is not None:
            tpl.user_prompt_template = payload.user_prompt_template
        if payload.is_active is not None:
            tpl.is_active = payload.is_active

        tpl.version = tpl.version + 1
        self._db.commit()
        self._db.refresh(tpl)
        return tpl
