"""Lambda : jointure candidats + métriques, contraintes dures, pré-classement ; prépare le débat.

Conception : docs/06_AWS.md
Sortie : `{"run_id", "debate_jobs": [{"run_id", "ticker"}, …]}`, lue par l'état `Map` du débat.
"""
from __future__ import annotations

from easytrade.orchestration.handlers.common import stage_handler
from easytrade.orchestration.pipeline import debate_jobs, stage_evidence_packs


def _work(ctx, ws, client) -> dict:
    stage_evidence_packs(ctx, ws, client)
    return {"debate_jobs": [{"run_id": ctx.run_id, "ticker": ticker} for ticker in debate_jobs(ctx)]}


handler = stage_handler("dossiers_de_preuves", _work)
