"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Chart rendering for the finance cockpit panel.

Snappy native QtCharts rendering for the trading cockpit: the main price
chart (candlestick or line, with optional execution-signal overlays and
Bollinger bands) and the cumulative bid/ask orderbook depth chart. Mixed
into :class:`axil.qt.finance_cockpit.FinanceCockpitPanel`, which provides
the chart views, tick data, and overlay state the painters read.
"""

from __future__ import annotations

import random

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
        # Replot Candlestick OHLCV Bars
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
        # Replot snappy illuminated Line Series
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
        # Visual indicator overlays scatter plots (Feature parity requested)
        if not self.chk_signals.isChecked():
            return
        scatter_buy = QScatterSeries()
        scatter_buy.setName("Auto Strategy Buy Signals")
        scatter_buy.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeTriangle)
        scatter_buy.setMarkerSize(12)
        scatter_buy.setColor(QColor(COLOR_SUCCESS))
        scatter_buy.setBorderColor(QColor(COLOR_SUCCESS))

        scatter_sell = QScatterSeries()
        scatter_sell.setName("Auto Strategy Sell Signals")
        scatter_sell.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeRectangle)
        scatter_sell.setMarkerSize(12)

        scatter_sell.setColor(QColor(COLOR_DANGER))
        scatter_sell.setBorderColor(QColor(COLOR_DANGER))

        # Populate mock signals along the series
        for i, t in enumerate(self.ticks_data):
            if i % 8 == 3:  # Mock crossover scatter spots
                ts = int(t["time"].timestamp() * 1000)
                scatter_buy.append(ts, t["low"] - 30.0)
            elif i % 8 == 6:
                ts = int(t["time"].timestamp() * 1000)
                scatter_sell.append(ts, t["high"] + 30.0)

        self.price_chart.addSeries(scatter_buy)
        scatter_buy.attachAxis(axis_x)
        scatter_buy.attachAxis(axis_y)

        self.price_chart.addSeries(scatter_sell)
        scatter_sell.attachAxis(axis_x)
        scatter_sell.attachAxis(axis_y)

    def _plot_bollinger_bands(self, axis_x, axis_y) -> None:
        # Bollinger Bands lines rendering
        if not self.chk_bollinger.isChecked():
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

        for t in self.ticks_data:
            ts = int(t["time"].timestamp() * 1000)
            upper_band.append(ts, t["close"] + 250.0)
            lower_band.append(ts, t["close"] - 250.0)

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

    def _replot_depth_chart(self) -> None:
        # ── Replot cumulative orderbook bid/ask depth (FinceptTerminal style) ──
        self._clear_chart(self.depth_chart)

        # Depth axis definition
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

        # Populate snappy bid/ask curves
        mid_price = self.ticks_data[-1]["close"]
        bids_line, asks_line, max_accum = self._build_depth_boundary_lines(mid_price)

        # Build area series with color gradients
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

        # Set ranges
        axis_depth_x.setRange(mid_price - 160.0, mid_price + 160.0)
        axis_depth_y.setRange(0.0, max_accum * 1.1)

    def _build_depth_boundary_lines(
        self, mid_price: float
    ) -> tuple[QLineSeries, QLineSeries, float]:
        """Build the cumulative bid/ask depth line series around the mid price."""
        bids_line = QLineSeries()
        asks_line = QLineSeries()

        # Cumulative bids depth (price gets lower, size gets higher)
        accum_bid = 0.0
        for offset in range(1, 15):
            price = mid_price - (offset * 10.0)
            accum_bid += random.uniform(0.5, 4.0)
            bids_line.append(price, accum_bid)

        # Cumulative asks depth (price gets higher, size gets higher)
        accum_ask = 0.0
        for offset in range(1, 15):
            price = mid_price + (offset * 10.0)
            accum_ask += random.uniform(0.5, 4.0)
            asks_line.append(price, accum_ask)

        return bids_line, asks_line, max(accum_bid, accum_ask)

    def replot_charts(self):
        """snappily clear and re-populate the QtCharts."""
        self._replot_price_chart()
        self._replot_depth_chart()
