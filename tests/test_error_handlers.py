"""Tests for unified error handling module."""

from error_handlers import (
    ErrorResponse,
    create_authentication_error,
    create_error_response,
    create_internal_error,
    create_not_found_error,
    create_validation_error,
)


class TestErrorResponse:
    """Test ErrorResponse class."""

    def test_error_response_basic(self):
        """Test basic error response creation."""
        error = ErrorResponse(
            error_type="TestError",
            error_message="Test message",
            status_code=400,
        )

        assert error.error_type == "TestError"
        assert error.error_message == "Test message"
        assert error.status_code == 400
        assert error.timestamp > 0

    def test_error_response_to_dict(self):
        """Test error response conversion to dictionary."""
        error = ErrorResponse(
            error_type="TestError",
            error_message="Test message",
            status_code=400,
            error_details={"field": "test"},
            user_action="Try again",
        )

        result = error.to_dict()

        assert result["success"] is False
        assert result["error_type"] == "TestError"
        assert result["error_message"] == "Test message"
        assert result["timestamp"] > 0
        assert result["error_details"] == {"field": "test"}
        assert result["user_action"] == "Try again"

    def test_error_response_to_tuple(self):
        """Test error response conversion to Flask tuple."""
        error = ErrorResponse(
            error_type="TestError", error_message="Test message", status_code=400
        )

        result_dict, status_code = error.to_tuple()

        assert status_code == 400
        assert result_dict["success"] is False
        assert result_dict["error_type"] == "TestError"


class TestErrorFactoryFunctions:
    """Test error factory functions."""

    def test_create_error_response(self):
        """Test generic error response creation."""
        error = ValueError("Test error")
        result_dict, status_code = create_error_response(error, log_error=False)

        assert status_code == 500
        assert result_dict["success"] is False
        assert result_dict["error_type"] == "ValueError"
        assert result_dict["error_message"] == "Test error"

    def test_create_error_response_custom(self):
        """Test error response with custom parameters."""
        error = ValueError("Test error")
        result_dict, status_code = create_error_response(
            error,
            error_type="CustomError",
            error_message="Custom message",
            status_code=400,
            error_details={"field": "test"},
            user_action="Fix it",
            log_error=False,
        )

        assert status_code == 400
        assert result_dict["error_type"] == "CustomError"
        assert result_dict["error_message"] == "Custom message"
        assert result_dict["error_details"] == {"field": "test"}
        assert result_dict["user_action"] == "Fix it"

    def test_create_validation_error(self):
        """Test validation error creation."""
        result_dict, status_code = create_validation_error(
            "Invalid input", field="username"
        )

        assert status_code == 400
        assert result_dict["error_type"] == "ValidationError"
        assert result_dict["error_message"] == "Invalid input"
        assert result_dict["error_details"]["field"] == "username"
        assert "check your input" in result_dict["user_action"].lower()

    def test_create_authentication_error(self):
        """Test authentication error creation."""
        result_dict, status_code = create_authentication_error()

        assert status_code == 401
        assert result_dict["error_type"] == "AuthenticationError"
        assert "authentication required" in result_dict["error_message"].lower()
        assert "log in" in result_dict["user_action"].lower()

    def test_create_not_found_error(self):
        """Test not found error creation."""
        result_dict, status_code = create_not_found_error("User", "123")

        assert status_code == 404
        assert result_dict["error_type"] == "NotFoundError"
        assert "User" in result_dict["error_message"]
        assert "123" in result_dict["error_message"]

    def test_create_internal_error(self):
        """Test internal server error creation."""
        error = RuntimeError("Something broke")
        result_dict, status_code = create_internal_error(error=error)

        assert status_code == 500
        assert result_dict["error_type"] == "InternalServerError"
        assert "internal server error" in result_dict["error_message"].lower()
        assert "try again later" in result_dict["user_action"].lower()


class TestErrorResponseFormat:
    """Test that error responses follow the standard format."""

    def test_all_errors_have_required_fields(self):
        """Test that all error types have required fields."""
        error_functions = [
            create_validation_error("test"),
            create_authentication_error(),
            create_not_found_error("Resource"),
            create_internal_error(),
        ]

        for result_dict, status_code in error_functions:
            assert "success" in result_dict
            assert result_dict["success"] is False
            assert "error_type" in result_dict
            assert "error_message" in result_dict
            assert "timestamp" in result_dict
            assert isinstance(status_code, int)
            assert 400 <= status_code < 600
