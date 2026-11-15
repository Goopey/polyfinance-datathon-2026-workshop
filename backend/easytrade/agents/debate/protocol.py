"""Protocole : tour 1 (indépendant), tour 2 (contre-examen, extra), tour 3 (position finale). Supprime les arguments sans preuve valide.

Conception : docs/02_AGENTS.md (section 3)
Pourquoi le débat existe : un seul modèle tend à confirmer la question posée. Trois points de
vue obligés de s'appuyer sur le **même** dossier de preuves font apparaître les compromis et
l'incertitude, que l'on conserve au lieu de les lisser.

- Tour 1 : chaque agent analyse seul le dossier (appels parallélisables).
- Tour 2 (contre-examen) : extra n° 5, non réalisé.
- Tour 3 : chaque agent lit les trois analyses du tour 1 et rend sa position finale
  (appui, appui avec réserve, opposition) avec un niveau de confiance.

Garde-fous du code, appliqués à chaque tour :
- un argument n'est gardé que s'il cite une preuve du dossier et passe le vérificateur de
  fidélité (aucun nombre non étayé, aucune formulation refusée) ; sinon il est supprimé et compté ;
- le `claim_kind` d'un argument est celui de ses preuves ;
- une question ouverte contenant un nombre non étayé ou une formulation refusée est supprimée.
Le débat ne modifie aucun score : il alimente la confiance et les désaccords (`engine.decision`).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable, Optional

from easytrade.agents.debate import bear, bull, realist
from easytrade.agents.llm_client import (
    MAX_ATTEMPTS,
    TIER_FAST,
    CallInfo,
    LLMClient,
    LLMOutputError,
    load_prompt,
    structured_call,
)
from easytrade.agents.profile_weighting import WeightingResult
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.explain.fidelity import check_claim, text_is_supported
from easytrade.schemas.candidate import EvidencePack
from easytrade.schemas.debate import AGENTS, Claim, DebateRecord, DebateTurn, DebateTurnDraft

MODULES = {"bull": bull, "realist": realist, "bear": bear}
MAX_ARGUMENTS = 4
MAX_OPEN_QUESTIONS = 3
UNANSWERED = "Position non exprimée : la réponse de l'agent était invalide après une relance."


def step_name(agent: str, round_number: int) -> str:
    return f"debate.{agent}.round{round_number}"


def profile_payload(weighting: WeightingResult) -> dict[str, Any]:
    """Contexte du profil, identique pour les trois agents."""
    weights = weighting.profile_weights
    return {
        "id": weighting.profile.id,
        "risk_level": weighting.risk_level,
        "weights": dict(weights.weights),
        "hard_constraints": weights.constraints.model_dump(),
        "facts": [fact.model_dump() for fact in weighting.facts],
    }


def evidence_payload(pack: EvidencePack) -> list[dict[str, Any]]:
    """Dossier de preuves tel qu'il est montré aux agents (valeurs lisibles, jamais à recopier)."""
    return [
        {
            "evidence_id": e.evidence_id,
            "role": pack.roles.get(e.evidence_id, e.type),
            "type": e.type,
            "claim_kind": e.claim_kind,
            "statement": e.statement,
            "value": e.value,
            "unit": e.unit,
            "window": {"start": str(e.window.start) if e.window.start else None,
                       "end": str(e.window.end) if e.window.end else None},
            "limits": e.limits,
        }
        for e in pack.evidence
    ]


def clean_turn(
    draft: DebateTurnDraft,
    *,
    ticker: str,
    agent: str,
    round_number: int,
    pack: EvidencePack,
    ledger: EvidenceLedger,
    forbidden: Iterable[str] = (),
    ignore: Iterable[str] = (),
) -> DebateTurn:
    """Contrôle la sortie d'un agent : arguments sans preuve valide supprimés."""
    forbidden, ignore = tuple(forbidden), tuple(ignore)
    allowed = set(pack.evidence_ids)
    kept: list[Claim] = []
    removed = 0
    for argument in draft.arguments:
        check = check_claim(argument, ledger, ledger.as_of, forbidden, ignore=ignore, allowed_ids=allowed)
        if check.ok and len(kept) < MAX_ARGUMENTS:
            kept.append(check.claim)
        else:
            removed += 1
    questions = [
        question.strip() for question in draft.open_questions
        if question.strip() and text_is_supported(question, pack.evidence, forbidden, ignore)
    ][:MAX_OPEN_QUESTIONS]
    return DebateTurn(
        ticker=ticker, agent=agent, round=round_number, stance=draft.stance, confidence=draft.confidence,
        arguments=tuple(kept), open_questions=tuple(dict.fromkeys(questions)), removed_arguments=removed,
    )


