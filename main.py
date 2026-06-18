"""Book Library API — a complete example using all chassis packages.

Quick start::

    docker compose up -d          # Start PostgreSQL + Redis
    uv run python main.py         # Start the API server

Then explore:

- **Books API**         http://localhost:8000/books
- **Auth (OAuth demo)** http://localhost:8000/auth/demo/login?redirect_uri=http://localhost:8000/
- **Auth (Phone mock)** POST http://localhost:8000/auth/phone/send  (code: 1234)
- **Auth (Email mock)** POST http://localhost:8000/auth/email/send (code: 1234)
- **Admin Panel**       http://localhost:8000/admin/  (admin / admin123)
- **API Docs**          http://localhost:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from chassis_admin.app import create_admin_app
from chassis_admin.auth import AdminAuthConfig
from chassis_auth.manager import AuthManager
from chassis_auth.routes import setup_auth
from chassis_auth.verification import MockEmailCodeProvider, MockPhoneCodeProvider
from chassis_cache.manager import CacheManager
from chassis_cache.setup import setup_cache
from chassis_core.app import CorsConfig, RateLimitConfig, setup_security
from chassis_core.exceptions import register_exception_handlers
from chassis_repo.session import setup_repo
from chassis_storage.protocols import StorageBackend
from chassis_storage.setup import setup_storage
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from example.config import ExampleConfig
from example.models import Base, Book
from example.providers import DemoOAuthProvider
from example.routes import book_router

import uvicorn


async def _create_tables() -> None:
    """Create all database tables using the async session factory."""
    from chassis_repo.session import _session_factory

    assert _session_factory is not None
    async with _session_factory() as session:
        conn = await session.connection()
        await conn.run_sync(Base.metadata.create_all)


async def on_auth_success(user_info, tokens) -> JSONResponse:
    """Callback for successful authentication via any method."""
    return JSONResponse(
        content={
            "message": f"Welcome, {user_info.name}!",
            "user": user_info.model_dump(),
            "tokens": tokens.model_dump(),
        }
    )


def create_app() -> FastAPI:
    """Build the example FastAPI application.

    Demonstrates the "Library Mode" pattern: the business project
    creates the app and calls chassis setup_*() functions.
    """
    config: ExampleConfig = ExampleConfig()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await _create_tables()
        yield

    # FastAPI app (business owns the process)
    app: FastAPI = FastAPI(
        title=config.app_name,
        version=config.app_version,
        lifespan=lifespan,
    )

    # --- chassis-core: security middleware ---
    setup_security(
        app,
        cors=CorsConfig(allow_origins=["*"]),
        rate_limit=RateLimitConfig(max_requests=100, window_seconds=60),
    )
    register_exception_handlers(app)
    # -----------------------------------------

    # --- chassis-repo: database (PostgreSQL via Docker) ---
    setup_repo(config=config)
    # ------------------------------------------------------

    # --- chassis-cache: Redis (via Docker) ---
    cache_manager: CacheManager = setup_cache(config)
    app.state.cache_manager = cache_manager
    # -----------------------------------------

    # --- chassis-storage: file storage (Local for example) ---
    storage_backend: StorageBackend = setup_storage(config)
    app.state.storage_backend = storage_backend
    # --------------------------------------------------------

    # --- chassis-auth: OAuth + phone + email ---
    manager: AuthManager = AuthManager(secret="example-secret-key-change-in-production")
    manager.register("demo", DemoOAuthProvider())

    setup_auth(
        app,
        manager=manager,
        on_auth_success=on_auth_success,
        phone_provider=MockPhoneCodeProvider(),
        email_provider=MockEmailCodeProvider(),
    )
    # -------------------------------------------

    # --- Business routes ---
    app.include_router(book_router)
    # -----------------------

    # --- chassis-admin: admin panel ---
    admin_app: FastAPI = create_admin_app(
        models={"books": Book},
        auth=AdminAuthConfig(username="admin", password="admin123"),
    )
    app.mount("/admin", admin_app)
    # ----------------------------------

    return app


def main() -> None:
    """Entry point. Starts uvicorn on localhost:8000."""
    app: FastAPI = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
