# AXIL-CLIENT quickstart

Run the served proofs of the client from the repository root.

## Dashboard reads and lifecycle (R001.2, R001.3)

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_service_dashboard_transport.py tests/test_service_dashboard_async.py
```

Expected: exact routes, redirect refusal, bounded reads and cancellation cleanup pass.

## Registry preflight and graph failures (R002.2, R005.1, R005.2)

```bash
uv run pytest tests/test_gateway_client_registry.py tests/test_graph_query_wiring.py
```

Expected: an unknown operation makes no request; a typed failure and a redirect keep their own result.

## Run view (R019.1 to R019.6, planned)

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_run_view.py
```

Expected once built: a served fixture renders summary, configuration, context, cost and an available plan.
