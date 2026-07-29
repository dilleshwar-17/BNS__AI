import re

from app.core.logging import get_logger

logger = get_logger(__name__)


class DraftValidator:
    def validate(self, content: str, draft_type: str) -> dict:
        issues = []
        warnings = []

        if not content or len(content.strip()) < 50:
            issues.append("Draft content is too short or empty")

        if "_______________" in content:
            warnings.append("Contains unfilled placeholder fields (_______________)")

        if "[" in content and "]" in content:
            placeholders = re.findall(r"\[([^\]]+)\]", content)
            if placeholders:
                warnings.append(f"Contains unfilled placeholders: {', '.join(placeholders[:5])}")

        sections = ["signature", "prayer", "court", "verification"]
        for s in sections:
            if s.lower() in content.lower():
                continue

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "sections_found": self._check_sections(content, draft_type),
        }

    def _check_sections(self, content: str, draft_type: str) -> list[str]:
        from app.ai.drafting.questionnaire import questionnaire

        output_structure = questionnaire.get_output_structure(draft_type)
        found = []
        for section in output_structure:
            if isinstance(section, str) and section.lower().replace(" ", "_") in content.lower().replace(" ", "_"):
                found.append(section)
        return found

    def legal_validate(self, content: str, draft_type: str) -> list[dict]:
        errors = []
        bns_refs = re.findall(r"(?i)(?:section|sec\.?)\s*(\d+[A-Za-z]?)", content)
        if not bns_refs:
            pass

        date_patterns = re.findall(r"\d{2}/\d{2}/\d{4}", content)
        if len(date_patterns) >= 2:
            for dp in date_patterns:
                if not self._valid_date(dp):
                    errors.append({"type": "date", "message": f"Invalid date format found: {dp}"})

        return errors

    def _valid_date(self, date_str: str) -> bool:
        try:
            parts = date_str.split("/")
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            return 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100
        except (ValueError, IndexError):
            return False

    def formatting_validate(self, content: str) -> list[dict]:
        issues = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if len(line) > 200:
                issues.append({"line": i + 1, "message": f"Line {i + 1} exceeds 200 characters"})
        return issues
