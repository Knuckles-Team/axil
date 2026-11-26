---
name: axil-development
skill_type: skill
description: >-
  How to develop, test, gate, and release the axil repository itself:
  the PySide6 desktop cockpit commands, the package layout, and the gates that
  must pass before a change lands. Use this when you are changing axil's
  own code or preparing a commit/PR in this repository.
license: MIT
tags: [axil, desktop, pyside6, development, test, gates]
tier: repository
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---

# axil-development (repository)

Engineering contract for the axil repository itself (the PySide6 desktop
cockpit), generated from `AGENTS.md`.

## Step 0: route the feature

Route the feature before any code.

1. Read the [ecosystem boundaries standard](https://github.com/Knuckles-Team/pipelines/blob/main/reference/ecosystem-boundaries.md).
2. Split the feature into parts with its routing procedure.
3. If a part is not owned by axil, stop work on that part. Write its row in the owner's `specs/`, then link it by ID.
4. Continue here only with the parts that axil owns.

## Spec-driven flow

Run this before any code. Full table and gates: the Spec-driven development section of `AGENTS.md` and the [spec standard](https://github.com/Knuckles-Team/pipelines/blob/main/reference/spec-standard.md).

1. Read `.specify/memory/constitution.md`; create it from `.specify/templates/constitution-template.md` if absent (`speckit-constitution`).
2. Specify the feature: `speckit-specify` gathers the inputs and writes `specs/<stable-id>/spec.md` and `requirements.md`.
3. Clarify: resolve every `[NEEDS CLARIFICATION: ...]` marker (`speckit-clarify`).
4. Plan: `plan.md` from `.specify/templates/plan-template.md`, including Build contract, Production caller chain and Cross-repo seams (`speckit-plan`).
5. Tasks: `tasks.md` lines `- [ ] T001 [P] [US1] <ROW-ID> ...` (`speckit-tasks`).
6. Analyze: fix the gaps and fill `checklists/requirements.md` (`speckit-analyze`).
7. Implement and land with the delivery contract in this skill (`speckit-implement`); release through pipelines `releases/*.yml` bundles.

Never write code for a row that is not SPECIFIED. Feature directories use the stable spec ID, never a numbered prefix. The state is computed from rows, `Spec:` trailers and test bindings; never write `status.json` or a `Status:` line.

## Delivery contract

Specs are already designed. The work is implementation.

**A row is delivered when**
- its behaviour is fully implemented, as the row says;
- it is wired to its production entry point (a production caller exists outside the new code and its tests);
- every test level its test-spec names passes;
- the tests are bound to the row;
- the gates verify it.

There is no time limit, no size limit per agent or per change, and no rule about how many agents deliver a row.

**Recommendations (optional)**
- Extend first: find the spec row that owns the behaviour (`git grep -n "<term>" -- specs`), cite its ID in the commit `Spec:` trailer, and reuse the existing function or module rather than adding a second implementation.
- Group rows that share an entry point into one bundle and deliver bundles in dependency order, producer first. Split a requirement into `<ID>.<n>` children when it names more than 2 code roots or is cross-repo; the destination repository copies a behaviour first, then the source switches importers and deletes.
- Net-new work can be sliced: `.1` typed model plus validation and refusal tests, `.2` the one entry point that uses it, `.3`+ each further behaviour.
- Every delivered ID gets at least one test bound to it in the same PR. Python: `@pytest.mark.spec("<ID>")`. Rust and TypeScript: a `// spec: <ID>` line directly above the test. Never write generated status files; the state is computed.
- Run the targeted tests for the change; leave the full suite to the main-branch gates.
- Report the PR URL, requirement IDs, test result, and any `ID:<main sha>` proof for rows already on main.

**Before every push**
- Work in a real `git worktree add` from `origin/main`. Never edit a shared checkout, never `git stash`, never `git add -A`, never force-push.
- Run the repo's own pre-commit on the changed files: `uvx --from pre-commit==4.6.0 pre-commit run --files $(git diff --name-only origin/main...HEAD)`. Fix every failure. No `noqa`, `type: ignore`, skip, xfail or whitelist entries to pass a gate.

**Landing**
- Open the pull request and merge it when every required check is green. Mechanical conflicts (generated files, Markdown) resolve by merging `origin/main`; real conflicts are additive in most cases and are resolved, not deferred.
- Full CI on main catches what the pull-request subset missed; regressions are fixed forward.

## Commands

```bash
uv sync --all-extras                       # locked environment
QT_QPA_PLATFORM=offscreen uv run --all-extras pytest tests -q -m "not slow and not integration" --timeout=60
uvx --from pre-commit==4.6.0 pre-commit run --files $(git diff --name-only origin/main...HEAD)
```

The Python package lives in `axil/`; tests live in `tests/`.

## Development rules

- Keep changes small, typed, and tied to one observable outcome.
- Never stage with `git add -A` or `git add .`; stage an explicit path allowlist.
- Never edit the canonical checkout or run `git stash`; use a real `git worktree add`.
- Never bypass a gate with `--no-verify` except as the contract above allows.

## Skill packaging

This directory (`axil/skills/<name>/SKILL.md`) sits inside the `axil`
package that `[tool.hatch.build.targets.wheel]` ships, so a new `SKILL.md`
needs no further packaging change.
