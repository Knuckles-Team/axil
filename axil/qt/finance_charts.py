"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Chart rendering for the finance cockpit panel.

Native QtCharts rendering for the trading cockpit: the main price chart
(candlestick or line, with optional execution-signal overlays and
Bollinger bands computed from the served tick series) and the cumulative
bid/ask orderbook depth chart built from served depth points. Every
painter reads only state the panel received from the gateway facade;
when the served state is missing the charts render an explicit
unavailable state instead of fabricated data. Mixed into
:class:`axil.qt.finance_cockpit.FinanceCockpitPanel`, which provides the
chart views, tick data, and overlay state the painters read.
"""

from __future__ import annotations

import math

from PySide6.QtCharts import (
    QAreaSeries,
    QCandlestickSeries,
    QCandlestickSet,
    QChart,
    QDateTimeAxis,
    QLineSeries,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QCheckBox

# Theme constants mapping colors.py
COLOR_ACCENT = "#7C4DFF"
COLOR_SUCCESS = "#00E676"
COLOR_DANGER = "#FF1744"
COLOR_BG_PRIMARY = "#121214"
COLOR_BG_SECONDARY = "#1E1E24"
COLOR_TEXT_MAIN = "#F5F5F7"
COLOR_TEXT_MUTED = "#8A8A93"
COLOR_BORDER = "#2E2E38"


class FinanceChartsMixin:
    """QtCharts painting methods bound to the panel's chart views."""

    # Widgets and state provided by the panel the mixin is mixed into.
    price_chart: QChart
    depth_chart: QChart
    ticks_data: list
    chart_style_candlestick: bool
    chk_signals: QCheckBox
    chk_bollinger: QCheckBox

    @staticmethod
    def _clear_chart(chart: QChart) -> None:
        chart.removeAllSeries()
        for axis in list(chart.axes()):
            chart.removeAxis(axis)

    def _build_price_axes(self) -> tuple[QDateTimeAxis, QValueAxis]:
        axis_x = QDateTimeAxis()
        axis_x.setFormat("hh:mm:ss")
        axis_x.setTitleText("Time (Tick Series)")
        axis_x.setTitleBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
        axis_x.setLabelsColor(QColor(COLOR_TEXT_MUTED))

        axis_y = QValueAxis()
        axis_y.setTitleText("Price (USD)")
        axis_y.setTitleBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
        axis_y.setLabelsColor(QColor(COLOR_TEXT_MUTED))

        self.price_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.price_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        return axis_x, axis_y

    def _plot_candlestick_series(self, axis_x, axis_y) -> tuple[float, float]:
        # Replot Candlestick OHLCV Bars from the served ticks
        candle_series = QCandlestickSeries()
        candle_series.setName("OHLCV Bars")
        candle_series.setIncreasingColor(QColor(COLOR_SUCCESS))
        candle_series.setDecreasingColor(QColor(COLOR_DANGER))

        min_price = float("inf")
        max_price = float("-inf")
        for t in self.ticks_data:
            ts = int(t["time"].timestamp() * 1000)
            candle_set = QCandlestickSet(t["open"], t["high"], t["low"], t["close"], ts)
            candle_series.append(candle_set)

            min_price = min(min_price, t["low"])
            max_price = max(max_price, t["high"])

        self.price_chart.addSeries(candle_series)
        candle_series.attachAxis(axis_x)
        candle_series.attachAxis(axis_y)
        return min_price, max_price

    def _plot_line_series(self, axis_x, axis_y) -> tuple[float, float]:
        # Replot the served close-price line series
        line_series = QLineSeries()
        line_series.setName("Close Price")
        pen = QPen(QColor(COLOR_ACCENT))
        pen.setWidth(2)
        line_series.setPen(pen)

        min_price = float("inf")
        max_price = float("-inf")
        for t in self.ticks_data:
            ts = int(t["time"].timestamp() * 1000)
            line_series.append(ts, t["close"])

            min_price = min(min_price, t["close"])
            max_price = max(max_price, t["close"])

        self.price_chart.addSeries(line_series)
        line_series.attachAxis(axis_x)
        line_series.attachAxis(axis_y)
        return min_price, max_price

    def _plot_signal_overlays(self, axis_x, axis_y) -> None:
        # Render the served execution-signal markers, if the gateway
        # provided any; no markers are fabricated locally.
        if not self.chk_signals.isChecked():
            return
        scatter_buy = QScatterSeries()
        scatter_buy.setName("Strategy Buy Signals")
        scatter_buy.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeTriangle)
        scatter_buy.setMarkerSize(12)
        scatter_buy.setColor(QColor(COLOR_SUCCESS))
        scatter_buy.setBorderColor(QColor(COLOR_SUCCESS))

        scatter_sell = QScatterSeries()
        scatter_sell.setName("Strategy Sell Signals")
        scatter_sell.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeRectangle)
        scatter_sell.setMarkerSize(12)
        scatter_sell.setColor(QColor(COLOR_DANGER))
        scatter_sell.setBorderColor(QColor(COLOR_DANGER))

        for signal in getattr(self, "_served_signals", []):
            side = signal.get("side")
            ts = int(signal.get("time_ms", 0))
            price = float(signal.get("price", 0.0))
            if side == "buy" and ts and price:
                scatter_buy.append(ts, price)
            elif side == "sell" and ts and price:
                scatter_sell.append(ts, price)

        self.price_chart.addSeries(scatter_buy)
        scatter_buy.attachAxis(axis_x)
        scatter_buy.attachAxis(axis_y)

        self.price_chart.addSeries(scatter_sell)
        scatter_sell.attachAxis(axis_x)
        scatter_sell.attachAxis(axis_y)

    def _plot_bollinger_bands(self, axis_x, axis_y) -> None:
        # Real Bollinger bands: 20-close SMA plus/minus 2 standard
        # deviations, computed from the served close prices.
        if not self.chk_bollinger.isChecked():
            return
        window = 20
        closes = [float(t["close"]) for t in self.ticks_data]
        if len(closes) < window:
            return
        upper_band = QLineSeries()
        upper_band.setName("Bollinger Upper (2.0σ)")
        lower_band = QLineSeries()
        lower_band.setName("Bollinger Lower (2.0σ)")

        pen_b = QPen(QColor(COLOR_TEXT_MUTED))
        pen_b.setStyle(Qt.PenStyle.DashLine)
        pen_b.setWidth(1)
        upper_band.setPen(pen_b)
        lower_band.setPen(pen_b)

        for i in range(window - 1, len(closes)):
            sample = closes[i - window + 1 : i + 1]
            mean = sum(sample) / window
            variance = sum((c - mean) ** 2 for c in sample) / window
            spread = 2.0 * math.sqrt(variance)
            ts = int(self.ticks_data[i]["time"].timestamp() * 1000)
            upper_band.append(ts, mean + spread)
            lower_band.append(ts, mean - spread)

        self.price_chart.addSeries(upper_band)
        upper_band.attachAxis(axis_x)
        upper_band.attachAxis(axis_y)

        self.price_chart.addSeries(lower_band)
        lower_band.attachAxis(axis_x)
        lower_band.attachAxis(axis_y)

    def _replot_price_chart(self) -> None:
        self._clear_chart(self.price_chart)
        axis_x, axis_y = self._build_price_axes()

        min_time = QDateTime.fromMSecsSinceEpoch(
            int(self.ticks_data[0]["time"].timestamp() * 1000)
        )
        max_time = QDateTime.fromMSecsSinceEpoch(
            int(self.ticks_data[-1]["time"].timestamp() * 1000)
        )

        if self.chart_style_candlestick:
            min_price, max_price = self._plot_candlestick_series(axis_x, axis_y)
        else:
            min_price, max_price = self._plot_line_series(axis_x, axis_y)

        self._plot_signal_overlays(axis_x, axis_y)
        self._plot_bollinger_bands(axis_x, axis_y)

        # Set axes ranges
        axis_x.setRange(min_time, max_time)
        # Margin scaling padding
        axis_y.setRange(min_price * 0.998, max_price * 1.002)

    def _plot_served_depth(self, depth: dict) -> None:
        """Paint cumulative bid/ask depth from the served depth points."""
        axis_depth_x = QValueAxis()
        axis_depth_x.setTitleText("Price Spread Shift ($)")
        axis_depth_x.setTitleBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
        axis_depth_x.setLabelsColor(QColor(COLOR_TEXT_MUTED))

        axis_depth_y = QValueAxis()
        axis_depth_y.setTitleText("Cumulative Depth Volume")
        axis_depth_y.setTitleBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
        axis_depth_y.setLabelsColor(QColor(COLOR_TEXT_MUTED))

        self.depth_chart.addAxis(axis_depth_x, Qt.AlignmentFlag.AlignBottom)
        self.depth_chart.addAxis(axis_depth_y, Qt.AlignmentFlag.AlignLeft)

        bids_line, asks_line = self._depth_line_series(depth)
        bid_area = QAreaSeries(bids_line)
        bid_area.setName("Bids Volume Depth")
        bid_area.setColor(QColor(0, 230, 118, 90))  # Translucent green
        bid_area.setBorderColor(QColor(COLOR_SUCCESS))

        ask_area = QAreaSeries(asks_line)
        ask_area.setName("Asks Volume Depth")
        ask_area.setColor(QColor(255, 23, 68, 90))  # Translucent red
        ask_area.setBorderColor(QColor(COLOR_DANGER))

        # QAreaSeries only borrows its boundary line series; PySide would free
        # the locals when this method returns and the chart layout then reads
        # a dangling pointer (AreaChartItem::fixEdgeSeriesDomain SIGSEGV).
        self._depth_boundary_lines = (bids_line, asks_line)

        self.depth_chart.addSeries(bid_area)
        bid_area.attachAxis(axis_depth_x)
        bid_area.attachAxis(axis_depth_y)

        self.depth_chart.addSeries(ask_area)
        ask_area.attachAxis(axis_depth_x)
        ask_area.attachAxis(axis_depth_y)

        prices = [p for p, _ in depth["bids"]] + [p for p, _ in depth["asks"]]
        spread = max(max(prices) - min(prices), 1.0)
        axis_depth_x.setRange(min(prices) - spread / 20, max(prices) + spread / 20)
        axis_depth_y.setRange(0.0, self._max_cumulative(depth) * 1.1)

    @staticmethod
    def _depth_line_series(depth: dict) -> tuple[QLineSeries, QLineSeries]:
        bids_line = QLineSeries()
        asks_line = QLineSeries()
        for series, points in ((bids_line, depth["bids"]), (asks_line, depth["asks"])):
            cumulative = 0.0
            for price, size in points:
                cumulative += float(size)
                series.append(float(price), cumulative)
        return bids_line, asks_line

    @staticmethod
    def _max_cumulative(depth: dict) -> float:
        def total(points):
            return sum(float(size) for _, size in points)

        return max(total(depth["bids"]), total(depth["asks"]), 0.0)

    def _replot_depth_chart(self, depth: dict | None) -> None:
        # ── Replot cumulative orderbook bid/ask depth from served points ──
        self._clear_chart(self.depth_chart)
        if not depth or not depth.get("bids") or not depth.get("asks"):
            self.depth_chart.setTitle("Orderbook depth unavailable")
            self.depth_chart.setTitleBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
            return
        self.depth_chart.setTitle("Bid / Ask Cumulative Orderbook Depth")
        self._plot_served_depth(depth)

    def _show_unavailable_charts(self) -> None:
        self._clear_chart(self.price_chart)
        self.price_chart.setTitle("Market data unavailable")
        self.price_chart.setTitleBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
        self._replot_depth_chart(None)

    def replot_charts(self):
        """Re-populate the QtCharts from the current served state only."""
        if not self.ticks_data:
            self._show_unavailable_charts()
            return
        self._replot_price_chart()
        self._replot_depth_chart(getattr(self, "_served_depth", None))
