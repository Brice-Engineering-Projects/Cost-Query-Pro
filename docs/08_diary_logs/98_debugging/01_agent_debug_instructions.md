````md
# Cost Query Pro: Mypy Strict-Mode Remediation Instructions

## Objective

Resolve the existing `mypy --strict` errors in the Cost Query Pro source code without weakening type checking, introducing unnecessary suppressions, or changing application behavior.

The application currently passes its runtime test suite:

- Ruff: passing
- Black: passing
- Pytest: 165 tests passing
- Mypy: 70 errors across 23 files
- Source files checked by mypy: 53

The mypy errors became visible after correcting package discovery for the project's `src/` layout. They should therefore be treated primarily as existing typing debt unless investigation demonstrates that a specific error represents an actual runtime or compatibility defect.

A recent Starlette major-version upgrade was also performed to address a security advisory, so Starlette/FastAPI compatibility issues must receive priority.

---

# 1. Preserve the Existing Architecture

The project uses a `src/` layout:

```text
cost_query_pro/
├── src/
│   └── cost_query_pro/
│       ├── __init__.py
│       ├── api/
│       ├── config/
│       ├── core/
│       ├── db/
│       ├── deps/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       └── web/
├── tests/
├── pyproject.toml
└── setup.cfg
````

Do not restructure the package merely to satisfy mypy.

Imports should use:

```python
from cost_query_pro...
```

Do not introduce imports using:

```python
from src.cost_query_pro...
```

The `src` directory is a package root and is not part of the Python package name.

---

# 2. Mypy Configuration

The duplicate-module discovery issue has been resolved using:

```ini
[mypy]
ignore_missing_imports = true
no_strict_optional = false
check_untyped_defs = true
explicit_package_bases = true
```

The canonical strict type-check command should be:

```bash
uv run mypy --strict src/cost_query_pro
```

Do not revert `explicit_package_bases`.

Do not attempt to solve typing errors by weakening strict mode globally.

---

# 3. Remediation Strategy

Do not attempt to fix all 70 errors as one undifferentiated change.

Work through the errors by category and architecture layer.

Use the following priority order.

---

## Priority 1: Starlette/FastAPI Compatibility

Investigate:

```text
src/cost_query_pro/web/views/routes.py
```

Current errors include:

```text
Argument 1 to "TemplateResponse" of "Jinja2Templates"
has incompatible type "str"; expected "Request[State]"

