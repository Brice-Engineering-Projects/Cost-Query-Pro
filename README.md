# 📂 Project Folder Structure – Explanations

---

## app/

Main FastAPI application code and core Python logic. All the “brains” of the app live here.

---

## app/models/

SQLAlchemy ORM classes that define:

- Projects table
- Items table
- Users table
- Any future tables

This layer handles how Python objects map to your database tables.

---

## app/db/

Database setup and connection utilities:

- Creating the SQLAlchemy engine
- Managing sessions
- Dependency injection for FastAPI routes

---

## app/api/

All API route definitions:

- `/auth` → login, registration, user management
- `/projects` → endpoints for project data
- `/items` → endpoints for item data
- `/purge` → endpoints for purging old data

Keeps your routing logic organized and modular.

---

## app/schemas/

Pydantic models for:

- Validating incoming requests
- Structuring API responses

Ensures type safety and consistent API payloads.

---

## app/core/

Core business logic and shared utilities:

- Data purge logic
- Data upload/cleaning routines
- Security helpers (password hashing, token management)

Central place for functions used across multiple parts of the app.

---

## app/templates/

HTML templates (if you’re serving web pages with Jinja2).  
Not needed if you’re only building an API or a separate frontend.

---

## app/static/

Static files:

- CSS
- JavaScript
- Images
- Fonts

Again, only necessary if you’re serving a frontend directly from FastAPI.

---

## app/services/

Business logic and data processing that doesn’t fit directly into API routes:

- Data analysis
- Export routines
- Advanced processing steps

Helps keep API route files clean and focused.

---

## migrations/

Database migration scripts (e.g. Alembic) to keep your database schema synchronized with your SQLAlchemy models as your app evolves.

---

## tests/

Unit tests and integration tests:

- Test API routes
- Validate data ingestion scripts
- Catch regressions as you develop

Helps ensure your code stays reliable and bug-free.

---

## .env

Environment variables:

- Database credentials
- Secret keys
- Configuration values

**Important:** should never be committed to version control with sensitive data.

---

## .gitignore

Files and folders that should NOT be tracked by Git:

- Python bytecode
- IDE configs (e.g. JetBrains)
- Virtual environments
- OS-specific junk

Keeps your repo clean.

---

## requirements.txt or pyproject.toml

Lists all your Python dependencies so others (or future you) can easily install them.

---

## README.md

Project overview:

- What the app does
- How to install and run it
- Usage instructions

Your project’s first impression for collaborators.

---

## LICENSE

Specifies how others can use or contribute to your code.

---
