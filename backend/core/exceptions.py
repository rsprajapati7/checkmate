class CheckMateError(Exception):
    """Base exception for all CheckMate errors."""


class IngestionError(CheckMateError):
    """Raised when document ingestion fails."""


class PipelineError(CheckMateError):
    """Raised when a forensic pipeline fails."""


class LLMError(CheckMateError):
    """Raised when LLM call fails or returns unparseable response."""


class RegistryError(CheckMateError):
    """Raised when registry verification fails."""


class ReportError(CheckMateError):
    """Raised when report generation fails."""


class FileTooLargeError(CheckMateError):
    """Raised when uploaded file exceeds size limit."""


class UnsupportedFileTypeError(CheckMateError):
    """Raised when the uploaded file type is not supported."""
