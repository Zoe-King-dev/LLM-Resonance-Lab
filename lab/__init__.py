"""LLM Resonance Lab V1 — implementation package.

Two-phase testing is a hard architectural constraint:
  - A 组 (batch_runner): every case = fresh session, never shared context.
  - B 组 (marathon_runner): one session, never reset, across N turns.
These are guarded by tests/test_design_guards.py.
"""

__version__ = "1.0.0"
