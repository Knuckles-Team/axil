# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [5.2.2] - 2026-11-25

### Added
- **Run harness cockpit (AXIL-CLIENT-R019.1 to AXIL-CLIENT-R019.6)**: `RunViewPanel` (sidebar index 18, `axil/qt/run_view.py`) renders one selected run through the served Arbora operations `runs.get` and `runs.metrics` via the new `GatewayClient` run facade (`axil/services/gateway_run_facade.py`): distinct terminal-reason labels (final answer / context overflow / stuck / step budget / error, unknown or missing reads as unavailable), peak context tokens against the run budget, per-run USD cost, the applied harness configuration reference with `context_policy` / `plan_scaffold` / `action_space` (missing configuration never falls back to defaults), a read-only current-plan snapshot (order, revision, item statuses; expired, wrong-run, regressing or unavailable snapshots reveal no items and no edit controls), and the cost-per-solved-task aggregate with its solved-task label (zero-solved abstention renders unavailable, never zero).
- **Finance cockpit gateway contract (AXIL-CLIENT-R014)**: `FinanceCockpitPanel` now fetches market state through the gateway facade's `market.ticks` registered operation instead of simulated state; when the route fails, is denied, is unregistered, or times out the panel renders an explicit unavailable state and a raised gateway error never escapes into the Qt event loop.
- **Concept ID registry (`docs/concepts.yaml`)**: canonical numeric `GBOT-X.Y` registry cross-referenced by `CONCEPT:` markers in code docstrings and by the `pytest.mark.concept` test markers.
- **Source-quality gate tests (`tests/test_source_quality.py`, `tests/test_source_quality_scored.py`)**: 41 tests covering the dependency matrix, function-size/complexity/module-size checks, test parametrization, documentation entry points and references, presentation/adapter separation, concept traceability, configured lint/type checks, the pinned formatter version, changelog format and recency, environment-variable documentation, the served-interface boundary, every scorer domain threshold, the overall grade, the installed entry wiring, and the served-entry proof.
- `tests/test_finance_cockpit.py` (offscreen panel contract with a failing gateway) and `tests/test_run_view.py` (served fixture transport for the run harness rows).

### Changed
- **Dependency contract**: the unused `medulla` engine dependency is removed (the client reaches data only through the served Arbora boundary), the Windows-only `pywin32` requirement carries a lower bound before its marker, and the `test` and `dev` extras declare `black` and `mypy` so the pinned formatter and type gates run from the declared environment.
- **Rename cutover geniusbot -> axil (hard cutover, no shims)**: dist `geniusbot` -> `axil`, import package `geniusbot` -> `axil`, CLIs `geniusbot`/`geniusbot-package` -> `axil`/`axil-package`, env vars `GENIUSBOT_*` -> `AXIL_*` (old names no longer read), packaging desktop file/icons/installer renamed; docs reference `meristem` and `tuig` by their new names.
- **KG extraction cockpit with native force graph (`CONCEPT:AU-ECO.connector.git-task-resolver`)**: `extraction_cockpit.py` (`ExtractionCockpitPanel`) brings the document→KG experience to the Qt cockpit over the real gateway with live SSE — text/URL input streams extracted facts onto `force_graph.py`, a native `QGraphicsView` force-directed widget (pure, unit-testable Fruchterman-Reingold `relax_layout`) where each fact is a clickable directed edge and node keys are normalized to mirror the backend.
- **Usage & Cost cockpit (`CONCEPT:AU-ECO.mcp.usage-cost-observability-surface`)**: `UsageCockpitPanel` (sidebar 💰 Usage & Cost) with agentsview parity — KPI cards, cost-by-model, tool/skill/db-call metrics, a day×hour heatmap, top-sessions browser, and Langfuse links, all over the shared SDK facade via the `QThreadPool` worker (never blocks the Qt loop, graceful-offline).
- **Source-quality module splits**: `axil/axil.py` became a thin orchestrator (window layout builders, chat and deck mixins moved to their own modules); `axil/services/gateway_client.py` became a thin facade over namespaced route facades; `scripts/check_tracked_privacy.py` became a thin entry over the `privacy_gate_*` modules; `axil/qt/finance_cockpit.py` split into the panel plus `finance_charts.py` / `finance_controls.py`; `axil/qt/service_dashboard.py` split into the panel plus `service_dashboard_worker.py` / `service_dashboard_widgets.py`. Every desktop module now sits under the shared module-size and function-size thresholds.
- Documented previously missing environment variables (`QT_QPA_PLATFORM`, `TERM`, `_MEIPASS`, `_MEIPASS2`, `AXIL_OPERATION_REGISTRY_PATH`, `AGENT_UTILITIES_*`, the process-identity inputs, and the toolchain bookkeeping vars) in `.env.example` and `README.md`.
- Expanded `AGENTS.md` with explicit project structure rules.
- Bumped dependency constraints for `pytest-qt`, `PySide6`, `agent-utilities`, and `ruff` in `pyproject.toml` to address code audit findings.
- Replaced `pypiwin32` with `pywin32` in `pyproject.toml` dependencies.
- Updated `ruff-pre-commit` hook to `v0.15.15` in `.pre-commit-config.yaml`.
## [3.29.6] - 2026-05-25

