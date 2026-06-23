"""Batch runner — A 组: each case runs in a brand-new session.

Hard constraint (guarded by tests/test_design_guards.py):
  - `run_batch` MUST NOT accept a `messages` parameter.
  - Every (case, model) pair gets a fresh `messages` list, allocated inside
    the inner loop. The list goes out of scope as soon as `complete()` returns.

This module's purpose is the OPPOSITE of marathon_runner: maximum isolation
between cases. The two runners must never be merged.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from lab.case_loader import Case
from lab.console import error, warning
from lab.llm_adapter import (
    CompletionResult,
    MissingAPIKeyError,
    complete,
)
from lab.model_registry import ModelEntry


@dataclass
class BatchSummary:
    cases_run: int = 0
    models_run: int = 0
    failures: int = 0
    skipped: int = 0
    failed_pairs: list[tuple[str, str]] = field(default_factory=list)  # (case_id, model_name)


def _format_response_file(
    case: Case,
    model: ModelEntry,
    response_text: str,
    timestamp: str,
) -> str:
    """Build a Markdown file with YAML frontmatter + response body."""
    meta = {
        "case_id": case.id,
        "model": model.name,
        "provider": model.provider,
        "category": case.category,
        "tags": case.tags,
        "timestamp": timestamp,
        "prompt": case.body.rstrip(),
    }
    frontmatter = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{frontmatter}\n---\n\n{response_text}\n"


def _run_single(
    case: Case,
    model: ModelEntry,
    *,
    mock: bool,
    mock_responses: dict[str, str] | None,
    mock_responses_file: Path | None,
) -> CompletionResult | None:
    """Run one (case, model) pair with a fresh messages list.

    Returns None if the call should be skipped (e.g. missing key outside mock).
    """
    # ↓↓↓ THIS LIST IS BRAND-NEW FOR EVERY (case, model) PAIR — DO NOT REUSE ↓↓↓
    messages: list[dict[str, str]] = [{"role": "user", "content": case.body}]
    try:
        return complete(
            model,
            messages,
            mock=mock,
            mock_responses=mock_responses,
            mock_responses_file=mock_responses_file,
        )
    except MissingAPIKeyError as exc:
        warning(str(exc))
        return None
    except Exception as exc:  # noqa: BLE001 - retry once then give up
        warning(f"{model.name} on {case.id} failed: {exc}. Retrying once...")
        time.sleep(2)
        try:
            return complete(
                model,
                messages,
                mock=mock,
                mock_responses=mock_responses,
                mock_responses_file=mock_responses_file,
            )
        except Exception as exc2:  # noqa: BLE001
            error(f"{model.name} on {case.id} failed twice: {exc2}")
            return None


def run_batch(
    cases: list[Case],
    models: list[ModelEntry],
    *,
    out_dir: Path,
    mock: bool = False,
    mock_responses: dict[str, str] | None = None,
    mock_responses_file: Path | None = None,
) -> BatchSummary:
    """Run every case against every model, writing results to `out_dir`.

    The output layout is:
        out_dir/
          case_001/
            <model_name>.md
          case_002/
            <model_name>.md
          ...
    where `out_dir` is normally `results/YYYY-MM-DD/`.
    """
    summary = BatchSummary()
    if not cases:
        warning("No cases to run.")
        return summary
    if not models:
        warning("No models configured. Edit models.yaml to add at least one model.")
        return summary

    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    total = len(cases) * len(models)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Batch run (A 组)", total=total)
        for case in cases:
            case_dir = out_dir / case.id
            for model in models:
                progress.update(task, description=f"A 组: {case.id} × {model.name}")
                result = _run_single(
                    case,
                    model,
                    mock=mock,
                    mock_responses=mock_responses,
                    mock_responses_file=mock_responses_file,
                )
                if result is None:
                    summary.skipped += 1
                    summary.failed_pairs.append((case.id, model.name))
                else:
                    case_dir.mkdir(parents=True, exist_ok=True)
                    out_path = case_dir / f"{model.name}.md"
                    out_path.write_text(
                        _format_response_file(case, model, result.text, timestamp),
                        encoding="utf-8",
                    )
                    summary.cases_run += 1
                    summary.models_run += 1
                progress.advance(task)

    summary.failures = summary.skipped
    return summary
