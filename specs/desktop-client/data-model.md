# AXIL-CLIENT data model

The client adds no durable store. These in-memory types exist today or are planned by a row.

| Type | File | Fields | Row |
|---|---|---|---|
| `OperationRegistryEntry` | axil/services/operation_registry.py | operation, digest, method | AXIL-CLIENT-R002.1 |
| `OperationRegistry` | axil/services/operation_registry.py | entries keyed by operation | AXIL-CLIENT-R002.1 |
| `PackagingTarget` | axil/services/packaging_manifest.py | name, build tool, output path, version | AXIL-CLIENT-R012.1 |
| `PackagingManifest` | axil/services/packaging_manifest.py | source version, targets | AXIL-CLIENT-R012.1 |
| `RunView` (planned) | axil/qt/run_view.py | run id, termination reason, token counts, cost, configuration, plan snapshot | AXIL-CLIENT-R019.1 |
