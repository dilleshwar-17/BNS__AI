import re

from app.core.logging import get_logger

logger = get_logger(__name__)


class DraftValidator:
    def validate(self, content: str, draft_type: str, context: str = "", details: dict = None) -> dict:
        issues = []
        warnings = []
        hallucinated = False

        if not content or len(content.strip()) < 50:
            issues.append("Draft content is too short or empty")

        if "_______________" in content:
            warnings.append("Contains unfilled placeholder fields (_______________)")

        if "[" in content and "]" in content:
            placeholders = re.findall(r"\[([^\]]+)\]", content)
            if placeholders:
                warnings.append(f"Contains unfilled placeholders: {', '.join(placeholders[:5])}")

        # Programmatic Section Hallucination Prevention
        section_pattern = r"(?i)(?:section|sec\.?)\s*(\d+[A-Za-z]?)"
        draft_sections = set(re.findall(section_pattern, content))

        if draft_sections:
            from app.services.drafting_service import get_draft_template
            tpl_data = get_draft_template(draft_type)
            tpl_text = tpl_data["template"] if tpl_data else ""

            allowed_sections = set(re.findall(section_pattern, tpl_text))
            if context:
                allowed_sections.update(re.findall(section_pattern, context))
            if details:
                allowed_sections.update(re.findall(section_pattern, str(details)))

            for sec in draft_sections:
                if sec not in allowed_sections:
                    # Common years / numbers allowed under standard templates
                    if sec in ["1872", "1955", "2019", "2023", "173", "478", "35", "13", "1", "2", "3"]:
                        continue
                    logger.warning(
                        "hallucinated_section_in_draft_detected",
                        section=sec,
                        allowed=list(allowed_sections),
                    )
                    issues.append(
                        f"Hallucinated section reference found in draft: Section {sec}"
                    )
                    hallucinated = True

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "hallucinated": hallucinated,
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
