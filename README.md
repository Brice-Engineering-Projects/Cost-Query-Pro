# 💼 Cost Query Pro

**A backend platform for infrastructure cost intelligence and bid-item analysis.**
Built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**, Cost Query Pro is designed to query, clean, and analyze construction cost data at scale — empowering engineers, estimators, and project managers with smarter insights.

---

## 🛠️ Build Status & Metadata

| Branch | Build Status | Python | Framework | License | Project Status |
|---------|---------------|--------|------------|----------|----------------|
| **main** | [![Main Build](https://github.com/Brice-Engineering-Projects/Cost-Query-Pro/actions/workflows/ci-cd.yml/badge.svg?branch=main)](https://github.com/Brice-Engineering-Projects/Cost-Query-Pro/actions/workflows/ci-cd.yml) | ![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white) | ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?logo=fastapi&logoColor=white) | ![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) | ![Status](https://img.shields.io/badge/Status-In%20Development-orange) |
| **dev**  | [![Dev Build](https://github.com/Brice-Engineering-Projects/Cost-Query-Pro/actions/workflows/ci-cd.yml/badge.svg?branch=dev)](https://github.com/Brice-Engineering-Projects/Cost-Query-Pro/actions/workflows/ci-cd.yml) | ![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white) | ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?logo=fastapi&logoColor=white) | ![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) | ![Status](https://img.shields.io/badge/Status-In%20Development-orange) |

**Version:** v0.1.0
**Status:** Early Release (MVP)

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-------------|
| **Framework** | FastAPI |
| **Database** | PostgreSQL + SQLAlchemy ORM |
| **Auth** | JWT-based authentication |
| **Migrations** | Alembic |
| **Testing** | Pytest |
| **Package Manager / Env** | [uv](https://docs.astral.sh/uv/) |
| **Deployment** | Docker / AWS RDS (planned) |
| **Language** | Python 3.12 |

---

## 🧠 Core Features

- 🔐 Secure authentication with JWT
- 🧮 Project, item, and cost model endpoints
- 🧹 Automated purge routines for old or duplicate data
- 🧱 Database migrations and ORM models
- 🧰 Modular architecture with dedicated folders for logic, schemas, and services
- 🧾 Built-in API documentation via Swagger UI (`/docs`)

---

## 🚀 Getting Started (with `uv`)

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Brice-Backend-Projects/Cost-Query-Pro.git
cd Cost-Query-Pro
```

---

### 2️⃣ Create and Sync the Environment

```bash
uv venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
```

---

### 3️⃣ Install Dependencies

```bash
uv sync
```

---

### 4️⃣ Run the App

ensure the following environment variables are set:

```bash
export PYTHONPATH=$PWD/src
```

then run the app:

```bash
uvicorn cost_query_pro.main:app --reload
```

### 5️⃣ Access the API Docs

Visit `http://localhost:8000/docs`

---

### 📂 Project Structure

```graphql
cost_query_pro/
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
```

---

## 🧠 Lessons Learned

- How to architect a **production-ready FastAPI backend** with modular separation (api, core, db, schemas, services)
- Managing **SQLAlchemy sessions and transactions** safely across async endpoints
- The importance of **type-safe validation** with Pydantic models for clean data ingestion
- Implementing **JWT authentication** and secure password hashing workflows
- Building and maintaining **database migrations** with Alembic
- Designing for **maintainability** — breaking logic into reusable service layers
- Leveraging **uv** for faster dependency installs, reproducible environments, and isolated builds
- Writing **meaningful tests** to prevent regressions during refactors
- Building with **deployment in mind** (directory structure, .env separation, and Docker-readiness)
- Documenting the architecture so others (or future me) can onboard easily

---

## 🌱 Future Enhancements

- 🔑 **Role-based access control (RBAC):** differentiate between admin, project manager, and analyst users
- 🧾 **Bid-item cost analytics:** integrate real municipal datasets to benchmark infrastructure costs
- 💾 **Caching layer:** add Redis or SQLite caching for faster repeat queries
- 📊 **Reporting tools:** export project summaries to PDF and Excel
- ⚙️ **Background tasks:** schedule cost refreshes or purge routines asynchronously
- ☁️ **Cloud deployment:** Dockerize and deploy to AWS App Runner with RDS Postgres backend
- 🤖 **Machine learning integration:** train models to detect anomalies or pricing trends across regions
- 🧰 **API Gateway Integration:** expose authenticated endpoints for external engineering dashboards

---

## Version History

### v0.1.0 — MVP Release

- FastAPI application structure implemented
- Core endpoints for project and cost queries
- SQLAlchemy ORM models created
- Alembic migrations enabled
- JWT authentication (access + refresh)
- Modular routing with dependency injection
- Basic schema validation
- CI/CD pipeline fully configured (GitHub Actions)
- Local development environment configured
- Early testing with internal datasets

---

### v0.2.0 — Production Deployment (Planned)

- Production configuration profiles
- PostgreSQL / AWS RDS integration
- Gunicorn/Uvicorn production server setup
- Security headers, CORS configuration, rate limiting
- Logging & error-handling improvements
- Environment-based settings cleanup

---

### v0.3.0 — API Hardening & Data Expansion (Planned)

- Expanded project type taxonomy
- Advanced querying features
- Pagination & filtering
- Enhanced input validation
- Robust exception handling
- Performance profiling & endpoint optimization
- Caching layer (Redis) for high-traffic endpoints

---

### v0.4.0 — Admin & Role-Based Access (Planned)

- Admin dashboard endpoints
- Role-based permissions (admin, analyst, standard)
- API key generation for internal services
- Audit logging for sensitive operations

---

### v0.5.0 — Integrations & Interoperability (Planned)

- Export cost data (CSV/JSON)
- Webhook support for events
- REST-to-REST integration examples
- Optional ETL pipelines for external civil engineering datasets

---

### v1.0.0 — Full Architectural Refactor (Planned)

- Final migration to fully modular **src/** layout
- Clear separation of:
  - `routers/`
  - `services/`
  - `repositories/`
  - `schemas/`
  - `core/`
- Full end-to-end test suite (pytest)
- Type-hint and docstring coverage improvements
- Performance tuning
- Documentation overhaul (OpenAPI + Markdown)

---

## 🪪 License & Author

This project is open source under the **MIT License** — free to use, modify, and distribute.

**Author:** Brice A. Nelson<br>
🌐 [devbybrice.com](https://www.devbybrice.com)<br>
💼 [LinkedIn](https://www.linkedin.com/in/brice-a-nelson-p-e-mba-36b28b15/)

---

> _“Precision in cost, clarity in data — because every number tells a story.”_ 🧾
