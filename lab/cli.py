"""Typer CLI for LLM Resonance Lab V1.

Subcommands:
    run                  Batch runner (A 组: isolated sessions). Default if no subcommand.
    blind <case_id>      Generate a blind comparison packet.
    eval <case_id>       Generate the human evaluation template.
    journal {new,note}   Resonance journal helpers.
    marathon <scenario>  Marathon runner (B 组: continuous session).
    models               List configured models + API key status.
    cases                List cases with category / tags.

Global flags (apply to `run` and `marathon`):
    --mock               Use canned responses (no API key required).
    --mock-file PATH     YAML file with {model_name: response_text} overrides.
    --date YYYY-MM-DD    Results folder date. Defaults to today.
    --model NAME [...]   Restrict to specific models.
    --cases ID [...]     Restrict to specific cases.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from lab import __version__
from lab.batch_runner import run_batch
from lab.blind import generate_blind
from lab.case_loader import Case, CaseFormatError, load_all_cases
from lab.config import DEFAULT_DATE_FORMAT, Paths
from lab.console import console, error, info, success, warning
from lab.evaluation import generate_evaluation
from lab.journal import append_journal_note, create_journal_entry
from lab.marathon_runner import run_marathon
from lab.model_registry import (
    ModelEntry,
    ModelRegistryError,
    load_models,
    resolve_api_key,
)

app = typer.Typer(
    name="resonance-lab",
    help="LLM Resonance Lab V1 — discover which LLM resonates with you.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)

journal_app = typer.Typer(help="Create or append to today's resonance journal.")
app.add_typer(journal_app, name="journal")


def _resolve_repo_root() -> Path:
    """The repository root is the parent of the `lab/` package directory."""
    return Path(__file__).resolve().parent.parent


def _get_paths() -> Paths:
    return Paths.from_root(_resolve_repo_root())


def _resolve_date(date_str: Optional[str]) -> str:
    if date_str is None:
        return datetime.now().strftime(DEFAULT_DATE_FORMAT)
    return date_str


def _load_models_or_exit(paths: Paths) -> list[ModelEntry]:
    try:
        models = load_models(paths.models_yaml)
    except ModelRegistryError as exc:
        error(str(exc))
        raise typer.Exit(code=1)
    if not models:
        error(f"No models defined in {paths.models_yaml}.")
        raise typer.Exit(code=1)
    return models


def _load_cases_or_exit(paths: Paths, case_ids: list[str] | None = None) -> list[Case]:
    try:
        cases = load_all_cases(paths.cases)
    except CaseFormatError as exc:
        error(str(exc))
        raise typer.Exit(code=1)
    if not cases:
        error(f"No cases found in {paths.cases}.")
        raise typer.Exit(code=1)
    if case_ids:
        wanted = set(case_ids)
        filtered = [c for c in cases if c.id in wanted]
        missing = wanted - {c.id for c in filtered}
        if missing:
            error(f"Cases not found: {sorted(missing)}")
            raise typer.Exit(code=1)
        return filtered
    return cases


def _filter_models(
    models: list[ModelEntry], names: list[str] | None
) -> list[ModelEntry]:
    if not names:
        return models
    by_name = {m.name: m for m in models}
    missing = [n for n in names if n not in by_name]
    if missing:
        error(f"Models not found: {missing}. Available: {list(by_name)}")
        raise typer.Exit(code=1)
    return [by_name[n] for n in names]


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", help="Print the version and exit."
    ),
) -> None:
    if version:
        console.print(f"LLM Resonance Lab V{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        # Default behavior: run the batch runner.
        ctx.invoke(run_cmd)


@app.command(name="run")
def run_cmd(
    mock: bool = typer.Option(False, "--mock", help="Use canned responses."),
    mock_file: Optional[Path] = typer.Option(
        None, "--mock-file", help="YAML file of mock responses."
    ),
    date: Optional[str] = typer.Option(
        None, "--date", help="Results folder date (default: today)."
    ),
    model: list[str] = typer.Option(
        None, "--model", help="Restrict to specific models (repeatable)."
    ),
    cases_: list[str] = typer.Option(
        None, "--cases", help="Restrict to specific case IDs (repeatable)."
    ),
) -> None:
    """A 组: run every (case × model) pair in fresh sessions."""
    paths = _get_paths()
    day = _resolve_date(date)
    models = _filter_models(_load_models_or_exit(paths), model or None)
    cases = _load_cases_or_exit(paths, cases_ or None)

    out_dir = paths.results / day
    mock_responses = None
    if mock_file is not None and not mock:
        warning("--mock-file given without --mock; ignoring it.")

    summary = run_batch(
        cases,
        models,
        out_dir=out_dir,
        mock=mock,
        mock_responses=mock_responses,
        mock_responses_file=mock_file if mock else None,
    )
    success(
        f"Batch done. cases_run={summary.cases_run}, skipped={summary.skipped}. "
        f"Output: {out_dir}"
    )


@app.command(name="blind")
def blind_cmd(
    case_id: str = typer.Argument(..., help="Case ID, e.g. case_001."),
    models: list[str] = typer.Option(
        None, "--model", help="Pick exactly two models (repeatable)."
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", help="Random seed for reproducible A/B assignment."
    ),
    date: Optional[str] = typer.Option(None, "--date"),
) -> None:
    """Generate a blind comparison packet for one case."""
    paths = _get_paths()
    day = _resolve_date(date)
    results_dir = paths.results / day
    model_pair: tuple[str, str] | None = None
    if models:
        if len(models) != 2:
            error("`blind --model` requires exactly two model names.")
            raise typer.Exit(code=1)
        model_pair = (models[0], models[1])
    out = generate_blind(
        results_dir,
        case_id,
        blind_root=paths.blind,
        date=day,
        models=model_pair,
        seed=seed,
    )
    success(f"Blind packet written to {out}")


@app.command(name="eval")
def eval_cmd(
    case_id: str = typer.Argument(..., help="Case ID, e.g. case_001."),
    date: Optional[str] = typer.Option(None, "--date"),
) -> None:
    """Generate the human evaluation template for a case."""
    paths = _get_paths()
    day = _resolve_date(date)
    cases = _load_cases_or_exit(paths, [case_id])
    case = cases[0]
    blind_dir = paths.blind / case_id
    out = generate_evaluation(
        case, blind_dir, out_dir=paths.evaluation, date=day
    )
    success(f"Evaluation template written to {out}")


@journal_app.command("new")
def journal_new_cmd(
    date: Optional[str] = typer.Option(None, "--date"),
) -> None:
    """Create today's journal entry (or open it if it already exists)."""
    paths = _get_paths()
    day = _resolve_date(date)
    path = create_journal_entry(journal_root=paths.journal, date=day)
    success(f"Journal entry ready: {path}")


