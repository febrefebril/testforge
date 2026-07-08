from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import typer
from typing_extensions import Annotated

from testforge.core.cli.app import app
from testforge.core.healing.models import FAMILIES, TAXONOMIES, HealingEntry
from testforge.core.healing.storage import HealingCatalog

healing_app = typer.Typer(help="Gerenciar catálogo de healing")
app.add_typer(healing_app, name="healing")


def _print_family_taxonomy_help() -> None:
    typer.echo("\nFamílias disponíveis:")
    for key, desc in FAMILIES.items():
        typer.echo(f"  {key:15s} {desc}")
    typer.echo("\nTaxonomias por família:")
    for family, tax_list in TAXONOMIES.items():
        for t in tax_list:
            typer.echo(f"  {family}.{t}")
    typer.echo()


@healing_app.command("add")
def healing_add(
    system: Annotated[
        str,
        typer.Option("--system", "-s", help="Nome do sistema alvo"),
    ],
    symptom: Annotated[
        str,
        typer.Option("--symptom", prompt="Sintoma (o que deu errado)"),
    ],
    root_cause: Annotated[
        str,
        typer.Option("--root-cause", "-r", prompt="Causa raiz"),
    ],
    fix: Annotated[
        str,
        typer.Option("--fix", "-f", prompt="Cura aplicada"),
    ],
    family: Annotated[
        Optional[str],
        typer.Option("--family", help="Família (use '--family help' para listar)"),
    ] = None,
    taxonomy: Annotated[
        Optional[str],
        typer.Option("--taxonomy", help="Taxonomia específica (use '--taxonomy help' para listar)"),
    ] = None,
    fix_type: Annotated[
        Optional[str],
        typer.Option("--fix-type", "-t", help="Tipo da cura, ex: overlay_selector, runner_fallback"),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", "-u", help="URL do sistema"),
    ] = None,
    files_changed: Annotated[
        Optional[str],
        typer.Option("--files", help="Arquivos alterados (separados por vírgula)"),
    ] = None,
    action: Annotated[
        Optional[str],
        typer.Option("--action", "-a", help="Ação que falhou, ex: click, fill"),
    ] = None,
    selector: Annotated[
        Optional[str],
        typer.Option("--selector", help="Seletor que falhou"),
    ] = None,
    tag: Annotated[
        Optional[str],
        typer.Option("--tag", help="Tag do elemento, ex: input"),
    ] = None,
    input_type: Annotated[
        Optional[str],
        typer.Option("--input-type", help="Type do input, ex: radio, checkbox"),
    ] = None,
    notes: Annotated[
        Optional[str],
        typer.Option("--notes", "-n", help="Observações adicionais"),
    ] = None,
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Registrar uma nova entrada no catálogo de healing."""
    if family == "help":
        _print_family_taxonomy_help()
        return
    if taxonomy == "help":
        _print_family_taxonomy_help()
        return

    catalog = HealingCatalog(db)
    entry = HealingEntry(
        system=system,
        symptom=symptom,
        root_cause=root_cause,
        fix=fix,
        family=family or "",
        taxonomy=taxonomy or "",
        fix_type=fix_type or "",
        url=url or "",
        action=action or "",
        selector=selector or "",
        tag=tag or "",
        input_type=input_type or "",
        notes=notes or "",
        files_changed=[f.strip() for f in files_changed.split(",") if f.strip()] if files_changed else [],
    )
    entry_id = catalog.add(entry)
    typer.secho(f"Entrada registrada: {entry_id}", fg=typer.colors.GREEN)


@healing_app.command("list")
def healing_list(
    system: Annotated[
        Optional[str],
        typer.Option("--system", "-s", help="Filtrar por sistema"),
    ] = None,
    family: Annotated[
        Optional[str],
        typer.Option("--family", help="Filtrar por família"),
    ] = None,
    taxonomy: Annotated[
        Optional[str],
        typer.Option("--taxonomy", help="Filtrar por taxonomia"),
    ] = None,
    fix_type: Annotated[
        Optional[str],
        typer.Option("--fix-type", "-t", help="Filtrar por tipo de cura"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Máximo de resultados"),
    ] = 50,
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Listar entradas do catálogo de healing."""
    catalog = HealingCatalog(db)
    entries = catalog.list(system=system, family=family, taxonomy=taxonomy, fix_type=fix_type, limit=limit)
    if not entries:
        typer.secho("Nenhuma entrada encontrada.", fg=typer.colors.YELLOW)
        return
    for e in entries:
        tag_parts = []
        if e.family:
            tag_parts.append(e.family)
        if e.taxonomy:
            tag_parts.append(e.taxonomy)
        tag_str = f" [{'.'.join(tag_parts)}]" if tag_parts else ""
        typer.secho(f"[{e.id}] {e.system}{tag_str}", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"  Sintoma: {e.symptom}")
        typer.echo(f"  Causa:   {e.root_cause}")
        typer.echo(f"  Cura:    {e.fix}")
        typer.echo(f"  Tipo:    {e.fix_type or '-'}  |  Data: {e.created_at[:19]}")
        if e.files_changed:
            typer.echo(f"  Arquivos: {', '.join(e.files_changed)}")
        typer.echo()


@healing_app.command("show")
def healing_show(
    entry_id: Annotated[
        str,
        typer.Argument(help="ID da entrada"),
    ],
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Exibir detalhes de uma entrada."""
    catalog = HealingCatalog(db)
    entry = catalog.get(entry_id)
    if not entry:
        typer.secho("Entrada não encontrada.", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho(f"ID:      {entry.id}", bold=True)
    typer.secho(f"Sistema: {entry.system}", bold=True)
    if entry.family:
        typer.echo(f"Família: {entry.family}")
    if entry.taxonomy:
        typer.echo(f"Taxonomia: {entry.taxonomy}")
    typer.echo(f"URL:     {entry.url or '-'}")
    typer.echo(f"Data:    {entry.created_at[:19]}")
    typer.echo()
    typer.secho("Sintoma:", bold=True)
    typer.echo(f"  {entry.symptom}")
    typer.echo()
    typer.secho("Causa raiz:", bold=True)
    typer.echo(f"  {entry.root_cause}")
    typer.echo()
    typer.secho("Cura:", bold=True)
    typer.echo(f"  {entry.fix}")
    typer.echo(f"  Tipo: {entry.fix_type or '-'}")
    if entry.action:
        typer.echo(f"  Ação: {entry.action}")
    if entry.selector:
        typer.echo(f"  Seletor: {entry.selector}")
    if entry.tag:
        typer.echo(f"  Tag: {entry.tag}")
    if entry.input_type:
        typer.echo(f"  Input type: {entry.input_type}")
    if entry.files_changed:
        typer.echo(f"  Arquivos alterados: {', '.join(entry.files_changed)}")
    if entry.notes:
        typer.echo()
        typer.secho("Observações:", bold=True)
        typer.echo(f"  {entry.notes}")


@healing_app.command("systems")
def healing_systems(
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Listar sistemas catalogados."""
    catalog = HealingCatalog(db)
    systems = catalog.systems()
    if not systems:
        typer.secho("Nenhum sistema catalogado.", fg=typer.colors.YELLOW)
        return
    typer.secho("Sistemas catalogados:", bold=True)
    for s in systems:
        typer.echo(f"  {s}")


@healing_app.command("taxonomy")
def healing_taxonomy(
    family: Annotated[
        Optional[str],
        typer.Argument(help="Filtrar taxonomias de uma família específica"),
    ] = None,
) -> None:
    """Listar famílias e taxonomias disponíveis."""
    if family:
        tax_list = TAXONOMIES.get(family, [])
        desc = FAMILIES.get(family, "")
        typer.secho(f"{family} — {desc}", bold=True)
        for t in tax_list:
            typer.echo(f"  {family}.{t}")
    else:
            _print_family_taxonomy_help()


@healing_app.command("review")
def healing_review(
    stale: Annotated[
        bool,
        typer.Option("--stale", help="Listar entradas stale (90+ dias sem uso)"),
    ] = False,
    duplicates: Annotated[
        bool,
        typer.Option("--duplicates", help="Listar grupos duplicados (mesmo system + symptom)"),
    ] = False,
    unresolved: Annotated[
        bool,
        typer.Option("--unresolved", help="Listar entradas com fix_type=unresolved"),
    ] = False,
    all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Mostrar tudo"),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Máximo por seção"),
    ] = 100,
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Revisar entradas do catálogo: stale, duplicatas, não resolvidas."""
    catalog = HealingCatalog(db)
    now = datetime.now(timezone.utc)
    has_output = False

    if stale or all:
        stale_entries = []
        for entry in catalog.list(limit=limit):
            if not entry.last_used_at:
                continue
            try:
                last = datetime.fromisoformat(entry.last_used_at)
                if (now - last) > timedelta(days=90):
                    stale_entries.append(entry)
            except (ValueError, TypeError):
                continue
        if stale_entries:
            typer.secho("=== Entradas Stale (90+ dias sem uso) ===", bold=True)
            _print_entries_table(stale_entries)
            has_output = True
        else:
            typer.echo("Nenhuma entrada stale encontrada.")
            has_output = True

    if duplicates or all:
        dupes = catalog.find_duplicates()
        if dupes:
            typer.secho("=== Grupos Duplicados ===", bold=True)
            for i, group in enumerate(dupes, 1):
                typer.secho(f"  Grupo {i}:", bold=True)
                _print_entries_table(group)
            has_output = True
        else:
            typer.echo("Nenhum duplicata encontrada.")
            has_output = True

    if unresolved or all:
        unresolved_entries = catalog.list(fix_type="unresolved", limit=limit)
        if unresolved_entries:
            typer.secho("=== Entradas Não Resolvidas ===", bold=True)
            _print_entries_table(unresolved_entries)
            has_output = True

    if not has_output:
        typer.secho("Nenhum resultado. Use --stale, --duplicates, --unresolved ou --all.", fg=typer.colors.YELLOW)


def _print_entries_table(entries: list[HealingEntry]) -> None:
    for e in entries:
        sym_short = e.symptom[:60] + "..." if len(e.symptom) > 60 else e.symptom
        last = e.last_used_at[:10] if e.last_used_at else "-"
        typer.echo(
            f"  [{e.id}] {e.system:<15s} | {sym_short:<50s} | "
            f"{e.fix_type:<12s} | {last:<10s} | falhas:{e.failure_count}"
        )
    typer.echo()


@healing_app.command("merge")
def healing_merge(
    entry_id_1: Annotated[str, typer.Argument(help="ID da primeira entrada")],
    entry_id_2: Annotated[str, typer.Argument(help="ID da segunda entrada")],
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Mesclar duas entradas duplicadas. Mantém a mais recente."""
    catalog = HealingCatalog(db)
    e1 = catalog.get(entry_id_1)
    e2 = catalog.get(entry_id_2)

    if not e1:
        typer.secho(f"Entrada {entry_id_1} não encontrada.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)
    if not e2:
        typer.secho(f"Entrada {entry_id_2} não encontrada.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    key1 = f"{e1.system.lower().strip()}|{re.sub(r'\s+', ' ', e1.symptom.lower().strip())}"
    key2 = f"{e2.system.lower().strip()}|{re.sub(r'\s+', ' ', e2.symptom.lower().strip())}"
    if key1 != key2:
        typer.secho(
            "Entradas não são do mesmo grupo (system + symptom diferentes).",
            err=True, fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    older, newer = (e1, e2) if e1.created_at <= e2.created_at else (e2, e1)

    if not typer.confirm(f"Mesclar {older.id} → {newer.id}?"):
        typer.echo("Cancelado.")
        return

    catalog._backup()
    merged_notes = " | ".join(filter(None, [older.notes, newer.notes]))
    merged_fix = newer.fix or older.fix
    merged_failure_count = older.failure_count + newer.failure_count
    catalog.update(newer.id, fix=merged_fix, notes=merged_notes, failure_count=merged_failure_count)
    catalog.delete(older.id)
    catalog._audit("merge", [entry_id_1, entry_id_2],
                   details=f"{older.id}→{newer.id}")

    typer.secho(f"Mesclado: {older.id} → {newer.id}", fg=typer.colors.GREEN)


@healing_app.command("promote")
def healing_promote(
    entry_id: Annotated[str, typer.Argument(help="ID da entrada")],
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Promover entrada a 'reviewed' (pula Layers 2 e 3)."""
    catalog = HealingCatalog(db)
    entry = catalog.get(entry_id)
    if not entry:
        typer.secho("Entrada não encontrada.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    if not typer.confirm(f"Promover {entry_id} para reviewed?"):
        typer.echo("Cancelado.")
        return

    catalog._backup()
    now = datetime.now(timezone.utc).isoformat()
    catalog.update(entry_id, fix_type="reviewed", last_used_at=now)
    catalog._audit("promote", [entry_id])
    typer.secho(f"Entrada {entry_id} promovida para reviewed.", fg=typer.colors.GREEN)


@healing_app.command("delete")
def healing_delete(
    entry_id: Annotated[str, typer.Argument(help="ID da entrada")],
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Remover uma entrada do catálogo (com backup automático)."""
    catalog = HealingCatalog(db)
    entry = catalog.get(entry_id)
    if not entry:
        typer.secho("Entrada não encontrada.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if not typer.confirm(f"Remover {entry_id}?"):
        typer.echo("Cancelado.")
        return
    catalog._backup()
    if catalog.delete(entry_id):
        catalog._audit("delete", [entry_id])
        typer.secho(f"Entrada {entry_id} removida.", fg=typer.colors.GREEN)
    else:
        typer.secho("Erro ao remover entrada.", fg=typer.colors.RED)
        raise typer.Exit(1)


@healing_app.command("update")
def healing_update(
    entry_id: Annotated[str, typer.Argument(help="ID da entrada")],
    symptom: Annotated[Optional[str], typer.Option("--symptom", help="Novo sintoma")] = None,
    root_cause: Annotated[Optional[str], typer.Option("--root-cause", "-r", help="Nova causa raiz")] = None,
    fix: Annotated[Optional[str], typer.Option("--fix", "-f", help="Nova cura")] = None,
    family: Annotated[Optional[str], typer.Option("--family", help="Nova família")] = None,
    taxonomy: Annotated[Optional[str], typer.Option("--taxonomy", help="Nova taxonomia")] = None,
    fix_type: Annotated[Optional[str], typer.Option("--fix-type", "-t", help="Novo tipo de cura")] = None,
    url: Annotated[Optional[str], typer.Option("--url", "-u", help="Nova URL")] = None,
    notes: Annotated[Optional[str], typer.Option("--notes", "-n", help="Novas observações")] = None,
    db: Annotated[
        str,
        typer.Option("--db", help="Caminho do catálogo JSONL"),
    ] = "./healing-catalog.jsonl",
) -> None:
    """Atualizar campos de uma entrada existente."""
    kwargs = {k: v for k, v in locals().items() if k not in ("entry_id", "db") and v is not None}
    kwargs.pop("kwargs", None)
    catalog = HealingCatalog(db)
    if catalog.update(entry_id, **kwargs):
        typer.secho(f"Entrada {entry_id} atualizada.", fg=typer.colors.GREEN)
    else:
        typer.secho("Entrada não encontrada.", fg=typer.colors.RED)
        raise typer.Exit(1)
