#!/usr/bin/env python3
"""Service Dashboard Panel — Homepage-style service management for Axil.

Displays all configured Agent-OS services as interactive cards with
real-time status, key metrics, and clickable links. Uses the
served Arbora dashboard endpoints for configuration and data fetching.

Concept: MERISTEM-019 (GUI Dashboard Panel)

The card/header widgets live in
:mod:`axil.qt.service_dashboard_widgets` and the bounded background
fetch worker in :mod:`axil.qt.service_dashboard_worker`.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from axil.qt.colors import (
    ACCENT_PRIMARY,
    TEXT_MUTED,
)
from axil.qt.service_dashboard_widgets import CategoryHeader, ServiceCard
from axil.qt.service_dashboard_worker import _FetchWorker

logger = logging.getLogger(__name__)


class ServiceDashboardPanel(QWidget):
    """Homepage-style service dashboard with grouped service cards.

    Reads layout and widget values through BackendAdapter's gateway transport.
    No configuration or widget aggregation runs in the desktop process.
    """

    def __init__(self, worker: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.worker = worker
        self._cards: dict[str, ServiceCard] = {}
        self._fetch_worker: _FetchWorker | None = None
        self._refresh_timer: QTimer | None = None
        self._closed = False

        self._init_ui()
        self._refresh_data()
        self._start_auto_refresh()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)

    def _init_ui(self) -> None:
        """Build the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header bar
        header_layout = QHBoxLayout()

        title = QLabel("🏠 Agent-OS Service Dashboard")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {ACCENT_PRIMARY};"
        )
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        header_layout.addWidget(self.stats_label)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self._refresh_data)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Scrollable card grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)

    def _clear_dashboard(self) -> None:
        self._cards.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

    def _populate_dashboard(self, layout: dict) -> None:
        """Render an already received layout on the UI thread."""
        self._clear_dashboard()
        if not layout["groups"]:
            empty = QLabel("No services configured on the gateway.")
            empty.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 14px; font-style: italic; padding: 40px;"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty)
            return

        for group in layout["groups"]:
            # Category header
            self.grid_layout.addWidget(CategoryHeader(group["name"]))
            self._add_service_grid(group["services"])

        self.grid_layout.addStretch()

        # Update stats
        total = len(self._cards)
        self.stats_label.setText(f"{total} services  |  Loading data...")

    def _add_service_grid(self, services: list[dict]) -> None:
        """Add one group's visible service cards as a 3-column grid."""
        grid = QGridLayout()
        grid.setSpacing(12)

        col = 0
        row = 0
        for svc in services:
            if not svc.get("visible", True):
                continue
            card = ServiceCard(
                service_id=svc["id"],
                display_name=svc["name"],
                url=svc.get("url", ""),
            )
            self._cards[svc["id"]] = card
            grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        # Add grid to the layout
        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        self.grid_layout.addWidget(grid_widget)

    def _refresh_data(self) -> None:
        """Kick off a background data fetch."""
        if self._closed or self._fetch_worker is not None:
            return

        self._fetch_worker = _FetchWorker()
        self._fetch_worker.data_ready.connect(self._on_snapshot_ready)
        self._fetch_worker.finished.connect(self._on_fetch_finished)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_finished(self) -> None:
        self._fetch_worker = None

    def _on_snapshot_ready(self, snapshot: dict) -> None:
        if self._closed:
            return
        self._populate_dashboard(snapshot["layout"])
        self._on_data_ready(snapshot["data"])

    def _on_data_ready(self, data: dict) -> None:
        """Update cards with fetched data."""
        ok_count = 0
        err_count = 0

        for svc_id, widget_data in data.items():
            card = self._cards.get(svc_id)
            if not card:
                continue

            card.update_data(
                status=widget_data["status"],
                fields=widget_data.get("fields", []),
                error=widget_data.get("error"),
            )

            if widget_data["status"] == "ok":
                ok_count += 1
            elif widget_data["status"] == "error":
                err_count += 1

        total = len(self._cards)
        self.stats_label.setText(
            f"{total} services  |  {ok_count} healthy  |  {err_count} errors"
        )

    def _on_fetch_error(self, error_msg: str) -> None:
        """Handle fetch error."""
        if self._closed:
            return
        self._clear_dashboard()
        logger.error("Dashboard fetch failed")
        self.stats_label.setText("⚠ Fetch error")

    def _start_auto_refresh(self) -> None:
        """Start periodic auto-refresh (every 30 seconds)."""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_data)
        self._refresh_timer.start(30_000)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        super().closeEvent(event)

    def cleanup(self) -> None:
        """Stop timers and threads on cleanup."""
        self._closed = True
        if self._refresh_timer:
            self._refresh_timer.stop()
        if self._fetch_worker is not None:
            self._fetch_worker.cancel()
