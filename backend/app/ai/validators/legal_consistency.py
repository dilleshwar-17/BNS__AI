import re


class LegalConsistencyChecker:
    def __init__(self):
        self.known_acts = ["bns", "bnss", "bsa", "cpc", "ipc", "crpc", "ica", "tpa", "hma"]

    def check(self, text: str) -> dict:
        text_lower = text.lower()
        issues = []
        for act in self.known_acts:
            if act in text_lower:
                pattern = rf"{act}\s+section\s+(\d+)"
                sections = re.findall(pattern, text_lower)
                if not sections:
                    issues.append(f"Reference to {act.upper()} without specific section number")
        return {"consistent": len(issues) == 0, "issues": issues}
