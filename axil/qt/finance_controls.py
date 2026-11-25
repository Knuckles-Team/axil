"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Controls column for the finance cockpit panel.

Builds the trading cockpit's left column on behalf of the panel: the
strategy parameters grid (symbol, RSI thresholds, trade quantity), the
visual overlay checkboxes, the chart-style and auto-trader action
buttons, the active-positions table, and the panel market log.
Each control the panel's signal handlers read is stored on the panel
instance, so the panel stays a thin orchestrator of columns and ticks.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
)

from axil.qt.finance_charts import (
    COLOR_BG_PRIMARY,
    COLOR_BG_SECONDARY,
    COLOR_BORDER,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
)


def setup_controls_column(panel, main_layout) -> None:
    """Build the left controls & strategy column into ``main_layout``."""
    left_panel = QFrame()
    left_panel.setFrameShape(QFrame.Shape.StyledPanel)
    left_panel.setStyleSheet(
        f"background-color: {COLOR_BG_SECONDARY}; border: 1px solid {COLOR_BORDER}; border-radius: 8px;"
    )
    left_panel.setMaximumWidth(360)
    left_layout = QVBoxLayout(left_panel)
    left_layout.setSpacing(10)
    left_layout.setContentsMargins(15, 15, 15, 15)

    # Section Header
    lbl_header = QLabel("📈 Visual Trading Dashboard")
    lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #7C4DFF;")
    left_layout.addWidget(lbl_header)

    # Parameters Box
    lbl_param_header = QLabel("🎛️ Strategy Parameters")
    lbl_param_header.setStyleSheet(
        "font-size: 11px; font-weight: bold; color: #8A8A93; margin-top: 5px;"
    )
    left_layout.addWidget(lbl_param_header)

    grid_params = QGridLayout()
    grid_params.setSpacing(8)

    grid_params.addWidget(QLabel("Symbol:"), 0, 0)
    panel.combo_symbol = QComboBox()
    panel.combo_symbol.addItems(["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    panel.combo_symbol.currentTextChanged.connect(panel.on_symbol_changed)
    grid_params.addWidget(panel.combo_symbol, 0, 1)

    grid_params.addWidget(QLabel("RSI Period:"), 1, 0)
    panel.inp_rsi = QLineEdit(str(panel.params["rsi_period"]))
    grid_params.addWidget(panel.inp_rsi, 1, 1)

    grid_params.addWidget(QLabel("Oversold Thr:"), 2, 0)
    panel.inp_oversold = QLineEdit(str(panel.params["oversold"]))
    grid_params.addWidget(panel.inp_oversold, 2, 1)

    grid_params.addWidget(QLabel("Overbought Thr:"), 3, 0)
    panel.inp_overbought = QLineEdit(str(panel.params["overbought"]))
    grid_params.addWidget(panel.inp_overbought, 3, 1)

    grid_params.addWidget(QLabel("Trade Quantity:"), 4, 0)
    panel.inp_qty = QLineEdit(str(panel.params["trade_quantity"]))
    grid_params.addWidget(panel.inp_qty, 4, 1)

    left_layout.addLayout(grid_params)

    # Interactive Indicator Overlays Checkboxes
    lbl_overlays = QLabel("🛡️ Visual Overlay Checks")
    lbl_overlays.setStyleSheet(
        "font-size: 11px; font-weight: bold; color: #8A8A93; margin-top: 5px;"
    )
    left_layout.addWidget(lbl_overlays)

    panel.chk_signals = QCheckBox("Show Execution Signals")
    panel.chk_signals.setChecked(True)
    panel.chk_signals.stateChanged.connect(panel.replot_charts)
    left_layout.addWidget(panel.chk_signals)

    panel.chk_bollinger = QCheckBox("Render Bollinger Bands")
    panel.chk_bollinger.setChecked(False)
    panel.chk_bollinger.stateChanged.connect(panel.replot_charts)
    left_layout.addWidget(panel.chk_bollinger)

    # Toggle Chart Style Layout
    panel.btn_toggle_style = QPushButton("🔄 Toggle Chart: Candlestick/Line")
    panel.btn_toggle_style.setStyleSheet(
        f"background-color: {COLOR_BG_PRIMARY}; border: 1px solid {COLOR_BORDER}; color: {COLOR_TEXT_MAIN};"
    )
    panel.btn_toggle_style.clicked.connect(panel.toggle_chart_style)
    left_layout.addWidget(panel.btn_toggle_style)

    # Action Buttons
    panel.btn_auto_trader = QPushButton("⚡ Start Auto Trader")
    panel.btn_auto_trader.setStyleSheet(
        f"background-color: {COLOR_SUCCESS}; color: black; font-weight: bold;"
    )
    panel.btn_auto_trader.clicked.connect(panel.toggle_auto_trader)
    left_layout.addWidget(panel.btn_auto_trader)

    # Positions/Balances Grid Table
    lbl_position_header = QLabel("💼 Active Positions (Served)")
    lbl_position_header.setStyleSheet(
        "font-size: 11px; font-weight: bold; color: #8A8A93; margin-top: 10px;"
    )
    left_layout.addWidget(lbl_position_header)

    panel.tbl_positions = QTableWidget(3, 4)
    panel.tbl_positions.setHorizontalHeaderLabels(["Symbol", "Size", "Entry", "PnL"])
    panel.tbl_positions.verticalHeader().setVisible(False)
    panel.tbl_positions.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch
    )
    panel.tbl_positions.setStyleSheet(
        f"QTableWidget {{ background: transparent; border: none; }} QHeaderView::section {{ background-color: {COLOR_BG_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}"
    )
    panel.update_positions_table()
    left_layout.addWidget(panel.tbl_positions)

    # Panel Log Scroll Box
    lbl_news_header = QLabel("📰 Market Log")
    lbl_news_header.setStyleSheet(
        "font-size: 11px; font-weight: bold; color: #8A8A93; margin-top: 10px;"
    )
    left_layout.addWidget(lbl_news_header)

    panel.txt_news = QTextEdit()
    panel.txt_news.setReadOnly(True)
    panel.txt_news.setStyleSheet(
        f"background-color: {COLOR_BG_PRIMARY}; border: 1px solid {COLOR_BORDER}; font-size: 11px;"
    )
    panel.txt_news.append(
        "[System Log] Market state is served through the gateway facade."
    )
    left_layout.addWidget(panel.txt_news)

    main_layout.addWidget(left_panel)
