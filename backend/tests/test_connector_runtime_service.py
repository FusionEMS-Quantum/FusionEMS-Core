"""Tests for connector runtime executors."""
from __future__ import annotations

import base64
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core_app.core.config import Settings
from core_app.services.connector_runtime_service import (
    GraphMailboxPullExecutor,
    OfficeAllySftpExecutor,
)


def test_officeally_executor_success() -> None:
    settings = Settings(
        officeally_sftp_host="sftp.officeally.example",
        officeally_sftp_port=22,
        officeally_sftp_username="user",
        officeally_sftp_password="password",
        officeally_sftp_remote_dir="/outbox",
    )
    executor = OfficeAllySftpExecutor(settings)

    job = SimpleNamespace(
        id=uuid.uuid4(),
        error_summary={
            "x12_payload_base64": base64.b64encode(b"ISA*00*~").decode(),
            "file_name": "batch-001.x12",
        },
    )
    profile = SimpleNamespace(config_payload={})

    with patch(
        "core_app.services.connector_runtime_service.submit_837_via_sftp",
        return_value="/outbox/batch-001.x12",
    ) as submit_mock:
        result = executor.execute(
            catalog=SimpleNamespace(),
            profile=profile,
            install=SimpleNamespace(),
            job=job,
        )

    assert result.success is True
    assert result.records_attempted == 1
    assert result.records_succeeded == 1
    assert result.records_failed == 0
    assert result.error_summary["remote_path"] == "/outbox/batch-001.x12"
    submit_mock.assert_called_once()


def test_officeally_executor_missing_payload_generates_dead_letter() -> None:
    settings = Settings(
        officeally_sftp_host="sftp.officeally.example",
        officeally_sftp_port=22,
        officeally_sftp_username="user",
        officeally_sftp_password="password",
    )
    executor = OfficeAllySftpExecutor(settings)

    job = SimpleNamespace(id=uuid.uuid4(), error_summary={})
    profile = SimpleNamespace(config_payload={})

    result = executor.execute(
        catalog=SimpleNamespace(),
        profile=profile,
        install=SimpleNamespace(),
        job=job,
    )

    assert result.success is False
    assert result.records_failed == 1
    assert len(result.dead_letters) == 1
    assert "Missing x12_payload_base64" in result.dead_letters[0].reason


def test_graph_executor_success() -> None:
    executor = GraphMailboxPullExecutor()
    profile = SimpleNamespace(config_payload={"top": 5, "folder": "inbox"})
    job = SimpleNamespace(id=uuid.uuid4())

    fake_graph_client = MagicMock()
    fake_graph_client.list_messages.return_value = {"value": [{"id": "1"}, {"id": "2"}]}

    with patch(
        "core_app.services.connector_runtime_service.get_graph_client",
        return_value=fake_graph_client,
    ):
        result = executor.execute(
            catalog=SimpleNamespace(),
            profile=profile,
            install=SimpleNamespace(),
            job=job,
        )

    assert result.success is True
    assert result.records_attempted == 2
    assert result.records_succeeded == 2
    assert result.error_summary["fetched"] == 2


def test_graph_executor_failure_generates_dead_letter() -> None:
    executor = GraphMailboxPullExecutor()
    profile = SimpleNamespace(config_payload={"top": 5, "folder": "inbox"})
    job = SimpleNamespace(id=uuid.uuid4())

    with patch(
        "core_app.services.connector_runtime_service.get_graph_client",
        side_effect=RuntimeError("graph_unavailable"),
    ):
        result = executor.execute(
            catalog=SimpleNamespace(),
            profile=profile,
            install=SimpleNamespace(),
            job=job,
        )

    assert result.success is False
    assert result.records_failed == 1
    assert len(result.dead_letters) == 1
    assert "Graph mailbox pull failed" in result.dead_letters[0].reason
