class FailureClassifier:
    def classify(self,error,match_count=None):
        m=str(error).lower()
        if "timeout" in m and "waiting" in m:
            return "LOCATOR_AMBIGUOUS" if match_count and match_count>1 else "LOCATOR_NOT_FOUND"
        if "disabled" in m: return "ACTIONABILITY_DISABLED"
        if "intercept" in m or "overlay" in m or "obscured" in m: return "ACTIONABILITY_OBSCURED"
        return "LOCATOR_NOT_FOUND"