### Added
- **Visual Finance Dashboard Panel (`finance_cockpit.py`)**: Renders high-performance native `PySide6.QtCharts` supporting candlestick charts, line charts, bid/ask depth volume graphs, togglable RSI/MACD strategy indicators, and background-loaded RSS financial news feeds. Integrates CCXT, Paper, Alpaca, and Polymarket simulated feeds (`CONCEPT:GBOT-6.0`, `CONCEPT:GBOT-7.0`, `CONCEPT:GBOT-8.0`).
- **Integrated Systems Cockpit panels**: Renders 5 modular space-dark visual monitors:
  * `graph_explorer.py` — Cypher shells + interactive node graph views.
  * `telemetry_dashboard.py` — Health success dial gauges + logfire trace lists.
  * `workflow_builder.py` — specialist agent pipeline layout + swarm debate console logs.
  * `security_policy.py` — Zero-Trust permission grid checkboxes + strictness slider.
  * `infra_cockpit.py` — Docker stack container tables + SSH tunnels map load meters.
- **Embedded Hybrid Terminal (`terminal_widget.py`)**: Hosts local xterm.js sessions via QWebEngineView + high-speed QWebChannel streams (`CONCEPT:GBOT-3.0`).
- **Dynamic Widget Schema Mapper (`widget_mapper.py`)**: Generates premium widgets from agent schemas on the fly (`CONCEPT:GBOT-2.0`).
- **Ecosystem Packaging Infrastructure**:
  * Added `setup.iss` Inno Setup compiler config to package Windows standalone executables.
  * Added `packaging/linux/control` and `packaging/linux/geniusbot.desktop` Debian configuration templates.
  * Added reusable Github workflow `pipelines/.github/workflows/desktop_release_pipeline.yml` to compile and distribute `.deb`, `.rpm`, `.exe` multi-platform releases.
- **Packaging Files**: Added `.bumpversion.cfg`, `.env`, `.env.example`, `requirements.txt`, and modern `pyproject.toml` Hatchling builds.
- **Headless Test Framework**: Added `tests/conftest.py` with session-scoped `qapp` fixtures, `tests/test_init_dynamics.py` import checks, `tests/test_concept_parity.py` registry validation, and `tests/test_cockpit_views.py` views verification.

### Changed
- Migrated core UI system from legacy PyQt6 to PySide6 and refactored startup to use async thread pools (`AgentBridgeWorker` / `CONCEPT:GBOT-5.0`).
- Updated central stack widget layouts to support left category navigation sidebars, action card decks, and retracting details drawers.

### Removed
- Safely deprecated and deleted all legacy plugins in `geniusbot/plugins/` (including subshift, webarchiver, systems manager, rom manager, media manager) and stripped `setup.py` packaging structures.
