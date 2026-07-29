class ResponseBuilder:
    def __init__(self):
        self.modes = {
            "legal_guidance": LegalGuidanceMode(),
            "legal_drafting": LegalDraftingMode(),
            "case_law": CaseLawMode(),
            "deep_research": DeepResearchMode(),
            "document_analysis": DocumentAnalysisMode(),
            "legal_procedure": LegalProcedureMode(),
            "rights_advisory": RightsAdvisoryMode(),
            "section_lookup": SectionLookupMode(),
            "comparison": ComparisonMode(),
        }

    def get_mode(self, mode: str):
        return self.modes.get(mode, self.modes["legal_guidance"])
