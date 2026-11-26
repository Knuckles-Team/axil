"""Finance cockpit gateway contract tests (AXIL-CLIENT-R014)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from axil.qt.finance_cockpit import FinanceCockpitPanel

pytestmark = pytest.mark.concept("GBOT-7.0")


class _SyncWorker:
    """Run panel tasks synchronously, mirroring AgentRunnable's signals:
    dict results emit finished, exceptions emit the error message."""

    def run_agent_task(
        self, async_func, on_finished=None, on_error=None, on_progress=None
    ):
        kwargs = {"progress_cb": on_progress}
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(async_func(**kwargs))
        except Exception as exc:
            if on_error is not None:
                on_error(f"Agent task failed ({type(exc).__name__})")
            return
        finally:
            loop.close()
        if on_finished is not None and isinstance(result, dict):
            on_finished(result)


class _StubMarketFacade:
    """A market facade whose served outcome is fixed by the test."""

    def __init__(self, outcome: Any, raise_error: Exception | None = None) -> None:
        self.outcome = outcome
        self.raise_error = raise_error
        self.calls: list[tuple[str, int]] = []

    async def fetch_market_ticks(self, symbol: str, *, limit: int = 40) -> dict:
        self.calls.append((symbol, limit))
        if self.raise_error is not None:
            raise self.raise_error
        return self.outcome


class _StubGateway:
    def __init__(self, market: _StubMarketFacade) -> None:
        self.market = market


@pytest.mark.spec("AXIL-CLIENT-R014")
@pytest.mark.concept("GBOT-8.0")
def test_panel_unavailable_state(qapp) -> None:
    """A raised gateway error never escapes; the panel reads unavailable."""
    facade = _StubMarketFacade(None, raise_error=RuntimeError("transport down"))
    panel = FinanceCockpitPanel(_SyncWorker(), gateway=_StubGateway(facade))
    assert facade.calls == [("BTC/USDT", 40)], "panel requested served state on startup"
    assert panel._available is False
    assert panel.ticks_data == []
    assert panel.tbl_positions.rowCount() == 0
    assert panel.price_chart.title() == "Market data unavailable"
    assert "unavailable" in panel.txt_news.toPlainText().lower()


@pytest.mark.spec("AXIL-CLIENT-R014")
@pytest.mark.concept("GBOT-8.0")
def test_unregistered_route_reads_unavailable(qapp) -> None:
    """The typed CLIENT_UNAVAILABLE facade default renders unavailable."""
    facade = _StubMarketFacade(
        {
            "error": "markets route unavailable (operation not registered)",
            "code": "CLIENT_UNAVAILABLE",
        }
    )
    panel = FinanceCockpitPanel(_SyncWorker(), gateway=_StubGateway(facade))
    assert panel._available is False
    assert panel.ticks_data == []
    assert "unavailable" in panel.txt_news.toPlainText().lower()


@pytest.mark.spec("AXIL-CLIENT-R014")
@pytest.mark.concept("GBOT-8.0")
def test_denied_market_route_reads_unavailable(qapp) -> None:
    """A typed gateway denial renders the unavailable state, not data."""
    facade = _StubMarketFacade(
        {"status": "failed", "code": "FORBIDDEN", "error": "denied"}
    )
    panel = FinanceCockpitPanel(_SyncWorker(), gateway=_StubGateway(facade))
    assert panel._available is False
    assert panel.price_chart.title() == "Market data unavailable"
    assert "denied" in panel.txt_news.toPlainText().lower()


def _served_result() -> dict:
    return {
        "ticks": [
            {
                "time": f"2026-11-25T10:{i:02d}:00",
                "open": 100 + i,
                "high": 101 + i,
                "low": 99 + i,
                "close": 100.5 + i,
            }
            for i in range(5)
        ],
        "positions": [{"symbol": "BTC/USDT", "size": 0.25, "entry": 100.0, "pnl": 5.5}],
        "depth": {"bids": [[100.0, 1.0]], "asks": [[101.0, 1.0]]},
    }


@pytest.mark.spec("AXIL-CLIENT-R014")
@pytest.mark.concept("GBOT-8.0")
def test_panel_renders_served_market_state(qapp) -> None:
    """A served success envelope renders ticks, positions, and depth."""
    facade = _StubMarketFacade({"status": "success", "result": _served_result()})
    panel = FinanceCockpitPanel(_SyncWorker(), gateway=_StubGateway(facade))
    assert panel._available is True
    assert len(panel.ticks_data) == 5
    assert panel.positions["BTC/USDT"]["pnl"] == 5.5
    assert panel.tbl_positions.rowCount() == 1
    assert panel.price_chart.title() == "Served Quotes: BTC/USDT"
