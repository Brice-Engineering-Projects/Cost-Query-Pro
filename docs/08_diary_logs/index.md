# Developer Diary Index

Entries are listed oldest first. Dates and titles are taken from each file's
YAML frontmatter, so this table and the documents cannot drift apart silently.

| Date       | Focus Area              | File                                                                                                                       | Status    | Summary                                                                                      |
| ---------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| 2025-07-11 | 01 Phase 1 · Debugging  | [00_debugging_auth_routes_migrations.md](./01_phase_1/04_debugging_sessions/00_debugging_auth_routes_migrations.md)        | Completed | Debugging auth, routes, and migrations; pytest attribute errors and settings refactor.       |
| 2025-07-20 | 01 Phase 1 · Schema     | [00_schema_and_migration.md](./01_phase_1/03_schema/00_schema_and_migration.md)                                            | Completed | Repaired Alembic `env.py`, rebuilt the database schema, confirmed environment switching.     |
| 2025-08-02 | 01 Phase 1 · Auth       | [00_auth_refactor.md](./01_phase_1/01_auth/00_auth_refactor.md)                                                            | Completed | Auth refactor and SQLAlchemy serialization fix.                                              |
| 2025-08-02 | 99 Future Tasks         | [00_tasks_checklist.md](./99_future_tasks/00_tasks_checklist.md)                                                           | On-going  | Consolidated backlog and to-do items.                                                        |
| 2025-09-01 | 01 Phase 1 · Auth       | [01_auth_flow_stabilization.md](./01_phase_1/01_auth/01_auth_flow_stabilization.md)                                        | On-going  | Login, register, and `/me` route fixes; Pydantic v2 migration; JWT testing plan.             |
| 2025-09-08 | 00 General · CI/CD      | [00_github_actions_pipeline.md](./00_general/02_ci_cd/00_github_actions_pipeline.md)                                       | Completed | CI/CD pipeline with PostgreSQL service, test isolation, and dependency locking.              |
| 2026-06-20 | 01 Phase 1              | [20260620_project_diary.md](./01_phase_1/20260620_project_diary.md)                                                        | Completed | Core API cleanup, Pyright zero-error pass, and the CSV/Excel ingestion pipeline.             |
| 2026-07-26 | 02 Phase 2 · AI Agent   | [00_llm_cost_accounting.md](./02_phase_2/05_ai_agent/00_llm_cost_accounting.md)                                            | Completed | Token usage foundation: provider metering, `llm_usage` table, fallback cost-attribution fix. |

## Archive

| File                             | Notes                                                                                                    |
| -------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [diary_log.md](./diary_log.md)   | The original single combined log (956 lines) that the split entries above were extracted from. Superseded, retained for history. |

## Index maintenance note

This index was rebuilt on 2026-07-26. It had been written against an earlier
flat layout (`./00_overview/`, `./01_auth/`, `./04_schema_refactor/`,
`./05_debugging_sessions/`) that no longer exists — entries were since
reorganized into phase folders, so every link in the old table was broken.

Five rows referenced files that no longer exist in any form, their content
having been consolidated into the entries above during that reorganization.
They are recorded here rather than silently dropped:

| Removed row                  | Where the content most likely went                                     |
| ---------------------------- | ------------------------------------------------------------------------ |
| `dev_environment_setup.md`   | Environment/test setup material — folded into the schema and debugging entries. |
| `testing_notes.md`           | Pytest and Alembic fixes — overlaps the 2025-07-11 debugging entry.      |
| `jwt_testing_plan.md`        | JWT testing next-steps — overlaps `01_auth_flow_stabilization.md`.       |
| `pydantic_v2_migration.md`   | Pydantic v2 / `@computed_field` work — overlaps the auth flow entry.     |
| `db_connection_hangs.md`     | DB lockup diagnosis — overlaps the 2025-07-11 debugging entry.           |

The mappings above are inferred from dates and subject matter, not from a
migration record. Treat them as leads, not provenance.
