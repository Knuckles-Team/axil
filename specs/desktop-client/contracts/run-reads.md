# Run reads contract

Provider: arbora ARBORA-OPS-R021.4.5
Consumer: axil AXIL-CLIENT-R019.1

## Wire shape

The client calls the registered run-read operation with one `run_id`. It receives the versioned Arbora envelope. The envelope carries these snake_case fields: `termination_reason`, `peak_context_tokens`, `context_budget_tokens`, `cost_usd`, `harness_config_ref`, `harness_config` and `current_plan`. The client accepts no other spelling of a field. A null field means unavailable. A measured zero is a value.

Aggregate reads (`runs.metrics`) carry `cost_per_solved_task_usd` with their group label. The client shows an aggregate only under that label.

## Refusal codes

- Operation absent from the installed registry: the client shows unavailable and makes no request.
- Denied or timed-out read: the client clears all protected values of the previous run and shows unavailable.
- Unknown `termination_reason`: the client shows unavailable and never infers success from a final answer.
- Expired, wrong-run or regressing `current_plan` snapshot: the client shows no items and no edit controls.

## Owner rows

- Provider rows: arbora ARBORA-OPS-R021.4.5 (per-run fields), arbora ARBORA-OPS-R021.4.6 (registration and generated client).
- Consumer rows: axil AXIL-CLIENT-R019.1 to AXIL-CLIENT-R019.6.
