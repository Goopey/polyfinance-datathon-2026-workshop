"""Agent 2 : présélection des candidats et collecte des preuves qualitatives. Seul agent à choisir ses outils.

Conception : docs/02_AGENTS.md (section 2)
Pourquoi il existe : c'est le seul composant qui décide *quoi aller chercher*. Il mobilise les
outils de données selon le profil.

Déroulement : le modèle reçoit le profil pondéré, l'univers (sans aucun chiffre) et la liste des
outils ; il renvoie des candidats, chacun avec un motif, et les appels d'outils qu'il demande.
Le code exécute ces appels (`agents/tools.py`, filtrés par `as_of`) et rattache les preuves
obtenues aux candidats.

Garde-fous du code :
- un ticker hors univers est retiré et noté (`dropped`) ;
- le titre demandé par l'utilisateur est toujours candidat, jamais filtré en silence ;
- le nombre de candidats et d'appels d'outils est plafonné ;
- la présélection ne change le score d'aucun actif : le moteur normalise sur tout l'univers
  admissible (`engine.decision.decide`, paramètre `candidates`).
"""
from __future__ import annotations

from typing import Iterable, Optional

from pydantic import BaseModel, Field

from easytrade.agents.llm_client import TIER_STRONG, CallInfo, LLMClient, load_prompt, structured_call
from easytrade.agents.profile_weighting import WeightingResult
from easytrade.agents.tools import TOOL_DESCRIPTIONS, ResearchTools
from easytrade.explain.wording import is_clean
from easytrade.schemas.candidate import Candidate, CandidateList

STEP = "research"
MAX_TOOL_CALLS = 200
REQUESTED_REASON = "Titre soumis par l'utilisateur : il est toujours analysé."


class CandidateDraft(BaseModel):
    ticker: str
    reason: str = ""


class ToolRequest(BaseModel):
    tool: str
    ticker: Optional[str] = None


class ResearchDraft(BaseModel):
    candidates: list[CandidateDraft] = Field(default_factory=list)
    tool_requests: list[ToolRequest] = Field(default_factory=list)


def run_research(
    weighting: WeightingResult,
    tools: ResearchTools,
    client: LLMClient,
    *,
    requested_ticker: Optional[str] = None,
    max_candidates: Optional[int] = None,
    forbidden: Iterable[str] = (),
) -> tuple[CandidateList, CallInfo]:
    universe = tools.lister_univers()
    known = {row["ticker"] for row in universe}
    limit = max_candidates or len(universe)
    weights = weighting.profile_weights

    payload = {
        "profile": {
            "id": weighting.profile.id,
            "weights": dict(weights.weights),
            "hard_constraints": weights.constraints.model_dump(),
            "preferred_themes": list(weighting.preferred_themes),
            "avoided_themes": list(weighting.avoided_themes),
            "facts": [fact.model_dump() for fact in weighting.facts],
        },
        "universe": universe,
        "tools": {name: text for name, text in TOOL_DESCRIPTIONS.items() if name != "lister_univers"},
        "requested_ticker": requested_ticker,
        "max_candidates": limit,
    }
    draft, info = structured_call(client, step=STEP, prompt=load_prompt(STEP), payload=payload,
                                  schema=ResearchDraft, tier=TIER_STRONG)

    # Candidats : univers seulement, sans doublon, motif sans formulation refusée.
    forbidden = tuple(forbidden)
    reasons: dict[str, str] = {}
    dropped: list[str] = []
    for item in draft.candidates:
        ticker = item.ticker.strip()
        if ticker not in known:
            dropped.append(ticker)
        elif ticker not in reasons:
            reasons[ticker] = item.reason.strip() if is_clean(item.reason, forbidden) else ""
    ordered = list(reasons)
    if requested_ticker and requested_ticker in known:
        if requested_ticker in ordered:
            ordered.remove(requested_ticker)
        ordered.insert(0, requested_ticker)  # jamais retiré par le plafond
        reasons[requested_ticker] = REQUESTED_REASON
    ordered = ordered[:limit]

    # Appels d'outils demandés par l'agent, exécutés par le code.
    found: dict[str, list[str]] = {ticker: [] for ticker in ordered}
    executed = 0
    for request in draft.tool_requests:
        if executed >= MAX_TOOL_CALLS:
            break
        if request.tool not in tools.names or request.tool == "lister_univers" or request.ticker not in found:
            continue
        executed += 1
        for row in tools.dispatch(request.tool, request.ticker):
            if "evidence_id" in row:
                found[request.ticker].append(row["evidence_id"])

    candidates = tuple(
        Candidate(ticker=ticker, reason=reasons[ticker], evidence_ids=tuple(dict.fromkeys(found[ticker])),
                  requested=ticker == requested_ticker)
        for ticker in ordered
    )
    return CandidateList(candidates=candidates, dropped=tuple(dropped), tools_called=tools.summary()), info
