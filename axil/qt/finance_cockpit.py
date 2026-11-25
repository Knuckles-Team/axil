#!/usr/bin/env python3
import random
from datetime import datetime, timedelta

from PySide6.QtCharts import QChart, QChartView
from PySide6.QtCore import Qt, QTimer, Slot
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
    COLOR_BG_PRIMARY,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    FinanceChartsMixin,
)
from axil.qt.finance_controls import setup_controls_column


class FinanceCockpitPanel(FinanceChartsMixin, QWidget):
    """
    High-Performance Visual Trading Dashboard Panel.

    CONCEPT:MERISTEM-GBOT.cockpit.through-gbot: Snappy Native Finance Charts using hardware-accelerated QtCharts.
    CONCEPT:GB-GBOT.cockpit.multi-backend-ingestion-simulated: Multi-Backend Ingestion with simulated and active emerald-exchange support.
    CONCEPT:GB-GBOT.cockpit.unified-parity-finance-cockpit: Unified Parity Finance Cockpit integrating charts, orderbooks, and RSS.
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

    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self.strategy_active = False
        self.chart_style_candlestick = True  # Toggle between Candlestick and Line Chart
        self.current_symbol = "BTC/USDT"

        # Strategy Parameters Defaults (Feature Parity with cryptobot)
        self.params = {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "short_ema": 9,
            "long_ema": 21,
            "trade_quantity": 0.05,
        }

        # Simulated state data (Emerald-Exchange/PaperBackend simulation)
        self.ticks_data = []
        self.positions = {
            "BTC/USDT": {"size": 0.25, "entry": 67300.0, "pnl": 0.0},
            "ETH/USDT": {"size": 2.10, "entry": 3450.0, "pnl": 0.0},
            "SOL/USDT": {"size": 15.0, "entry": 148.5, "pnl": 0.0},
        }
        self.generate_initial_market_data()

        # Build visual hierarchy
        self.initialize_layout()

        # Snappy Tick Update Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_market_tick)
        self.update_timer.start(1500)

        # Background RSS News Timer
        self.news_timer = QTimer(self)
        self.news_timer.timeout.connect(self.on_news_tick)
        self.news_timer.start(5000)

    def generate_initial_market_data(self):
        """Pre-populate historical series for smooth startup rendering."""
        base_price = 68000.0
        now = datetime.now()
        for i in range(30):
            t = now - timedelta(minutes=(30 - i))
            change = random.uniform(-400, 400)
            open_p = base_price
            close_p = base_price + change
            high_p = max(open_p, close_p) + random.uniform(50, 150)
            low_p = min(open_p, close_p) - random.uniform(50, 150)
            self.ticks_data.append(
                {
                    "time": t,
                    "open": open_p,
                    "close": close_p,
                    "high": high_p,
                    "low": low_p,
                }
            )
            base_price = close_p

    def initialize_layout(self):
        """Construct visual columns, controls grid, and visual charts."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ── Left Columns Pane (Controls & Strategy Grid) ──
        setup_controls_column(self, main_layout)

        # ── Right Graphics Split Pane (Real-Time snappy charts) ──
        right_splitter = QSplitter(Qt.Vertical)
        self._setup_chart_views(right_splitter)
        right_splitter.setSizes([500, 300])
        main_layout.addWidget(right_splitter)

        # Replot initial view
        self.replot_charts()

    def _setup_chart_views(self, right_splitter) -> None:
        """Create the price and depth chart views inside the split pane."""
        # 1. Main Price Chart
        self.price_chart_view = QChartView()
        self.price_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.price_chart_view.setStyleSheet("background: transparent; border: none;")
        self.price_chart = QChart()
        self.price_chart.setBackgroundVisible(False)
        self.price_chart.setTitle(f"Real-Time Quotes: {self.current_symbol}")
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

    @Slot()
    def toggle_chart_style(self):
        """Switch between Candlestick and Line series snappy render loops."""
        self.chart_style_candlestick = not self.chart_style_candlestick
        self.replot_charts()

    @Slot()
    def toggle_auto_trader(self):
        """Toggle active auto trading state machine."""
        self.strategy_active = not self.strategy_active
        if self.strategy_active:
            self.btn_auto_trader.setText("🛑 Stop Auto Trader")
            self.btn_auto_trader.setStyleSheet(
                f"background-color: {COLOR_DANGER}; color: white; font-weight: bold;"
            )
            self.txt_news.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Strategy Engine started for {self.current_symbol}."
            )
        else:
            self.btn_auto_trader.setText("⚡ Start Auto Trader")
            self.btn_auto_trader.setStyleSheet(
                f"background-color: {COLOR_SUCCESS}; color: black; font-weight: bold;"
            )
            self.txt_news.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Strategy Engine stopped."
            )

    @Slot(str)
    def on_symbol_changed(self, text):
        """Change current currency symbol context and clear queues."""
        self.current_symbol = text
        self.price_chart.setTitle(f"Real-Time Quotes: {self.current_symbol}")
        self.replot_charts()

    def update_positions_table(self):
        """Sync and re-render values inside Positions Grid."""
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

    @Slot()
    def on_market_tick(self):
        """Simulate real-time snappy data ticks or CCXT data streaming (emerald-exchange)."""
        current_time = datetime.now()
        last_tick = self.ticks_data[-1]

        # Random Walk close dynamics
        step = random.uniform(-180, 200)
        new_close = last_tick["close"] + step
        new_open = last_tick["close"]
        new_high = max(new_open, new_close) + random.uniform(10, 60)
        new_low = min(new_open, new_close) - random.uniform(10, 60)

        # Update historical buffer (keep max 40 data coordinates)
        self.ticks_data.append(
            {
                "time": current_time,
                "open": new_open,
                "close": new_close,
                "high": new_high,
                "low": new_low,
            }
        )
        if len(self.ticks_data) > 40:
            self.ticks_data.pop(0)

        # Trigger auto trader strategy evaluation if active
        if self.strategy_active:
            self.evaluate_indicators(new_close)

        # Live calculate simulated PnL based on latest closes
        self._update_simulated_pnl(new_close)
        self.update_positions_table()
        self.replot_charts()

    def _update_simulated_pnl(self, new_close: float) -> None:
        """Live calculate simulated PnL based on latest closes."""
        for sym, pos in self.positions.items():
            if sym == "BTC/USDT":
                pos["pnl"] = (new_close - pos["entry"]) * pos["size"]
            else:
                # Add slight random float for other active simulated slots
                pos["pnl"] += random.uniform(-5, 5)

    def evaluate_indicators(self, latest_price):
        """Calculate mock technical strategy and publish signals."""
        now_str = datetime.now().strftime("%H:%M:%S")
        # Trigger buy/sell indicator overlay scatter signals with a low probability
        if random.random() < 0.15:
            action = random.choice(["BUY", "SELL"])
            if action == "BUY":
                msg = f"🟢 [{now_str}] RSI Strategy trigger: BUY {self.params['trade_quantity']} {self.current_symbol.split('/')[0]} @ ${latest_price:.2f}"
            else:
                msg = f"🔴 [{now_str}] EMA Crossover alert: SELL {self.params['trade_quantity']} {self.current_symbol.split('/')[0]} @ ${latest_price:.2f}"
            self.txt_news.append(msg)

    @Slot()
    def on_news_tick(self):
        """Asynchronously stream parsed simulated crypto-world events."""
        topics = [
            "Federal Reserve hints at potential cryptocurrency backing policies.",
            "Polymarket predicted odds surge to 83% for BTC hitting $100k.",
            "CCXT exchange backend registers high liquidity spikes across stablecoins.",
            "Emerald-Exchange processes record 12,000 parallel transactions under test-suite execution.",
            "New security audit on meristem system detects 0 vulnerabilities.",
            "Algorithmic swarm debate registers optimal outcome consensus on ETH scalability.",
        ]
        now_str = datetime.now().strftime("%H:%M:%S")
        self.txt_news.append(f"📰 [{now_str}] {random.choice(topics)}")
