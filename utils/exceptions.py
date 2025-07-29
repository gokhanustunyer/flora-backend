"""Custom exception classes for the FastAPI application."""


class BaseCustomException(Exception):
    """Base class for all custom exceptions."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class InvalidImageError(BaseCustomException):
    """Raised when uploaded image is invalid."""
    pass


class FileSizeExceededError(BaseCustomException):
    """Raised when uploaded file exceeds size limit."""
    pass


class InvalidFileTypeError(BaseCustomException):
    """Raised when uploaded file type is not allowed."""
    pass


class AIGenerationFailedError(BaseCustomException):
    """Raised when AI image generation fails."""
    pass


class AzureAPIError(BaseCustomException):
    """Raised when Azure API calls fail."""
    pass


class ImageProcessingError(BaseCustomException):
    """Raised when image processing operations fail."""
    pass


class LogoOverlayError(BaseCustomException):
    """Raised when logo overlay operation fails."""
    pass 