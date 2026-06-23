"""Marathon runner — B 组: one session, never reset, across N turns.

Hard constraint (guarded by tests/test_design_guards.py):
  - This module MUST NOT expose any `reset_*` / `clear_*` / `new_session_*`
    function. The whole point of B 组 is to keep the context.
  - The `messages` list grows monotonically across all turns. It is never
    truncated, replaced, or restarted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from lab.console import error, warning
from lab.llm_adapter import MissingAPIKeyError, complete
from lab.model_registry import ModelEntry


@dataclass
class MarathonSummary:
    turns_run: int = 0
    model: str = ""
    scenario: str = ""


def _load_turns(marathons_root: Path, scenario: str) -> list[str]:
    """Load every `turn_NN.md` from `marathons_root/<scenario>/` in lex order.

    Files are read verbatim (no frontmatter expected). A leading/trailing
    newline is stripped so prompts are clean.
    """
    scenario_dir = marathons_root / scenario
    if not scenario_dir.is_dir():
        available = sorted(
            p.name for p in marathons_root.iterdir() if p.is_dir()
        ) if marathons_root.is_dir() else []
        raise FileNotFoundError(
            f"Marathon scenario not found: {scenario_dir}. "
            f"Available scenarios: {available}"
        )
    files = sorted(scenario_dir.glob("turn_*.md"))
    if not files:
        raise FileNotFoundError(
            f"No turn_*.md files in {scenario_dir}. "
            "A marathon scenario must contain at least one turn."
        )
    return [f.read_text(encoding="utf-8").strip() for f in files]


def _format_turn_snapshot(
    scenario: str,
    model: ModelEntry,
    turn_index: int,
    total_turns: int,
    messages: list[dict[str, str]],
) -> str:
    """Render the conversation up to and including the current turn."""
    header = (
        f"# Marathon: {scenario}\n\n"
        f"- Model: `{model.name}`\n"
        f"- Turn: {turn_index + 1} of {total_turns}\n"
        f"- Captured at: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n\n"
        "---\n\n"
    )
    transcript_lines: list[str] = []
    for msg in messages:
        label = "User" if msg["role"] == "user" else "Assistant"
        transcript_lines.append(f"## {label}\n\n{msg['content']}\n")
    return header + "\n".join(transcript_lines)


def run_marathon(
    scenario: str,
    model: ModelEntry,
    *,
    marathons_dir: Path,
    out_dir: Path,
    mock: bool = False,
    mock_responses: dict[str, str] | None = None,
    mock_responses_file: Path | None = None,
) -> MarathonSummary:
    """Run a marathon scenario for one model.

    The conversation `messages` list is built up monotonically: the user
    content for each turn is appended, then the assistant reply is appended,
    then the next turn begins. The list is never reset.

    Inputs are read from `marathons_dir/<scenario>/turn_*.md`.
    Outputs are written to `out_dir/marathon_<scenario>_<model>/turn_NN.md`,
    where `out_dir` is normally `results/YYYY-MM-DD/`.
    """
    summary = MarathonSummary(model=model.name, scenario=scenario)
    turns = _load_turns(marathons_dir, scenario)

    # ↓↓↓ THIS LIST IS THE ENTIRE STATE OF THE CONVERSATION — DO NOT RESET ↓↓↓
    messages: list[dict[str, str]] = []

    marathon_out = out_dir / f"marathon_{scenario}_{model.name}"
    marathon_out.mkdir(parents=True, exist_ok=True)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(f"Marathon: {scenario}", total=len(turns))
        for turn_idx, user_text in enumerate(turns):
            messages.append({"role": "user", "content": user_text})
            try:
                result = complete(
                    model,
                    messages,
                    mock=mock,
                    mock_responses=mock_responses,
                    mock_responses_file=mock_responses_file,
                )
            except MissingAPIKeyError as exc:
                warning(str(exc))
                return summary
            except Exception as exc:  # noqa: BLE001 - retry once then give up
                warning(f"Turn {turn_idx + 1} failed: {exc}. Retrying once...")
                time.sleep(2)
                try:
                    result = complete(
                        model,
                        messages,
                        mock=mock,
                        mock_responses=mock_responses,
                        mock_responses_file=mock_responses_file,
                    )
                except Exception as exc2:  # noqa: BLE001
                    error(f"Turn {turn_idx + 1} failed twice: {exc2}")
                    return summary

            messages.append({"role": "assistant", "content": result.text})
            turn_path = marathon_out / f"turn_{turn_idx + 1:02d}.md"
            turn_path.write_text(
                _format_turn_snapshot(
                    scenario, model, turn_idx, len(turns), messages
                ),
                encoding="utf-8",
            )
            summary.turns_run += 1
            progress.advance(task)

    return summary
