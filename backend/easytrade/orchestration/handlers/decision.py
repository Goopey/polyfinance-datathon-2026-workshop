"""Lambda : étape 4, moteur de décision. Rassemble d'abord les débats des candidats (état `Map`).

Conception : docs/06_AWS.md
"""
from __future__ import annotations

from easytrade.orchestration import aws_runtime
from easytrade.orchestration.handlers.common import debate_key, stage_handler
from easytrade.orchestration.pipeline import debate_jobs, record_debate, stage_decision


def _work(ctx, ws, client) -> None:
    store = aws_runtime.state_store()
    record_debate(ctx, {ticker: store.load(ctx.run_id, debate_key(ticker)) for ticker in debate_jobs(ctx)})
    stage_decision(ctx, ws, client)


handler = stage_handler("decision", _work)
