"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Cockpit layout construction for the Axil window.

Builds the window's four layout regions on behalf of the window: the left
navigation sidebar, the central stacked pane (deck, terminal, chat and
lazy panel placeholders), the right telemetry detail drawer, and the
bottom console with its stream wrappers. Each builder mutates the
window's widget attributes so the window class stays a thin orchestrator.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from axil.qt.colors import BG_SECONDARY, BORDER_COLOR
from axil.qt.output_wrapper import OutputWrapper
from axil.qt.terminal_widget import TerminalWidget

# (window attribute name, button label, view index) — sidebar navigation
# buttons in display order. Built from the table so adding a view is one
# row here plus the window's _PANEL_SPECS entry.
_NAV_BUTTONS = (
    ("btn_deck", "🌌 Specialist Deck", 0),
    ("btn_term", "🖥️ CLI Terminal", 1),
    ("btn_chat", "💬 Copilot Chat", 2),
)
_COCKPIT_NAV_BUTTONS = (
    ("btn_graph", "🌌 Graph Explorer", 3),
    ("btn_temporal", "🕰️ Temporal Graph", 13),
    ("btn_extraction", "🧬 KG Extraction", 12),
    ("btn_telemetry", "📈 Live Telemetry", 4),
    ("btn_workflow", "⛓️ Swarm Builder", 5),
    ("btn_security", "🛡️ Security Policies", 6),
    ("btn_infra", "🏥 Infrastructure", 7),
    ("btn_finance", "📊 Trading Cockpit", 8),
    ("btn_dashboard", "🏠 Service Dashboard", 9),
    ("btn_fleet", "🛰️ Fleet Supervisor", 10),
    ("btn_usage", "💰 Usage & Cost", 11),
    ("btn_ask_data", "🔎 Ask Data", 14),
    ("btn_metrics", "📊 Engine Metrics", 15),
    ("btn_federated", "🌐 Federated Search", 16),
    ("btn_voice", "🎙️ Voice Dictation", 17),
    ("btn_run", "📋 Run Surface", 18),
)

# Views that stay None until first visit (lazy panels 3..17 plus run 18).
_LAZY_PANEL_ATTRS = (
    "graph_panel",
    "telemetry_panel",
    "workflow_panel",
    "security_panel",
    "infra_panel",
    "finance_panel",
    "dashboard_panel",
    "fleet_panel",
    "usage_panel",
    "extraction_panel",
    "temporal_panel",
    "data_query_panel",
    "metrics_panel",
    "federated_panel",
    "voice_panel",
    "run_panel",
)


def _add_nav_buttons(window, layout, buttons):
    for attr_name, label, view_index in buttons:
        button = QPushButton(label)
        button.clicked.connect(
            lambda _checked=False, i=view_index: window.switch_view(i)
        )
        setattr(window, attr_name, button)
        layout.addWidget(button)


def setup_sidebar(window):
    """CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
    Setup the left navigation sidebar."""
    window.sidebar = QFrame()
    window.sidebar.setObjectName("Sidebar")
    window.sidebar.setMinimumWidth(180)
    window.sidebar.setMaximumWidth(220)
    sidebar_layout = QVBoxLayout(window.sidebar)
    sidebar_layout.setContentsMargins(10, 20, 10, 20)
    sidebar_layout.setSpacing(12)

    # Sidebar Title
    title_label = _label(
        "Axil",
        "font-size: 18px; font-weight: bold; color: #7C4DFF; padding-left: 10px; margin-bottom: 10px;",
    )
    sidebar_layout.addWidget(title_label)

    _add_nav_buttons(window, sidebar_layout, _NAV_BUTTONS)

    # Cockpit Controls Header
    cockpit_header = _label(
        "🎛️ COCKPIT CONTROLS",
        "font-size: 10px; font-weight: bold; color: #8A8A93; padding-left: 10px; margin-top: 15px; margin-bottom: 5px;",
    )
    sidebar_layout.addWidget(cockpit_header)

    _add_nav_buttons(window, sidebar_layout, _COCKPIT_NAV_BUTTONS)

    sidebar_layout.addStretch()

    # Sidebar footer status
    window.lbl_status = QLabel("System Ready")
    window.lbl_status.setStyleSheet(
        "color: #8A8A93; font-size: 11px; padding-left: 10px;"
    )
    sidebar_layout.addWidget(window.lbl_status)
    window.centralSplitter.addWidget(window.sidebar)


