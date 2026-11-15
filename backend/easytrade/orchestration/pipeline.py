"""Pipeline local : enchaîne les mêmes fonctions que la machine d'états Step Functions.

Conception : docs/01_ARCHITECTURE.md (flux d'une analyse), docs/08_CONFORMITE.md (gouvernance)

    1. profil                 agent de pondération            (LLM + garde-fous du code)
    2. validation             indicateurs déterministes       (code)        ┐ en parallèle
       recherche              candidats, preuves qualitatives (LLM + outils)┘ sur AWS
    3. dossiers de preuves    jointure, contraintes dures, pré-classement   (code)  → contrôle 1
    4. débat                  Bull ∥ Réaliste ∥ Bear, tours 1 et 3          (LLM)
    5. décision               confiance, désaccords, panier, cohérence      (code)  → contrôle 2
    6. explication            rédaction + vérificateur de fidélité          (LLM + code) → contrôle 3

Les LLM argumentent, le code décide : le classement et les rejets sont calculés aux étapes 3 et 5
sans aucun modèle. En local, validation et recherche s'exécutent l'une après l'autre, dans un
ordre fixe, pour que les identifiants de preuves soient reproductibles.

Sans Bedrock configuré, les agents sont simulés (`agents/simulated.py`) : la trace et
l'explication le disent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import pandas as pd

from easytrade.agents import simulated
from easytrade.agents.debate.protocol import run_debate, step_name
from easytrade.agents.explanation import explain
from easytrade.agents.llm_client import CallInfo, LLMClient, make_client
from easytrade.agents.profile_weighting import SOURCE_PROFILE, WeightingResult, template_for, weigh_profile
from easytrade.agents.research import run_research
from easytrade.agents.tools import ResearchTools
from easytrade.config import Settings, load_settings
from easytrade.data.point_in_time import DateLike, PointInTimeStore, to_timestamp
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.engine import governance
from easytrade.engine.coherence import evaluate_idea, limit_tensions, reference_medians, verdict_from
from easytrade.engine.decision import apply_debate, decide
from easytrade.engine.signals import THEMES, build_signals, preference_signals, sector_counts
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.explain.fidelity import FidelityReport, check_claim
from easytrade.explain.trace import TraceRecorder
from easytrade.explain.wording import load_forbidden
from easytrade.schemas.candidate import CandidateList, EvidencePack
from easytrade.schemas.debate import AGENTS, Claim, DebateRecord
from easytrade.schemas.decision import Decision
from easytrade.schemas.evidence import EvidenceDraft
from easytrade.schemas.explanation import Alternative, CoherenceAnalysis, Explanation, RejectedItem
from easytrade.schemas.profile import Profile
from easytrade.schemas.trace import RunTrace, TraceStep
from easytrade.validation.metrics import basket_volatility_metric, compute_metrics_table

VERSION = "v1"
SOURCE_UNIVERSE = "starter_universe"
SOURCE_PRICES = "starter_prices"
SOURCE_HYPOTHESES = "easytrade_hypotheses"
STARTER_INPUTS = ("data/raw/starter/prices_daily.csv", "data/raw/starter/fx_usdcad_daily.csv",
                  "data/raw/starter/corporate_actions.csv")
REQUIRED_SIGNALS = ("croissance", "stabilite")  # sans eux, un candidat n'a pas d'indicateurs valides
LOW_CONFIDENCE_REASON = (
    "Confiance faible sur toutes les pistes : le débat s'oppose aux candidats ou les données sont insuffisantes."
)


class UnknownTickerError(ValueError):
    """Titre demandé absent de l'univers analysé."""


@dataclass
class Workspace:
    """Ressources partagées entre exécutions : données, registre des sources, personas, formulations."""

    settings: Settings
    store: PointInTimeStore
    registry: SourcesRegistry
    personas: dict
    forbidden: tuple[str, ...]

    @classmethod
    def load(cls, settings: Optional[Settings] = None) -> "Workspace":
        settings = settings or load_settings()
        with open(settings.reference_dir / "personas.json", encoding="utf-8") as f:
            personas = json.load(f)
        return cls(
            settings=settings,
            store=PointInTimeStore.from_settings(settings),
            registry=SourcesRegistry.load(settings.reference_dir),
            personas=personas,
            forbidden=load_forbidden(settings.reference_dir),
        )

    def profile(self, profile_id: str) -> Profile:
        for persona in self.personas["personas"]:
            if persona["id"] == profile_id:
                return Profile.from_persona(persona)
        raise KeyError(f"Profil inconnu : {profile_id}")


