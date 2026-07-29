import re

from fastapi import HTTPException, Request, status

from app.core.logging import get_logger

logger = get_logger(__name__)

# Layered detection patterns: (name, pattern, severity)
SENSITIVE_PATTERNS = [
    ("ignore_instructions", r"(?i)ignore\s+(all\s+)?previous\s+instructions", "high"),
    ("forget_rules", r"(?i)forget\s+(all\s+)?(your|the)\s+(instructions|rules|guidelines)", "high"),
    ("role_hijack", r"(?i)you\s+are\s+(now|not)\s+.*\s*(a\s+)?(legal\s+)?(AI|assistant|bot)", "high"),
    ("system_prompt_leak", r"(?i)system\s+prompt", "medium"),
    ("persona_switch", r"(?i)act\s+as\s+(a\s+)?(different|another)\s+(AI|assistant|persona)", "high"),
    ("jailbreak_dan", r"(?i)(do\s+anything\s+now|DAN\s+mode)", "high"),
    ("encoding_bypass", r"(?i)(base64|rot13|hex)\s*(encode|decode|decipher)", "medium"),
    ("instruction_sep", r"(?i)(---\s*instruction|###\s*new\s+system)", "high"),
    ("role_play", r"(?i)pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(different|another)", "medium"),
    (
        "data_exfil",
        r"(?i)(show|reveal|repeat|output)\s+(me\s+)?(your|the)\s+(system|initial)\s+(prompt|message)",
        "high",
    ),
]

# Allowed contexts where patterns might legitimately appear
ALLOWED_CONTEXTS = [
    r"(?i)(explain|describe|discuss|what\s+is)\s+(prompt\s+injection|jailbreak)",
    r"(?i)(security|attack|vulnerability|threat)",
]


def _check_text(text: str) -> list[dict]:
    violations = []
    for name, pattern, severity in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            is_allowed = any(re.search(ap, text) for ap in ALLOWED_CONTEXTS)
            if not is_allowed:
                violations.append({"pattern": name, "severity": severity})
    return violations


async def detect_prompt_injection(request: Request):
    if request.method not in ("POST", "PUT", "PATCH"):
        return

    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return

        body = await request.json()
        if not isinstance(body, dict):
            return

        # Check all string values in the body
        text_parts = []
        for key, value in body.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, str):
                        text_parts.append(v)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict):
                        text_parts.extend(str(v) for v in item.values() if isinstance(v, str))

        full_text = " ".join(text_parts)
        violations = _check_text(full_text)

        if violations:
            high_severity = [v for v in violations if v["severity"] == "high"]
            logger.warning(
                "prompt_injection_detected",
                path=request.url.path,
                violations=[v["pattern"] for v in violations],
                severity="high" if high_severity else "medium",
            )
            if high_severity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Input contains prohibited content",
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("prompt_injection_check_error", error=str(e))


def check_text_for_injection(text: str) -> list[dict]:
    """Public API for checking arbitrary text (e.g., in chat messages)."""
    return _check_text(text)
