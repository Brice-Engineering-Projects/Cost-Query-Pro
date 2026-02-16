# Diary Log Structure

```mermaid
docs/
└── diary_logs/
    ├── 00_overview/
    │   ├── dev_environment_setup.md
    │   ├── alembic_migration_recovery.md
    │   └── testing_notes.md
    │
    ├── 01_auth/
    │   ├── auth_refactor_and_fixes.md
    │   ├── auth_flow_stabilization.md
    │   ├── jwt_testing_plan.md
    │   └── me_endpoint_validation.md
    │
    ├── 02_api/
    │   ├── projects_routes_and_items.md
    │   ├── search_endpoint_tests.md
    │   ├── purge_admin_functionality.md
    │   └── file_upload_integration.md
    │
    ├── 03_ci_cd/
    │   ├── github_actions_pipeline.md
    │   ├── test_database_isolation.md
    │   ├── alembic_migration_in_ci.md
    │   └── dependency_locking_strategy.md
    │
    ├── 04_schema/
    │   ├── schema_and_migration.md
    │   ├── orm_serialization_fixes.md
    │   └── computed_fields_refactor.md
    │
    ├── 05_debugging_sessions/
    │   ├── db_connection_hangs.md
    │   ├── alembic_env_py_fixes.md
    │   ├── pytest_attribute_errors.md
    │   └── test_teardown_issues.md
    │
    ├── 06_future_tasks/
    │   ├── dependabot_and_security.md
    │   ├── coverage_and_linting_plan.md
    │   ├── performance_benchmarks.md
    │   └── staging_deployment_notes.md
    │
    └── index.md
```

## Headers Template

```md
---
title: Auth Flow Stabilization
date: 2025-09-01
module: auth
status: completed
---
```
