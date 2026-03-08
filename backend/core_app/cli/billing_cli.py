from __future__ import annotations

import logging

import typer

from core_app.services.ai_assistant_service import AIAssistantService

logger = logging.getLogger(__name__)

app = typer.Typer(help="FusionEMS Billing CLI")


def get_sync_db():
    raise RuntimeError("Sync DB session wiring is required before using billing CLI commands.")

@app.command()
def audit_claims(tenant_id: str):
    """
    Run AI Audit on all DRAFT claims for a tenant.
    """
    _ = AIAssistantService()
    typer.echo(
        f"audit_claims is disabled until sync DB wiring is configured (tenant_id={tenant_id})."
    )
    raise typer.Exit(
        code=2,
    )



@app.command()
def generate_narratives(tenant_id: str):
    """
    Generate AI Narratives for claims missing them.
    """
    typer.echo(
        f"generate_narratives is disabled until sync DB wiring is configured (tenant_id={tenant_id})."
    )
    raise typer.Exit(
        code=2,
    )


if __name__ == "__main__":
    app()
