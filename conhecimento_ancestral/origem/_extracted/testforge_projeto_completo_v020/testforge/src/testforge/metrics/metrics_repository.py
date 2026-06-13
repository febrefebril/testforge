from ..evidence.evidence_store import EvidenceStore
class MetricsRepository:
    def __init__(self,store):self.store=store
    def summary(self,application=None):return self.store.get_metrics(application)
