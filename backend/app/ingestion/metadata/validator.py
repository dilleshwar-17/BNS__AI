class MetadataValidator:
    def validate(self, metadata: dict) -> list[str]:
        issues = []
        if "source" not in metadata:
            issues.append("Missing source")
        if "char_count" in metadata and metadata["char_count"] == 0:
            issues.append("Empty content")
        return issues
