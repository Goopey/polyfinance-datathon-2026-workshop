"""Lambda : étape 5, explication et vérificateur de fidélité. Dernier état : termine le run.

Conception : docs/06_AWS.md
Sortie : `{"run_id", "status"}`. Le résultat, les artefacts JSON et le statut final sont publiés.
"""
from __future__ import annotations

from typing import Any

from easytrade.orchestration.handlers.common import execute, finalize, load_context
from easytrade.orchestration.pipeline import stage_explanation


def handler(event: dict, context: Any = None) -> dict:
    ctx = load_context(event["run_id"])
    execute("explication", ctx, stage_explanation, save=False)
    finalize(ctx)
    return {"run_id": ctx.run_id, "status": ctx.result.status}
