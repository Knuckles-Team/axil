"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Copilot chat behavior for the Axil window.

The window builds the chat pane (via :meth:`_setup_copilot_chat`) and this
mixin supplies the chat behavior: slash-command autocomplete, message
dispatch and the streamed master-copilot request. All gateway calls run off
the UI thread through the shared :class:`AgentBridgeWorker`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from axil.qt.colors import BORDER_COLOR
from axil.services.gateway_client import GatewayClient
from axil.utils.agent_bridge import AgentBridgeWorker


class CopilotChatMixin:
    """Chat behavior bound to the window's ``chat_*`` widgets and worker."""

    # Dependencies provided by the window the mixin is mixed into.
    gateway: GatewayClient
    worker: AgentBridgeWorker
    chat_input: QLineEdit
    chat_log: QTextEdit
    completer: QCompleter
    graph_display: QLabel
    telemetry_log: QTextEdit
    lbl_status: QLabel
    centralStackWidget: Any

    def _setup_copilot_chat(self):
        """
        CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
        Setup the Copilot chat pane inside the central stack.
        """
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        chat_layout.setContentsMargins(20, 20, 20, 20)
        chat_layout.setSpacing(12)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(
            f"background-color: #121214; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 10px;"
        )
        chat_layout.addWidget(self.chat_log)

        input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask the master agent anything...")
        self.chat_input.returnPressed.connect(self.send_chat_message)

        # Native Autocomplete Completer
        self.completer = QCompleter([], self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.chat_input.setCompleter(self.completer)
        self.chat_input.textChanged.connect(self.handle_input_text_changed)

        input_row.addWidget(self.chat_input)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_chat_message)
        input_row.addWidget(self.btn_send)
        chat_layout.addLayout(input_row)

        self.centralStackWidget.addWidget(self.chat_container)

    def handle_input_text_changed(self, text):
        """Asynchronously fetch autocomplete suggestions and populate QCompleter."""
        if text.startswith("/"):

            async def fetch_suggestions(progress_cb=None):
                return await self.gateway.copilot.fetch_autocomplete_suggestions(text)

            def on_finished(suggestions):
                if suggestions:
                    from PySide6.QtCore import QStringListModel

                    model = QStringListModel(suggestions, self.completer)
                    self.completer.setModel(model)
                    self.completer.complete()

            self.worker.run_agent_task(fetch_suggestions, on_finished=on_finished)

    def send_chat_message(self):
        """
        CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
        Execute master copilot query with prompt injection scan and secure guard confirmations.
        """
        query = self.chat_input.text().strip()
        if not query:
            return

        self.chat_input.clear()
        self.chat_log.append(f"\n👤 You: {query}")

        self._execute_copilot_request(query)

    def _execute_copilot_request(self, query: str):
        """
        CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
        Internal async handler to route the copilot request to the gateway.
        """

        async def ask_copilot(progress_cb=None):
            if query.startswith("/"):
                return await self.gateway.copilot.execute_slash_command(query)
            return await self.gateway.copilot.stream_copilot_query(query, progress_cb)

        def on_done(res):
            ans = res.get("result", str(res))
            self.chat_log.append(f"🤖 Copilot: {ans}")
            mermaid = res.get("mermaid")
            if isinstance(mermaid, str):
                self.graph_display.setText(mermaid)

            for action_dict in res.get("client_actions", []):
                if action_dict.get("action") == "clear_chat":
                    self.chat_log.clear()
                    self.chat_log.append("🧹 Chat log cleared via slash command.")

        def on_fail(err):
            self.chat_log.append(f"❌ Error: {err}")

        def on_progress(msg):
            self.telemetry_log.append(msg)
            self.lbl_status.setText("Agent thinking...")

        self.worker.run_agent_task(
            ask_copilot, on_finished=on_done, on_error=on_fail, on_progress=on_progress
        )
