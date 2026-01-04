from fastapi import FastAPI

from .config import Settings, load_settings
from .ingress.gateway import build_gateway_router
from .ingress.pairing import build_pairing_router
from .ingress.streaming import build_streaming_router
from .ingress.ops import build_ops_router
from .ingress.sessions import build_sessions_router
from .logging_config import configure_logging
from .memory import MemoryStore
from .persistence.pairing import PairingRepository
from .persistence.permissions import PermissionRepository
from .persistence.audit import AuditLog
from .pinset import pinset_from_settings
from .models import ModelProvider, OpenAIModelProvider
from .friend_brain import FriendBrain
from .ops_brain import OpsBrainGate


app: FastAPI | None = None


def create_app(
    settings: Settings | None = None,
    model_provider: ModelProvider | None = None,
    memory_store: MemoryStore | None = None,
    friend_brain: FriendBrain | None = None,
    audit_log: AuditLog | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    This function initializes all core services (persistence, memory, brains, models)
    and routes them into the application.

    Args:
        settings: Application settings. If None, loaded from environment/files.
        model_provider: LLM provider instance. If None, defaults to OpenAI.
        memory_store: Memory storage instance. If None, initialized from settings.
        friend_brain: Tone/personality logic. If None, initialized with OpsGate.
        audit_log: Audit logging service. If None, initialized from settings.

    Returns:
        FastAPI: The configured application instance.
    """
    global app  # noqa: PLW0603
    settings = settings or load_settings()
    configure_logging(level=settings.log_level)

    pinset_service = pinset_from_settings(settings)
    pairing_repository = PairingRepository(settings.pairing_db_path)
    permission_repository = PermissionRepository(settings.ops_db_path)
    audit = audit_log or AuditLog(settings.audit_db_path)
    provider = model_provider or OpenAIModelProvider(
        settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    memory = memory_store or MemoryStore(settings.memory_db_path)
    ops_gate = OpsBrainGate(permission_repository)
    friend = friend_brain or FriendBrain(ops_gate=ops_gate)

    application = FastAPI(title=settings.app_name)

    @application.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint to verify service status."""
        return {"status": "ok"}

    application.include_router(
        build_pairing_router(
            settings=settings,
            pinset_service=pinset_service,
            pairing_repository=pairing_repository,
        )
    )

    application.include_router(build_gateway_router())
    application.include_router(build_sessions_router(pairing_repository))
    application.include_router(build_streaming_router(provider, memory, friend, audit))
    application.include_router(build_ops_router(permission_repository))
    from .ingress.audit import build_audit_router  # local import to avoid cycle

    application.include_router(build_audit_router(audit))

    app = application
    return application
