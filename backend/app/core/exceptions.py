from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class SolarSentryException(Exception):
    """Base exception for all domain errors in Solar Sentry."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class DeviceNotFoundError(SolarSentryException):
    def __init__(self, device_id: str):
        super().__init__(
            message=f"Device with ID '{device_id}' was not found.",
            code="DEVICE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"device_id": device_id}
        )


class InvalidCommandError(SolarSentryException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INVALID_COMMAND",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class SafetyViolationError(SolarSentryException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SAFETY_VIOLATION",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class ImageNotFoundError(SolarSentryException):
    def __init__(self, image_id: str):
        super().__init__(
            message=f"Image with ID '{image_id}' was not found.",
            code="IMAGE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"image_id": image_id}
        )


class MissionNotFoundError(SolarSentryException):
    def __init__(self, mission_id: str):
        super().__init__(
            message=f"Mission with ID '{mission_id}' was not found.",
            code="MISSION_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"mission_id": mission_id}
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application."""

    @app.exception_handler(SolarSentryException)
    async def domain_exception_handler(request: Request, exc: SolarSentryException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"[{request_id[:8]}] Domain error {exc.code}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "code": exc.code,
                "details": exc.details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"[{request_id[:8]}] Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Request validation failed.",
                "code": "VALIDATION_ERROR",
                "details": {"validation_errors": exc.errors()},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": f"HTTP_{exc.status_code}",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"[{request_id[:8]}] Unhandled server exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "An unexpected internal server error occurred.",
                "code": "INTERNAL_SERVER_ERROR",
                "details": {"message": str(exc)},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        )