@journal_app.command("note")
def journal_note_cmd(
    text: str = typer.Argument(..., help="Note text to append."),
    date: Optional[str] = typer.Option(None, "--date"),
) -> None:
    """Append a note to today's journal."""
    paths = _get_paths()
    path = append_journal_note(text, journal_root=paths.journal, date=_resolve_date(date))
    success(f"Note appended to {path}")


@app.command(name="marathon")
def marathon_cmd(
    scenario: str = typer.Argument(..., help="Marathon scenario name, e.g. career_choice."),
    model: str = typer.Option(..., "--model", help="Model name (required)."),
    mock: bool = typer.Option(False, "--mock"),
    mock_file: Optional[Path] = typer.Option(None, "--mock-file"),
    date: Optional[str] = typer.Option(None, "--date"),
) -> None:
    """B 组: run a marathon scenario with one model in a continuous session."""
    paths = _get_paths()
    day = _resolve_date(date)
    models = _filter_models(_load_models_or_exit(paths), [model])
    out_dir = paths.results / day
    summary = run_marathon(
        scenario,
        models[0],
        marathons_dir=paths.marathons,
        out_dir=out_dir,
        mock=mock,
        mock_responses_file=mock_file if mock else None,
    )
    success(
        f"Marathon done. turns_run={summary.turns_run}, model={summary.model}. "
        f"Output: {out_dir}/marathon_{summary.scenario}_{summary.model}"
    )


@app.command(name="models")
def models_cmd() -> None:
    """List configured models and their API key status."""
    paths = _get_paths()
    try:
        models = load_models(paths.models_yaml)
    except ModelRegistryError as exc:
        error(str(exc))
        raise typer.Exit(code=1)
    if not models:
        info("No models configured.")
        raise typer.Exit()

    table = Table(title="Configured Models")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("API Key Env", style="yellow")
    table.add_column("Status", style="green")
    for m in models:
        key = resolve_api_key(m)
        status = "[green]set[/green]" if key else "[red]missing[/red]"
        table.add_row(m.name, m.provider, m.api_key_env, status)
    console.print(table)


@app.command(name="cases")
def cases_cmd() -> None:
    """List all available cases."""
    paths = _get_paths()
    try:
        cases = load_all_cases(paths.cases)
    except CaseFormatError as exc:
        error(str(exc))
        raise typer.Exit(code=1)
    if not cases:
        info(f"No cases found in {paths.cases}.")
        raise typer.Exit()

    table = Table(title=f"Cases ({len(cases)})")
    table.add_column("ID", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Tags", style="yellow")
    table.add_column("Description", style="white")
    for c in cases:
        table.add_row(c.id, c.category, ", ".join(c.tags), c.description or "—")
    console.print(table)
