from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.chat_stream import router as chat_stream_router
from app.api.errors import register_exception_handlers
from app.config import settings

app = FastAPI(title="Document Copilot API")

register_exception_handlers(app)


# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(chat_stream_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    """
    return {"status": "ok"}
