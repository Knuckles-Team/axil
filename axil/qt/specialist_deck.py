"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Specialist deck and agent lifecycle behavior for the Axil window.

The window builds the deck scroll container (via the layout setup module)
and this mixin supplies the specialist-deck behavior: async specialist
discovery through the gateway facade, deck card population, and the agent
execution signal handlers. All gateway calls run off the UI thread
through the shared :class:`AgentBridgeWorker`.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout

from axil.qt.widget_mapper import WidgetSchemaMapper
from axil.services.gateway_client import GatewayClient
from axil.utils.agent_bridge import AgentBridgeWorker

logger = logging.getLogger("axil")


class SpecialistDeckMixin:
    """Specialist deck + agent lifecycle behavior for the Axil window."""

    # Dependencies provided by the window the mixin is mixed into.
    gateway: GatewayClient
    worker: AgentBridgeWorker
    discovered_specialists: list[Any]
    deck_layout: QVBoxLayout
    graph_display: QLabel
    telemetry_log: QTextEdit
    lbl_status: QLabel

    def async_load_specialists(self):
        """
        CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
        Asynchronously load all specialists from the Knowledge Graph via the Gateway.
        """
        self.lbl_status.setText("Connecting Graph...")

        async def fetch(progress_cb=None):
            return {"specialists": await self.gateway.copilot.fetch_specialists()}

        def on_finished(result):
            specs = result["specialists"]
            self.discovered_specialists = specs
            self.lbl_status.setText(f"{len(specs)} specialists loaded.")
            self.populate_specialist_deck()

        def on_error(err):
            logger.error("Specialist discovery failed")
            self.lbl_status.setText("Graph offline.")

        self.worker.run_agent_task(fetch, on_finished=on_finished, on_error=on_error)

    def populate_specialist_deck(self):
        """Add discovered specialists control widgets into the scrolling deck layout."""
        for i in reversed(range(self.deck_layout.count())):
            widget = self.deck_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        cards = WidgetSchemaMapper.build_deck(
            self.discovered_specialists, self.worker, self
        )
        for card in cards:
            card.execution_started.connect(self.on_agent_started)
            card.execution_finished.connect(self.on_agent_finished)
            card.execution_failed.connect(self.on_agent_failed)
            self.deck_layout.addWidget(card)

        self.deck_layout.addStretch()

    def on_agent_started(self, agent_name):
        self.lbl_status.setText(f"Running {agent_name}...")
        self.telemetry_log.append(f"⏱️ Spawning {agent_name} Specialist...")

    def on_agent_finished(self, agent_name, result):
        self.lbl_status.setText(f"{agent_name} Complete.")
        self.telemetry_log.append(f"✅ {agent_name} Completed execution.\n")
        result_text = result.get("result", str(result))
        self.telemetry_log.append(f"Output:\n{result_text}\n")
        mermaid = result.get("mermaid")
        if mermaid:
            self.graph_display.setText(mermaid)

    def on_agent_failed(self, agent_name, error_trace):
        self.lbl_status.setText(f"{agent_name} Failed!")
        self.telemetry_log.append(f"❌ {agent_name} Crashed:\n{error_trace}\n")

    def run_health_check(self):
        """Run health check against the centralized Gateway."""
        self.telemetry_log.append("🏥 Initiating Engine Diagnostics...")
        self.lbl_status.setText("Health checking...")

        async def verify(progress_cb=None):
            return await self.gateway.copilot.run_health_check()

        self.worker.run_agent_task(
            verify,
            on_finished=lambda res: self.telemetry_log.append(
                f"Diagnostics:\n{res.get('result')}\n"
            ),
            on_error=lambda err: self.telemetry_log.append(
                f"Health check failed:\n{err}\n"
            ),
        )
