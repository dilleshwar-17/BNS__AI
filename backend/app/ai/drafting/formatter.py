import re

from app.core.logging import get_logger

logger = get_logger(__name__)


class DraftFormatter:
    def format(self, content: str, draft_type: str) -> str:
        lines = content.split("\n")
        formatted = []
        in_table = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted.append("")
                continue
            if stripped.startswith("**") and stripped.endswith("**"):
                formatted.append(f"\n{stripped}\n")
            elif stripped.startswith("# "):
                formatted.append(f"\n{stripped.upper()}\n")
            elif stripped.startswith("## "):
                formatted.append(f"\n{stripped.title()}\n")
            elif stripped.startswith("* ") or stripped.startswith("- "):
                formatted.append(stripped)
            elif re.match(r"^\d+[.)]", stripped):
                formatted.append(stripped)
            elif "|" in stripped and stripped.count("|") >= 2:
                if not in_table:
                    formatted.append("")
                    in_table = True
                formatted.append(stripped)
            else:
                if in_table:
                    formatted.append("")
                    in_table = False
                formatted.append(stripped)

        result = "\n".join(formatted)
        result = self._format_citations(result)
        return result

    def _format_citations(self, text: str) -> str:
        text = re.sub(r"(?i)(bns|bnss|bsa|ipc|crpc|cpc)\s+(section\s+)?(\d+[A-Za-z]?)", r"**\1 Section \3**", text)
        return text
