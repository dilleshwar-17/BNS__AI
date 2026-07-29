class CaseLawMode:
    name = "case_law"
    prompt_template = "Find relevant case law for: {query}\nContext: {context}"

    def format_response(self, content: str) -> str:
        return content
