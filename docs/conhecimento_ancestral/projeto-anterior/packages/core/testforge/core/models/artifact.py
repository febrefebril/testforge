from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArtifactPaths:
    output_dir: str = ""
    script_path: str = ""
    data_path: str = ""
    config_path: str = ""
    testforge_dir: str = ""
    reports_dir: str = ""
    traces_dir: str = ""
    curation_dir: str = ""
    evidence_dir: str = ""
