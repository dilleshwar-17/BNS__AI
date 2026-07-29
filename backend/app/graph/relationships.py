class RelationshipManager:
    RELATION_TYPES = {
        "REFERENCES": "REFERENCES",
        "BELONGS_TO": "BELONGS_TO",
        "RELATED_TO": "RELATED_TO",
        "CITES": "CITES",
        "AMENDS": "AMENDS",
        "OVERRULES": "OVERRULES",
        "CONFERS_RIGHT": "CONFERS_RIGHT",
        "HAS_BAIL_INFO": "HAS_BAIL_INFO",
        "RETRIEVED_FROM": "RETRIEVED_FROM",
        "TAGGED_WITH": "TAGGED_WITH",
    }

    def get_type(self, name: str) -> str:
        return self.RELATION_TYPES.get(name.upper(), name.upper())
