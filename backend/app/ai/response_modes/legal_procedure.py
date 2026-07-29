class LegalProcedureMode:
    name = "legal_procedure"
    prompt_template = "Explain the legal procedure for: {query}\nProcedural law: {context}"

    def format_response(self, content: str) -> str:
        return content
