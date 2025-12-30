import uvicorn

from ap.config import load_settings


if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(
        "ap.app:create_app",
        host=settings.host,
        port=settings.port,
        reload=False,
        factory=True,
        log_level=settings.log_level.lower(),
    )
