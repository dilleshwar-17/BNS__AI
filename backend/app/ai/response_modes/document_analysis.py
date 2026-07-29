class DocumentAnalysisMode:
    name = "document_analysis"
    prompt_template = "Analyze this legal document: {query}\nRelevant law: {context}"

    def format_response(self, content: str) -> str:
        return content
