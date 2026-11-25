"""Card and header widgets for the service dashboard panel.

The glassmorphic ``ServiceCard`` (status dot, name, URL, key fields, and
an error line) and the ``CategoryHeader`` group label, plus the status
color/icon tables they render from.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from axil.qt.colors import (
    ACCENT_PRIMARY,
    BG_SECONDARY,
    BORDER_COLOR,
    TEXT_MAIN,
    TEXT_MUTED,
)

# ── Status Colors ───────────────────────────────────────────────────

_STATUS_COLORS = {
    "ok": "#00E676",
    "warning": "#FFD600",
    "error": "#FF5252",
    "unknown": "#8A8A93",
}

_STATUS_ICONS = {
    "ok": "●",
    "warning": "●",
    "error": "●",
    "unknown": "○",
}


class ServiceCard(QFrame):
    """A single glassmorphic service card widget."""

    def __init__(
        self,
        service_id: str,
        display_name: str,
        url: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service_id = service_id
        self.display_name = display_name
        self.url = url

        self.setObjectName("ServiceCard")
        self.setStyleSheet(f"""
            QFrame#ServiceCard {{
                background-color: {BG_SECONDARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 14px;
            }}
            QFrame#ServiceCard:hover {{
                border: 1px solid {ACCENT_PRIMARY};
            }}
        """)
        self.setMinimumWidth(220)
        self.setMinimumHeight(120)
        self.setMaximumWidth(350)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Top row: status + name
        top_row = QHBoxLayout()
        self.status_label = QLabel("○")
        self.status_label.setStyleSheet(
            f"font-size: 14px; color: {_STATUS_COLORS['unknown']};"
        )
        top_row.addWidget(self.status_label)

        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {TEXT_MAIN};"
        )
        top_row.addWidget(self.name_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        # URL line
        if url:
            url_label = QLabel(url)
            url_label.setStyleSheet(
                f"font-size: 10px; color: {TEXT_MUTED}; font-style: italic;"
            )
            layout.addWidget(url_label)

        # Fields area
        self.fields_container = QVBoxLayout()
        self.fields_container.setSpacing(2)
        layout.addLayout(self.fields_container)

        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("font-size: 11px; color: #FF5252;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        layout.addStretch()

    def update_data(
        self,
        status: str,
        fields: list[dict[str, str]],
        error: str | None = None,
    ) -> None:
        """Update card with fresh widget data."""
        color = _STATUS_COLORS.get(status, _STATUS_COLORS["unknown"])
        icon = _STATUS_ICONS.get(status, "○")
        self.status_label.setText(icon)
        self.status_label.setStyleSheet(f"font-size: 14px; color: {color};")

        # Clear existing fields
        while self.fields_container.count():
            item = self.fields_container.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        if error:
            self.error_label.setText(f"⚠ {type(error).__name__}")
            self.error_label.show()
            return

        self.error_label.hide()

        # Render fields (max 5)
        for field in fields[:5]:
            field_widget = QLabel(
                f"<span style='color:{TEXT_MUTED};'>{field['label']}:</span> "
                f"<span style='font-weight:bold;color:{TEXT_MAIN};'>{field['value']}</span>"
            )
            field_widget.setStyleSheet("font-size: 11px;")
            self.fields_container.addWidget(field_widget)


class CategoryHeader(QLabel):
    """Styled category group header."""

    def __init__(self, category_name: str, parent: QWidget | None = None) -> None:
        super().__init__(f"▸ {category_name.upper()}", parent)
        self.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {ACCENT_PRIMARY}; padding: 8px 0 4px 0; margin-top: 12px;"
        )
