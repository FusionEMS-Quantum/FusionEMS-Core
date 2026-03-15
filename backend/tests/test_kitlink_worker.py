from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


class _Boto3Stub:
    @staticmethod
    def client(_service_name: str) -> SimpleNamespace:
        return SimpleNamespace()


class _CursorStub:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []

    def execute(self, query: str, params: object) -> None:
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, params))

    def fetchall(self) -> list[tuple[str, str, int]]:
        return [("item-1", "loc-1", 5)]

    def fetchone(self) -> None:
        return None

    def close(self) -> None:
        pass


class _ConnectionStub:
    def __init__(self, cursor: _CursorStub) -> None:
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self) -> _CursorStub:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def _load_kitlink_worker(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setitem(sys.modules, "boto3", _Boto3Stub)
    module_name = "test_kitlink_worker_module"
    sys.modules.pop(module_name, None)
    module_path = (
        Path(__file__).resolve().parents[1] / "core_app" / "workers" / "kitlink_worker.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_handle_stock_rebuild_uses_static_query_without_location_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kitlink_worker = _load_kitlink_worker(monkeypatch)
    cursor = _CursorStub()
    connection = _ConnectionStub(cursor)
    monkeypatch.setattr(kitlink_worker, "_db_conn", lambda: connection)

    result = kitlink_worker.handle_stock_rebuild({"body": '{"tenant_id": "tenant-1"}'})

    query, params = cursor.executed[0]
    assert "WHERE tenant_id = %s AND deleted_at IS NULL" in query
    assert "(%s IS NULL OR data->>'location_id' = %s)" in query
    assert params == ("tenant-1", None, None)
    assert result == {"tenant_id": "tenant-1", "balances_rebuilt": 1}
    assert connection.committed is True
    assert connection.closed is True


def test_handle_stock_rebuild_uses_static_query_with_location_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kitlink_worker = _load_kitlink_worker(monkeypatch)
    cursor = _CursorStub()
    connection = _ConnectionStub(cursor)
    monkeypatch.setattr(kitlink_worker, "_db_conn", lambda: connection)

    result = kitlink_worker.handle_stock_rebuild(
        {"body": '{"tenant_id": "tenant-1", "location_id": "loc-9"}'}
    )

    query, params = cursor.executed[0]
    assert "WHERE tenant_id = %s AND deleted_at IS NULL" in query
    assert "(%s IS NULL OR data->>'location_id' = %s)" in query
    assert params == ("tenant-1", "loc-9", "loc-9")
    assert result == {"tenant_id": "tenant-1", "balances_rebuilt": 1}
    assert connection.committed is True
    assert connection.closed is True
