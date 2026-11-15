"""Lambda : débat d'un candidat (Bull ∥ Réaliste ∥ Bear, tours 1 et 3), un élément de l'état `Map`.

Conception : docs/06_AWS.md
Entrée : `{"run_id", "ticker"}`. Le débat lit le registre de preuves sans y écrire : les candidats
s'exécutent en parallèle sans modifier le contexte. Le résultat est enregistré à part, puis
rassemblé par l'étape de décision.
"""
from __future__ import annotations

from typing import Any

from easytrade.orchestration import aws_runtime
from easytrade.orchestration.handlers.common import debate_key, debate_workers, execute, load_context
from easytrade.orchestration.pipeline import debate_one, record_debate_failure


def handler(event: dict, context: Any = None) -> dict:
    ctx = load_context(event["run_id"])
    ticker = event["ticker"]

    def work(ctx, ws, client) -> None:
        result = debate_one(ctx, ws, client, ticker, max_workers=debate_workers())
        aws_runtime.state_store().save(ctx.run_id, debate_key(ticker), result)

    execute("debat", ctx, work, on_failure=record_debate_failure, save=False)
    return {"run_id": ctx.run_id, "ticker": ticker}
