#!/usr/bin/env python3
import importlib
import logging
import os
import sys
import warnings

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QSystemTrayIcon,
    QTextEdit,
    QWidget,
)

# Suppress annoying library warnings
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv.*")

# Append directories for local execution
sys.path.append(os.path.dirname(__file__))

# Local imports
from axil.qt.colors import DARK_COCKPIT_STYLE
from axil.qt.copilot_chat import CopilotChatMixin
from axil.qt.layout_setup import (
    setup_central_pane,
    setup_console_wrapper,
    setup_detail_drawer,
    setup_sidebar,
)
from axil.qt.output_wrapper import OutputWrapper
from axil.qt.specialist_deck import SpecialistDeckMixin
from axil.qt.terminal_widget import TerminalWidget
from axil.services.gateway_client import GatewayClient
from axil.services.operation_registry import load_installed_registry
from axil.utils.agent_bridge import AgentBridgeWorker
from axil.utils.daemon import AxilDaemon

__version__ = "5.2.2"


# Resolve centralized log directory via the single backend seam
from axil.services.backend_adapter import backend

axil_log_dir = backend.resolve_log_dir()
axil_log_dir.mkdir(parents=True, exist_ok=True)
axil_log_path = axil_log_dir / "axil.log"

logger = logging.getLogger("axil")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh = logging.FileHandler(axil_log_path)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


