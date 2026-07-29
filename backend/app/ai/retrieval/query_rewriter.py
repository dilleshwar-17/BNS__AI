class QueryRewriter:
    def rewrite(self, query: str) -> str:
        query = query.strip()
        if not query.endswith("?"):
            query = query + "?"
        if not any(kw in query.lower() for kw in ["indian", "bns", "bnss", "bsa", "constitution", "act", "section"]):
            query = f"Under Indian law, {query[0].lower()}{query[1:]}"
        return query
