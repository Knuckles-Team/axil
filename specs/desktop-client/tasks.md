# AXIL-CLIENT implementation tasks

Generated from the active rows of [requirements.md](requirements.md); one line per row, producer rows first.

## Tasks

- [ ] T001 AXIL-CLIENT-R001.1 implement and prove: One backend-adapter import seam
- [ ] T002 AXIL-CLIENT-R001.2 implement and prove: Served dashboard reads
- [ ] T003 AXIL-CLIENT-R001.3 implement and prove: Nonblocking dashboard lifecycle
- [x] T004 AXIL-CLIENT-R002.1 implement and prove: Typed registry-entry model and validator
- [ ] T005 AXIL-CLIENT-R002.2 implement and prove: Operation validated against the installed generated registry at the call site
- [ ] T006 AXIL-CLIENT-R003 implement and prove: Verified credential over TLS, bounded responses
- [ ] T007 AXIL-CLIENT-R004.1 implement and prove: Off-thread, non-blocking dispatch
- [ ] T008 AXIL-CLIENT-R004.2 implement and prove: Queued worker signal lifetime
- [ ] T009 AXIL-CLIENT-R005.3 implement and prove: Retained generic facade failure obligation
- [ ] T010 AXIL-CLIENT-R005.1 implement and prove: Preserve typed failed graph responses
- [ ] T011 AXIL-CLIENT-R005.2 implement and prove: Refuse graph redirects without following
- [ ] T012 AXIL-CLIENT-R006 implement and prove: No local approval authority
- [ ] T013 AXIL-CLIENT-R007 implement and prove: Embedded terminal sandbox
- [ ] T014 AXIL-CLIENT-R008 implement and prove: Lazy, on-demand cockpit panel loading
- [ ] T015 AXIL-CLIENT-R009 implement and prove: Honest voice-dictation states
- [ ] T016 AXIL-CLIENT-R010.1 implement and prove: Background tray residency
- [ ] T017 AXIL-CLIENT-R010.2 implement and prove: Console stream lifetime
- [ ] T018 AXIL-CLIENT-R011 implement and prove: Dynamic specialist discovery and schema-driven execution deck
- [x] T019 AXIL-CLIENT-R012.1 implement and prove: Typed packaging manifest model and validator
- [ ] T020 AXIL-CLIENT-R012.2 implement and prove: Cross-platform packaging and distribution
- [x] T021 AXIL-CLIENT-R013 implement and prove: Generated design-token colors
- [ ] T022 AXIL-CLIENT-R014 implement and prove: Finance cockpit panel contract
- [x] T023 AXIL-CLIENT-R015 implement and prove: Packaged `axil-development` skill
- [ ] T024 AXIL-CLIENT-R016.1 implement and prove: Spec and docs hooks in pre-commit
- [ ] T025 AXIL-CLIENT-R016.2 implement and prove: Canonical shared guardrails
- [x] T026 AXIL-CLIENT-R017 implement and prove: Docs layout parity
- [x] T027 AXIL-CLIENT-R018 implement and prove: AGENTS.md section parity
- [ ] T028 AXIL-CLIENT-R019.1 implement and prove: Run operation wiring
- [ ] T029 AXIL-CLIENT-R019.2 implement and prove: Applied configuration
- [ ] T030 AXIL-CLIENT-R019.3 implement and prove: Context and cost
- [ ] T031 AXIL-CLIENT-R019.4 implement and prove: Read-only current plan
- [ ] T032 AXIL-CLIENT-R019.5 implement and prove: Distinct terminal reasons
- [ ] T033 AXIL-CLIENT-R019.6 implement and prove: Served surface proof
- [ ] T034 AXIL-CLIENT-R020.1 implement and prove: The desktop test adapter dependency must satisfy the supported test matrix. Touches axil/,
- [ ] T035 AXIL-CLIENT-R020.2 implement and prove: The desktop UI dependency must satisfy the supported platform matrix. Touches axil/, tests
- [ ] T036 AXIL-CLIENT-R020.3 implement and prove: The desktop dependency contract must use the supported served-client boundary. Touches axi
- [ ] T037 AXIL-CLIENT-R020.4 implement and prove: The Windows dependency marker must resolve on supported platforms. Touches axil/, tests or
- [ ] T038 AXIL-CLIENT-R020.5 implement and prove: The formatter dependency must satisfy the supported source-check configuration. Touches ax
- [ ] T039 AXIL-CLIENT-R020.6 implement and prove: The main-window initialization must meet the shared function-size checks. Touches axil/, t
- [ ] T040 AXIL-CLIENT-R020.7 implement and prove: The desktop entry module must meet the shared complexity checks. Touches axil/, tests or t
- [ ] T041 AXIL-CLIENT-R020.8 implement and prove: Desktop tests must cover positive, negative and failure behavior. Touches axil/, tests or 
- [ ] T042 AXIL-CLIENT-R020.9 implement and prove: Documentation examples must match the tested desktop behavior. Touches axil/, tests or the
- [ ] T043 AXIL-CLIENT-R020.10 implement and prove: The README must cover each supported desktop entry point. Touches axil/, tests or the name
- [ ] T044 AXIL-CLIENT-R020.11 implement and prove: The contributor guide must describe the desktop source structure. Touches axil/, tests or 
- [ ] T045 AXIL-CLIENT-R020.12 implement and prove: Documentation file references must resolve to tracked targets. Touches axil/, tests or the
- [ ] T046 AXIL-CLIENT-R020.13 implement and prove: Desktop modules must meet the shared module-size checks. Touches axil/, tests or the named
- [ ] T047 AXIL-CLIENT-R020.14 implement and prove: The desktop must separate presentation from its served client adapter. Touches axil/, test
- [ ] T048 AXIL-CLIENT-R020.15 implement and prove: The desktop must trace each declared concept to its owning implementation. Touches axil/, 
- [ ] T049 AXIL-CLIENT-R020.16 implement and prove: The desktop must resolve each orphaned concept reference. Touches axil/, tests or the name
- [ ] T050 AXIL-CLIENT-R020.17 implement and prove: Desktop tests must bind their owning contract identifiers. Touches axil/, tests or the nam
- [ ] T051 AXIL-CLIENT-R020.18 implement and prove: Significant desktop functions must identify their owning contracts. Touches axil/, tests o
- [ ] T052 AXIL-CLIENT-R020.19 implement and prove: The desktop source must retain a clean configured lint result. Touches axil/, tests or the
- [ ] T053 AXIL-CLIENT-R020.20 implement and prove: The desktop source must pass the configured type checks. Touches axil/, tests or the named
- [ ] T054 AXIL-CLIENT-R020.21 implement and prove: The repository must validate its pinned formatter hook version. Touches axil/, tests or th
- [ ] T055 AXIL-CLIENT-R020.22 implement and prove: The changelog must follow its declared parseable format. Touches axil/, tests or the named
- [ ] T056 AXIL-CLIENT-R020.23 implement and prove: The changelog must describe each shipped desktop change. Touches axil/, tests or the named
- [ ] T057 AXIL-CLIENT-R020.24 implement and prove: The changelog validation environment must supply its required parser. Touches axil/, tests
- [ ] T058 AXIL-CLIENT-R020.25 implement and prove: Desktop tests must parameterize repeated input cases with observable assertions. Touches a
- [ ] T059 AXIL-CLIENT-R020.26 implement and prove: The documentation must cover every supported desktop environment variable. Touches axil/, 
- [ ] T060 AXIL-CLIENT-R020.27 implement and prove: The documentation must explain terminal and bundled-runtime environment inputs. Touches ax
- [ ] T061 AXIL-CLIENT-R020.28 implement and prove: The environment example must document desktop platform inputs without credentials. Touches
- [ ] T062 AXIL-CLIENT-R020.29 implement and prove: The desktop analysis command must use supported served interfaces without importing remove
- [ ] T063 AXIL-CLIENT-R020.30 implement and prove: The desktop must score at least 80 in test coverage. Touches the desktop source and qualit
- [ ] T064 AXIL-CLIENT-R020.31 implement and prove: The desktop must score at least 80 in architecture & design patterns. Touches the desktop 
- [ ] T065 AXIL-CLIENT-R020.32 implement and prove: The desktop must score at least 80 in concept traceability. Touches the desktop source and
- [ ] T066 AXIL-CLIENT-R020.33 implement and prove: The desktop must score at least 80 in test execution. Touches the desktop source and quali
- [ ] T067 AXIL-CLIENT-R020.34 implement and prove: The desktop must score at least 80 in changelog audit. Touches the desktop source and qual
- [ ] T068 AXIL-CLIENT-R020.35 implement and prove: The desktop must score at least 80 in environment variables. Touches the desktop source an
- [ ] T069 AXIL-CLIENT-R020.36 implement and prove: The desktop must score at least 80 in analyze_xdg_kg. Touches the desktop source and quali
- [ ] T070 AXIL-CLIENT-R020.37 implement and prove: The desktop must achieve an overall source-quality grade of at least 3.0. Touches the desk
- [ ] T071 AXIL-CLIENT-R020.38 implement and prove: The desktop must achieve grade B or higher in all 17 source-quality domains. Touches the d
- [ ] T072 AXIL-CLIENT-R020.39 implement and prove: The desktop must resolve all 29 actionable source findings. Touches the desktop source and
- [ ] T073 AXIL-CLIENT-R020.40 implement and prove: Source-quality repairs must preserve the installed command path through axil/axil.py:715. 
- [ ] T074 AXIL-CLIENT-R020.41 implement and prove: A served integration test must launch the installed command and observe client behavior af
- [ ] T075 AXIL-CLIENT-R016.3 implement and prove: Locked headless CI test environment

