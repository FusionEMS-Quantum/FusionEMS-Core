"""NEMSIS integration quick-start reference.

This module is documentation-only and intentionally avoids executable integration
logic. Use it as a pointer map to the canonical production modules.
"""

from __future__ import annotations


def print_quick_start() -> None:
    """Print canonical module entry points for NEMSIS integration work."""
    lines = [
        "NEMSIS Quick Start",
        "- API routes: core_app.api.nemsis_routes",
        "- Submission service: core_app.nemsis.submission_service",
        "- Production client: core_app.nemsis.production_client",
        "- CTA service: core_app.nemsis.cta_service",
        "- Local Schematron: core_app.nemsis.local_schematron",
    ]
    for line in lines:
        print(line)


if __name__ == "__main__":
    print_quick_start()
