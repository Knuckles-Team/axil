"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Run harness surface: served run state rendered read-only.

RunViewPanel renders one selected run's termination reason, context
use against budget, per-run cost, applied harness configuration, and
read-only current-plan snapshot — all read through the gateway run
facade's registered runs.get / runs.metrics operations (ARBORA-OPS-
R021.4). Null wire fields render unavailable (a measured zero stays
zero), missing configuration never falls back to defaults, and
expired, wrong-run, regressing, or unavailable plan snapshots reveal
no items and no edit controls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_UNAVAILABLE = "unavailable"

#: AU plan item statuses the snapshot may carry (ARBORA-OPS-R021.4.5.1).
_PLAN_STATUSES = frozenset({"pending", "in_progress", "done"})

#: One distinct label per recorded terminal reason (MEDULLA-ORCH-VOCAB-R009.1).
_TERMINAL_LABELS = {
    "final_answer": "Final answer",
    "context_overflow": "Context overflow",
    "stuck": "Stuck",
    "step_budget": "Step budget exhausted",
    "error": "Error",
}

#: Summary-section value labels cleared together on a refused read.
_SUMMARY_KEYS = (
    "termination",
    "peak",
    "budget",
    "cost",
    "config_ref",
    "config_policy",
    "config_scaffold",
    "config_action",
    "plan_revision",
)


def terminal_label(reason: Any) -> str:
    """Map one recorded terminal reason to its distinct label.

    Unknown or missing reasons read as unavailable; overflow and stuck
    keep their own labels instead of collapsing to a generic failure.
    """
    if reason is None or reason not in _TERMINAL_LABELS:
        return _UNAVAILABLE
    return _TERMINAL_LABELS[reason]


def number_label(value: Any) -> str:
    """Render a measured count; null reads unavailable, zero stays zero."""
    if value is None:
        return _UNAVAILABLE
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return str(value)


def usd_label(value: Any) -> str:
    """Render a measured USD cost; null reads unavailable, zero stays zero."""
    if value is None:
        return _UNAVAILABLE
    try:
        return f"${float(value):.4f}"
    except (TypeError, ValueError):
        return _UNAVAILABLE


def config_value(value: Any) -> str:
    """Render a configuration field; null reads unavailable, no defaults."""
    return _UNAVAILABLE if value is None else str(value)


def _coerce_time(value: Any) -> datetime | None:
    """Parse a UTC instant (ISO-8601); malformed values stay None."""
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _clear_layout(container: QWidget) -> None:
    """Remove every child widget from a container's layout."""
    layout = container.layout()
    while layout is not None and layout.count():
        item = layout.takeAt(0)
        if item is None:
            break
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