def _summary(turn: DebateTurn) -> dict[str, Any]:
    return {
        "stance": turn.stance,
        "confidence": turn.confidence,
        "arguments": [{"text": a.text, "evidence_ids": list(a.evidence_ids), "claim_kind": a.claim_kind}
                      for a in turn.arguments],
        "open_questions": list(turn.open_questions),
    }


def run_debate(
    pack: EvidencePack,
    weighting: WeightingResult,
    client: LLMClient,
    ledger: EvidenceLedger,
    *,
    forbidden: Iterable[str] = (),
    ignore: Iterable[str] = (),
    max_workers: int = 1,
) -> tuple[DebateRecord, list[CallInfo]]:
    """Tours 1 et 3 pour un candidat. Les trois agents reçoivent le même dossier et le même profil."""
    forbidden, ignore = tuple(forbidden), tuple(ignore)
    base = {
        "ticker": pack.ticker, "name": pack.name, "asset_class": pack.asset_class, "sector": pack.sector,
        "profile": profile_payload(weighting),
        "evidence": evidence_payload(pack),
    }
    infos: list[CallInfo] = []

    def call(agent: str, round_number: int, extra: Optional[dict] = None) -> tuple[DebateTurn, CallInfo]:
        module = MODULES[agent]
        payload = {**base, "agent": agent, "mandate": module.MANDATE, "round": round_number, **(extra or {})}
        step = step_name(agent, round_number)
        prompt = load_prompt(module.PROMPT)
        try:
            draft, info = structured_call(client, step=step, prompt=prompt, payload=payload,
                                          schema=DebateTurnDraft, tier=TIER_FAST)
        except LLMOutputError:
            # Une sortie invalide (même après relance) ne fait pas échouer l'analyse entière : la position
            # de cet agent est « non exprimée », sans argument, et la confiance de la piste baisse.
            turn = DebateTurn(ticker=pack.ticker, agent=agent, round=round_number, stance="appui_reserve",
                              confidence="faible", arguments=(), open_questions=(UNANSWERED,))
            return turn, CallInfo(step=step, model_id=client.model_id(TIER_FAST), prompt_version=prompt.tag,
                                  attempts=MAX_ATTEMPTS)
        turn = clean_turn(draft, ticker=pack.ticker, agent=agent, round_number=round_number, pack=pack,
                          ledger=ledger, forbidden=forbidden, ignore=ignore)
        return turn, info

    def run_round(round_number: int, extras: dict[str, dict]) -> list[DebateTurn]:
        if max_workers > 1:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(AGENTS))) as pool:
                results = list(pool.map(lambda agent: call(agent, round_number, extras.get(agent)), AGENTS))
        else:
            results = [call(agent, round_number, extras.get(agent)) for agent in AGENTS]
        infos.extend(info for _, info in results)
        return [turn for turn, _ in results]

    round1 = run_round(1, {})
    summaries = {turn.agent: _summary(turn) for turn in round1}
    extras = {agent: {"own_round1": summaries[agent], "round1": summaries} for agent in AGENTS}
    final = run_round(3, extras)
    # Une réponse invalide isolée est tolérée (position « non exprimée ») ; si la majorité des tours de
    # ce candidat est invalide, le débat n'a rien produit d'exploitable : erreur, comme avant.
    turns = (*round1, *final)
    unanswered = sum(1 for turn in turns if UNANSWERED in turn.open_questions)
    if unanswered * 2 > len(turns):
        raise LLMOutputError(f"Débat de {pack.ticker} : {unanswered} réponses invalides sur {len(turns)}.")
    return DebateRecord(ticker=pack.ticker, round1=tuple(round1), final=tuple(final)), infos