Argument 2 to "TemplateResponse" of "Jinja2Templates"
has incompatible type "dict[str, Any]"; expected "str"
```

The project recently upgraded Starlette from the `0.49.x` line to `1.x`.

Determine whether the `Jinja2Templates.TemplateResponse` calling convention changed.

Do not silence these errors.

Update the application to use the currently supported Starlette API while preserving existing route behavior.

After making the change, run the relevant route tests before proceeding.

---

# 4. SQLAlchemy Base Typing

Multiple ORM models currently report:

```text
Class cannot subclass "Base" (has type "Any")
```

Affected models include:

```text
models/system_setting.py
models/project.py
models/user.py
models/upload_history.py
models/llm_usage.py
models/item.py
models/data_quality_issue.py
models/audit_log.py
models/archived_project.py
models/archived_item.py
```

Investigate the project's SQLAlchemy declarative base definition.

The project uses SQLAlchemy 2.x.

Prefer modern SQLAlchemy typing patterns such as a properly typed `DeclarativeBase` implementation where appropriate.

Example architectural direction:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Do not blindly apply this example without first examining the existing database configuration, model imports, Alembic configuration, and metadata usage.

The goal is to fix the base typing at its source rather than adding suppressions to every ORM model.

After modifying the declarative base:

```bash
uv run pytest
uv run mypy --strict src/cost_query_pro
```

Confirm that database metadata and migrations remain functional.

---

# 5. Missing Function Annotations

A significant number of errors are:

```text
Function is missing a return type annotation
Function is missing a type annotation for one or more parameters
```

These occur primarily in:

```text
api/
main.py
models/
db/
web/
```

Add meaningful parameter and return annotations.

Do not use `Any` merely to make mypy pass when a concrete type can reasonably be determined.

For FastAPI routes, determine the actual response contract and annotate accordingly.

For functions that intentionally return nothing:

```python
def function_name(...) -> None:
```

For SQLAlchemy sessions, requests, responses, dependency injection parameters, and model instances, use their appropriate concrete types.

---

# 6. Generic Collections

Errors currently include:

```text
Missing type arguments for generic type "dict"
```

Affected areas include:

```text
services/agent_tools.py
services/llm_provider.py
core/security.py
```

Replace bare collections such as:

```python
dict
list
tuple
```

with parameterized types.

For example:

```python
dict[str, Any]
```

is acceptable when the structure is genuinely dynamic.

However, when the dictionary has a known contract, prefer stronger typing such as:

```python
TypedDict
Pydantic models
dataclasses
specific value unions
```

Do not automatically replace every `dict` with `dict[str, Any]` without examining the data contract.

---

# 7. Pydantic Schema Properties

Investigate:

```text
src/cost_query_pro/schemas/item.py
```

Current errors occur around lines 75, 81, 87, and 93:

```text
Decorators on top of @property are not supported
```

Inspect the decorator ordering and determine whether these are Pydantic computed fields or ordinary Python properties.

If Pydantic `computed_field` is being used, implement it according to the supported Pydantic 2.x typing pattern.

Do not suppress these errors unless there is a documented incompatibility that cannot reasonably be resolved.

---

# 8. Import/Export Typing

Current errors include:

```text
Module "cost_query_pro.api.auth" does not explicitly export
attribute "get_current_user"
```

Affected modules include:

```text
api/projects.py
api/items.py
```

Investigate how `get_current_user` is imported or re-exported by:

```text
cost_query_pro.api.auth
```

Correct the module ownership/import path if the function belongs elsewhere.

Prefer importing the function from the module where it is actually defined rather than creating artificial re-exports solely to satisfy mypy.

---

# 9. Unknown Callable / Any Propagation

Investigate errors such as:

```text
Cannot call function of unknown type
Returning Any from function declared to return ...
```

Currently seen in:

```text
services/agent_tools.py
```

Trace the source of the unknown callable or `Any`.

Fix typing at the boundary where type information is lost rather than casting downstream repeatedly.

Use `Protocol`, `Callable`, typed mappings, or other appropriate typing constructs when needed.

---

# 10. Remove Obsolete Type Ignores

Current errors include:

```text
Unused "type: ignore" comment
```

in:

```text
services/ingestion.py
```

Remove obsolete ignores when the underlying expression now type-checks correctly.

Do not replace them with broader ignore directives.

---

# 11. Suppression Policy

Avoid:

```python
# type: ignore
```

unless all of the following are true:

1. The underlying library typing is demonstrably incorrect or incomplete.
2. There is no reasonable typed implementation available.
3. The suppression is narrowly scoped.
4. The specific mypy error code is included.

If suppression is unavoidable, prefer:

```python
# type: ignore[specific-error-code]
```

rather than:

```python
# type: ignore
```

Document why the suppression is necessary.

Do not configure mypy to globally ignore entire categories simply to obtain a passing build.

---

# 12. Do Not Change Python Versions

The project currently runs Python 3.12.

Do not migrate the project to Python 3.13 or later as part of this remediation.

The discovered mypy errors are not evidence that the Python runtime needs upgrading.

Python-version changes should be handled as a separate planned migration.

---

# 13. Incremental Validation

After each logical category of changes, run:

```bash
uv run ruff check .
uv run black --check .
uv run mypy --strict src/cost_query_pro
uv run pytest
```

For dependency/security verification also run:

```bash
uv run pip-audit
```

Do not wait until all typing changes are complete before running tests.

---

# 14. Commit Strategy

Keep changes logically separated.

Recommended sequence:

```text
1. fix: update Starlette template response compatibility
2. refactor: modernize SQLAlchemy declarative base typing
3. refactor: add FastAPI endpoint type annotations
4. refactor: strengthen service and core typing
5. fix: correct Pydantic computed field typing
6. refactor: correct authentication dependency imports
7. chore: remove obsolete mypy suppressions
```

Combine commits where appropriate if changes are tightly coupled, but avoid one massive "fix mypy" commit containing unrelated architectural changes.

---

# 15. Definition of Done

The remediation is complete when:

```bash
uv run ruff check .
uv run black --check .
uv run mypy --strict src/cost_query_pro
uv run pytest
uv run pip-audit
```

all pass.

Additionally:

* No global mypy strictness has been weakened.
* No unnecessary `Any` types have been introduced.
* No broad `# type: ignore` comments have been added.
* Existing FastAPI behavior remains unchanged.
* Existing SQLAlchemy/Alembic behavior remains unchanged.
* Existing API contracts remain unchanged unless a Starlette compatibility change requires an internal implementation update.
* All existing tests continue to pass.
* New tests are added where remediation changes behavior or fixes an uncovered compatibility issue.

---

# Current Baseline

Before remediation:

```text
Ruff:
PASS

Black:
PASS
84 files unchanged
Python target-version configuration should be reviewed separately.

Pytest:
PASS
165 tests

Mypy:
70 errors
23 files affected
53 source files checked

Python:
3.12.3

FastAPI:
0.140.0

Starlette:
Upgraded from 0.49.x to the patched 1.x release line

Pillow:
12.3.0
```

Treat the 165 passing tests as the behavioral baseline.

The objective is not merely to make mypy display zero errors. The objective is to improve the actual type safety and maintainability of the codebase while preserving that behavioral baseline.

```
```