@dataclass
class RunResult:
    run_id: str
    status: str  # termine | echec
    as_of: date
    profile_id: str
    requested_ticker: Optional[str]
    model_id: str
    trace: RunTrace
    ledger: EvidenceLedger
    explanation: Optional[Explanation] = None
    decision: Optional[Decision] = None
    weighting: Optional[WeightingResult] = None
    candidates: Optional[CandidateList] = None
    debate: dict[str, DebateRecord] = field(default_factory=dict)
    fidelity: Optional[FidelityReport] = None
    error: Optional[str] = None
    metrics: Optional[pd.DataFrame] = None  # table d'indicateurs du run (fiche d'un actif servie par l'API)

    def save(self, out_dir: Path) -> Path:
        """Écrit les artefacts du run (mêmes fichiers que ceux déposés sur S3 par les Lambda)."""
        target = Path(out_dir) / self.run_id
        target.mkdir(parents=True, exist_ok=True)

        def dump(name: str, payload: Any) -> None:
            with open(target / name, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)

        dump("run.json", {
            "run_id": self.run_id, "status": self.status, "as_of": str(self.as_of), "profile_id": self.profile_id,
            "requested_ticker": self.requested_ticker, "model_id": self.model_id, "error": self.error,
        })
        dump("trace.json", self.trace.model_dump(mode="json"))
        dump("evidence.json", self.ledger.to_records())
        if self.explanation is not None:
            dump("explanation.json", self.explanation.model_dump(mode="json"))
        if self.decision is not None:
            dump("decision.json", self.decision.model_dump(mode="json"))
        if self.weighting is not None:
            dump("profile_weights.json", self.weighting.model_dump(mode="json"))
        if self.debate:
            dump("debate.json", {t: r.model_dump(mode="json") for t, r in self.debate.items()})
        if self.fidelity is not None:
            dump("fidelity.json", {**self.fidelity.model_dump(mode="json"),
                                   "first_pass_rate": self.fidelity.first_pass_rate})
        return target


def make_run_id(as_of: date, profile_id: str, requested_ticker: Optional[str] = None) -> str:
    suffix = f"_{requested_ticker}" if requested_ticker else ""
    return f"run_{as_of}_{profile_id}{suffix}"


# --- preuves ajoutées par le pipeline ---------------------------------------------------------
def _add_signal_evidence(
    assets: pd.DataFrame, weighting: WeightingResult, signals: dict, evidence: dict,
    ledger: EvidenceLedger, registry: SourcesRegistry,
) -> None:
    """Renseigne le critère `preferences` et donne une preuve aux critères `diversification` et
    `preferences` (les autres critères sourcés ont déjà la preuve de leur indicateur)."""
    as_of = ledger.as_of
    universe_src = registry.require_used(SOURCE_UNIVERSE).as_evidence_source()
    hypothesis_src = registry.require_used(SOURCE_HYPOTHESES).as_evidence_source()
    counts = sector_counts(assets)
    preferences = preference_signals(assets, weighting.preferred_themes, weighting.avoided_themes)
    for _, row in assets.iterrows():
        ticker, sector = str(row["ticker"]), str(row["sector"])
        evidence[ticker]["diversification"] = ledger.add(EvidenceDraft(
            type="metric", claim_kind="HYPOTHESE", subject=ticker,
            statement=f"Nombre d'actifs du secteur « {sector} » dans l'univers analysé (repère de diversification)",
            value=float(counts[sector]), unit="actif(s)", observed_at=as_of, published_at=as_of,
            source=universe_src,
            processing="Décompte des actifs de l'univers par secteur ; un secteur rare vaut un meilleur score",
            produced_by=f"engine.signals.diversification@{VERSION}",
            limits="Approximation de l'apport de diversification (hypothèse de l'équipe), à remplacer par la "
                   "corrélation au panier. Univers choisi en 2026 : biais du survivant.",
        )).evidence_id
        value, liked, disliked = preferences[ticker]
        if liked or disliked:
            parts = []
            if liked:
                parts.append("Se rattache à un thème d'intérêt du profil ("
                             + ", ".join(THEMES[t]["label"] for t in liked) + ")")
            if disliked:
                parts.append("Se rattache à un thème que le profil préfère éviter ("
                             + ", ".join(THEMES[t]["label"] for t in disliked) + ")")
            statement = " ; ".join(parts)
        else:
            statement = "Ne se rattache à aucun thème d'intérêt déclaré dans le profil"
        signals[ticker]["preferences"] = value
        evidence[ticker]["preferences"] = ledger.add(EvidenceDraft(
            type="profile", claim_kind="HYPOTHESE", subject=ticker, statement=statement, value=value,
            unit="thème(s)", observed_at=as_of, published_at=as_of, source=hypothesis_src,
            processing="Thèmes lus dans le profil par l'agent de pondération ; rattachement de l'actif à un thème "
                       "par sa classe d'actifs et son secteur (table du moteur)",
            produced_by=f"engine.signals.preferences@{VERSION}",
            limits="Rattachement par secteur, sans analyse de l'activité réelle de l'émetteur (hypothèse de l'équipe).",
        )).evidence_id


