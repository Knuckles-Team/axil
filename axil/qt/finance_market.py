"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Market state handling for the finance cockpit panel.

Fetches the served ``markets.ticks`` state through the gateway market
facade on behalf of the panel and classifies the envelope into the
panel's available/unavailable state. Mixed into
:class:`axil.qt.finance_cockpit.FinanceCockpitPanel`, which provides
the worker, gateway, and the widgets and served state this mixin reads
and updates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _coerce_time(value: Any) -> datetime | None:
    """Coerce a served tick time (ISO string or epoch seconds/ms)."""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        try:
            seconds = float(value)
            if seconds > 1e12:  # epoch milliseconds
                seconds /= 1000.0
            return datetime.fromtimestamp(seconds)
        except (OverflowError, OSError, ValueError):
            return None
    return None


class FinanceMarketMixin:
    """Served market state fetch and classification for the panel."""

    # Worker, widgets, and state provided by the panel the mixin is
    # mixed into.
    worker: Any
    _gateway: Any
    gateway: Any
    current_symbol: str
    ticks_data: list
    positions: dict
    _served_signals: list
    _served_depth: dict | None
    _available: bool
    price_chart: Any
    txt_news: Any
    tbl_positions: Any
    update_positions_table: Any
    replot_charts: Any

    def request_market_data(self) -> None:
        """Request the served market state for the selected symbol."""
        self._log(f"Requesting served market state for {self.current_symbol}.")
        self.worker.run_agent_task(
            self._fetch_market,
            on_finished=self._on_market_data,
            on_error=self._on_market_error,
        )

    async def _fetch_market(self, progress_cb=None) -> dict:
        """Fetch the served ticks through the gateway market facade."""
        return await self.gateway.market.fetch_market_ticks(
            self.current_symbol, limit=40
        )

    def _on_market_data(self, data: dict) -> None:
        """Classify the served envelope; render available or unavailable."""
        if data.get("status") == "failed" or data.get("code") == "CLIENT_UNAVAILABLE":
            self._render_unavailable(
                str(data.get("error") or data.get("code") or "route refused")
            )
            return
        result = data.get("result") if data.get("status") == "success" else None
        if not isinstance(result, dict):
            self._render_unavailable("no served ticks")
            return
        ticks = result.get("ticks")
        if not isinstance(ticks, list) or not ticks:
            self._render_unavailable("no served ticks")
            return
        self.ticks_data = [
            tick for tick in map(self._normalize_tick, ticks) if tick is not None
        ]
        if not self.ticks_data:
            self._render_unavailable("no valid served ticks")
            return
        self.positions = self._normalize_positions(result.get("positions"))
        self._served_signals = result.get("signals") or []
        self._served_depth = result.get("depth")
        self._available = True
        self.price_chart.setTitle(f"Served Quotes: {self.current_symbol}")
        self._log(
            f"Served market state for {self.current_symbol}: {len(self.ticks_data)} ticks."
        )
        self.update_positions_table()
        self.replot_charts()

    @staticmethod
    def _normalize_tick(raw: Any) -> dict | None:
        """Coerce one served tick into the chart shape, or None if malformed."""
        if not isinstance(raw, dict):
            return None
        time_value = _coerce_time(raw.get("time"))
        if time_value is None:
            return None
        try:
            return {
                "time": time_value,
                "open": float(raw["open"]),
                "high": float(raw["high"]),
                "low": float(raw["low"]),
                "close": float(raw["close"]),
            }
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_positions(raw: Any) -> dict[str, dict]:
        """Coerce the served positions list into the positions grid shape."""
        positions: dict[str, dict] = {}
        if not isinstance(raw, list):
            return positions
        for item in raw:
            if not isinstance(item, dict) or not isinstance(item.get("symbol"), str):
                continue
            try:
                positions[item["symbol"]] = {
                    "size": float(item.get("size", 0.0)),
                    "entry": float(item.get("entry", 0.0)),
                    "pnl": float(item.get("pnl", 0.0)),
                }
            except (TypeError, ValueError):
                continue
        return positions

    def _on_market_error(self, message: str) -> None:
        """A gateway failure must never escape the panel as a crash."""
        self._render_unavailable(message)

    def _render_unavailable(self, reason: str) -> None:
        """Render the explicit unavailable state; no fabricated data."""
        self._available = False
        self.ticks_data = []
        self.positions = {}
        self._served_signals = []
        self._served_depth = None
        self.price_chart.setTitle("Market data unavailable")
        self._log(f"Market data unavailable: {reason}")
        self.update_positions_table()
        self.replot_charts()

    def _log(self, message: str) -> None:
        """Append one timestamped line to the panel log."""
        self.txt_news.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
