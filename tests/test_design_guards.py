"""Design guard tests — protect the two-phase testing architecture.

These tests assert public-API invariants that future refactors must not break.
They exist because the difference between A 组 (isolated) and B 组 (continuous)
is the single most important constraint in this project.
"""

from __future__ import annotations

import inspect

from lab import batch_runner, marathon_runner
from lab.batch_runner import run_batch
from lab.llm_adapter import complete
from lab.marathon_runner import run_marathon


class TestAGroupIsolation:
    """A 组: batch_runner must keep every case in a fresh session."""

    def test_run_batch_has_no_messages_parameter(self) -> None:
        sig = inspect.signature(run_batch)
        assert "messages" not in sig.parameters
        assert "session" not in sig.parameters

    def test_run_batch_does_not_expose_session_kwargs(self) -> None:
        sig = inspect.signature(run_batch)
        forbidden = {"messages", "session", "history", "context", "previous_messages"}
        leaked = forbidden & set(sig.parameters)
        assert not leaked, (
            f"run_batch accepts session-state kwargs {leaked}. "
            "A 组 forbids any way for a caller to share state across cases."
        )


class TestBGroupContinuity:
    """B 组: marathon_runner must never expose a way to reset context."""

    def test_no_reset_or_clear_function_in_marathon(self) -> None:
        forbidden_prefixes = ("reset_", "clear_", "new_session_", "restart_", "truncate_")
        offenders = [
            name
            for name in dir(marathon_runner)
            if any(name.startswith(p) for p in forbidden_prefixes)
            and callable(getattr(marathon_runner, name))
            and not name.startswith("__")
        ]
        assert not offenders, (
            f"marathon_runner exposes session-resetting functions {offenders}. "
            "B 组 requires that the conversation context is never reset."
        )

    def test_run_marathon_takes_no_messages_argument(self) -> None:
        sig = inspect.signature(run_marathon)
        forbidden = {"messages", "session", "history"}
        leaked = forbidden & set(sig.parameters)
        assert not leaked, (
            f"run_marathon accepts {leaked}; the conversation state must be "
            "built internally and grow monotonically across turns."
        )


class TestAdapterContract:
    """The `complete` function is the single point of contact with the LLM.
    It must not hide any state — every call is independent."""

    def test_complete_returns_a_fresh_result(self) -> None:
        sig = inspect.signature(complete)
        # The caller controls the conversation; `complete` must not retain
        # any reference to `messages` between calls.
        assert "messages" in sig.parameters
        # No `session_id` or similar that would let the adapter track state.
        forbidden = {"session_id", "conversation_id", "thread_id"}
        leaked = forbidden & set(sig.parameters)
        assert not leaked, (
            f"complete() accepts {leaked}; the adapter must be stateless."
        )


class TestArchitecturalSeparation:
    """batch_runner and marathon_runner must not import each other."""

    def test_batch_runner_does_not_import_marathon(self) -> None:
        # This catches accidental reuse of helper code that would let A 组
        # leak into B 组 (or vice versa).
        import lab.batch_runner as br

        src = inspect.getsource(br)
        assert "marathon_runner" not in src
        assert "from lab.marathon" not in src
        assert "import marathon" not in src

    def test_marathon_runner_does_not_import_batch(self) -> None:
        import lab.marathon_runner as mr

        src = inspect.getsource(mr)
        assert "batch_runner" not in src
        assert "from lab.batch" not in src
        assert "import batch" not in src