class Axil(SpecialistDeckMixin, CopilotChatMixin, QMainWindow):
    """
    CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
    Axil Cockpit Dashboard Window.
    """

    # Window-level widgets and collaborators the mixins and layout builders
    # populate; declared here so static type-checking resolves them.
    centralSplitter: QSplitter
    centralStackWidget: QStackedWidget
    term_widget: TerminalWidget
    console: QTextEdit
    stdout_wrapper: OutputWrapper
    stderr_wrapper: OutputWrapper

    # index -> (panel attribute name, module path, class name). Every lazily
    # loaded view (3..18) follows the identical pattern: import on first
    # visit, instantiate with the shared worker, cache on the instance
    # attribute, and swap the placeholder widget in the stack.
    _PANEL_SPECS: dict[int, tuple[str, str, str]] = {
        3: ("graph_panel", "axil.qt.graph_explorer", "GraphExplorerPanel"),
        4: (
            "telemetry_panel",
            "axil.qt.telemetry_dashboard",
            "TelemetryDashboardPanel",
        ),
        5: ("workflow_panel", "axil.qt.workflow_builder", "WorkflowBuilderPanel"),
        6: ("security_panel", "axil.qt.security_policy", "SecurityPolicyPanel"),
        7: ("infra_panel", "axil.qt.infra_cockpit", "InfrastructureCockpitPanel"),
        8: ("finance_panel", "axil.qt.finance_cockpit", "FinanceCockpitPanel"),
        9: (
            "dashboard_panel",
            "axil.qt.service_dashboard",
            "ServiceDashboardPanel",
        ),
        10: ("fleet_panel", "axil.qt.fleet_cockpit", "FleetCockpitPanel"),
        11: ("usage_panel", "axil.qt.usage_cockpit", "UsageCockpitPanel"),
        12: (
            "extraction_panel",
            "axil.qt.extraction_cockpit",
            "ExtractionCockpitPanel",
        ),
        13: (
            "temporal_panel",
            "axil.qt.temporal_graph_panel",
            "TemporalGraphPanel",
        ),
        14: ("data_query_panel", "axil.qt.data_query_panel", "DataQueryPanel"),
        15: ("metrics_panel", "axil.qt.metrics_panel", "MetricsPanel"),
        16: (
            "federated_panel",
            "axil.qt.federated_search_panel",
            "FederatedSearchPanel",
        ),
        17: ("voice_panel", "axil.qt.voice_panel", "VoicePanel"),
        18: ("run_panel", "axil.qt.run_view", "RunViewPanel"),
    }

    # index -> sidebar button attribute name, for the active-view styling
    # pass at the end of switch_view.
    _SIDEBAR_BUTTON_ATTRS: dict[int, str] = {
        0: "btn_deck",
        1: "btn_term",
        2: "btn_chat",
        3: "btn_graph",
        4: "btn_telemetry",
        5: "btn_workflow",
        6: "btn_security",
        7: "btn_infra",
        8: "btn_finance",
        9: "btn_dashboard",
        10: "btn_fleet",
        11: "btn_usage",
        12: "btn_extraction",
        13: "btn_temporal",
        14: "btn_ask_data",
        15: "btn_metrics",
        16: "btn_federated",
        17: "btn_voice",
        18: "btn_run",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        # R002.2: refuse to start the application if the installed generated
        # operation registry is missing or malformed.
        self.operation_registry = load_installed_registry()
        self.worker = AgentBridgeWorker()
        self.daemon = AxilDaemon(self)
        self.gateway = GatewayClient(operation_registry=self.operation_registry)
        self.discovered_specialists = []
        self.active_agent_card = None

        self.initialize_user_interface()
        self.setup_tray_daemon()

        # Asynchronously load specialists from Knowledge Graph after application startup
        QTimer.singleShot(100, self.async_load_specialists)

    def initialize_user_interface(self):
        """
        CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
        Initialize the main user interface components.
        Refactored to orchestrate sub-components.
        """
        self.setWindowTitle("Axil")
        self.resize(1200, 800)
        self.setStyleSheet(DARK_COCKPIT_STYLE)

        self.centralSplitter = QSplitter(Qt.Horizontal)

        setup_sidebar(self)
        setup_central_pane(self)
        setup_detail_drawer(self)
        setup_console_wrapper(self)

    def _swap_placeholder(self, index: int, new_widget: QWidget):
        placeholder = self.centralStackWidget.widget(index)
        if placeholder is None:
            return
        self.centralStackWidget.removeWidget(placeholder)
        placeholder.deleteLater()
        self.centralStackWidget.insertWidget(index, new_widget)

    def _ensure_panel_loaded(self, index: int) -> None:
        """Lazily import + instantiate the panel for `index`, if any, and
        swap it into the placeholder slot. No-op if already loaded."""
        spec = self._PANEL_SPECS.get(index)
        if spec is None:
            return
        attr_name, module_path, class_name = spec
        if getattr(self, attr_name) is not None:
            return
        module = importlib.import_module(module_path)
        panel_cls = getattr(module, class_name)
        panel = panel_cls(self.worker)
        setattr(self, attr_name, panel)
        self._swap_placeholder(index, panel)

    def _style_sidebar_buttons(self, active_index: int) -> None:
        """Clear styling on the active view's sidebar button; transparent
        the rest."""
        for idx, attr_name in self._SIDEBAR_BUTTON_ATTRS.items():
            btn = getattr(self, attr_name)
            btn.setStyleSheet(
                "background-color: transparent; border: none;"
                if active_index != idx
                else ""
            )

    def switch_view(self, index: int):
        self._ensure_panel_loaded(index)
        self.centralStackWidget.setCurrentIndex(index)
        self._style_sidebar_buttons(index)

        if index == 1 and not self.term_widget.fd:
            self.term_widget.start_shell("tuig")

    def setup_tray_daemon(self):
        """Bind Daemon trays and system states."""
        self.daemon.show_requested.connect(self.showNormal)
        self.daemon.terminal_requested.connect(
            lambda: (self.showNormal(), self.switch_view(1))
        )
        self.daemon.health_check_requested.connect(self.run_health_check)
        self.daemon.exit_requested.connect(self.close)
        self.daemon.start()

    @Slot(str, bool)
    def log_to_console(self, text, is_stdout=True):
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        self.console.insertPlainText(text)

    def closeEvent(self, event):
        """Minimize window to tray instead of quitting."""
        if self.daemon.tray_icon.isVisible():
            self.hide()
            self.daemon.tray_icon.showMessage(
                "Axil",
                "Application is still running in background tray.",
                QSystemTrayIcon.Information,
                2000,
            )
            event.ignore()
        else:
            self.daemon.stop()
            self.stdout_wrapper.restore()
            self.stderr_wrapper.restore()
            for panel in self.findChildren(QWidget):
                cleanup = getattr(panel, "cleanup", None)
                if callable(cleanup):
                    cleanup()
            event.accept()


def axil():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    bot_window = Axil()
    bot_window.show()
    sys.exit(app.exec())


def main():
    axil()


if __name__ == "__main__":
    axil()
