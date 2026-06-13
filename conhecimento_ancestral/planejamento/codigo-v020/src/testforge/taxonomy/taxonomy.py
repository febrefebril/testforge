import yaml
from pathlib import Path
class FailureTaxonomy:
    def __init__(self,policy_path="policies/failure_taxonomy.yaml"):
        data=yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"));self._codes={}
        for fam,codes in data.get("taxonomy",{}).items():
            for code,info in codes.items(): self._codes[code]={"family":fam,**info}
    def allows_healing(self,code): return self._codes.get(code,{}).get("allow_healing",False)
