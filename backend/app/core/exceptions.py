"""Domain exception hierarchy and structured error contract.

Every client-visible error maps to a stable machine-readable ``code`` plus a
human ``message`` and is attached to the request context via ``request_id``.
"""

from __future__ import annotations

from typing import Any


class BNSAIError(Exception):
    """Base class for all BNS AI domain errors."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if request_id:
            payload["request_id"] = request_id
        return payload


class InvalidRequestError(BNSAIError):
    code = "INVALID_REQUEST"
    http_status = 400
    message = "The request is invalid."


class AuthenticationRequiredError(BNSAIError):
    code = "AUTHENTICATION_REQUIRED"
    http_status = 401
    message = "Authentication is required."


class InvalidCredentialsError(BNSAIError):
    code = "INVALID_CREDENTIALS"
    http_status = 401
    message = "Invalid username or password."


class TokenExpiredError(BNSAIError):
    code = "TOKEN_EXPIRED"
    http_status = 401
    message = "The token has expired."


class PermissionDeniedError(BNSAIError):
    code = "PERMISSION_DENIED"
    http_status = 403
    message = "You do not have permission to perform this action."


class OutOfBNSScopeError(BNSAIError):
    code = "OUT_OF_BNS_SCOPE"
    http_status = 422
    message = "This question falls outside the legal sources currently supported by BNS AI."


class AmbiguousQueryError(BNSAIError):
    code = "AMBIGUOUS_QUERY"
    http_status = 422
    message = "The query is ambiguous. Please clarify."


class InsufficientInformationError(BNSAIError):
    code = "INSUFFICIENT_INFORMATION"
    http_status = 422
    message = "There is not enough information to answer this question."


class PromptInjectionDetectedError(BNSAIError):
    code = "PROMPT_INJECTION_DETECTED"
    http_status = 422
    message = "The request was rejected by security validation."


class RetrievalFailedError(BNSAIError):
    code = "RETRIEVAL_FAILED"
    http_status = 502
    message = "Legal retrieval failed. Please try again."


class InsufficientBNSEvidenceError(BNSAIError):
    code = "INSUFFICIENT_BNS_EVIDENCE"
    http_status = 422
    message = "The available BNS sources do not provide sufficient evidence to answer this question reliably."


class LLMProviderUnavailableError(BNSAIError):
    code = "LLM_PROVIDER_UNAVAILABLE"
    http_status = 503
    message = "No LLM provider is currently available."


class LLMGenerationFailedError(BNSAIError):
    code = "LLM_GENERATION_FAILED"
    http_status = 502
    message = "LLM generation failed."


class GroundingValidationFailedError(BNSAIError):
    code = "GROUNDING_VALIDATION_FAILED"
    http_status = 422
    message = "The generated response could not be grounded in retrieved BNS evidence."


class CitationValidationFailedError(BNSAIError):
    code = "CITATION_VALIDATION_FAILED"
    http_status = 422
    message = "A citation could not be validated against the retrieved evidence."


class DraftIncompleteError(BNSAIError):
    code = "DRAFT_INCOMPLETE"
    http_status = 422
    message = "The draft is missing required information."


class DraftValidationFailedError(BNSAIError):
    code = "DRAFT_VALIDATION_FAILED"
    http_status = 422
    message = "The draft failed validation."


class DocumentProcessingFailedError(BNSAIError):
    code = "DOCUMENT_PROCESSING_FAILED"
    http_status = 422
    message = "The document could not be processed."


class VoiceTranscriptionFailedError(BNSAIError):
    code = "VOICE_TRANSCRIPTION_FAILED"
    http_status = 502
    message = "Speech-to-text transcription failed."


class VoiceTranscriptionUncertainError(BNSAIError):
    code = "VOICE_TRANSCRIPTION_UNCERTAIN"
    http_status = 422
    message = "The transcription of legally material content is uncertain; confirmation is required."


class CaseAccessDeniedError(BNSAIError):
    code = "CASE_ACCESS_DENIED"
    http_status = 403
    message = "You do not have access to this case."


class SourceNotActiveError(BNSAIError):
    code = "SOURCE_NOT_ACTIVE"
    http_status = 409
    message = "The legal source is not active."


class IngestionFailedError(BNSAIError):
    code = "INGESTION_FAILED"
    http_status = 500
    message = "Knowledge ingestion failed."


class NotFoundError(BNSAIError):
    code = "NOT_FOUND"
    http_status = 404
    message = "The requested resource was not found."
