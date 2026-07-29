class DeepResearchMode:
    name = "deep_research"
    prompt_template = "Research in depth: {query}\nSources: {context}"

    def format_response(self, content: str) -> str:
        return content
