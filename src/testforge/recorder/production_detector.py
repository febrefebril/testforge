"""Alerta quando URL parece ser ambiente de PRODUCAO.

Contrato: NAO bloqueia. So alerta o usuario. Se ele quiser gravar em producao,
gravacao segue normalmente — massa de teste continua indo pro repo LOCAL
da rede interna, nunca pro GitHub publico.
"""
import re
from urllib.parse import urlparse

# Padroes conhecidos de producao (customize com o dominio real da sua organizacao)
_PROD_PATTERNS = [
    re.compile(r"^([a-z0-9-]+\.)*banco\.example\.com$", re.I),
]

# Sufixos que indicam ambientes de teste — se URL contem, NAO e producao
_TESTING_SUFFIXES = [
    "-des", "-tqs", "-hom", "-dev", "-uat", "-stg", "nprd", ".local", "localhost",
]


def is_production(url: str) -> bool:
    """Retorna True se URL parece producao sem sufixo de ambiente teste."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    if any(sfx in host for sfx in _TESTING_SUFFIXES):
        return False
    return any(p.match(host) for p in _PROD_PATTERNS)


def alert_if_production(url: str) -> None:
    """Emite alerta stdout se URL parece producao. Nao bloqueia."""
    if not is_production(url):
        return
    print(f"\n[TestForge] AVISO: URL '{url}' parece ambiente de PRODUCAO.")
    print(f"  Gravacao prossegue normalmente — dados capturados sao massa de teste.")
    print(f"  Massa vai para o REPO LOCAL da rede interna. GitHub publico nao recebe massa.")
    print(f"  Continue apenas se estiver ciente de que esta gravando em producao.\n")
