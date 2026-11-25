#!/usr/bin/env python3
"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Finance cockpit panel: market state served through the gateway facade.

Market data is only ever fetched, never fabricated: the panel requests
the served ``markets.ticks`` operation through the gateway facade on
startup and whenever the selected symbol changes, and renders an
explicit unavailable state when the route fails, is denied, is
unregistered, or times out. Strategy parameters, the chart style, and
the auto-trader toggle remain clearly local UI state; no simulated
ticks, news, or PnL are generated.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCharts import QChart, QChartView
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QBrush, QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QWidget,
)

from axil.qt.finance_charts import (
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    FinanceChartsMixin,
)
from axil.qt.finance_controls import setup_controls_column
from axil.qt.finance_market import FinanceMarketMixin


class FinanceCockpitPanel(FinanceMarketMixin, FinanceChartsMixin, QWidget):
    """
    High-Performance Visual Trading Dashboard Panel.

    CONCEPT:MERISTEM-GBOT.cockpit.through-gbot: Snappy Native Finance
    Charts using hardware-accelerated QtCharts, rendered exclusively from
    state served through the gateway facade (never simulated data).
    """

    # State provided to the chart mixins and control column builder.
    params: dict
    ticks_data: list
    positions: dict
    chart_style_candlestick: bool
    current_symbol: str
    strategy_active: bool
    price_chart: QChart
    depth_chart: QChart
    tbl_positions: QTableWidget
    txt_news: QTextEdit
    btn_auto_trader: QPushButton

    def __init__(
        self, worker: Any, gateway: Any = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.worker = worker
        # the gateway facade (injectable for tests); lazy default
        self._gateway = gateway
        self.strategy_active = False
        self.chart_style_candlestick = True  # Toggle between Candlestick and Line Chart
        self.current_symbol = "BTC/USDT"

        # Served state (empty until the gateway route answers)
        self.ticks_data: list[dict] = []
        self.positions: dict[str, dict] = {}
        self._served_signals: list[dict] = []
        self._served_depth: dict | None = None
        self._available = False

        # Strategy Parameters Defaults (clearly local, editable UI state)
        self.params = {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "short_ema": 9,
            "long_ema": 21,
            "trade_quantity": 0.05,
        }

        # Build visual hierarchy, then request the served market state
        self.initialize_layout()
        self.request_market_data()

    @property
    def gateway(self) -> Any:
        if self._gateway is None:
            from axil.services.gateway_client import GatewayClient

            self._gateway = GatewayClient()
        return self._gateway

    def initialize_layout(self):
        """Construct visual columns, controls grid, and visual charts."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ── Left Columns Pane (Controls & Strategy Grid) ──
        setup_controls_column(self, main_layout)

        # ── Right Graphics Split Pane (served-data charts) ──
        right_splitter = QSplitter(Qt.Vertical)
        self._setup_chart_views(right_splitter)
        right_splitter.setSizes([500, 300])
        main_layout.addWidget(right_splitter)

        # Replot initial view (unavailable state until data is served)
        self.replot_charts()

    def _setup_chart_views(self, right_splitter) -> None:
        """Create the price and depth chart views inside the split pane."""
        # 1. Main Price Chart
        self.price_chart_view = QChartView()
        self.price_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.price_chart_view.setStyleSheet("background: transparent; border: none;")
        self.price_chart = QChart()
        self.price_chart.setBackgroundVisible(False)
        self.price_chart.setTitle(f"Served Quotes: {self.current_symbol}")
        self.price_chart.setTitleFont(QFont("Outfit", 12, QFont.Weight.Bold))
        self.price_chart.setTitleBrush(QBrush(QColor(COLOR_TEXT_MAIN)))
        self.price_chart_view.setChart(self.price_chart)
        right_splitter.addWidget(self.price_chart_view)

        # 2. Cumulative Orderbook Bid/Ask Volume Depth Chart
        self.depth_chart_view = QChartView()
        self.depth_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.depth_chart_view.setStyleSheet("background: transparent; border: none;")
        self.depth_chart = QChart()
        self.depth_chart.setBackgroundVisible(False)
        self.depth_chart.setTitle("Bid / Ask Cumulative Orderbook Depth")
        self.depth_chart.setTitleFont(QFont("Outfit", 11, QFont.Weight.Bold))
        self.depth_chart.setTitleBrush(QBrush(QColor(COLOR_TEXT_MAIN)))
        self.depth_chart_view.setChart(self.depth_chart)
        right_splitter.addWidget(self.depth_chart_view)

    # ── Local UI state ──

    @Slot()
    def toggle_chart_style(self):
        """Switch between Candlestick and Line series snappy render loops."""
        self.chart_style_candlestick = not self.chart_style_candlestick
        self.replot_charts()

    @Slot()
    def toggle_auto_trader(self):
        """Toggle the local auto-trader flag (clearly local UI state only)."""
        self.strategy_active = not self.strategy_active
        self.btn_auto_trader.setText(
            "🛑 Stop Auto Trader" if self.strategy_active else "⚡ Start Auto Trader"
        )
        color = COLOR_DANGER if self.strategy_active else COLOR_SUCCESS
        self.btn_auto_trader.setStyleSheet(
            f"background-color: {color}; font-weight: bold;"
        )
        state = "enabled" if self.strategy_active else "disabled"
        self._log(f"Auto-trader flag {state} (local UI state; no local execution).")

    @Slot(str)
    def on_symbol_changed(self, text: str) -> None:
        """Change the selected symbol and request a fresh served state."""
        self.current_symbol = text
        self.price_chart.setTitle(f"Served Quotes: {self.current_symbol}")
        self.request_market_data()

    def update_positions_table(self) -> None:
        """Sync and re-render values inside the served Positions Grid."""
        self.tbl_positions.setRowCount(len(self.positions))
        for row, (sym, pos) in enumerate(self.positions.items()):
            self.tbl_positions.setItem(row, 0, QTableWidgetItem(sym))
            self.tbl_positions.setItem(row, 1, QTableWidgetItem(f"{pos['size']:.2f}"))
            self.tbl_positions.setItem(row, 2, QTableWidgetItem(f"${pos['entry']:.2f}"))

            pnl_item = QTableWidgetItem(f"${pos['pnl']:+.2f}")
            if pos["pnl"] >= 0:
                pnl_item.setForeground(QColor(COLOR_SUCCESS))
            else:
                pnl_item.setForeground(QColor(COLOR_DANGER))
            self.tbl_positions.setItem(row, 3, pnl_item)
