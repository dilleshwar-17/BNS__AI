class LegalGuidanceMode:
    name = "legal_guidance"
    prompt_template = "Provide legal guidance on: {query}\nRelevant law: {context}"

    def format_response(self, content: str) -> str:
        if not content:
            return content
        if content.startswith("## Direct Answer") or content.startswith("# Direct Answer"):
            return content
        lines = content.strip().split("\n")
        if not lines[0].startswith("#"):
            intro = lines[0].strip()
            if intro and len(intro) < 200 and not intro.endswith(":"):
                content = f"## Direct Answer\n\n{intro}\n\n## Explanation\n\n" + "\n".join(lines[1:]).strip()
        content = content.replace("I can provide general legal information", "## Direct Answer\n\n")
        return content
