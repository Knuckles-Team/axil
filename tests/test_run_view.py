"""Run harness surface tests (AXIL-CLIENT-R019.1 to R019.6)."""

from __future__ import annotations

import asyncio
import importlib
import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

# The package's __init__ re-exports a function named `axil`, which shadows
# the submodule in `import ... as` bindings; resolve the module object directly.
axil_module = importlib.import_module("axil.axil")
from axil.axil import Axil
from axil.qt.run_view import RunViewPanel
from axil.services.gateway_client import GatewayClient
from axil.services.operation_registry import build_registry

VALID_DIGEST = "a" * 64


class _SyncWorker:
    """Run panel tasks synchronously, mirroring AgentRunnable's signals:
    dict results emit finished, exceptions emit the error message, and
    the progress_cb keyword is injected as in production."""

    def run_agent_task(
        self, async_func, on_finished=None, on_error=None, on_progress=None
    ):
        kwargs = {"progress_cb": on_progress}
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(async_func(**kwargs))
        except Exception as exc:
            if on_error is not None:
                on_error(f"Agent task failed ({type(exc).__name__})")
            return
        finally:
            loop.close()
        if on_finished is not None and isinstance(result, dict):
            on_finished(result)


class _StubRunFacade:
    """A run facade whose served outcomes are fixed by the test."""

    def __init__(self, summary: Any, metrics: Any) -> None:
        self.summary = summary
        self.metrics = metrics
        self.summary_calls: list[str] = []
        self.metrics_calls: list[str] = []

    async def fetch_run_summary(self, run_id: str) -> dict:
        self.summary_calls.append(run_id)
        return self.summary

    async def fetch_run_metrics(self, run_id: str) -> dict:
        self.metrics_calls.append(run_id)
        return self.metrics


class _StubGateway:
    def __init__(self, run: _StubRunFacade) -> None:
        self.run = run


def _success_envelope(result: dict) -> dict:
    return {"status": "success", "result": result}


def _plan_snapshot(
    run_id: str,
    revision: int = 2,
    *,
    expires_in_seconds: int = 300,
    items: list | None = None,
) -> dict:
    now = datetime.now(UTC)
    return {
        "run_id": run_id,
        "revision": revision,
        "observed_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=expires_in_seconds)).isoformat(),
        "items": (
            items
            if items is not None
            else [
                {"text": "step one", "status": "done"},
                {"text": "step two", "status": "in_progress"},
                {"text": "step three", "status": "pending"},
            ]
        ),
    }


def _summary_result(**overrides) -> dict:
    base = {
        "run_id": "run-a",
        "termination_reason": "final_answer",
        "peak_context_tokens": 120_000,
        "context_budget_tokens": 200_000,
        "cost_usd": 1.25,
        "harness_config_ref": "decision:abc",
        "harness_config": {
            "context_policy": "sliding",
            "plan_scaffold": "staged",
            "action_space": "bounded",
        },
        "current_plan": _plan_snapshot("run-a"),
    }
    base.update(overrides)
    return base


def _panel(summary: Any, metrics: Any = None) -> RunViewPanel:
    if metrics is None:
        metrics = _success_envelope({})
    return RunViewPanel(
        _SyncWorker(), gateway=_StubGateway(_StubRunFacade(summary, metrics))
    )