def _build_pack(ticker: str, assets_by_ticker: dict, metrics: pd.DataFrame, evidence: dict,
                weighting: WeightingResult, candidates: CandidateList, ledger: EvidenceLedger) -> EvidencePack:
    roles: dict[str, str] = {}
    rows = metrics[(metrics["ticker"] == ticker) & metrics["evidence_id"].notna()]
    for _, row in rows.iterrows():
        roles[row["evidence_id"]] = f"{row['metric']}:{row['window']}"
    for criterion in ("diversification", "preferences"):
        evidence_id = evidence.get(ticker, {}).get(criterion)
        if evidence_id:
            roles[evidence_id] = f"signal:{criterion}"
    for candidate in candidates.candidates:
        if candidate.ticker == ticker:
            for evidence_id in candidate.evidence_ids:
                roles.setdefault(evidence_id, ledger.get(evidence_id).type)
    for fact in weighting.facts:
        roles[fact.evidence_id] = f"profil:{fact.kind}"
    for name, evidence_id in weighting.constraint_evidence.items():
        roles[evidence_id] = f"regle:{name}"
    for name, evidence_id in weighting.limit_evidence.items():
        roles[evidence_id] = f"repere:{name}"
    for criterion, evidence_id in weighting.weight_evidence.items():
        roles[evidence_id] = f"poids:{criterion}"
    asset = assets_by_ticker[ticker]
    return EvidencePack(
        ticker=ticker, name=asset["name"], asset_class=asset["asset_class"], sector=asset["sector"],
        evidence=tuple(ledger.get(evidence_id) for evidence_id in roles), roles=roles,
    )


def _rule_evidence(rule: str, weighting: WeightingResult) -> tuple[str, ...]:
    """Preuves d'une règle du profil : la valeur de la règle (hypothèse) et la phrase du profil qui la fonde."""
    name = {
        governance.RULE_SECTOR: "max_weight_per_sector",
        governance.RULE_CRYPTO: "max_weight_crypto",
    }.get(rule, rule)
    ids = [weighting.constraint_evidence[name]] if name in weighting.constraint_evidence else []
    ids.extend(weighting.rationale_evidence(f"hard_constraints.{name}"))
    if not ids:  # règle sans valeur chiffrée ni phrase rattachée : on cite la tolérance déclarée
        tolerance = weighting.fact("tolerance")
        ids.extend([tolerance.evidence_id] if tolerance else [])
    return tuple(dict.fromkeys(ids))


def _metric(metrics: pd.DataFrame, ticker: str, metric: str, window: str = "full") -> tuple[Optional[float], Optional[str]]:
    rows = metrics[(metrics["ticker"] == ticker) & (metrics["metric"] == metric) & (metrics["window"] == window)]
    if rows.empty or pd.isna(rows.iloc[0]["value"]):
        return None, None
    return float(rows.iloc[0]["value"]), rows.iloc[0]["evidence_id"]