def _label(text, style=""):
    label = QLabel(text)
    label.setStyleSheet(style)
    return label


def setup_central_pane(window):
    """CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
    Setup the main central content stacked widget."""
    window.centralStackWidget = QStackedWidget()

    # View 0: Agent Deck (Scroll Area)
    window.deck_scroll = QScrollArea()
    window.deck_scroll.setWidgetResizable(True)
    window.deck_scroll.setStyleSheet(
        "QScrollArea { border: none; background: transparent; }"
    )
    window.deck_container = QWidget()
    window.deck_layout = QVBoxLayout(window.deck_container)
    window.deck_layout.setSpacing(16)
    window.deck_layout.setContentsMargins(20, 20, 20, 20)
    window.deck_scroll.setWidget(window.deck_container)
    window.centralStackWidget.addWidget(window.deck_scroll)

    # View 1: xterm.js Terminal
    window.term_widget = TerminalWidget()
    window.centralStackWidget.addWidget(window.term_widget)

    # View 2: Copilot Chat
    window._setup_copilot_chat()

    # Views 3-18: lazy-loaded panel placeholders
    for attr_name in _LAZY_PANEL_ATTRS:
        setattr(window, attr_name, None)
    for _ in range(16):
        window.centralStackWidget.addWidget(QWidget())

    window.centralSplitter.addWidget(window.centralStackWidget)


def setup_detail_drawer(window):
    """CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
    Setup the right slide-out telemetry detail drawer."""
    window.detail_drawer = QFrame()
    window.detail_drawer.setStyleSheet(
        f"background-color: {BG_SECONDARY}; border-left: 1px solid {BORDER_COLOR};"
    )
    window.detail_drawer.setMinimumWidth(320)
    window.detail_drawer.setMaximumWidth(400)

    drawer_layout = QVBoxLayout(window.detail_drawer)
    drawer_layout.setContentsMargins(15, 20, 15, 20)
    drawer_layout.setSpacing(12)

    drawer_title = _label(
        "🔮 TELEMETRY & LOGS", "font-size: 14px; font-weight: bold; color: #7C4DFF;"
    )
    drawer_layout.addWidget(drawer_title)

    drawer_layout.addWidget(_label("Telemetry / Diagnostics Info:"))
    window.telemetry_log = QTextEdit()
    window.telemetry_log.setReadOnly(True)
    window.telemetry_log.setStyleSheet(
        "background-color: #121214; border-radius: 6px; font-family: monospace; font-size: 11px;"
    )
    drawer_layout.addWidget(window.telemetry_log)

    drawer_layout.addWidget(_label("Live Execution Graph Flow:"))
    window.graph_display = QLabel("No active execution diagram.")
    window.graph_display.setWordWrap(True)
    window.graph_display.setStyleSheet(
        f"background-color: #121214; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 11px;"
    )
    drawer_layout.addWidget(window.graph_display)

    window.centralSplitter.addWidget(window.detail_drawer)


def setup_console_wrapper(window):
    """CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
    Setup the bottom global terminal logger."""
    # Splitter sizing ratio: 15% sidebar, 50% central view, 35% right drawer
    window.centralSplitter.setSizes([180, 600, 360])

    window.console = QTextEdit()
    window.console.setReadOnly(True)
    window.console.setMaximumHeight(150)
    window.console.setStyleSheet(
        "background-color: #0b0b0d; color: #8A8A93; border: none; font-family: monospace; font-size: 11px;"
    )

    window.stdout_wrapper = OutputWrapper(window, True)
    window.stdout_wrapper.outputWritten.connect(window.log_to_console)
    window.stderr_wrapper = OutputWrapper(window, False)
    window.stderr_wrapper.outputWritten.connect(window.log_to_console)

    main_layout = QVBoxLayout()
    main_layout.addWidget(window.centralSplitter)
    main_layout.addWidget(window.console)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    container = QWidget()
    container.setLayout(main_layout)
    window.setCentralWidget(container)