class _RunTransport(httpx.AsyncBaseTransport):
    """Serve the run fixtures over the client's real transport."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/v1/ops/runs.get":
            return httpx.Response(
                200, json=_success_envelope(_summary_result()), request=request
            )
        if request.url.path == "/api/v1/ops/runs.metrics":
            return httpx.Response(
                200,
                json=_success_envelope({"cost_per_solved_task_usd": 0.4}),
                request=request,
            )
        return httpx.Response(
            404, json={"status": "failed", "code": "NOT_FOUND"}, request=request
        )


@pytest.mark.spec("AXIL-CLIENT-R019.1")
def test_run_read_uses_arbora_operations(qapp) -> None:
    """The selected run renders through the served operations and client."""
    transport = _RunTransport()
    client = GatewayClient(
        "http://localhost:8000",
        allow_insecure_http=True,
        operation_registry=build_registry(
            [
                {"operation": "runs.get", "digest": VALID_DIGEST},
                {"operation": "runs.metrics", "digest": VALID_DIGEST},
            ]
        ),
    )
    client._direct_http = httpx.AsyncClient(
        base_url=client.base_url, transport=transport
    )
    panel = RunViewPanel(_SyncWorker(), gateway=client)
    try:
        panel.load_run("run-a")
    finally:
        asyncio.run(client.aclose())

    assert [r.url.path for r in transport.requests] == [
        "/api/v1/ops/runs.get",
        "/api/v1/ops/runs.metrics",
    ]
    assert all(r.method == "POST" for r in transport.requests)
    assert json.loads(transport.requests[0].content) == {"run_id": "run-a"}
    assert panel._value_labels["termination"].text() == "Final answer"
    assert panel._value_labels["peak"].text() == "120,000"
    assert panel.lbl_status.text() == "Loaded run run-a"


@pytest.mark.spec("AXIL-CLIENT-R019.2")
def test_harness_config_shown(qapp) -> None:
    """A committed configuration keeps its reference and values; no defaults."""
    panel = _panel(_success_envelope(_summary_result()))
    panel.load_run("run-a")
    labels = panel._value_labels
    assert labels["config_ref"].text() == "decision:abc"
    assert labels["config_policy"].text() == "sliding"
    assert labels["config_scaffold"].text() == "staged"
    assert labels["config_action"].text() == "bounded"

    missing = _panel(
        _success_envelope(_summary_result(harness_config_ref=None, harness_config=None))
    )
    missing.load_run("run-a")
    assert missing._value_labels["config_ref"].text() == "unavailable"
    assert missing._value_labels["config_policy"].text() == "unavailable"
    assert missing._value_labels["config_action"].text() == "unavailable"


@pytest.mark.spec("AXIL-CLIENT-R019.3")
def test_context_and_cost_shown(qapp) -> None:
    """Peak, budget, and per-run cost are labelled separately; null != zero."""
    zeroed = _panel(
        _success_envelope(
            _summary_result(
                peak_context_tokens=0, context_budget_tokens=None, cost_usd=0.0
            )
        ),
        _success_envelope({"cost_per_solved_task_usd": None}),
    )
    zeroed.load_run("run-a")
    assert zeroed._value_labels["peak"].text() == "0"
    assert zeroed._value_labels["budget"].text() == "unavailable"
    assert zeroed._value_labels["cost"].text() == "$0.0000"
    assert zeroed._value_labels["cost_solved"].text() == "unavailable"

    panel = _panel(
        _success_envelope(_summary_result()),
        _success_envelope({"cost_per_solved_task_usd": 0.4}),
    )
    panel.load_run("run-a")
    assert panel._value_labels["peak"].text() == "120,000"
    assert panel._value_labels["budget"].text() == "200,000"
    assert panel._value_labels["cost"].text() == "$1.2500"
    assert panel._value_labels["cost_solved"].text() == "$0.4000 per solved task"


@pytest.mark.spec("AXIL-CLIENT-R019.4")
def test_plan_read_only(qapp) -> None:
    """A fresh matching snapshot keeps order, revision, and AU statuses."""
    panel = _panel(_success_envelope(_summary_result()))
    panel.load_run("run-a")
    assert panel._value_labels["plan_revision"].text() == "revision 2"
    rows = [w.text() for w in panel._plan_items.findChildren(QLabel)]
    assert rows == [
        "step one  [done]",
        "step two  [in_progress]",
        "step three  [pending]",
    ]
    assert not panel._plan_items.findChildren(QLineEdit)
    assert not panel._plan_items.findChildren(QPushButton)

    expired = _panel(
        _success_envelope(
            _summary_result(current_plan=_plan_snapshot("run-a", expires_in_seconds=-1))
        )
    )
    expired.load_run("run-a")
    assert expired._value_labels["plan_revision"].text() == "unavailable"
    assert not expired._plan_items.findChildren(QLabel)

    foreign = _panel(
        _success_envelope(_summary_result(current_plan=_plan_snapshot("run-other")))
    )
    foreign.load_run("run-a")
    assert foreign._value_labels["plan_revision"].text() == "unavailable"
    assert not foreign._plan_items.findChildren(QLabel)


@pytest.mark.spec("AXIL-CLIENT-R019.5")
@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("final_answer", "Final answer"),
        ("context_overflow", "Context overflow"),
        ("stuck", "Stuck"),
        ("step_budget", "Step budget exhausted"),
        ("error", "Error"),
        ("unknown_reason", "unavailable"),
        (None, "unavailable"),
    ],
)
def test_termination_reasons_distinct(qapp, reason, expected) -> None:
    """Each recorded terminal reason has its own label; no generic collapse."""
    panel = _panel(_success_envelope(_summary_result(termination_reason=reason)))
    panel.load_run("run-a")
    assert panel._value_labels["termination"].text() == expected


class _EndToEndTransport(httpx.AsyncBaseTransport):
    """Serve the run fixtures; flip every run read to a typed denial."""

    def __init__(self) -> None:
        self.deny = False
        self.run_paths: list[str] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in {"/api/v1/ops/runs.get", "/api/v1/ops/runs.metrics"}:
            self.run_paths.append(path)
            if self.deny:
                return httpx.Response(
                    403,
                    json={"status": "failed", "code": "FORBIDDEN", "error": "denied"},
                    request=request,
                )
            body = (
                _success_envelope(_summary_result())
                if path == "/api/v1/ops/runs.get"
                else _success_envelope({"cost_per_solved_task_usd": 0.4})
            )
            return httpx.Response(200, json=body, request=request)
        return httpx.Response(
            404, json={"status": "failed", "code": "NOT_FOUND"}, request=request
        )


def _assert_loaded_fields(panel: RunViewPanel) -> None:
    labels = panel._value_labels
    assert labels["termination"].text() == "Final answer"
    assert labels["peak"].text() == "120,000"
    assert labels["budget"].text() == "200,000"
    assert labels["cost"].text() == "$1.2500"
    assert labels["config_ref"].text() == "decision:abc"
    assert labels["config_policy"].text() == "sliding"
    assert labels["config_scaffold"].text() == "staged"
    assert labels["config_action"].text() == "bounded"
    assert labels["plan_revision"].text() == "revision 2"
    assert labels["cost_solved"].text() == "$0.4000 per solved task"
    assert panel.lbl_status.text() == "Loaded run run-a"


@pytest.mark.spec("AXIL-CLIENT-R019.6")
def test_run_surface_end_to_end(qapp, qtbot, monkeypatch) -> None:
    """Enter the production UI; served fields render, denial clears them."""
    transport = _EndToEndTransport()
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    registry = build_registry(
        [
            {"operation": "runs.get", "digest": VALID_DIGEST},
            {"operation": "runs.metrics", "digest": VALID_DIGEST},
        ]
    )
    monkeypatch.setattr(axil_module, "load_installed_registry", lambda: registry)
    monkeypatch.setattr(httpx, "AsyncClient", factory)

    bot = Axil()
    try:
        bot.switch_view(18)
        # set dynamically by switch_view (setattr), invisible to mypy
        panel = bot.run_panel  # type: ignore[attr-defined]
        assert isinstance(panel, RunViewPanel)
        assert panel._gateway is bot.gateway

        panel.inp_run_id.setText("run-a")
        panel.btn_load.click()
        qtbot.waitUntil(lambda: "Loaded run" in panel.lbl_status.text(), timeout=5000)
        _assert_loaded_fields(panel)

        transport.deny = True
        panel.load_run("run-a")
        qtbot.waitUntil(
            lambda: "Run unavailable" in panel.lbl_status.text(), timeout=5000
        )
        for key in (
            "termination",
            "peak",
            "budget",
            "cost",
            "config_ref",
            "config_policy",
            "plan_revision",
            "cost_solved",
        ):
            assert panel._value_labels[key].text() == "unavailable"
        assert not panel._plan_items.findChildren(QLabel)
    finally:
        bot.close()
