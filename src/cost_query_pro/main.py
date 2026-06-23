"""src/cost_query_pro/main.py"""

import logging
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import routers
from cost_query_pro.api import admin_users, agent, auth, ingest, items, projects, purge
from cost_query_pro.config.settings import settings
from cost_query_pro.core.errors import AppError
from cost_query_pro.db.session import get_db
from cost_query_pro.web.views.routes import router as web_router

# Import models to register them

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """--- startup ---
    # Log the route map so prefix issues are visible at boot."""
    for r in app.routes:
        methods = sorted(list(getattr(r, "methods", []) or []))
        path = getattr(r, "path", "")
        logger.info(f"Route: {path} ({methods})")

    # Warn if LLM API keys are absent — the server starts regardless;
    # the agent endpoint will return an AppError at request time.
    if settings.llm_provider == "claude" and not settings.anthropic_api_key:
        logger.warning(
            "ANTHROPIC_API_KEY is not set. Claude provider will error at request time."
        )
    if not settings.openai_api_key:
        logger.warning(
            "OPENAI_API_KEY is not set. OpenAI fallback provider is unavailable."
        )

    yield
    """ --- shutdown --- """
    logger.info("Shutting down...")


class CustomJSONResponse(JSONResponse):
    def render(self, content):
        def convert_decimal(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return obj

        return super().render(
            jsonable_encoder(content, custom_encoder={Decimal: convert_decimal})
        )


app = FastAPI(
    title="Cost Query Pro API",
    description="API for querying historical unit costs in infrastructure projects.",
    version="1.0.0",
    debug=settings.fastapi_debug,
    lifespan=lifespan,
    default_response_class=CustomJSONResponse,
)

# Allow Swagger UI and local dev clients to reach the API.
# Tighten allow_origins before any external deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "HTTP_ERROR", "message": str(exc.detail)},
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "errors": exc.errors(),
        },
    )


# Include routers (no duplicate prefixes)
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])
app.include_router(purge.router)
app.include_router(admin_users.router)
app.include_router(web_router)


@app.get("/")
def read_root(db: Session = Depends(get_db)):
    """
    Simple health check route to confirm:
    - FastAPI is running
    - DB connection works
    """
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "message": "Cost Query Pro is alive!",
            "db_check": result,
            "environment": settings.environment,
        }
    except Exception as e:
        logger.exception("DB connectivity check failed.")
        return {"message": "Error connecting to DB", "error": str(e)}
