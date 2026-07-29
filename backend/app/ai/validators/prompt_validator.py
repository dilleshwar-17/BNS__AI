import re


class PromptValidator:
    def validate(self, prompt: str) -> dict:
        issues = []
        if len(prompt) < 10:
            issues.append("Prompt too short")
        if len(prompt) > 10000:
            issues.append("Prompt exceeds maximum length")
        suspicious = re.search(
            r"(?i)(ignore|forget|disregard|override)\s+(all\s+)?(previous|your|the)\s+(instructions|rules)", prompt
        )
        if suspicious:
            issues.append("Contains prompt injection patterns")
        return {"valid": len(issues) == 0, "issues": issues}
