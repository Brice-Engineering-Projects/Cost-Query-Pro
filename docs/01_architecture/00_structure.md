# Project Structure (src layout)

cost_query_pro/
│
├── src/
│   └── cost_query_pro/                        # Main application package
│        ├── __init__.py
│        ├── main.py                           # FastAPI app entry point
│        │
│        ├── api/                              # API route definitions
│        │    ├── __init__.py
│        │    ├── auth.py
│        │    ├── projects.py
│        │    ├── items.py
│        │    └── purge.py
│        │
│        ├── config/                           # Configuration management
│        │    ├── __init__.py
│        │    └── settings.py                  # Environment and settings config
│        │
│        ├── core/                             # Core logic and system utilities
│        │    ├── __init__.py
│        │    ├── security.py                  # JWT, password hashing, auth helpers
│        │    └── data_upload.py               # Data upload + validation logic
│        │
│        ├── db/                               # Database setup and session control
│        │    ├── __init__.py
│        │    ├── base.py                      # SQLAlchemy Base and metadata
│        │    └── session.py                   # Database engine and session factory
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
│        │    ├── project.py
│        │    ├── system_setting.py
│        │    ├── upload_history.py
│        │    └── user.py
│        │
│        ├── schemas/                          # Pydantic models for validation
│        │    ├── __init__.py
│        │    ├── auth.py
│        │    ├── item.py
│        │    ├── project.py
│        │    ├── token.py
│        │    └── user.py
│        │
│        ├── services/                         # Business logic / service layer
│        │    ├── __init__.py
│        │    ├── auth_service.py
│        │    ├── item_service.py
│        │    └── project_service.py
│        │
│        ├── templates/                        # Global Jinja2 templates (Bootstrap-based)
│        │    ├── base.html
│        │    ├── dashboard.html
│        │    └── login.html
│        │
│        ├── static/                           # Static assets (CSS, JS, images)
│        │    └── ...
│        │
│        └── web/                              # Web views and Jinja2 routes
│             ├── __init__.py
│             ├── views/
│             │    ├── __init__.py
│             │    └── routes.py               # Web routes for rendering templates
│             ├── templates/                   # Optional web-specific templates
│             └── static/                      # Optional web-specific static files
│
├── migrations/                                # Alembic migration scripts
│
├── tests/                                     # Unit + integration tests
│    ├── unit_tests
│    │    ├── test_auth.py
│    │    └── test_routes.py
│    ├── __init__.py
│    ├── conftest.py
│    └── test_smoke.py
│
├── utils/                                     # Utility helpers
│    ├── __init__.py
│    └── debug_url.py
│
├── .env                                       # Environment variables (do not commit)
├── .gitignore
├── requirements.txt                           # Fallback for legacy installs
├── pyproject.toml                             # uv + modern Python packaging config
├── README.md
└── LICENSE
