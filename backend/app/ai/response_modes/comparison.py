class ComparisonMode:
    name = "comparison"
    prompt_template = "Compare: {query}\nLegal provisions: {context}"

    def format_response(self, content: str) -> str:
        return content
