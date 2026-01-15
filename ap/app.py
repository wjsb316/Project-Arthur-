from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from .config import Settings, load_settings
from .database import get_session_maker, init_db
from .ingress.gateway import build_gateway_router
from .ingress.streaming import build_streaming_router
from .ingress.professional import build_professional_router
from .ingress.auth import build_auth_router
from .ingress.chat import build_chat_router
from .ingress.agents import build_agents_router
from .ingress.memories import router as memories_router
from .logging_config import configure_logging
from .memory import MemoryStore
from .persistence.permissions import PermissionRepository
from .persistence.audit import AuditLog
from .models import ModelProvider, OpenAIModelProvider
from .personal_brain import PersonalBrain
from .professional_brain import ProfessionalBrainGate
from .middleware import FrontendAccessMiddleware


app: FastAPI | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB
    await init_db()
    yield
    # Shutdown: Clean up (if needed)


def create_app(
    settings: Settings | None = None,
    model_provider: ModelProvider | None = None,
    memory_store: MemoryStore | None = None,
    personal_brain: PersonalBrain | None = None,
    audit_log: AuditLog | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    global app  # noqa: PLW0603
    settings = settings or load_settings()
    configure_logging(level=settings.log_level)

    # Initialize ORM session maker
    session_maker = get_session_maker()

    # Initialize repositories with session factory instead of paths
    permission_repository = PermissionRepository(session_maker)
    audit = audit_log or AuditLog(session_maker)
    
    provider = model_provider or OpenAIModelProvider(
        settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    
    # Use the ORM-based MemoryStore
    memory = memory_store or MemoryStore(session_maker)
    
    professional_gate = ProfessionalBrainGate(permission_repository)
    personal = personal_brain or PersonalBrain(professional_gate=professional_gate)

    application = FastAPI(
        title=settings.app_name,
        docs_url=None,  # Disable Swagger UI
        redoc_url=None,  # Disable ReDoc
        lifespan=lifespan,
    )

    # Restrict access to frontend only
    application.add_middleware(FrontendAccessMiddleware)
    
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust this to your specific frontend origin in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint to verify service status."""
        return {"status": "ok"}

    application.include_router(build_gateway_router())
    application.include_router(build_streaming_router(provider, memory, personal, audit))
    application.include_router(build_professional_router(permission_repository))
    application.include_router(build_auth_router()) # No repo arg needed, uses dependency
    application.include_router(build_chat_router(provider, memory, personal, audit))
    application.include_router(build_agents_router())
    application.include_router(memories_router)

    from .ingress.audit import build_audit_router  # local import to avoid cycle

    application.include_router(build_audit_router(audit))

    # Static Files & SPA Handling
    # Search order:
    # 1. 'static' in current dir (legacy/manual override)
    # 2. 'frontend/dist' in current dir (local dev with built frontend)
    # 3. '/usr/share/app/static' (container fallback when /app is mounted)
    possible_static_dirs = [
        Path("static"),
        Path("frontend/dist"),
        Path("/usr/share/app/static"),
    ]

    static_dir = None
    for path in possible_static_dirs:
        if path.exists():
            static_dir = path
            break

    if static_dir and static_dir.exists():
        # Mount assets folder
        if (static_dir / "assets").exists():
            application.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        # Catch-all for SPA
        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Allow API routes to pass through (though they should match earlier)
            if full_path.startswith("api") or full_path.startswith("ws"):
                 return {"status": "404", "message": "Not found"}

            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            
            # Fallback to index.html
            return FileResponse(static_dir / "index.html")

    app = application
    return application
