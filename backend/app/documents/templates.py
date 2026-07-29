class DocumentTemplates:
    @staticmethod
    def get_template(doc_type: str) -> str:
        templates = {
            "cover_letter": "Dear Sir/Madam,\n\n\n\nYours faithfully,\n",
            "legal_memo": "LEGAL MEMORANDUM\n\nTO:\nFROM:\nDATE:\nRE:\n\n",
        }
        return templates.get(doc_type, "")
