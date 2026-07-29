import re


class EntityExtractor:
    def extract(self, text: str) -> dict:
        sections = re.findall(r"(?i)section\s+(\d+[A-Za-z]?)", text)
        acts = re.findall(r"(?i)(BNS|BNSS|BSA|CPC|IPC|CrPC|IT\s+Act|Constitution)", text)
        return {"sections": list(set(sections)), "acts": list(set(acts))}
