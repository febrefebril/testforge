#!/usr/bin/env python3
"""Consolidar gravacoes/ + testes_semanticos/ em unico documento para analise LLM.

Combina sessoes de navegador gravadas (eventos brutos, etapas, metadados)
com codigo de teste Playwright compilado. Produz saida JSONL ou Markdown
para LLM analisar qualidade de teste, confiabilidade de seletores,
cobertura de healing e fidelidade de compilacao.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


# ── Funcoes de varredura ────────────────────────────────────────


def scan_recordings(recordings_dir: Path) -> list[dict[str, Any]]:
    """Varre subdiretorios de gravacao. Extrai metadados + resumos de eventos/etapas."""
    results: list[dict[str, Any]] = []
    if not recordings_dir.exists():
        return results
    for entry in sorted(recordings_dir.iterdir()):
        if not entry.is_dir():
            continue
        rec = _read_recording(entry)
        if rec:
            results.append(rec)
    return results


def _read_recording(rec_dir: Path) -> dict[str, Any] | None:
    """Le um diretorio de gravacao em dicionario estruturado."""
    entry: dict[str, Any] = {
        "type": "recording",
        "recording_id": rec_dir.name,
    }

    # Metadata
    meta_path = rec_dir / "recording_metadata.json"
    if meta_path.exists():
        entry["metadata"] = json.loads(meta_path.read_text())

    # Raw events
    raw_path = rec_dir / "raw_events.jsonl"
    if raw_path.exists():
        lines = [l for l in raw_path.read_text().strip().splitlines() if l.strip()]
        events = [json.loads(l) for l in lines]
        types: dict[str, int] = {}
        for e in events:
            t = e.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        entry["raw_events"] = {"count": len(events), "by_type": types}

    # Curated steps
    steps_path = rec_dir / "steps.jsonl"
    if steps_path.exists():
        lines = [l for l in steps_path.read_text().strip().splitlines() if l.strip()]
        steps = [json.loads(l) for l in lines]
        actions: dict[str, int] = {}
        for s in steps:
            a = s.get("action", "unknown")
            actions[a] = actions.get(a, 0) + 1
        entry["steps"] = {"count": len(steps), "by_action": actions}

    # Network log
    net_path = rec_dir / "network_log.json"
    if net_path.exists():
        net = json.loads(net_path.read_text())
        entry["network"] = {
            "entries": len(net) if isinstance(net, list) else 1,
        }

    # Asset counts (screenshots, DOM, a11y)
    assets: dict[str, int] = {}
    for sub in ("screenshots", "dom_snapshots", "ax_snapshots"):
        sub_path = rec_dir / sub
        if sub_path.exists():
            assets[sub] = len(list(sub_path.iterdir()))
    if assets:
        entry["assets"] = assets

    return entry


def scan_semantic_tests(semantic_dir: Path) -> list[dict[str, Any]]:
    """Varre subdiretorios de teste semantico. Extrai codigo compilado + dados."""
    results: list[dict[str, Any]] = []
    if not semantic_dir.exists():
        return results
    for entry in sorted(semantic_dir.iterdir()):
        if not entry.is_dir():
            continue
        st = _read_semantic_test(entry)
        if st:
            results.append(st)
    return results


def _read_semantic_test(st_dir: Path) -> dict[str, Any] | None:
    """Le um diretorio de teste semantico."""
    entry: dict[str, Any] = {
        "type": "semantic_test",
        "test_id": st_dir.name,
    }

    for f in sorted(st_dir.iterdir()):
        if f.name.startswith("test_") and f.suffix == ".py":
            entry["test_file"] = f.name
            entry["test_code"] = f.read_text()
        elif f.name == "test_data.json":
            entry["test_data"] = json.loads(f.read_text())

    return entry if "test_code" in entry else None


# ── Pareamento ──────────────────────────────────────────────────


def _normalize(name: str) -> str:
    """Normaliza um ID de gravacao/teste-semantico para correspondencia."""
    if name.lower().startswith("st-"):
        name = name[3:]
    return name.lower().replace("-", "_").replace(" ", "_")


def pair_artifacts(
    recordings: list[dict[str, Any]],
    semantic_tests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pareia gravacoes com testes semanticos por correspondencia fuzzy.

    Estrategia: normalizar IDs (remover prefixo ST-, minusculo, substituir hifens/espacos).
    Gravacoes sem teste semantico correspondente recebem `semantic_test: null`.
    Testes semanticos nao pareados recebem `recording: null`.
    """
    pairs: list[dict[str, Any]] = []

    # Build lookup: normalized name → semantic test
    st_lookup: dict[str, dict[str, Any]] = {}
    for st in semantic_tests:
        key = _normalize(st["test_id"])
        st_lookup[key] = st

    matched_st_keys: set[str] = set()

    for rec in recordings:
        key = _normalize(rec["recording_id"])
        pair: dict[str, Any] = {"recording": rec}
        if key in st_lookup:
            pair["semantic_test"] = st_lookup[key]
            matched_st_keys.add(key)
        else:
            pair["semantic_test"] = None
        pairs.append(pair)

    # Add unmatched semantic tests
    for st in semantic_tests:
        key = _normalize(st["test_id"])
        if key not in matched_st_keys:
            pairs.append({"recording": None, "semantic_test": st})

    return pairs


