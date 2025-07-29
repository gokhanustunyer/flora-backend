"""Logging configuration for the FastAPI application."""

import structlog
import logging
import sys
from typing import Any, Dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_request(endpoint: str, method: str, **kwargs) -> None:
    """Log incoming request details."""
    logger = get_logger("api.request")
    logger.info(
        "Request received",
        endpoint=endpoint,
        method=method,
        **kwargs
    )


def log_response(endpoint: str, status_code: int, duration: float, **kwargs) -> None:
    """Log response details."""
    logger = get_logger("api.response")
    logger.info(
        "Response sent",
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """Log error details."""
    logger = get_logger("api.error")
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {}
    )


def log_api_call(service: str, operation: str, duration: float, success: bool, **kwargs) -> None:
    """Log API call details."""
    logger = get_logger(f"{service}.api")
    logger.info(
        f"{service.title()} API call",
        operation=operation,
        duration_ms=round(duration * 1000, 2),
        success=success,
        **kwargs
    ) 