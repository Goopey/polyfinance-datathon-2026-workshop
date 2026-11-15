"""Lambda : étape 1, pondération du profil. Premier état de la machine d'états : crée le contexte du run.

Conception : docs/06_AWS.md
Entrée (envoyée par l'API, `POST /runs`) :
    {"run_id", "profile_id", "as_of", "requested_ticker", "persona", "profile_source"}
`persona` n'est présent que pour un profil fictif (absent de personas.json).
"""
from __future__ import annotations

from typing import Any

from easytrade.agents.profile_weighting import SOURCE_PROFILE
from easytrade.orchestration.handlers.common import execute, runtime
from easytrade.orchestration.pipeline import new_context, stage_profile


def handler(event: dict, context: Any = None) -> dict:
    ws, client = runtime(event.get("persona"))
    ctx = new_context(
        ws, client, event["profile_id"], as_of=event.get("as_of"), requested_ticker=event.get("requested_ticker"),
        persona=event.get("persona"), profile_source=event.get("profile_source") or SOURCE_PROFILE,
    )
    if event.get("run_id") and event["run_id"] != ctx.run_id:
        raise ValueError(f"Identifiant de run incohérent : {event['run_id']} contre {ctx.run_id}")
    execute("profil", ctx, stage_profile)
    return {"run_id": ctx.run_id}
