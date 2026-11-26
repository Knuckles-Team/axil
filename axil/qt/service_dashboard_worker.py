"""Background fetch worker for the service dashboard panel.

The dashboard's data fetch runs on a ``QThreadPool`` thread with its own
bounded asyncio loop, so the UI thread never blocks on the gateway.
Cancellation is cooperative: the task is cancelled from the UI thread via
``call_soon_threadsafe`` and a bounded deadline expires the cleanup rather
than waiting on it, so a stuck fetch can never hold the process open at
exit.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class _FetchRunnable(QRunnable):
    def __init__(self, worker: _FetchWorker) -> None:
        super().__init__()
        self.worker = worker

    def run(self) -> None:
        self.worker.run()


class _FetchWorker(QObject):
    """Background thread that fetches all widget data."""

    data_ready = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self) -> None:
        # The runnable retains this bridge until bounded async cleanup finishes.
        super().__init__()
        self._done = threading.Event()
        self._shutting_down = threading.Event()
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[dict] | None = None
        self.finished.connect(self.deleteLater)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def start(self) -> None:
        QThreadPool.globalInstance().start(_FetchRunnable(self))

    def shutdown(self) -> None:
        """Drain cooperative cleanup at process exit without an unbounded wait."""
        self._shutting_down.set()
        self.cancel()
        self._done.wait(timeout=1.0)

    def cancel(self) -> None:
        with self._lock:
            if self._cancelled.is_set():
                return
            self._cancelled.set()
            if self._loop is not None and self._task is not None:
                self._loop.call_soon_threadsafe(self._cancel_task)

    def _cancel_task(self) -> None:
        if self._task is not None and self._loop is not None:
            self._task.cancel()
            self._loop.call_later(0.5, self._expire_cleanup)

    def _expire_cleanup(self) -> None:
        if self._task is not None and not self._task.done() and self._loop is not None:
            logger.warning("Dashboard cancellation exceeded cleanup deadline")
            self._task.cancel()
            # Stop only this coroutine loop, never a Qt or operating-system thread.
            self._loop.call_later(0.1, self._loop.stop)

    def run(self) -> None:
        from axil.services.backend_adapter import backend

        loop = asyncio.new_event_loop()
        try:
            with self._lock:
                self._loop = loop
                self._task = loop.create_task(backend.service_dashboard_snapshot())
                if self._cancelled.is_set():
                    self._task.cancel()
            result = loop.run_until_complete(self._task)
            if not self._cancelled.is_set():
                self.data_ready.emit(result)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            if not self._cancelled.is_set():
                self.error.emit(type(exc).__name__)
        finally:
            with self._lock:
                self._loop = None
                self._task = None
            loop.close()
            self._done.set()
            if not self._shutting_down.is_set():
                self.finished.emit()
