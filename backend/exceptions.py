"""
Domain-Specific Structured Exceptions for MedLens.
Provides explicit failure cases without broad exception swallowing.
"""

class MedLensError(Exception):
    """Base exception for all MedLens domain and service errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentNotFoundError(MedLensError):
    def __init__(self, document_id: str):
        super().__init__(f"Document '{document_id}' not found or access denied.", status_code=404)
        self.document_id = document_id


class PatientNotFoundError(MedLensError):
    def __init__(self, patient_id: str):
        super().__init__(f"Patient '{patient_id}' not found or access denied.", status_code=404)
        self.patient_id = patient_id


class UnsupportedFileTypeError(MedLensError):
    def __init__(self, extension: str, allowed: set):
        super().__init__(
            f'Unsupported file extension: "{extension}". Allowed formats: {", ".join(sorted(allowed))}',
            status_code=400
        )
        self.extension = extension


class FileTooLargeError(MedLensError):
    def __init__(self, size_bytes: int, max_bytes: int):
        super().__init__(
            f"Uploaded file exceeds the maximum {max_bytes // (1024 * 1024)}MB limit.",
            status_code=413
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class MagicBytesMismatchError(MedLensError):
    def __init__(self, extension: str):
        super().__init__(
            f"File content does not match expected {extension} binary signature (magic bytes check failed).",
            status_code=400
        )
        self.extension = extension


class EmptyDocumentError(MedLensError):
    def __init__(self, message: str = "Uploaded file is empty (0 bytes)."):
        super().__init__(message, status_code=400)


class DocumentExtractionError(MedLensError):
    def __init__(self, detail: str = "No readable text could be extracted from the file."):
        super().__init__(detail, status_code=422)


class RateLimitExceededError(MedLensError):
    def __init__(self, max_reqs: int, window_secs: float):
        super().__init__(
            f"Rate limit exceeded ({max_reqs} req/{int(window_secs)}s). Please wait before retrying.",
            status_code=429
        )


class LLMServiceError(MedLensError):
    def __init__(self, detail: str):
        super().__init__(detail, status_code=500)
