# Engineering Diary

## Timeline of commits (oldest → newest)
- 2025-08-27 dd3ab32: explain GraphQL queries without fragments; groundwork.
- 2025-08-27 0ec38ee: explain queries with fragments; documentation tweak.
- 2025-08-27 b429662: further fragment query explanations.
- 2025-08-29 0728200: general improvements to codebase.
- 2025-08-30 7953fb0: split servers into modules for cleaner structure.
- 2025-08-31 c4e9103: MCP improvements.
- 2025-08-31 df134b6: additional working state refinements.
- 2025-09-04 860e1e4: tool router implementation.
- 2025-09-04 78ff313: working with router.
- 2025-09-04 b0ea7f9: tool selection with retries.
- 2025-09-04 ac0b044: updated (router/stability tweaks).
- 2025-09-04 6d07652: merge branch step_32_AI into step_31.
- 2025-09-04 0919768: docker added for reproducible environment.
- 2025-11-24 d115a36: first note implementation scaffold.
- 2025-11-24 b752ffe: RBAC/Jacob integration groundwork.
- 2025-12-08 940b7b8: mutation helpers refactored (mutace_func).
- 2026-01-11 c18e2e5: baseline note flow confirmed (“this works”).
- 2026-01-11 e7884d8: owner mutations added (`noteUpdateOwn`, `noteDeleteOwn`) with ownership checks.
- 2026-01-11 1fa77b3: removed legacy `owner_id`; rely on RBAC object linkage.
- 2026-01-12 c80cf85: tests added covering note CRUD, optimistic locking, and ownership enforcement.

## Definition of issues to be resolved
- Decide which roles are permitted to call the generic `note_update` / `note_delete` mutations; `NOTE_ALLOWED_ROLES` is empty, so non-owner updates/deletes are effectively blocked unless policy is set.
- Improve and extend note tests (TODO in `src/GraphTypeDefinitions/NoteGQLModel.py`); add coverage for RBAC role-based paths and error variants beyond ownership cases.
- Confirm dependency setup for running tests locally; `pytest` is missing in the current environment and needs installation in the virtualenv/Poetry environment.
- Clarify expected behaviour for `rbacobject_id` when a client supplies a different value; currently we silently override missing values with the caller’s id.

## What I discovered
- Note insertion now auto-derives `rbacobject_id` from the authenticated user via `NoteInsertPrepareExtension`, ensuring ownership metadata is filled even when the client omits it.
- Owner-specific mutations (`note_update_own`, `note_delete_own`) return explicit errors when the caller is not the creator, matching the new tests in `tests/test_notes.py`.
- Optimistic locking is enforced on update/delete through `lastchange`; stale updates return `UpdateError` and the tests simulate concurrent writes to verify this.
- Tests stub the external UG service by replacing `WhoAmIExtension` with `NoopWhoAmIExtension`, so integration tests run without network calls.

## Which issues cannot be resolved right now
- Role policy for generic update/delete cannot be finalized without product/security input; leaving `NOTE_ALLOWED_ROLES` empty preserves denial-by-default.
- Automated test run is blocked locally because `pytest` is not installed; requires environment setup before verification.

## How the resolved items were addressed (from recent commits)
- Ownership enforcement: commit e7884d8 introduced owner-scoped mutations and explicit “you can update/delete only notes you created” errors.
- RBAC linkage: commit 1fa77b3 removed `owner_id` duplication, relying on `rbacobject_id` and user context instead.
- Safety defaults: `NoteInsertPrepareExtension` now back-fills `rbacobject_id` with the caller’s id when absent, preventing unbound notes.
- Reliability: commit c80cf85 added integration tests that cover happy-path CRUD, ownership errors, and optimistic locking to guard future changes.