## Earlier task notes

Notes from the previous task list, kept as context. The lines above are authoritative.

- Review the existing `GatewayClient` facade, `BackendAdapter` seam, `AgentBridgeWorker`
      dispatch, and panel-loading dispatch table against this spec; preserve unrelated
      concurrent edits and reuse every existing path instead of adding a parallel one.
- Run the repository's configured Ruff, mypy and pytest checks; define and run CCCC,
      `jscpd` and Dupehound commands/thresholds or document their explicit acceptance
      exception.
- Reconcile the `pip install axil[all]` instruction in `README.md` with
      `pyproject.toml`'s actual optional-dependency groups (`dev`, `test`, `types`; no `all`
      group is currently defined), and reconcile the supported Python range stated in
      `AGENTS.md` (`>=3.11, <3.14`) with `pyproject.toml`'s `requires-python`
      (`>=3.12, <3.15`).
- Publish the exact merged revision, checks, and packaging/consumer receipts in
      `status.json`; move a requirement to `LANDED` only after merge, and to `ACCEPTED` only
      after the served end-to-end approval and packaging proof.
- Implement R001.2 served dashboard transport and R001.3 cancellable off-thread refresh.
- Preserve R001.1 and migrate six required checks to canonical owners under R016.
- Complete full declared-environment, live-gateway and packaging qualification; local transport and Qt fixtures do not establish release acceptance.
- Repair bounded signal lifetime under R004.2 and console stream lifetime under R010.2.
- Preserve generic R004.1 and R010.1 acceptance gaps independently of these repairs.
- R016.2 migrates the six required checks to immutable canonical owners. R016.1 retains docs-hook acceptance.
- Define R005.1 and R005.2 for the client behavior already implemented in #42 and bind its regressions.
- Retain generic facade, live-gateway, Qt and release qualification gaps; do not infer those passes from the scoped graph tests.
