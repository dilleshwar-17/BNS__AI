class LegalDraftingMode:
    name = "legal_drafting"
    prompt_template = "Draft a legal document: {query}\nContext: {context}"

    def format_response(self, content: str) -> str:
        return content
