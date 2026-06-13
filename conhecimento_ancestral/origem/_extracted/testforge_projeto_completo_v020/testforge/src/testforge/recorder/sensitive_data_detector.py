import re
PATTERNS={"cpf_pattern":re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),"cnpj_pattern":re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"),"long_numeric_identifier":re.compile(r"(?<!\d)\d{8,}(?!\d)")}
def scan_for_sensitive_data(texts):
    cats=set()
    for t in (texts or []):
        if not t: continue
        for c,p in PATTERNS.items():
            if p.search(str(t)): cats.add(c)
    return {"enabled":True,"policy":"alert_only","masking_applied":False,"possible_sensitive_data_detected":bool(cats),"detected_categories":sorted(cats)}
