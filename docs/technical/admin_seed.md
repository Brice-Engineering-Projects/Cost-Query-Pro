# Recommended Admin Bootstrap Method (Future-proof for AWS + Snowflake)

> TL;DR — Use a **one-time management CLI** (Typer) that creates the first admin **only if** a secret `ADMIN_BOOTSTRAP_TOKEN` is present and no admin exists. It hashes the password using your app’s hasher, is idempotent, and works the same on local, Docker, or AWS.  
> Note: Snowflake will remain OLAP; **auth should stay in Postgres/RDS**. This CLI talks to your SQLAlchemy OLTP DB, so nothing changes when you add Snowflake later.

---

## Why this over other options
- **Safe by default:** The HTTP surface stays minimal (no public “make admin” endpoint).  
- **Idempotent:** Refuses to run if an admin already exists.  
- **Proper hashing:** Reuses your `get_password_hash`, avoiding plaintext.  
- **Deployable anywhere:** Run as a one-off job in CI/CD or AWS (ECS task / EB SSH / App Runner exec).

---

## Files to add

### `src/app/cli.py`

```python
from __future__ import annotations

import os
from getpass import getpass
import typer

from sqlalchemy.orm import Session
from src.cost_query_pro.db.session import SessionLocal  # your existing sessionmaker
from src.cost_query_pro.models.user import User as DBUser
from src.cost_query_pro.core.security import get_password_hash  # same hasher used by auth

cli = typer.Typer(add_completion=False, help="Cost Query Pro management commands")


def _admin_exists(db: Session) -> bool:
    return db.query(DBUser).filter(DBUser.is_admin.is_(True)).first() is not None


@cli.command("bootstrap-admin")
def bootstrap_admin(
        token: str = typer.Option(
            ..., "--token",
            envvar="ADMIN_BOOTSTRAP_TOKEN",
            help="One-time bootstrap token (required)."
        ),
        username: str = typer.Option(
            "admin", "--username", envvar="ADMIN_BOOTSTRAP_USERNAME",
            help="Admin username to create if none exists."
        ),
        password: str | None = typer.Option(
            None, "--password", envvar="ADMIN_BOOTSTRAP_PASSWORD",
            help="Admin password. Omit to be prompted securely."
        ),
):
    """Create the first admin user if none exists (idempotent)."""
    expected = os.getenv("ADMIN_BOOTSTRAP_TOKEN")
    if not expected:
        typer.secho("ADMIN_BOOTSTRAP_TOKEN not set; refusing to bootstrap.", fg="red", err=True)
        raise typer.Exit(code=2)
    if token != expected:
        typer.secho("Invalid bootstrap token.", fg="red", err=True)
        raise typer.Exit(code=1)

    if password is None:
        # Avoid shell history; prompt with hidden input
        pw1 = getpass("Admin password: ")
        pw2 = getpass("Confirm password: ")
        if pw1 != pw2:
            typer.secho("Passwords do not match.", fg="red", err=True)
            raise typer.Exit(code=1)
        password = pw1

    db: Session = SessionLocal()
    try:
        if _admin_exists(db):
            typer.secho("Admin already exists; nothing to do.", fg="yellow")
            raise typer.Exit(code=0)

        hashed = get_password_hash(password)
        user = DBUser(username=username, password_hash=hashed, is_admin=True)
        db.add(user)
        db.commit()
        typer.secho(f"Admin '{username}' created.", fg="green")
    finally:
        db.close()


if __name__ == "__main__":
    cli()
```

## Run the script locally

### 1) Set a one-time secret (don’t commit this)

```bash
export ADMIN_BOOTSTRAP_TOKEN=$(python - <<'PY'
import secrets; print(secrets.token_urlsafe(24))
PY)
```

### 2) Execute the command; you’ll be prompted for the password

```bash
uv run python -m src.cost_query_pro.cli bootstrap-admin --token "$ADMIN_BOOTSTRAP_TOKEN" --username admin
```

### Expected Results

- If no admin exists → creates one with a hashed password.
- If an admin exists → prints “nothing to do” and exits 0.

### Run the scrip with CI/CD or AWS

- GitHub Actions: add a one-off job guarded by if: github.ref == 'refs/heads/main' && github.run_number == 1 (or a manual workflow dispatch). Inject ADMIN_BOOTSTRAP_TOKEN and run:

```bash
python -m src.cost_query_pro.cli bootstrap-admin --token "$ADMIN_BOOTSTRAP_TOKEN" --username admin
```

- Elastic Beanstalk / ECS / App Runner: run as a one-time exec/command on the web container with the same environment variable set.
- Disable afterward by removing the secret or setting it blank.

## Verification

### 1. Login as 'admin' and call:
```vbnet
GET /api/v1/auth/me
Authorization: Bearer <token>
```

#### Expect:

```json
{ "username": "admin", "is_admin": true, ... }
```

### 2. Hit an admin-only route (e.g., `/api/v1/admin/purge`) and confirm 200 (admin) vs 403 (non-admin). 

#### Cleanup / Guardrails

- Keep registration hard-coded to is_admin=False.
- Do not include a public HTTP “bootstrap” endpoint in prod.
- If you add is_admin into JWT claims for frontend UX, still re-check DB in get_current_admin for every request.

#### Next Steps

- Add src/app/cli.py as above.
- Store ADMIN_BOOTSTRAP_TOKEN as an environment secret in dev/stage/prod (temporarily).
- Run the CLI once per environment, then remove the secret.
- Write a small doc in docs/ops/bootstrap_admin.md describing the runbook and rollback (demote or delete the admin).