# ── Saida ───────────────────────────────────────────────────────


def output_jsonl(artifacts: list[dict[str, Any]], output_path: Path) -> None:
    """Escreve artefatos como JSONL (um objeto JSON por linha)."""
    with output_path.open("w", encoding="utf-8") as f:
        for obj in artifacts:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def output_markdown(artifacts: list[dict[str, Any]], output_path: Path) -> None:
    """Escreve artefatos como relatorio Markdown legivel."""
    lines: list[str] = [
        "# TestForge Artefatos Consolidados",
        "",
        f"> Gerado a partir de `recordings/` + `semantic_tests/`",
        "",
    ]

    rec_count = sum(1 for a in artifacts if a.get("recording"))
    st_count = sum(1 for a in artifacts if a.get("semantic_test"))
    paired = sum(
        1 for a in artifacts if a.get("recording") and a.get("semantic_test")
    )

    lines.append(f"- **Gravacoes:** {rec_count}")
    lines.append(f"- **Testes Semanticos:** {st_count}")
    lines.append(f"- **Pareados:** {paired}")
    lines.append("")

    for i, art in enumerate(artifacts, 1):
        rec = art.get("recording")
        st = art.get("semantic_test")

        heading = f"## {i}. "
        if rec:
            heading += f"Recording `{rec['recording_id']}`"
        if rec and st:
            heading += " + "
        if st:
            heading += f"Semantic Test `{st['test_id']}`"
        lines.append(heading)
        lines.append("")

        # Recording section
        if rec:
            meta = rec.get("metadata", {})
            lines.append(f"### [LISTA] Gravacao: `{rec['recording_id']}`")
            lines.append("")
            lines.append(f"| Campo | Valor |")
            lines.append(f"|---|---|")
            lines.append(f"| Aplicacao | {meta.get('application', '—')} |")
            lines.append(f"| URL Base | {meta.get('base_url', '—')} |")
            lines.append(f"| Status | {meta.get('status', '—')} |")
            lines.append(
                f"| Iniciado | {str(meta.get('started_at', '—'))[:19]} |"
            )
            lines.append("")

            if raw := rec.get("raw_events"):
                lines.append(f"- **Eventos Brutos:** {raw['count']}  ")
                lines.append(f"  `{json.dumps(raw.get('by_type', {}))}`")
            if steps := rec.get("steps"):
                lines.append(f"- **Etapas:** {steps['count']}  ")
                lines.append(f"  `{json.dumps(steps.get('by_action', {}))}`")
            if net := rec.get("network"):
                lines.append(f"- **Rede:** {net['entries']} entradas")
            if assets := rec.get("assets"):
                parts = [f"{k}={v}" for k, v in assets.items()]
                lines.append(f"- **Recursos:** {', '.join(parts)}")
            lines.append("")

        # Semantic test section
        if st:
            lines.append(f"### [TESTE] Teste Semantico: `{st['test_id']}`")
            lines.append(f"- **Arquivo de Teste:** `{st.get('test_file', '—')}`")
            lines.append("")
            if "test_data" in st:
                lines.append("**Dados de Teste:**")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(st["test_data"], ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
            if "test_code" in st:
                lines.append("**Codigo de Teste:**")
                lines.append("")
                lines.append("```python")
                lines.append(st["test_code"].rstrip())
                lines.append("```")
                lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ─────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Consolidar gravacoes + testes_semanticos para analise LLM",
    )
    parser.add_argument(
        "--recordings-dir",
        default="recordings",
        help="Caminho do diretorio de gravacoes (padrao: recordings/)",
    )
    parser.add_argument(
        "--semantic-dir",
        default="semantic_tests",
        help="Caminho do diretorio de testes_semanticos (padrao: semantic_tests/)",
    )
    parser.add_argument(
        "--output", "-o",
        default="consolidated_artifacts.jsonl",
        help="Caminho do arquivo de saida (padrao: consolidated_artifacts.jsonl)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=("jsonl", "markdown"),
        default="jsonl",
        help="Formato de saida (padrao: jsonl)",
    )
    args = parser.parse_args(argv)

    rec_dir = Path(args.recordings_dir)
    sem_dir = Path(args.semantic_dir)
    out_path = Path(args.output)

    recordings = scan_recordings(rec_dir)
    semantic_tests = scan_semantic_tests(sem_dir)
    artifacts = pair_artifacts(recordings, semantic_tests)

    if args.format == "markdown":
        output_markdown(artifacts, out_path)
    else:
        output_jsonl(artifacts, out_path)

    print(
        f"Consolidado {len(recordings)} gravacoes + "
        f"{len(semantic_tests)} testes semanticos → "
        f"{len(artifacts)} artefatos"
    )
    print(f"Saida: {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
