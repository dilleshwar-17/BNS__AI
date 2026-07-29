class RightsAdvisoryMode:
    name = "rights_advisory"
    prompt_template = "Advise on legal rights regarding: {query}\nRights under law: {context}"

    def format_response(self, content: str) -> str:
        return content
