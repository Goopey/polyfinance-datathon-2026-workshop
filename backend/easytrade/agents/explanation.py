"""Agent 5 : Decision → Explanation en langage simple, bornée par les preuves. Soumise au vérificateur de fidélité.

Conception : docs/02_AGENTS.md (section 5), docs/05_EXPLICABILITE.md (section 4)
Pourquoi il existe : rendre le résultat compréhensible par quelqu'un qui n'est pas du métier,
sans rien ajouter aux preuves.

Partage des rôles :
- le modèle rédige, pour chaque piste retenue, deux ou trois raisons courtes (`why`) et, pour
  « Tester une idée », une mise en contexte du risque. Il n'écrit aucun chiffre : il place
  `{EV-…}` là où une valeur doit apparaître ;
- le code assemble tout le reste à partir d'éléments déjà vérifiés : adéquation, confiance,
  contributions, positions du débat, risques, limites, « ce que nous ne savons pas », rejets.

Vérification (contrôle n° 3 de la gouvernance) : chaque affirmation rédigée passe
`explain.fidelity.check_claim`. En cas d'écart, **une relance** avec le motif ; si l'écart
persiste, la phrase est retirée et l'incident est compté. Une piste qui perd toutes ses raisons
reçoit une raison recomposée par le code à partir de sa contribution principale. La sortie
complète est ensuite recontrôlée (`verify_explanation`).
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from easytrade.agents.debate.protocol import evidence_payload, profile_payload
from easytrade.agents.llm_client import TIER_STRONG, CallInfo, LLMClient, load_prompt, structured_call
from easytrade.agents.profile_weighting import WeightingResult
from easytrade.engine.constraints import RISK_FLAG
from easytrade.engine.decision import MISSING_LABELS
from easytrade.engine.scoring import fit_level
from easytrade.engine.signals import horizon_label, horizon_metric
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.explain.fidelity import (
    ClaimCheck,
    FidelityIssue,
    FidelityReport,
    check_claim,
    verify_explanation,
)
from easytrade.explain.wording import is_clean
from easytrade.schemas.candidate import EvidencePack, ScoredCandidate
from easytrade.schemas.debate import AGENT_LABELS, AGENTS, STANCE_LABELS, Claim, DebateRecord
from easytrade.schemas.decision import Decision
from easytrade.schemas.explanation import (
    CoherenceAnalysis,
    DebatePosition,
    DebateSummary,
    Explanation,
    ExplanationDraft,
    ExplanationItem,
    RejectedItem,
)
from easytrade.schemas.weights import CRITERION_LABELS

STEP = "explanation"
MAX_WHY = 3
MAX_NOTES = 2
MAX_LIMITS = 3
CONFIDENCE_LABELS = {"élevé": "élevée", "moyen": "moyenne", "faible": "faible"}
NO_ARGUMENT = "Aucun argument étayé retenu."
PAST_ONLY = "Les indicateurs décrivent le passé sur la période disponible : ils ne prévoient rien."

# Raison recomposée par le code quand la rédaction d'une piste a été entièrement retirée.
FALLBACK_TEMPLATES = {
    "croissance": "Rendement annualisé observé de {id} sur la période disponible.",
    "stabilite": "Volatilité annualisée observée de {id} sur la période disponible.",
    "horizon": "Pire période glissante de {window} observée sur la période : {id}.",
    "diversification": "Corrélation moyenne de {id} avec les autres actifs analysés, un repère pour la diversification.",
    "preferences": "Se rattache à un thème d'intérêt déclaré dans votre profil.",
}


STRENGTH_SCORE = 0.5  # un critère est un « point fort » si le candidat y dépasse la médiane de l'univers


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


def _top_criteria(candidate: ScoredCandidate, weighting: WeightingResult) -> list[dict[str, Any]]:
    """Critères qui expliquent réellement le classement : les points forts du candidat (score au-dessus
    de la médiane de l'univers), par contribution décroissante ; à défaut, sa meilleure contribution."""
    sourced = [c for c in candidate.criteria if not c.missing and c.evidence_id]
    sourced.sort(key=lambda c: (-c.contribution, c.criterion))
    scored = [c for c in sourced if c.score >= STRENGTH_SCORE] or sourced[:1]
    window = horizon_label(horizon_metric(weighting.profile.horizon_annees.min))
    return [
        {"criterion": c.criterion, "label": CRITERION_LABELS[c.criterion], "evidence_id": c.evidence_id,
         "weight_evidence_id": weighting.weight_evidence.get(c.criterion),
         **({"window": window} if c.criterion == "horizon" else {})}
        for c in scored[:MAX_WHY]
    ]


def _fallback_why(candidate: ScoredCandidate, weighting: WeightingResult, ledger: EvidenceLedger,
                  forbidden: tuple[str, ...], ignore: tuple[str, ...]) -> tuple[Claim, ...]:
    for top in _top_criteria(candidate, weighting):
        template = FALLBACK_TEMPLATES.get(top["criterion"])
        if not template:
            continue
        text = template.replace("{id}", "{" + top["evidence_id"] + "}").replace("{window}", top.get("window", ""))
        check = check_claim(Claim(text=text, evidence_ids=(top["evidence_id"],)), ledger, ledger.as_of,
                            forbidden, ignore=ignore)
        if check.ok:
            return (check.claim,)
    return ()


def _debate_summary(record: Optional[DebateRecord]) -> DebateSummary:
    texts: dict[str, str] = {}
    for agent in AGENTS:
        turn = record.position(agent) if record else None
        if turn is None:
            texts[agent] = "Non débattu."
            continue
        first = turn.arguments[0].text if turn.arguments else NO_ARGUMENT
        texts[agent] = f"{_capital(STANCE_LABELS[turn.stance])} — {first}"
    return DebateSummary(bull=texts["bull"], realist=texts["realist"], bear=texts["bear"],
                         dissent=bool(record and record.dissent))


def _item(candidate: ScoredCandidate, why: tuple[Claim, ...], decision: Decision,
          record: Optional[DebateRecord], ledger: EvidenceLedger, forbidden: tuple[str, ...]) -> ExplanationItem:
    positions = tuple(
        DebatePosition(agent=t.agent, stance=t.stance, confidence=t.confidence, arguments=t.arguments,
                       open_questions=t.open_questions)
        for t in (record.final if record else ())
    )
    bear = record.position("bear") if record else None
    risks = [a.text for a in (bear.arguments if bear else ())]
    if "spéculatif signalé" in candidate.flags:
        risks.append("Actif signalé comme hautement spéculatif par une règle de votre profil.")
    if RISK_FLAG in candidate.flags:
        risks.append("Dépasse un repère de risque de votre profil : adéquation plafonnée à « partielle ».")
    limits: list[str] = []
    for claim in why:
        for evidence_id in claim.evidence_ids:
            text = ledger.get(evidence_id).limits
            if text and text not in limits:
                limits.append(text)
    unknowns = [_capital(MISSING_LABELS.get(c, c)) + "." for c in candidate.missing_criteria]
    for position in positions:
        unknowns.extend(q for q in position.open_questions if q not in unknowns)
    return ExplanationItem(
        ticker=candidate.ticker, name=candidate.name, asset_class=candidate.asset_class, sector=candidate.sector,
        fit=fit_level(candidate),
        confidence=CONFIDENCE_LABELS[decision.candidate_confidence.get(candidate.ticker, decision.confidence)],
        to_review=candidate.ticker in decision.to_review,
        why=why,
        contributions={c.criterion: c.contribution for c in candidate.criteria},
        not_applicable=tuple(c.criterion for c in candidate.criteria if not c.applicable),
        debate=positions,
        debate_summary=_debate_summary(record),
        risks=tuple(r for r in risks if is_clean(r, forbidden)),
        limits=tuple(limits[:MAX_LIMITS]),
        unknowns=tuple(u for u in unknowns if is_clean(u, forbidden)),
    )


def _headline(decision: Decision, retained: int, rejected: int) -> str:
    if decision.no_recommendation:
        return "Aucune piste à présenter pour ce profil : les preuves ne suffisent pas."
    pistes = "piste cohérente" if retained == 1 else "pistes cohérentes"
    ecartees = "écartée" if rejected == 1 else "écartées"
    return f"{retained} {pistes} avec votre profil, {rejected} {ecartees}"


def explain(
    *,
    run_id: str,
    decision: Decision,
    weighting: WeightingResult,
    packs: Mapping[str, EvidencePack],
    records: Mapping[str, DebateRecord],
    rejected: Iterable[RejectedItem],
    coherence: Optional[CoherenceAnalysis],
    client: LLMClient,
    ledger: EvidenceLedger,
    forbidden: Iterable[str] = (),
    ignore: Iterable[str] = (),
    reading_level: str = "simple",
    notes: Iterable[str] = (),
) -> tuple[Explanation, FidelityReport, list[CallInfo]]:
    """Rédige, vérifie et assemble l'`Explanation`. Retourne aussi le rapport de fidélité et les appels."""
    forbidden, ignore = tuple(forbidden), tuple(ignore)
    rejected = tuple(rejected)
    as_of = ledger.as_of
    by_ticker = {c.ticker: c for c in decision.ranking}
    retained = [] if decision.no_recommendation else [by_ticker[t] for t in decision.retained if t in by_ticker]
    coherence_pack = packs.get(coherence.ticker) if coherence else None

    # --- 1. rédaction par le modèle, contrôlée affirmation par affirmation ---------------------
    infos: list[CallInfo] = []
    why_by_ticker: dict[str, list[Claim]] = {c.ticker: [] for c in retained}
    coherence_notes: list[Claim] = []
    first_checked = first_ok = removed = kind_corrected = 0
    retried = False
    issues: list[FidelityIssue] = []

    if retained or coherence is not None:
        payload: dict[str, Any] = {
            "reading_level": reading_level,
            "profile": profile_payload(weighting),
            "items": [
                {
                    "ticker": c.ticker, "name": c.name, "asset_class": c.asset_class, "sector": c.sector,
                    "fit": fit_level(c),
                    "top_criteria": _top_criteria(c, weighting),
                    "evidence": evidence_payload(packs[c.ticker]) if c.ticker in packs else [],
                    "debate": dict(records[c.ticker].stances) if c.ticker in records else {},
                }
                for c in retained
            ],
            "coherence": None if coherence is None else {
                "ticker": coherence.ticker, "name": coherence.name, "verdict": coherence.verdict,
                "tensions": [claim.text for claim in coherence.tensions],
                "evidence": evidence_payload(coherence_pack) if coherence_pack else [],
            },
        }

        def allowed_for(ticker: str) -> Optional[set[str]]:
            return set(packs[ticker].evidence_ids) if ticker in packs else None

        def check_draft(draft: ExplanationDraft) -> list[tuple[str, str, ClaimCheck]]:
            """(emplacement, ticker ou '', contrôle) pour chaque affirmation rédigée."""
            checks: list[tuple[str, str, ClaimCheck]] = []
            for item in draft.items:
                if item.ticker not in why_by_ticker:
                    continue  # piste inventée : ignorée
                for index, claim in enumerate(item.why[:MAX_WHY]):
                    checks.append((f"items.{item.ticker}.why[{index}]", item.ticker, check_claim(
                        claim, ledger, as_of, forbidden, ignore=ignore, allowed_ids=allowed_for(item.ticker))))
            if coherence is not None:
                for index, claim in enumerate(draft.coherence_notes[:MAX_NOTES]):
                    checks.append((f"coherence_notes[{index}]", "", check_claim(
                        claim, ledger, as_of, forbidden, ignore=ignore, allowed_ids=allowed_for(coherence.ticker))))
            return checks

        prompt = load_prompt(STEP)
        draft, info = structured_call(client, step=STEP, prompt=prompt, payload=payload,
                                      schema=ExplanationDraft, tier=TIER_STRONG)
        infos.append(info)
        checks = check_draft(draft)
        first_checked = len(checks)
        first_ok = sum(1 for _, _, check in checks if check.ok)
        failing = [(where, check) for where, _, check in checks if not check.ok]
        issues = [FidelityIssue(where=where, text=check.claim.text, codes=check.issues, details=check.details)
                  for where, check in failing]

        if failing:  # une relance, avec le motif de chaque rejet
            retried = True
            corrections = [{"where": i.where, "text": i.text, "problems": list(i.details)} for i in issues]
            draft, info = structured_call(client, step=STEP, prompt=prompt,
                                          payload={**payload, "corrections": corrections},
                                          schema=ExplanationDraft, tier=TIER_STRONG)
            infos.append(info)
            checks = check_draft(draft)

        for where, ticker, check in checks:
            if not check.ok:
                removed += 1  # l'écart persiste : la phrase est retirée, l'incident est compté
                continue
            kind_corrected += check.kind_corrected
            if ticker:
                why_by_ticker[ticker].append(check.claim)
            else:
                coherence_notes.append(check.claim)

    # --- 2. assemblage par le code ---------------------------------------------------------------
    fallbacks = 0
    items: list[ExplanationItem] = []
    for candidate in retained:
        why = tuple(why_by_ticker[candidate.ticker])
        if not why:
            why = _fallback_why(candidate, weighting, ledger, forbidden, ignore)
            fallbacks += bool(why)
        items.append(_item(candidate, why, decision, records.get(candidate.ticker), ledger, forbidden))

    if coherence is not None and coherence_notes:
        coherence = coherence.model_copy(update={"context": (*coherence.context, *coherence_notes)})

    unknowns = [_capital(label) + "." for label in decision.missing_info]
    unknowns.extend(weighting.missing_information)
    unknowns.append(PAST_ONLY)
    unknowns.extend(notes)
    missing = ((decision.reason,) if decision.reason else ()) if decision.no_recommendation else ()

    explanation = Explanation(
        run_id=run_id, as_of=as_of, profile_id=weighting.profile.id,
        headline=_headline(decision, len(items), len(rejected)),
        no_recommendation=decision.no_recommendation,
        missing=tuple(m for m in missing if is_clean(m, forbidden)),
        warnings=() if decision.no_recommendation else tuple(w for w in decision.warnings if is_clean(w, forbidden)),
        items=tuple(items),
        rejected=rejected,
        coherence=coherence,
        unknowns=tuple(dict.fromkeys(u for u in unknowns if u and is_clean(u, forbidden))),
    )

    # --- 3. recontrôle de la sortie complète -----------------------------------------------------
    final_checked, final_issues = verify_explanation(explanation, ledger, forbidden, ignore=ignore)
    report = FidelityReport(
        first_pass_checked=first_checked, first_pass_ok=first_ok, retried=retried, removed=removed,
        kind_corrected=kind_corrected, fallbacks=fallbacks, final_checked=final_checked,
        issues=tuple(issues), final_issues=final_issues,
    )
    return explanation, report, infos
