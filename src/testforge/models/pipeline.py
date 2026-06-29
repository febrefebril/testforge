"""TestForge — Estágios de pipeline, manifesto, e inspetor.

Documenta e introspecta o pipeline de transformação de dados de quatro estágios:

Estágio 1: raw_events (captura)
    Fonte: Listeners de eventos do navegador injetados por RecorderController.
    Formato: raw_events.jsonl — um objeto JSON por linha.
    Conteúdo: RawRecordedEvent (click, fill, navegação, submit, postback).
    Propósito: Captura sem perdas de toda interação do navegador.

Estágio 2: steps (curado)
    Fonte: Ações iniciadas pelo usuário (clicks, asserts via Shift+A).
    Formato: steps.jsonl — um objeto JSON por passo curado.
    Conteúdo: Ações pretendidas pelo usuário com seletores de alvo explícitos.
    Propósito: Passos de teste curados por humano com decisões de assertion.

Estágio 3: semantic_steps (compilado)
    Fonte: RecordingNormalizer transforma raw_events + steps em SemanticTestCase.
    Formato: semantic_steps.jsonl — cabeçalho de metadados + um passo por linha.
    Conteúdo: SemanticAction com candidatos de localizador, skip_reason, contexto.
    Propósito: Trilha de auditoria legível por máquina de cada passo compilado.

Estágio 4: script (executável)
    Fonte: PlaywrightCompiler gera a partir de SemanticTestCase.
    Formato: test_<id>.py — arquivo Python usando playwright.sync_api.
    Conteúdo: Teste Playwright executável com loops de seletor fallback.
    Propósito: Teste executável que reproduz o fluxo de usuário gravado.

Fluxo de Dados:
    Navegador → raw_events.jsonl + steps.jsonl → RecordingNormalizer
    → SemanticTestCase → PlaywrightCompiler → test_*.py + semantic_steps.jsonl
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PipelineStage(Enum):
    """Os quatro estágios do pipeline de transformação de dados TestForge.

    Cada estágio representa um artefato distinto no fluxo gravação→execução.
    """

    RAW_EVENTS = "raw_events"
    STEPS = "steps"
    SEMANTIC_STEPS = "semantic_steps"
    SCRIPT = "script"

    @property
    def label(self) -> str:
        """Nome legível por humano do estágio."""
        labels = {
            PipelineStage.RAW_EVENTS: "Eventos Brutos",
            PipelineStage.STEPS: "Passos Curados",
            PipelineStage.SEMANTIC_STEPS: "Passos Semânticos",
            PipelineStage.SCRIPT: "Script Executável",
        }
        return labels[self]

    @property
    def stage_type(self) -> str:
        """Classificação de estágio: captura, curado, compilado, ou executável."""
        types = {
            PipelineStage.RAW_EVENTS: "capture",
            PipelineStage.STEPS: "curated",
            PipelineStage.SEMANTIC_STEPS: "compiled",
            PipelineStage.SCRIPT: "executable",
        }
        return types[self]

    @property
    def file_name(self) -> str:
        """Nome de arquivo padrão para artefato deste estágio."""
        names = {
            PipelineStage.RAW_EVENTS: "raw_events.jsonl",
            PipelineStage.STEPS: "steps.jsonl",
            PipelineStage.SEMANTIC_STEPS: "semantic_steps.jsonl",
            PipelineStage.SCRIPT: None,  # Script name varies by test_id
        }
        return names[self]

    @property
    def description(self) -> str:
        """Descricao detalhada deste estagio do pipeline."""
        descriptions = {
            PipelineStage.RAW_EVENTS: (
                "Eventos do navegador capturados por listeners JS injetados. "
                "Cada click, fill, navegacao, submit e postback e registrado "
                "com informacao completa do alvo (tag, text, role, accessible_name, bounding_box, "
                "class_list, aria_attrs, data_attrs). Armazenado como JSONL para escritas append-only."
            ),
            PipelineStage.STEPS: (
                "Passos de teste curados pelo usuario capturados via atalhos de teclado (Shift+A para asserts) "
                "ou gravacao explicita de passos. Inclui tipo de assertion (textual, estado, visivel, "
                "automatico), valores esperados e seletores de elemento explicitos. "
                "Campos opcionais: blocking, depends_on para cadeias de dependencia."
            ),
            PipelineStage.SEMANTIC_STEPS: (
                "Representacao intermediaria compilada produzida pelo RecordingNormalizer. "
                "Cada passo e um SemanticAction com LocatorCandidates ranqueados, "
                "flags skip_reason para passos nao viaveis/duplicados, "
                "e metadados de cadeia de dependencia (blocking, depends_on). "
                "Serve como trilha de auditoria e artefato de debugging."
            ),
            PipelineStage.SCRIPT: (
                "Script Python Playwright executavel final gerado pelo PlaywrightCompiler. "
                "Contem loops de seletor fallback para auto-healing, "
                "suporte a teste data-driven via fixtures JSON externas, "
                "e wrappers expect_navigation para submissao de formularios. "
                "Pronto para executar com pytest + pytest-playwright."
            ),
        }
        return descriptions[self]

    @property
    def consumes(self) -> list["PipelineStage"]:
        """Quais estagios upstream este estagio depende."""
        upstream = {
            PipelineStage.RAW_EVENTS: [],
            PipelineStage.STEPS: [],
            PipelineStage.SEMANTIC_STEPS: [PipelineStage.RAW_EVENTS, PipelineStage.STEPS],
            PipelineStage.SCRIPT: [PipelineStage.SEMANTIC_STEPS],
        }
        return upstream[self]

    @property
    def produces(self) -> list["PipelineStage"]:
        """Quais estagios downstream consomem a saida deste estagio."""
        downstream = {
            PipelineStage.RAW_EVENTS: [PipelineStage.SEMANTIC_STEPS],
            PipelineStage.STEPS: [PipelineStage.SEMANTIC_STEPS],
            PipelineStage.SEMANTIC_STEPS: [PipelineStage.SCRIPT],
            PipelineStage.SCRIPT: [],
        }
        return downstream[self]


@dataclass
class PipelineManifest:
    """Rastreia existencia e caminhos dos quatro arquivos de estagio do pipeline.

    Usado para descobrir quais estagios foram executados para um dado diretorio de gravacao.
    """

    recording_dir: str
    raw_events_path: str = ""
    steps_path: str = ""
    semantic_steps_path: str = ""
    script_path: str = ""

    def __post_init__(self):
        self.refresh()

    def refresh(self) -> None:
        """Escaneia diretorio de gravacao e atualiza caminhos para arquivos de estagio encontrados."""
        if not os.path.isdir(self.recording_dir):
            return

        raw_events = os.path.join(self.recording_dir, "raw_events.jsonl")
        if os.path.isfile(raw_events):
            self.raw_events_path = raw_events

        steps = os.path.join(self.recording_dir, "steps.jsonl")
        if os.path.isfile(steps):
            self.steps_path = steps

        semantic_steps = os.path.join(self.recording_dir, "semantic_steps.jsonl")
        if os.path.isfile(semantic_steps):
            self.semantic_steps_path = semantic_steps

        # Arquivos de script seguem padrao test_*.py
        for entry in os.listdir(self.recording_dir):
            if entry.startswith("test_") and entry.endswith(".py"):
                self.script_path = os.path.join(self.recording_dir, entry)
                break

    @property
    def stages_present(self) -> list[PipelineStage]:
        """Retorna lista de estagios cujos artefatos estao presentes."""
        present: list[PipelineStage] = []
        if self.raw_events_path:
            present.append(PipelineStage.RAW_EVENTS)
        if self.steps_path:
            present.append(PipelineStage.STEPS)
        if self.semantic_steps_path:
            present.append(PipelineStage.SEMANTIC_STEPS)
        if self.script_path:
            present.append(PipelineStage.SCRIPT)
        return present

    @property
    def stages_missing(self) -> list[PipelineStage]:
        """Retorna lista de estagios cujos artefatos estao ausentes."""
        present_set = set(self.stages_present)
        return [s for s in PipelineStage if s not in present_set]

    @property
    def is_complete(self) -> bool:
        """True se todos os quatro estagios estao presentes."""
        return len(self.stages_present) == 4

    @property
    def pipeline_depth(self) -> int:
        """Quantos estagios de profundidade o pipeline progrediu (0-4)."""
        return len(self.stages_present)

    def stage_path(self, stage: PipelineStage) -> Optional[str]:
        """Obtem caminho do arquivo para um estagio especifico, ou None se ausente."""
        mapping = {
            PipelineStage.RAW_EVENTS: self.raw_events_path,
            PipelineStage.STEPS: self.steps_path,
            PipelineStage.SEMANTIC_STEPS: self.semantic_steps_path,
            PipelineStage.SCRIPT: self.script_path,
        }
        path = mapping.get(stage, "")
        return path if path else None

    def to_dict(self) -> dict:
        """Serializa manifesto para dicionario."""
        return {
            "recording_dir": self.recording_dir,
            "stages_present": [s.value for s in self.stages_present],
            "stages_missing": [s.value for s in self.stages_missing],
            "is_complete": self.is_complete,
            "pipeline_depth": self.pipeline_depth,
            "paths": {
                "raw_events": self.raw_events_path or None,
                "steps": self.steps_path or None,
                "semantic_steps": self.semantic_steps_path or None,
                "script": self.script_path or None,
            },
        }


class PipelineInspector:
    """Faz introspeccao de arquivos de estagio do pipeline e extrai estatisticas.

    Le o arquivo de artefato de cada estagio e produz um resumo do conteudo.
    Util para debugging, auditoria e verificacao em CI.
    """

    @staticmethod
    def inspect_raw_events(file_path: str) -> dict:
        """Inspeciona um arquivo raw_events.jsonl.

        Retorna dict com event_count, histograma event_types e metadados.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        events = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        type_counts: dict[str, int] = {}
        urls: set[str] = set()
        has_screenshots = False
        has_dom_snapshots = False

        for evt in events:
            etype = evt.get("type", "unknown")
            type_counts[etype] = type_counts.get(etype, 0) + 1
            if evt.get("url"):
                urls.add(evt["url"])
            if evt.get("screenshot"):
                has_screenshots = True
            if evt.get("dom_snapshot"):
                has_dom_snapshots = True

        return {
            "stage": PipelineStage.RAW_EVENTS.value,
            "file": file_path,
            "event_count": len(events),
            "event_types": type_counts,
            "unique_urls": sorted(urls),
            "has_screenshots": has_screenshots,
            "has_dom_snapshots": has_dom_snapshots,
        }

    @staticmethod
    def inspect_steps(file_path: str) -> dict:
        """Inspeciona um arquivo steps.jsonl.

        Retorna dict com step_count, histograma de acoes, assert_types presentes.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        steps = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    steps.append(json.loads(line))

        action_counts: dict[str, int] = {}
        assert_types: list[str] = []
        has_blocking = False
        has_dependencies = False

        for step in steps:
            action = step.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            if action == "assert" and step.get("assert_type"):
                atype = step["assert_type"]
                if atype not in assert_types:
                    assert_types.append(atype)
            if step.get("blocking"):
                has_blocking = True
            if step.get("depends_on"):
                has_dependencies = True

        return {
            "stage": PipelineStage.STEPS.value,
            "file": file_path,
            "step_count": len(steps),
            "actions": action_counts,
            "assert_types": assert_types,
            "has_blocking_steps": has_blocking,
            "has_dependency_chains": has_dependencies,
        }

    @staticmethod
    def inspect_semantic_steps(file_path: str) -> dict:
        """Inspeciona um arquivo semantic_steps.jsonl.

        Retorna dict com step_count, detalhamento skip_reason, histograma de acoes.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        lines = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))

        metadata = {}
        steps = []
        for obj in lines:
            if obj.get("type") == "metadata":
                metadata = obj
            else:
                steps.append(obj)

        action_counts: dict[str, int] = {}
        skip_reasons: dict[str, int] = {}
        total_candidates = 0

        for step in steps:
            action = step.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            if step.get("skip_reason"):
                reason = step["skip_reason"]
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            if step.get("target") and step["target"].get("candidates"):
                total_candidates += len(step["target"]["candidates"])

        return {
            "stage": PipelineStage.SEMANTIC_STEPS.value,
            "file": file_path,
            "metadata": metadata,
            "step_count": len(steps),
            "actions": action_counts,
            "skip_reasons": skip_reasons,
            "total_locator_candidates": total_candidates,
        }

    @staticmethod
    def inspect_script(file_path: str) -> dict:
        """Inspeciona um script test_*.py gerado.

        Retorna dict com contagem de linhas, function_name, passos de teste encontrados.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path) as f:
            content = f.read()

        lines = content.split("\n")
        step_count = 0
        function_name = ""
        has_data_driven = "DATA_FILE" in content or "_data" in content
        has_fallback = "for _sel in _sels:" in content

        for line in lines:
            if line.startswith("def test_"):
                function_name = line.split("(")[0].replace("def ", "").strip()
            if line.strip().startswith("# Step "):
                step_count += 1

        return {
            "stage": PipelineStage.SCRIPT.value,
            "file": file_path,
            "line_count": len(lines),
            "function_name": function_name,
            "test_steps": step_count,
            "has_data_driven_support": has_data_driven,
            "has_fallback_loops": has_fallback,
        }

    @classmethod
    def inspect_stage(cls, stage: PipelineStage, file_path: str) -> dict:
        """Auto-despacho para inspector correto baseado no tipo de estagio.

        Args:
            stage: Membro do enum PipelineStage.
            file_path: Caminho para o arquivo de artefato do estagio.

        Returns:
            Dict com resultados da inspecao do estagio.
        """
        inspectors = {
            PipelineStage.RAW_EVENTS: cls.inspect_raw_events,
            PipelineStage.STEPS: cls.inspect_steps,
            PipelineStage.SEMANTIC_STEPS: cls.inspect_semantic_steps,
            PipelineStage.SCRIPT: cls.inspect_script,
        }
        inspect_fn = inspectors.get(stage)
        if not inspect_fn:
            raise ValueError(f"No inspector for stage: {stage}")
        return inspect_fn(file_path)

    @classmethod
    def inspect_directory(cls, recording_dir: str) -> dict[str, dict]:
        """Inspeciona um diretorio de gravacao e relata todos os estagios encontrados.

        Args:
            recording_dir: Caminho para um diretorio de sessao de gravacao.

        Returns:
            Dict mapeando valor do estagio para resultados de inspecao (estagios ausentes omitidos).
        """
        manifest = PipelineManifest(recording_dir)
        results: dict[str, dict] = {}

        for stage in PipelineStage:
            path = manifest.stage_path(stage)
            if path:
                try:
                    results[stage.value] = cls.inspect_stage(stage, path)
                except Exception as exc:
                    results[stage.value] = {"error": str(exc)}

        return results
