# Project Structure (src layout)

cost_query_pro/
│
├── src/
│   └── cost_query_pro/                        # Main application package
│        ├── __init__.py
│        ├── main.py                           # FastAPI app entry point, router wiring, error handlers
│        │
│        ├── api/                              # API route definitions
│        │    ├── __init__.py
│        │    ├── admin_users.py               # Admin-only user management endpoints
│        │    ├── agent.py                     # POST /agent/query — natural language cost search
│        │    ├── auth.py                      # Login / token endpoints
│        │    ├── ingest.py                    # CSV/Excel upload endpoint
│        │    ├── items.py
│        │    ├── projects.py
│        │    └── purge.py                     # Archive/purge maintenance endpoints
│        │
│        ├── config/                           # Configuration management
│        │    ├── __init__.py
│        │    ├── pricing.py                   # Per-model LLM token rates for cost estimates
│        │    ├── prompts.py                   # Domain system prompt + PROMPT_VERSION
│        │    └── settings.py                  # Environment and settings config
│        │
│        ├── core/                             # Core logic and system utilities
│        │    ├── __init__.py
│        │    ├── errors.py                    # AppError structured error class
│        │    └── security.py                  # JWT, password hashing, auth helpers
│        │
│        ├── db/                               # Database setup and session control
│        │    ├── __init__.py
│        │    ├── base.py                      # SQLAlchemy DeclarativeBase
│        │    └── session.py                   # Database engine, session factory, get_db
│        │
│        ├── deps/                             # Dependency injection modules
│        │    ├── __init__.py
│        │    └── payloads.py
│        │
│        ├── models/                           # SQLAlchemy ORM models
│        │    ├── __init__.py
│        │    ├── archived_item.py
│        │    ├── archived_project.py
│        │    ├── audit_log.py
│        │    ├── data_quality_issue.py
│        │    ├── item.py
│        │    ├── llm_usage.py                 # Per-completion token usage and cost
│        │    ├── project.py
│        │    ├── system_setting.py
│        │    ├── upload_history.py
│        │    └── user.py
│        │
│        ├── schemas/                          # Pydantic models for validation
│        │    ├── __init__.py
│        │    ├── agent.py                     # SearchParameters, CostSummary, agent request/response
│        │    ├── auth.py
│        │    ├── ingest.py
│        │    ├── item.py
│        │    ├── project.py
│        │    ├── token.py
│        │    └── user.py
│        │
│        ├── services/                         # Business logic / service layer
│        │    ├── __init__.py
│        │    ├── agent_tools.py               # Tool definitions + handlers for the agent
│        │    ├── analytics.py                 # Pipeline step 3 — aggregate cost statistics
│        │    ├── ingestion.py                 # CSV/Excel parsing, validation, persistence
│        │    ├── intent_parser.py             # Pipeline step 1 — question → SearchParameters
│        │    ├── item_search.py               # Pipeline step 2 — SearchParameters → DB query
│        │    ├── llm_provider.py              # Claude primary / OpenAI fallback abstraction
│        │    ├── response_generator.py        # Pipeline steps 4-5 — sanitize + generate answer
│        │    └── usage_recorder.py            # Writes llm_usage rows
│        │
│        ├── templates/                        # Jinja2 templates (Bootstrap-based)
│        │    ├── base.html
│        │    └── dashboard.html
│        │
│        └── web/                              # Web views and Jinja2 routes
│             ├── __init__.py
│             └── views/
│                  ├── __init__.py
│                  └── routes.py               # Web routes for rendering templates
│
├── migrations/                                # Active Alembic migration scripts
│    ├── env.py
│    ├── script.py.mako
│    └── versions/
│
├── migrations_old/                            # Retired migration environment (kept for reference)
│
├── tests/                                     # Unit + integration tests
│    ├── __init__.py
│    ├── conftest.py                           # Shared fixtures (test DB, client, auth)
│    ├── test_smoke.py
│    ├── integration_tests/
│    │    └── __init__.py
│    └── unit_tests/
│         ├── __init__.py
│         ├── conftest.py
│         ├── test_admin_users.py
│         ├── test_agent_endpoint.py
│         ├── test_agent_tools.py
│         ├── test_analytics.py
│         ├── test_auth.py
│         ├── test_auth_jwt.py
│         ├── test_ingest.py
│         ├── test_intent_parser.py
│         ├── test_item_search.py
│         ├── test_items.py
│         ├── test_llm_provider.py
│         ├── test_projects.py
│         ├── test_response_generator.py
│         ├── test_routes.py
│         ├── test_usage_recorder.py
│         └── test_web_views.py
│
├── utils/                                     # Utility helpers
│    ├── __init__.py
│    └── debug_url.py                          # Prints resolved DB URLs for debugging
│
├── docs/                                      # Project documentation (numbered by topic)
│    ├── 00_overview/                          # Business scope, doc plan, roadmap
│    ├── 01_architecture/                      # Structure and architecture overviews
│    ├── 02_auth/                              # Auth design notes
│    ├── 03_api/                               # API docs, secure AI query architecture
│    ├── 04_core/                              # Data transformation steps
│    ├── 05_db_and_migrations/                 # Schema docs, Alembic debugging
│    ├── 06_technical/                         # Operational how-tos (admin seed, ingestion)
│    ├── 07_checklist/                         # Roadmap checklists + archives
│    ├── 08_diary_logs/                        # Dated development diary entries
│    └── 09_audit_reports/                     # Phase audit reports and responses
│
├── .github/
│    └── workflows/                            # GitHub Actions CI pipelines
│         ├── ci.yml
│         └── ci-cd.yml
│
├── .env                                       # Environment variables (do not commit)
├── .gitignore
├── .python-version                            # Pinned Python version for uv
├── .pre-commit-config.yaml                    # Pre-commit hook definitions
├── .yamllint.yml                              # YAML lint rules for workflow files
├── alembic.ini                                # Alembic configuration
├── dependabot.yml                             # Dependency update config
├── setup.cfg                                  # flake8, isort, pytest, coverage config
├── pyproject.toml                             # uv packaging + ruff/mypy config
├── uv.lock                                    # Locked dependencies managed by uv
├── README.md
└── LICENSE
