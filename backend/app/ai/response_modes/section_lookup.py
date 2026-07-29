class SectionLookupMode:
    name = "section_lookup"
    prompt_template = "Look up legal section: {query}\nStatutory text: {context}"

    def format_response(self, content: str) -> str:
        return content
