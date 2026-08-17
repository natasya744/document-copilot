"""Standard error taxonomy for the API.

Every error response is ``{"detail": "<frontend-facing message>"}``. 401 is
raised by the auth dependency, 403/404 by route handlers via the helpers
below, 502 wraps upstream (Supabase/LLM) failures, and a global handler keeps
422 and 500 in the same JSON shape. The frontend only renders ``detail`` when
it is a string, so handlers that reshape the defaults are registered here.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def not_found(resource: str) -> HTTPException:
    """404 for a missing resource, named for the frontend-facing message."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found",
    )


def forbidden() -> HTTPException:
    """403 for an authenticated user reaching another user's resource."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this resource",
    )


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # FastAPI's default detail is a list of error dicts; reduce to the first
    # field + message so the frontend gets a renderable string.
    errors = exc.errors()
    if errors:
        loc = errors[0].get("loc", ())
        field = ".".join(str(part) for part in loc if part != "body")
        message = errors[0].get("msg", "invalid value")
        detail = f"Invalid {field}: {message}" if field else f"Invalid input: {message}"
    else:
        detail = "Invalid request"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": detail},
    )


async def _internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # FastAPI logs the traceback separately; only the response shape changes.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the 422/500 handlers so every error is ``{"detail": str}``."""
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _internal_error_handler)
