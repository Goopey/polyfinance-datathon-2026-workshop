"""Enveloppe commune des Lambda d'étape : charger le contexte, exécuter l'étape, enregistrer, publier.

Conception : docs/06_AWS.md, infra/statemachine/pipeline.asl.json
Deux sortes d'erreur, pour que la machine d'états sache quoi faire :
- `RetryableStageError` : Bedrock indisponible (quota, réseau). Le contexte n'est pas enregistré ;
  Step Functions relance l'étape depuis le dernier point enregistré (champ `Retry`).
- `StageError` : toute autre erreur (sortie de modèle invalide après relance, fidélité, donnée). Le run
  est marqué « echec » avec sa trace, puis l'erreur remonte : pas de relance (champ `Catch`).
Le message commence par « [étape] » : la fonction d'échec s'en sert pour inscrire l'étape dans la trace.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Optional

from easytrade.agents.llm_client import LLMClient, LLMUnavailableError
from easytrade.orchestration import aws_runtime
from easytrade.orchestration.pipeline import RunContext, Workspace, fail, finish, with_persona

CONTEXT = "context"
RESULT = "result"


class StageError(RuntimeError):
    """Échec définitif d'une étape : le run est déjà marqué « echec »."""


class RetryableStageError(RuntimeError):
    """Échec passager (Bedrock indisponible) : la machine d'états relance l'étape."""


def debate_key(ticker: str) -> str:
    return "debate_" + "".join(c if c.isalnum() else "_" for c in ticker)


def debate_workers() -> int:
    return max(1, int(os.environ.get("EASYTRADE_DEBATE_WORKERS", "3")))


def load_context(run_id: str) -> RunContext:
    return aws_runtime.state_store().load(run_id, CONTEXT)


def save_context(ctx: RunContext) -> None:
    aws_runtime.state_store().save(ctx.run_id, CONTEXT, ctx.detach())


def publish(ctx: RunContext, status: str = "en_cours", error: Optional[str] = None) -> None:
    """Progression lue par l'API (GET /runs/{id}) : statut et étapes fermées de la trace."""
    aws_runtime.run_table().update_run(ctx.run_id, status=status, error=error,
                                       steps=aws_runtime.steps_payload(ctx.trace.steps))


def finalize(ctx: RunContext) -> None:
    """Fin du run (réussi ou non) : résultat pour l'API, artefacts JSON sur S3, statut final."""
    if not ctx.finished:
        finish(ctx)
    store = aws_runtime.state_store()
    store.save(ctx.run_id, RESULT, ctx.result)
    store.save_artifacts(ctx.result)
    save_context(ctx)
    publish(ctx, status=ctx.result.status, error=ctx.result.error)


def runtime(ctx_persona: Optional[dict] = None) -> tuple[Workspace, LLMClient]:
    return with_persona(aws_runtime.workspace(), ctx_persona), aws_runtime.llm()


def execute(stage: str, ctx: RunContext, work: Callable[[RunContext, Workspace, LLMClient], Any], *,
            on_failure: Optional[Callable[[RunContext, BaseException], None]] = None,
            save: bool = True) -> Any:
    """Exécute `work` sur le contexte et applique la règle d'erreur décrite en tête de module."""
    ws, client = runtime(ctx.persona)
    try:
        out = work(ctx, ws, client)
    except LLMUnavailableError as error:
        raise RetryableStageError(f"[{stage}] {error}") from error
    except Exception as error:
        if on_failure is not None:
            on_failure(ctx, error)
        fail(ctx, error)
        finalize(ctx)
        raise StageError(f"[{stage}] {type(error).__name__} : {error}") from error
    if save:
        save_context(ctx)
        publish(ctx)
    return out


def stage_handler(stage: str, work: Callable[[RunContext, Workspace, LLMClient], Any]) -> Callable:
    """Lambda d'une étape qui reprend un run existant : l'entrée et la sortie sont `{"run_id": …}`."""

    def handler(event: dict, context: Any = None) -> dict:
        ctx = load_context(event["run_id"])
        out = execute(stage, ctx, work)
        return {"run_id": ctx.run_id, **(out or {})}

    return handler
