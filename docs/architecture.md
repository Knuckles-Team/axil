# Architecture

Axil is a PySide6 (Qt6) desktop cockpit. It reaches data only through Arbora, using `arbora.client`. Axil holds no store.

## Layers

- `axil/axil.py` builds the main window and the system tray.
- `axil/qt/` holds the cockpit panels, the terminal widget and the tool guard.
- `axil/services/` holds the packaging commands and backend adapters.
- `axil/utils/` holds the agent bridge and the background daemon.

## Rules

- Qt calls must run on the UI thread. Long work must run on `QThreadPool`.
- Arbora owns admission, authentication and served operations. Medulla owns facts and memory. Meristem runs agent loops. The cockpit must call Arbora and reuse its client.

See the [technical overview](overview.md) for diagrams.