def _build_coherence(
    ticker: str, *, ws: Workspace, assets: pd.DataFrame, names: dict[str, str], metrics: pd.DataFrame,
    signals: dict, evidence: dict, weighting: WeightingResult, decision: Decision, ledger: EvidenceLedger,
    ignore: tuple[str, ...], dropped: list[str],
) -> CoherenceAnalysis:
    """« Tester une idée » : tensions chiffrées et sourcées, verdict, effet sur le panier simulé, alternatives."""
    as_of = ledger.as_of
    weights = weighting.profile_weights
    prices_src = ws.registry.require_used(SOURCE_PRICES).as_evidence_source()
    report = evaluate_idea(ticker, assets, signals, evidence, weights, as_of)
    full = decide(assets, signals, evidence, weights, as_of)
    medians = reference_medians(ticker, [c.ticker for c in full.ranking], signals)

    def median_evidence(key: str, statement: str) -> Optional[str]:
        if medians[key] is None:
            return None
        return ledger.add(EvidenceDraft(
            type="metric", claim_kind="FAIT", subject=weighting.profile.id, statement=statement,
            value=float(medians[key]), unit="%", currency="CAD", observed_at=as_of, published_at=as_of,
            source=prices_src,
            processing="Médiane de l'indicateur sur les actifs admissibles classés pour ce profil, hors titre testé",
            produced_by=f"engine.coherence.reference_medians@{VERSION}",
            limits="Décrit le passé sur la période disponible, pas une prévision. Biais du survivant.",
        )).evidence_id

    median_ids = {
        "volatilité": median_evidence("volatilite", "Médiane de la volatilité annualisée des actifs classés pour ce profil"),
        "horizon": median_evidence("horizon", "Médiane de la pire période glissante de 3 ans des actifs classés pour ce profil"),
    }
    volatility, volatility_id = _metric(metrics, ticker, "annualized_volatility")
    drawdown, drawdown_id = _metric(metrics, ticker, "max_drawdown")
    all_tensions = list(report.tensions) + limit_tensions(
        level=weighting.risk_level, volatility=volatility, max_drawdown=drawdown,
        volatility_evidence=volatility_id, drawdown_evidence=drawdown_id, limit_evidence=weighting.limit_evidence,
    )

    def verified(text: str, ids: Iterable[Optional[str]]) -> Optional[Claim]:
        check = check_claim(Claim(text=text, evidence_ids=tuple(i for i in ids if i)), ledger, as_of,
                            ws.forbidden, ignore=ignore)
        if not check.ok:
            dropped.append(f"{text} ({', '.join(check.issues)})")
            return None
        return check.claim

    tensions: list[Claim] = []
    for tension in all_tensions:
        if tension.dimension == "contrainte":
            rule = next((r.rule for r in decision.rejected if r.ticker == ticker), "")
            ids: list[Optional[str]] = list(_rule_evidence(rule, weighting))
        else:
            ids = [tension.evidence_id, *tension.evidence_ids, median_ids.get(tension.dimension)]
        claim = verified(tension.detail, ids)
        if claim is not None:
            tensions.append(claim)

    # Effet sur le panier simulé (scénario fictif) : volatilité du panier avant / avec le titre.
    context: list[Claim] = []
    retained = [t for t in decision.retained if t != ticker]
    if retained and ticker not in decision.retained and not decision.no_recommendation:
        n = len(retained)
        share = weights.constraints.max_weight_per_asset
        before = basket_volatility_metric(
            ws.store, as_of, ledger, ws.registry, {t: 1.0 / n for t in retained},
            f"{n} pistes retenues, parts égales", ws.settings.quality)
        after = basket_volatility_metric(
            ws.store, as_of, ledger, ws.registry, {ticker: share, **{t: (1.0 - share) / n for t in retained}},
            f"{ticker} à {share * 100:.0f} %, le reste à parts égales entre les {n} pistes retenues",
            ws.settings.quality)
        if before.evidence_id and after.evidence_id:
            cap_id = weighting.constraint_evidence["max_weight_per_asset"]
            claim = verified(
                f"Scénario fictif : un panier simulé des {n} pistes retenues, à parts égales, affiche une volatilité "
                f"annualisée observée de {{{before.evidence_id}}}. Avec {ticker} à hauteur de {{{cap_id}}} du panier, "
                f"elle aurait été de {{{after.evidence_id}}} sur la même période.",
                [before.evidence_id, cap_id, after.evidence_id])
            if claim is not None:
                context.append(claim)

    alternatives: list[Alternative] = []
    for other in report.alternatives:
        other_vol, other_id = _metric(metrics, other, "annualized_volatility")
        if other_vol is None or volatility is None or other_vol >= volatility:
            continue  # une alternative doit présenter moins de tension, preuve à l'appui
        claim = verified(f"Même secteur ; volatilité annualisée observée de {{{other_id}}} sur la période.", [other_id])
        if claim is not None:
            alternatives.append(Alternative(ticker=other, name=names[other], why=claim))

    return CoherenceAnalysis(
        ticker=ticker, name=names[ticker], verdict=verdict_from(all_tensions),
        tensions=tuple(tensions), context=tuple(context), alternatives=tuple(alternatives),
    )


