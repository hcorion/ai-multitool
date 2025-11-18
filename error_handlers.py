"""Unified error handling for the AI Multitool application.

This module provides standardized error response formats and utility functions
for consistent error handling across all API endpoints.
"""

import logging
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

# Module-level logger
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ErrorResponse:
    """Standard error response structure for all API endpoints."""

    error_type: str
    error_message: str
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    error_details: dict[str, Any] = field(default_factory=dict)
    user_action: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        """Convert error response to dictionary format."""
        response = {
            "success": False,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }

        if self.error_details:
            response["error_details"] = self.error_details

        if self.user_action:
            response["user_action"] = self.user_action

        return response

    def to_tuple(self) -> tuple[dict[str, Any], int]:
        """Convert error response to Flask response tuple."""
        return self.to_dict(), self.status_code


def create_error_response(
    error: Exception,
    error_type: str | None = None,
    error_message: str | None = None,
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
    error_details: dict[str, Any] | None = None,
    user_action: str | None = None,
    log_error: bool = True,
) -> tuple[dict[str, Any], int]:
    """Create a standardized error response.

    Args:
        error: The exception that occurred
        error_type: Optional custom error type (defaults to exception class name)
        error_message: Optional custom error message (defaults to str(error))
        status_code: HTTP status code (default: 500)
        error_details: Optional technical details for debugging
        user_action: Optional guidance for user
        log_error: Whether to log the error (default: True)

    Returns:
        Tuple of (error_dict, status_code) for Flask response
    """
    if log_error:
        logger.error("Error occurred: %s", error, exc_info=True)

    response = ErrorResponse(
        error_type=error_type or type(error).__name__,
        error_message=error_message or str(error),
        status_code=status_code,
        error_details=error_details or {},
        user_action=user_action,
    )

    return response.to_tuple()


def create_validation_error(
    message: str,
    field: str | None = None,
    error_details: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Create a validation error response.

    Args:
        message: User-friendly validation error message
        field: Optional field name that failed validation
        error_details: Optional additional validation details

    Returns:
        Tuple of (error_dict, status_code) for Flask response
    """
    details = error_details or {}
    if field:
        details["field"] = field

    return create_error_response(
        error=ValueError(message),
        error_type="ValidationError",
        error_message=message,
        status_code=HTTPStatus.BAD_REQUEST,
        error_details=details,
        user_action="Please check your input and try again.",
        log_error=False,
    )


def create_authentication_error(
    message: str = "Authentication required",
) -> tuple[dict[str, Any], int]:
    """Create an authentication error response.

    Args:
        message: User-friendly authentication error message

    Returns:
        Tuple of (error_dict, status_code) for Flask response
    """
    return create_error_response(
        error=PermissionError(message),
        error_type="AuthenticationError",
        error_message=message,
        status_code=HTTPStatus.UNAUTHORIZED,
        user_action="Please log in to continue.",
        log_error=False,
    )


def create_not_found_error(
    resource: str,
    resource_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Create a not found error response.

    Args:
        resource: Type of resource that was not found
        resource_id: Optional ID of the resource

    Returns:
        Tuple of (error_dict, status_code) for Flask response
    """
    message = f"{resource} not found"
    if resource_id:
        message = f"{resource} with ID '{resource_id}' not found"

    return create_error_response(
        error=FileNotFoundError(message),
        error_type="NotFoundError",
        error_message=message,
        status_code=HTTPStatus.NOT_FOUND,
        log_error=False,
    )


def create_internal_error(
    error: Exception | None = None,
    message: str = "Internal server error",
) -> tuple[dict[str, Any], int]:
    """Create an internal server error response.

    Args:
        error: Optional exception that caused the error
        message: User-friendly error message

    Returns:
        Tuple of (error_dict, status_code) for Flask response
    """
    # Delegate to create_error_response for consistent logging and construction
    return create_error_response(
        error=error or RuntimeError(message),
        error_type="InternalServerError",
        error_message=message,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        user_action="Please try again later. If the problem persists, contact support.",
        log_error=True,
    )