class RunViewPanel(QWidget):
    """Read-only run harness surface over the served runs.* operations."""

    def __init__(
        self, worker: Any, gateway: Any = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.worker = worker
        # the gateway facade (injectable for tests); lazy default
        self._gateway = gateway
        self._selected_run_id: str | None = None
        self._last_plan_revision: int | None = None
        self._value_labels: dict[str, QLabel] = {}
        self.initialize_ui()

    @property
    def gateway(self) -> Any:
        if self._gateway is None:
            from axil.services.gateway_client import GatewayClient

            self._gateway = GatewayClient()
        return self._gateway

    def initialize_ui(self) -> None:
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.inp_run_id = QLineEdit()
        self.inp_run_id.setPlaceholderText("run id")
        self.btn_load = QPushButton("Load Run")
        self.btn_load.clicked.connect(
            lambda: self.load_run(self.inp_run_id.text().strip())
        )
        top.addWidget(self.inp_run_id)
        top.addWidget(self.btn_load)
        layout.addLayout(top)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        form = QFormLayout()
        for key, caption in (
            ("termination", "Termination reason"),
            ("peak", "Peak context tokens"),
            ("budget", "Context budget tokens"),
            ("cost", "Run cost (USD)"),
            ("config_ref", "Harness configuration"),
            ("config_policy", "Context policy"),
            ("config_scaffold", "Plan scaffold"),
            ("config_action", "Action space"),
            ("plan_revision", "Current plan"),
            ("cost_solved", "Cost per solved task"),
        ):
            label = QLabel(_UNAVAILABLE)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(QLabel(caption), label)
            self._value_labels[key] = label
        layout.addLayout(form)

        self._plan_items = QWidget()
        self._plan_items_layout = QVBoxLayout(self._plan_items)
        layout.addWidget(self._plan_items)

    def load_run(self, run_id: str) -> None:
        """Select one run and request its served state through the client."""
        if not run_id:
            self.lbl_status.setText("No run selected")
            return
        self._selected_run_id = run_id
        self._last_plan_revision = None
        self.lbl_status.setText(f"Loading run {run_id}...")
        self.worker.run_agent_task(
            self._fetch_run, on_finished=self._on_result, on_error=self._on_error
        )

    async def _fetch_run(self, progress_cb=None) -> dict:
        """Fetch summary and metrics through the gateway run facade."""
        run_id = self._selected_run_id or ""
        summary = await self.gateway.run.fetch_run_summary(run_id)
        metrics = await self.gateway.run.fetch_run_metrics(run_id)
        return {"run_id": run_id, "summary": summary, "metrics": metrics}

    def _on_result(self, data: dict) -> None:
        """Render the served parts; stale responses read unavailable."""
        if not isinstance(data, dict) or data.get("run_id") != self._selected_run_id:
            self._on_error("stale run response")
            return
        self._render_summary(data.get("summary"))
        self._render_metrics(data.get("metrics"))

    def _on_error(self, message: str) -> None:
        """Clear every protected value so no prior state survives a failure."""
        for label in self._value_labels.values():
            label.setText(_UNAVAILABLE)
        _clear_layout(self._plan_items)
        self.lbl_status.setText(f"Run unavailable: {message}")

    def _render_summary(self, data: Any) -> None:
        """Classify the summary envelope; clear protected values on refusal."""
        if isinstance(data, dict) and data.get("status") == "success":
            result = data.get("result")
            if isinstance(result, dict):
                labels = self._value_labels
                labels["termination"].setText(
                    terminal_label(result.get("termination_reason"))
                )
                labels["peak"].setText(number_label(result.get("peak_context_tokens")))
                labels["budget"].setText(
                    number_label(result.get("context_budget_tokens"))
                )
                labels["cost"].setText(usd_label(result.get("cost_usd")))
                self._render_config(result)
                self._render_plan(result.get("current_plan"))
                self.lbl_status.setText(f"Loaded run {self._selected_run_id}")
                return
        reason = (
            str(data.get("error") or data.get("code") or "route refused")
            if isinstance(data, dict)
            else "invalid response"
        )
        for key in _SUMMARY_KEYS:
            self._value_labels[key].setText(_UNAVAILABLE)
        _clear_layout(self._plan_items)
        self.lbl_status.setText(f"Run unavailable: {reason}")

    def _render_config(self, result: dict) -> None:
        """Show the recorded configuration reference and projected values."""
        config = result.get("harness_config")
        config = config if isinstance(config, dict) else {}
        labels = self._value_labels
        labels["config_ref"].setText(config_value(result.get("harness_config_ref")))
        labels["config_policy"].setText(config_value(config.get("context_policy")))
        labels["config_scaffold"].setText(config_value(config.get("plan_scaffold")))
        labels["config_action"].setText(config_value(config.get("action_space")))

    def _render_plan(self, plan: Any) -> None:
        """Render only an available, authorized plan snapshot — read-only."""
        if not self._plan_accepted(plan):
            self._value_labels["plan_revision"].setText(_UNAVAILABLE)
            _clear_layout(self._plan_items)
            return
        self._last_plan_revision = plan["revision"]
        self._value_labels["plan_revision"].setText(f"revision {plan['revision']}")
        _clear_layout(self._plan_items)
        items = [item for item in plan["items"] if isinstance(item, dict)]
        for item in items:
            row = QLabel(f"{item['text']}  [{item['status']}]")
            row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._plan_items_layout.addWidget(row)
        if not items:
            self._plan_items_layout.addWidget(QLabel("Available — no items"))

    def _plan_accepted(self, plan: Any) -> bool:
        """Accept only a fresh, matching, unexpired, well-formed snapshot."""
        if not isinstance(plan, dict) or plan.get("run_id") != self._selected_run_id:
            return False
        revision = plan.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            return False
        if self._last_plan_revision is not None and revision < self._last_plan_revision:
            return False
        expires = _coerce_time(plan.get("expires_at"))
        if expires is None or expires <= datetime.now(UTC):
            return False
        items = plan.get("items")
        if not isinstance(items, list):
            return False
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                return False
            if item.get("status") not in _PLAN_STATUSES:
                return False
        return True

    def _render_metrics(self, data: Any) -> None:
        """Show the per-solved-task aggregate; abstention reads unavailable."""
        label = self._value_labels["cost_solved"]
        if (
            isinstance(data, dict)
            and data.get("status") == "success"
            and isinstance(data.get("result"), dict)
        ):
            value = data["result"].get("cost_per_solved_task_usd")
            if value is not None:
                label.setText(f"{usd_label(value)} per solved task")
                return
        label.setText(_UNAVAILABLE)