def _llm_fields(infos: Iterable[CallInfo]) -> dict[str, Any]:
    infos = list(infos)
    if not infos:
        return {}
    return {
        "model_id": infos[0].model_id,
        "prompt_version": infos[0].prompt_version,
        "attempts": sum(info.attempts for info in infos),
    }


# --- exécution ----------------------------------------------------------------------------------
def run_pipeline(
    profile_id: str,
    *,
    as_of: Optional[DateLike] = None,
    requested_ticker: Optional[str] = None,
    client: Optional[LLMClient] = None,
    workspace: Optional[Workspace] = None,
    profile: Optional[Profile] = None,
    reading_level: str = "simple",
    max_candidates: Optional[int] = None,
    max_workers: int = 1,
    on_step: Optional[Callable[[TraceStep], None]] = None,
    profile_source: str = SOURCE_PROFILE,
) -> RunResult:
    """Exécute une analyse complète. Un échec d'étape donne `status = "echec"`, trace à l'appui.

    `on_step` est appelé à la fermeture de chaque étape (progression affichée par le mobile).
    `profile_source` : source des phrases du profil (énoncé du case, ou questionnaire de l'application).
    """
    ws = workspace or Workspace.load()
    client = client or make_client("auto")
    as_of_date = to_timestamp(as_of if as_of is not None else ws.settings.as_of).date()
    requested_ticker = requested_ticker.strip().upper() if requested_ticker else None
    run_id = make_run_id(as_of_date, profile_id, requested_ticker)
    ledger = EvidenceLedger(as_of_date)
    trace = TraceRecorder(run_id, as_of_date, profile_id, on_step=on_step)
    result = RunResult(run_id=run_id, status="echec", as_of=as_of_date, profile_id=profile_id,
                       requested_ticker=requested_ticker, model_id=client.model_id("strong"),
                       trace=trace.to_trace(), ledger=ledger)
    try:
        assets = ws.store.assets()
        assets_by_ticker = {str(r["ticker"]): {k: str(r[k]) for k in ("name", "asset_class", "sector")}
                            for _, r in assets.iterrows()}
        names = {ticker: a["name"] for ticker, a in assets_by_ticker.items()}
        if requested_ticker and requested_ticker not in names:
            raise UnknownTickerError(f"Titre absent de l'univers analysé : {requested_ticker}")
        ignore = (*names.values(), *names.keys())  # noms contenant des chiffres (« S&P 500 ») et tickers

        # 1. Profil → ProfileWeights
        with trace.step("profil", "llm") as step:
            profile = profile or ws.profile(profile_id)
            weighting, info = weigh_profile(profile, template_for(profile, ws.personas), client, ledger,
                                            ws.registry, forbidden=ws.forbidden, profile_source=profile_source)
            weights = weighting.profile_weights
            step.set(**_llm_fields([info]), outputs=weighting.evidence_ids)
            step.note(f"Niveau de risque : {weighting.risk_level} ; thèmes : "
                      f"{', '.join(weighting.preferred_themes) or 'aucun'} ; écarts au gabarit : "
                      f"{', '.join(weighting.deviations) or 'aucun'}.")
        result.weighting = weighting

        # 2a. Validation : indicateurs déterministes pour tout l'univers, à la date as_of
        with trace.step("validation", "code", version=f"validation@{VERSION}", inputs=STARTER_INPUTS) as step:
            before = len(ledger)
            metrics = compute_metrics_table(ws.store, as_of_date, ledger, ws.registry, ws.settings.quality)
            step.note(f"{len(metrics)} indicateurs calculés, {len(ledger) - before} preuves créées, "
                      f"aucune donnée publiée après le {as_of_date}.")
        result.metrics = metrics

        # 2b. Recherche : candidats et preuves qualitatives
        with trace.step("recherche", "llm") as step:
            tools = ResearchTools(assets, as_of_date, ws.settings.reference_dir, ledger, ws.registry)
            candidates, info = run_research(weighting, tools, client, requested_ticker=requested_ticker,
                                            max_candidates=max_candidates, forbidden=ws.forbidden)
            step.set(**_llm_fields([info]), tools_called=candidates.tools_called, outputs=candidates.tickers)
            notes = sorted({c["note"] for c in tools.calls if c["note"]})
            step.note(f"{len(candidates.candidates)} candidats. " + " ".join(notes))
            if candidates.dropped:
                step.note(f"Propositions retirées (hors univers) : {', '.join(candidates.dropped)}.")
        result.candidates = candidates

        # 3. Dossiers de preuves : jointure, contraintes dures, pré-classement (aucun LLM)
        with trace.step("dossiers_de_preuves", "code", version=f"engine@{VERSION}") as step:
            signals, evidence = build_signals(metrics, assets)
            _add_signal_evidence(assets, weighting, signals, evidence, ledger, ws.registry)
            without_metrics = [t for t in candidates.tickers
                               if any(signals[t].get(c) is None for c in REQUIRED_SIGNALS)]
            classable = [t for t in candidates.tickers if t not in without_metrics]
            decision = decide(assets, signals, evidence, weights, as_of_date, candidates=classable)
            selection = governance.select_basket(() if decision.no_recommendation else decision.ranking,
                                                 weights.constraints)
            to_debate = list(dict.fromkeys(
                [*selection.tickers, *(r.ticker for r in selection.displaced),
                 *([requested_ticker] if requested_ticker and requested_ticker in classable else [])]))
            packs = {t: _build_pack(t, assets_by_ticker, metrics, evidence, weighting, candidates, ledger)
                     for t in to_debate}
            step.set(outputs=tuple(to_debate))
            step.note(f"{len(decision.ranking)} candidats classés ; {len(to_debate)} dossiers de preuves.")
        control = governance.control_pre_debate(
            universe=len(assets), rejected_by_rule=len(decision.rejected), without_evidence=len(without_metrics),
            candidates=len(decision.ranking))
        trace.control(control.name, control.passed, control.note)

        # 4. Débat : Bull ∥ Réaliste ∥ Bear, mêmes preuves, tours 1 et 3
        records: dict[str, DebateRecord] = {}
        if packs:
            started = trace.now()
            infos: list[CallInfo] = []
            try:
                for ticker, pack in packs.items():
                    record, calls = run_debate(pack, weighting, client, ledger, forbidden=ws.forbidden,
                                               ignore=ignore, max_workers=max_workers)
                    records[ticker] = record
                    infos.extend(calls)
            except Exception as error:
                trace.record("debat", "llm", "echec", started_at=started, note=f"{type(error).__name__} : {error}")
                raise
            for round_number in (1, 3):
                for agent in AGENTS:
                    name = step_name(agent, round_number)
                    turns = [t for r in records.values() for t in (r.round1 if round_number == 1 else r.final)
                             if t.agent == agent]
                    removed = sum(t.removed_arguments for t in turns)
                    trace.record(
                        name, "llm", started_at=started, **_llm_fields(i for i in infos if i.step == name),
                        outputs=tuple(records), evidence_in=tuple(sorted({i for p in packs.values() for i in p.evidence_ids})),
                        note=f"{len(turns)} candidats ; {sum(len(t.arguments) for t in turns)} arguments gardés, "
                             f"{removed} supprimés (preuve absente ou nombre non étayé).",
                    )
        else:
            trace.record("debat", "llm", "ignore", note="Aucun candidat à débattre : " + (decision.reason or "aucun dossier."))
        result.debate = records

        # 5. Décision : confiance, désaccords, panier, cohérence d'une demande (aucun LLM)
        coherence: Optional[CoherenceAnalysis] = None
        dropped_claims: list[str] = []
        with trace.step("decision", "code", version=f"engine@{VERSION}") as step:
            decision = apply_debate(decision, records.values(), profile_evidence_ids=weighting.evidence_ids)
            updates: dict[str, Any] = {"retained": selection.tickers, "displaced": selection.displaced}
            confidences = [decision.candidate_confidence.get(t) for t in selection.tickers]
            if selection.tickers and all(c == "faible" for c in confidences):
                updates.update(no_recommendation=True, reason=LOW_CONFIDENCE_REASON)
            decision = decision.model_copy(update=updates)
            if requested_ticker:
                coherence = _build_coherence(
                    requested_ticker, ws=ws, assets=assets, names=names, metrics=metrics, signals=signals,
                    evidence=evidence, weighting=weighting, decision=decision, ledger=ledger, ignore=ignore,
                    dropped=dropped_claims)
                step.note(f"Tester une idée — {requested_ticker} : {coherence.verdict}, "
                          f"{len(coherence.tensions)} tension(s).")
            step.set(outputs=decision.retained)
            step.note(f"{len(decision.retained)} pistes retenues ; {len(decision.disagreements)} désaccord(s) conservé(s) ; "
                      f"{len(decision.to_review)} à examiner.")
            if dropped_claims:
                step.note("Affirmations retirées par le vérificateur : " + " | ".join(dropped_claims))
        result.decision = decision
        for control in (governance.control_basket(selection, weights.constraints),
                        governance.control_diversification(selection),
                        governance.control_no_recommendation(decision.no_recommendation, decision.reason)):
            trace.control(control.name, control.passed, control.note)

        # 6. Explication : rédaction, vérificateur de fidélité, filtre de formulations
        rejected = [
            RejectedItem(ticker=r.ticker, reason=r.reason, kind="contrainte",
                         evidence_ids=_rule_evidence(r.rule, weighting))
            for r in decision.rejected
        ]
        if not decision.no_recommendation:
            rejected.extend(
                RejectedItem(ticker=r.ticker, reason=r.reason, kind="classement",
                             evidence_ids=_rule_evidence(r.rule, weighting))
                for r in decision.displaced
            )
        rejected.extend(
            RejectedItem(ticker=t, kind="preuves",
                         reason="Écarté faute d'indicateurs valides : historique de prix insuffisant à cette date.")
            for t in without_metrics
        )
        simulated_run = client.model_id("strong") == simulated.MODEL_ID
        with trace.step("explication", "llm") as step:
            explanation, report, infos = explain(
                run_id=run_id, decision=decision, weighting=weighting, packs=packs, records=records,
                rejected=rejected, coherence=coherence, client=client, ledger=ledger, forbidden=ws.forbidden,
                ignore=ignore, reading_level=reading_level, notes=(simulated.NOTE,) if simulated_run else (),
            )
            step.set(**_llm_fields(infos))
            if not infos:
                step.set(kind="code")
                step.note("Aucune piste à rédiger : explication assemblée par le code, sans appel au modèle.")
            if report.retried:
                step.note("Une relance après refus du vérificateur de fidélité.")
        control = governance.control_display(
            checked=report.final_checked, first_pass_ok=report.first_pass_ok,
            first_pass_checked=report.first_pass_checked, removed=report.removed,
            remaining_issues=len(report.final_issues))
        trace.control(control.name, control.passed, control.note)
        result.fidelity = report
        if not report.faithful:
            raise RuntimeError(
                "Explication non affichée : le vérificateur de fidélité relève encore "
                f"{len(report.final_issues)} écart(s) : "
                + " | ".join(f"{i.where} ({', '.join(i.codes)})" for i in report.final_issues[:5]))
        result.explanation, result.fidelity, result.status = explanation, report, "termine"
    except Exception as error:  # échec propre : visible dans le résultat et dans la trace
        result.status, result.error = "echec", f"{type(error).__name__} : {error}"
    result.trace = trace.to_trace()
    return result
