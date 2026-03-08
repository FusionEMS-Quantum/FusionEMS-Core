from __future__ import annotations

import logging

try:
    import importlib

    typer = importlib.import_module("typer")
except ImportError:  # pragma: no cover
    class _TyperExit(SystemExit):
        def __init__(self, code: int = 0) -> None:
            super().__init__(code)

    class _TyperApp:
        def command(self, *_args, **_kwargs):
            def _decorator(func):
                return func

            return _decorator

        def __call__(self) -> None:
            return None

    class _TyperStub:
        Exit = _TyperExit

        @staticmethod
        def Typer(*_args, **_kwargs) -> _TyperApp:
            return _TyperApp()

        @staticmethod
        def echo(message: str) -> None:
            print(message)

    typer = _TyperStub()  # type: ignore[assignment]

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
