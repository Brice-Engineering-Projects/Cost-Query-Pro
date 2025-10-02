# Structure

project_cost_query/
│
├── app/                      # Main application code
│   ├── __init__.py
│   ├── main.py               # FastAPI app entry point
│   ├── models/               # SQLAlchemy models
│   │    └── __init__.py
│   ├── db/                   # Database config and session utilities
│   │    └── __init__.py
│   ├── api/                  # API route definitions
│   │    ├── __init__.py
│   │    ├── auth.py
│   │    ├── projects.py
│   │    ├── items.py
│   │    └── purge.py
│   ├── config/                 # Configuration files
│   │    ├── __init__.py        # initialization file
│   │    └── settings.py        # settings file
│   ├── core/                 # Core logic/utilities (e.g. purge scripts)
│   │    ├── __init__.py
│   │    ├── security.py
│   │    └── data_upload.py
│   ├── schemas/              # Pydantic schemas for API validation
│   │    └── __init__.py
│   ├── templates/            # HTML templates (if using Jinja2)
│   │    └── ...
│   ├── static/               # CSS, JS, images (if applicable)
│   │    └── ...
│   └── services/             # Business logic services
│        └── __init__.py
│
├── migrations/               # DB migrations (e.g. Alembic)
│
├── tests/                    # Unit and integration tests
│   ├── __init__.py
│   ├── test_projects.py
│   ├── test_items.py
│   └── test_auth.py
│
├── .env                      # Environment variables (never commit secrets!)
├── .gitignore
├── requirements.txt          # Python package dependencies
├── README.md
├── LICENSE
└── pyproject.toml            # Optional: modern Python packaging config
