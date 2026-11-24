"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Console output bridging for the Axil window.

Bridges the process standard streams into Qt signals so the window's
console view renders output thread-safely. A wrapper keeps itself on the
stream until it is destroyed or deactivated, and nested wrappers forward
to the stream below them instead of dropping writes. The window owns one
wrapper per stream and restores them on a real close.
"""

import sys
import weakref

from PySide6.QtCore import QObject, Signal


class OutputWrapper(QObject):
    """Bridge standard output streams into Qt Signals thread-safely."""

    outputWritten = Signal(str, bool)

    def __init__(self, parent, stdout=True):
        super().__init__(parent)
        self._stdout = stdout
        self._active = True
        self._emitting = False
        self._stream = sys.stdout if stdout else sys.stderr
        original = self._stream
        reference = weakref.ref(self)

        def restore():
            wrapper = reference()
            if wrapper is not None:
                wrapper._active = False
            current = sys.stdout if stdout else sys.stderr
            if current is wrapper:
                target = original
                while isinstance(target, OutputWrapper) and not target._active:
                    target = target._stream
                if stdout:
                    sys.stdout = target
                else:
                    sys.stderr = target

        self.restore = restore
        self.destroyed.connect(lambda *_: restore())
        if stdout:
            sys.stdout = self
        else:
            sys.stderr = self

    def write(self, text):
        self._stream.write(text)
        if self._active and not self._emitting:
            self._emitting = True
            try:
                self.outputWritten.emit(text, self._stdout)
            finally:
                self._emitting = False

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __del__(self):
        restore = self.__dict__.get("restore")
        if restore is not None:
            restore()
