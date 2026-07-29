import re


class MarkdownRenderer:
    @staticmethod
    def to_html(text: str) -> str:
        html = text
        html = re.sub(r"### (.+)", r"<h3>\1</h3>", html)
        html = re.sub(r"## (.+)", r"<h2>\1</h2>", html)
        html = re.sub(r"# (.+)", r"<h1>\1</h1>", html)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
        html = re.sub(r"^- (.+)", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"(<li>.*</li>\n?)+", r"<ul>\g<0></ul>", html)
        html = re.sub(r"\n\n", "</p><p>", html)
        return f"<p>{html}</p>"

    @staticmethod
    def strip_markdown(text: str) -> str:
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"#{1,6}\s+", "", text)
        return text.strip()
