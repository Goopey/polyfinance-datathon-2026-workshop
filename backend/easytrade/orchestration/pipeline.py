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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import pandas as pd

from easytrade.agents import simulated
from easytrade.agents.debate.protocol import UNANSWERED, run_debate, step_name
from easytrade.agents.explanation import explain
from easytrade.agents.llm_client import CallInfo, LLMClient, LLMOutputError, make_client
from easytrade.agents.profile_weighting import SOURCE_PROFILE, WeightingResult, template_for, weigh_profile
from easytrade.agents.research import run_research
from easytrade.agents.tools import ResearchTools
from easytrade.config import FUNDAMENTALS_ANNUAL_LAG_DAYS, Settings, load_settings
from easytrade.data.fundamentals import latest_known, load_fundamentals
from easytrade.data.calendar import align_prices
from easytrade.data.point_in_time import DateLike, PointInTimeStore, to_timestamp
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.engine import governance
from easytrade.engine.coherence import evaluate_idea, limit_tensions, reference_medians, verdict_from
from easytrade.engine.constraints import RULE_TOLERANCE, is_capped_class
from easytrade.engine import esg
from easytrade.engine.decision import apply_debate, decide, esg_focused
from easytrade.engine.quality import quality_scores
from easytrade.engine.signals import (
    THEMES,
    build_signals,
    correlation_diversification,
    horizon_label,
    horizon_metric,
    preference_signals,
)
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.explain.fidelity import FidelityReport, check_claim
from easytrade.explain.trace import TraceRecorder
from easytrade.explain.wording import load_forbidden
from easytrade.schemas.candidate import CandidateList, EvidencePack
from easytrade.schemas.debate import AGENTS, Claim, DebateRecord
from easytrade.schemas.decision import Decision
from easytrade.schemas.evidence import EvidenceDraft, EvidenceWindow
from easytrade.schemas.explanation import Alternative, CoherenceAnalysis, Explanation, RejectedItem
from easytrade.schemas.profile import Profile
from easytrade.schemas.trace import RunTrace, TraceStep
from easytrade.validation.metrics import basket_volatility_metric, compute_metrics_table

VERSION = "v1"
SOURCE_UNIVERSE = "starter_universe"
SOURCE_PRICES = "starter_prices"
SOURCE_HYPOTHESES = "easytrade_hypotheses"
SOURCE_FUNDAMENTALS = "finnhub"
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
    ledger: EvidenceLedger, registry: SourcesRegistry, store: PointInTimeStore, min_common: int,
    esg_proven: frozenset[str] = frozenset(),
) -> None:
    """Renseigne les critères `diversification` (corrélation observée) et `preferences`, avec leur
    preuve (les autres critères sourcés ont déjà la preuve de leur indicateur)."""
    as_of = ledger.as_of
    prices_src = registry.require_used(SOURCE_PRICES).as_evidence_source()
    hypothesis_src = registry.require_used(SOURCE_HYPOTHESES).as_evidence_source()
    preferences = preference_signals(assets, weighting.preferred_themes, weighting.avoided_themes, esg_proven)
    tickers = [str(t) for t in assets["ticker"]]
    aligned = align_prices(store.prices(as_of, tickers), tickers, "adj_close_cad")
    correlations = correlation_diversification(aligned, min_common)
    others = len(tickers) - 1
    for _, row in assets.iterrows():
        ticker = str(row["ticker"])
        found = correlations.get(ticker)
        if found is None:  # historique commun trop court : critère manquant, jamais un bon score
            signals[ticker]["diversification"] = None
            evidence[ticker]["diversification"] = None
        else:
            mean_corr, n_returns = found
            signals[ticker]["diversification"] = -mean_corr
            evidence[ticker]["diversification"] = ledger.add(EvidenceDraft(
                type="metric", claim_kind="FAIT", subject=ticker,
                statement=(f"Corrélation moyenne des rendements quotidiens avec les {others} autres actifs "
                           "de l'univers analysé"),
                value=round(mean_corr, 2), unit="ratio", currency="CAD",
                window=EvidenceWindow(start=aligned.index[0].date(), end=aligned.index[-1].date(),
                                      observations=n_returns),
                observed_at=aligned.index[-1].date(), published_at=aligned.index[-1].date(),
                retrieved_at=registry.get(SOURCE_PRICES).date_extraction, source=prices_src,
                processing=("adj_close en CAD ; rendements quotidiens sur les dates communes à tous les actifs "
                            "(sans remplissage) ; moyenne des corrélations de Pearson avec chacun des autres "
                            "actifs ; plus elle est basse, plus l'actif diversifie"),
                produced_by=f"engine.signals.correlation_diversification@{VERSION}",
                limits=("Décrit le passé sur la fenêtre indiquée, pas une prévision. Mesure la diversification "
                        "par rapport à l'univers analysé, pas à un panier précis ; les corrélations varient "
                        "dans le temps et montent souvent pendant les crises."),
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
                       "par sa classe d'actifs et son secteur (table du moteur), et au thème ESG par une preuve "
                       "« Filtre ESG » datée",
            produced_by=f"engine.signals.preferences@{VERSION}",
            limits="Rattachement par secteur, sans analyse de l'activité réelle de l'émetteur (hypothèse de l'équipe).",
        )).evidence_id


SOURCE_MACRO_BOC = "starter_macro_boc"
POLICY_RATE_SERIES = "V39079"  # taux cible du financement à un jour, Banque du Canada


def _add_cash_evidence(store: PointInTimeStore, ledger: EvidenceLedger, registry: SourcesRegistry) -> Optional[str]:
    """Placement sans risque de référence : taux directeur moyen de la Banque du Canada sur la fenêtre des
    prix, avec les seules valeurs publiées à la date d'analyse. Sert aux agents (rendement « rémunéré » ?)."""
    if SOURCE_MACRO_BOC not in registry or registry.get(SOURCE_MACRO_BOC).statut != "utilisé":
        return None
    as_of = ledger.as_of
    prices = store.prices(as_of)
    if prices.empty:
        return None
    start = prices["date"].min()
    rates = store.macro(as_of, [POLICY_RATE_SERIES])
    rates = rates[rates["observed_at"] >= start]
    if rates.empty:
        return None
    end = rates["observed_at"].max()
    return ledger.add(EvidenceDraft(
        type="macro", claim_kind="FAIT", subject="CA",
        statement="Taux directeur moyen de la Banque du Canada sur la période (placement sans risque de référence)",
        value=round(float(rates["value"].mean()), 2), unit="%",
        window=EvidenceWindow(start=start.date(), end=end.date(), observations=int(len(rates))),
        observed_at=end.date(), published_at=rates["published_at"].max().date(),
        retrieved_at=registry.get(SOURCE_MACRO_BOC).date_extraction,
        source=registry.require_used(SOURCE_MACRO_BOC).as_evidence_source(),
        processing=f"Série {POLICY_RATE_SERIES} ; moyenne simple des valeurs quotidiennes publiées sur la fenêtre des prix",
        produced_by=f"orchestration.cash_rate@{VERSION}",
        limits="Approximation du rendement d'un placement sans risque ; ne tient pas compte des frais ni de l'impôt.",
    )).evidence_id


def _fr(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


QUALITY_PARTS = (  # (composante, libellé, unité, facteur d'affichage, décimales)
    ("roe", "Rentabilité des fonds propres (ROE)", "%", 100.0, 1),
    ("leverage", "Dette / fonds propres", "ratio", 1.0, 2),
    ("margin", "Marge nette", "%", 100.0, 1),
)


def _add_quality_evidence(assets: pd.DataFrame, signals: dict, evidence: dict, ledger: EvidenceLedger,
                          registry: SourcesRegistry, reference_dir: Path) -> None:
    """Critère `qualite` des actions (engine.quality) : une preuve FAIT par chiffre Finnhub publié à la
    date d'analyse, et une preuve HYPOTHESE pour le score (méthode de l'équipe). FNB et crypto : non
    applicable. Source absente ou non « utilisé » : le critère reste manquant."""
    if SOURCE_FUNDAMENTALS not in registry or registry.get(SOURCE_FUNDAMENTALS).statut != "utilisé":
        return
    scores = quality_scores(assets, latest_known(load_fundamentals(reference_dir), ledger.as_of))
    if not scores:
        return
    facts_src = registry.require_used(SOURCE_FUNDAMENTALS).as_evidence_source()
    method_src = registry.require_used(SOURCE_HYPOTHESES).as_evidence_source()
    for ticker, quality in scores.items():
        parts, ids, published = [], [], []
        for attribute, label, unit, factor, decimals in QUALITY_PARTS:
            point = getattr(quality, attribute)
            if point is None:
                continue
            value = round(point.value * factor, decimals)
            ids.append(ledger.add(EvidenceDraft(
                type="metric", claim_kind="FAIT", subject=ticker,
                statement=f"{label}, exercice clos le {point.period_end}", value=value, unit=unit,
                observed_at=point.period_end, published_at=point.published_at, retrieved_at=point.retrieved_at,
                source=facts_src,
                processing=(f"Finnhub, série annuelle « {point.metric} » ({point.document_url}) ; publication "
                            f"supposée {FUNDAMENTALS_ANNUAL_LAG_DAYS} jours après la clôture de l'exercice"),
                produced_by=f"data.fundamentals@{VERSION}",
                limits="Ratio calculé par Finnhub, non audité ; décrit l'exercice indiqué, pas l'avenir.",
            )).evidence_id)
            published.append(point.published_at)
            text = f"{label.split(' (')[0].lower()} {_fr(value, decimals)}{' %' if unit == '%' else ''}"
            if attribute == "leverage" and quality.leverage_position is not None:
                rank = f"{quality.leverage_position}{'er' if quality.leverage_position == 1 else 'e'}"
                text += f" ({rank} plus faible sur {quality.sector_peers} dans le secteur « {quality.sector} »)"
            parts.append(text)
        statement = "Qualité (méthode EasyTrade) : " + " ; ".join(parts)
        composite = ledger.add(EvidenceDraft(
            type="metric", claim_kind="HYPOTHESE", subject=ticker, statement=statement,
            observed_at=max(published), published_at=max(published), source=method_src,
            processing=("Moyenne des rangs centiles : ROE parmi les actions de l'univers ; dette / fonds propres "
                        "dans le secteur seulement (au moins deux actions) ; marge nette quand elle existe"),
            produced_by=f"engine.quality@{VERSION}",
            limits="Méthode de l'équipe (hypothèse) ; ne compare pas les modèles d'affaires ; pas de FNB ni de crypto.",
        )).evidence_id
        signals[ticker]["qualite"] = quality.score
        evidence[ticker]["qualite"] = composite
        evidence[ticker]["qualite_composantes"] = tuple(ids)


ESG_THRESHOLD_STATEMENT = "Seuil d'émetteur majeur retenu par EasyTrade (émissions directes de GES par an)"


def _add_esg_evidence(assets: pd.DataFrame, signals: dict, evidence: dict, ledger: EvidenceLedger,
                      registry: SourcesRegistry, reference_dir: Path) -> dict[str, esg.EsgAssessment]:
    """Critère `esg` (engine.esg) : preuves ESG datées de chaque actif (mêmes preuves que l'outil
    `preuves_esg`, réutilisées si la recherche les a déjà demandées), constat par actif et score
    absolu. Un constat non concluant laisse le critère manquant, preuves visibles dans le dossier."""
    tools = ResearchTools(assets, ledger.as_of, reference_dir, ledger, registry)
    tickers = [str(t) for t in assets["ticker"]]
    rows = {t: tools.preuves_esg(t) for t in tickers}
    assessments = esg.assess(assets[["ticker", "sector"]].to_dict("records"), rows)
    method_src = registry.require_used(SOURCE_HYPOTHESES).as_evidence_source()
    as_of = ledger.as_of
    threshold_id: Optional[str] = None
    for ticker in tickers:
        found = assessments.get(ticker)
        if found is None:
            continue
        evidence[ticker]["esg_preuves"] = found.evidence_ids
        basis = list(found.basis_ids)
        if found.finding == "emetteur_majeur":
            threshold_id = threshold_id or ledger.add(EvidenceDraft(
                type="esg", claim_kind="HYPOTHESE", subject="EasyTrade", statement=ESG_THRESHOLD_STATEMENT,
                value=esg.MAJOR_EMITTER_TONNES / 1_000_000, unit="Mt CO2e", observed_at=as_of, published_at=as_of,
                source=method_src,
                processing="Ordre de grandeur fixé par l'équipe, au-dessus des écarts de méthode entre sources (AR4, AR5)",
                produced_by=f"engine.esg@{VERSION}",
                limits="Choix de l'équipe, pas une norme ; les émissions documentées sont des bornes inférieures.",
            )).evidence_id
            basis.append(threshold_id)
            statement = ("ESG (méthode EasyTrade) : émetteur majeur documenté, émissions directes déclarées "
                         "au-dessus du seuil retenu")
            processing = ("Plus grande borne inférieure documentée parmi les preuves d'émissions du titre, comparée "
                          "au seuil d'émetteur majeur ; score ESG nul (préoccupation documentée)")
        elif found.finding == "controverse":
            statement = "ESG (méthode EasyTrade) : controverse documentée"
            processing = "Preuve de type « Controverse » publiée à la date d'analyse ; score ESG nul"
        elif found.finding == "filtre_esg":
            statement = "ESG (méthode EasyTrade) : titre ESG prouvé par un document daté (filtre ESG)"
            processing = "Preuve « Filtre ESG » de esg_evidence.csv publiée à la date d'analyse ; score ESG maximal"
        else:  # non concluant : critère manquant, preuves gardées pour le dossier
            continue
        signals[ticker]["esg"] = found.score
        evidence[ticker]["esg"] = ledger.add(EvidenceDraft(
            type="esg", claim_kind="HYPOTHESE", subject=ticker, statement=statement, value=found.score,
            unit="score", observed_at=as_of, published_at=as_of, source=method_src, processing=processing,
            produced_by=f"engine.esg@{VERSION}",
            limits=("Méthode de l'équipe (hypothèse) ; dimension environnementale seulement (émissions directes) "
                    "ou classification d'un fonds ; ni sociale ni gouvernance."),
        )).evidence_id
        evidence[ticker]["esg_composantes"] = tuple(dict.fromkeys(basis))
    return assessments


def _esg_sets(assessments: dict) -> tuple[frozenset[str], frozenset[str]]:
    """(titres avec controverse documentée, émetteurs majeurs documentés) pour les contraintes dures."""
    rules = esg.exclusions(assessments)
    return (frozenset(t for t, r in rules.items() if r == esg.RULE_CONTROVERSY),
            frozenset(t for t, r in rules.items() if r == esg.RULE_EMISSIONS))


def _build_pack(ticker: str, assets_by_ticker: dict, metrics: pd.DataFrame, evidence: dict,
                weighting: WeightingResult, candidates: CandidateList, ledger: EvidenceLedger,
                cash_id: Optional[str] = None) -> EvidencePack:
    roles: dict[str, str] = {}
    if cash_id:
        roles[cash_id] = "macro:taux_directeur_moyen"
    rows = metrics[(metrics["ticker"] == ticker) & metrics["evidence_id"].notna()]
    for _, row in rows.iterrows():
        roles[row["evidence_id"]] = f"{row['metric']}:{row['window']}"
    for criterion in ("diversification", "preferences", "qualite", "esg"):
        evidence_id = evidence.get(ticker, {}).get(criterion)
        if evidence_id:
            roles[evidence_id] = f"signal:{criterion}"
    for evidence_id in evidence.get(ticker, {}).get("qualite_composantes", ()):
        roles[evidence_id] = "fondamentaux"
    for key in ("esg_preuves", "esg_composantes"):
        for evidence_id in evidence.get(ticker, {}).get(key, ()):
            roles.setdefault(evidence_id, "esg")
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


def _risk_table(metrics: pd.DataFrame) -> dict[str, tuple[Optional[float], Optional[float]]]:
    """ticker → (volatilité annualisée %, perte maximale %) sur toute la période : entrées de la règle
    de tolérance au risque (`engine.constraints`)."""
    tickers = sorted(set(metrics["ticker"]))
    return {t: (_metric(metrics, t, "annualized_volatility")[0], _metric(metrics, t, "max_drawdown")[0])
            for t in tickers}


def _horizon(weighting: WeightingResult) -> str:
    """Indicateur du critère horizon selon l'horizon minimal déclaré du profil."""
    return horizon_metric(weighting.profile.horizon_annees.min)


def _tolerance_evidence(ticker: str, metrics: pd.DataFrame, weighting: WeightingResult) -> tuple[str, ...]:
    """Preuves d'une exclusion par la tolérance : indicateurs de l'actif, repères et tolérance déclarée."""
    ids = [_metric(metrics, ticker, "annualized_volatility")[1], _metric(metrics, ticker, "max_drawdown")[1],
           weighting.limit_evidence.get("volatilite"), weighting.limit_evidence.get("perte_max")]
    tolerance = weighting.fact("tolerance")
    ids.append(tolerance.evidence_id if tolerance else None)
    return tuple(dict.fromkeys(i for i in ids if i))


def _rule_evidence(rule: str, weighting: WeightingResult) -> tuple[str, ...]:
    """Preuves d'une règle du profil : la valeur de la règle (hypothèse) et la phrase du profil qui la fonde."""
    name = {
        governance.RULE_SECTOR: "max_weight_per_sector",
        governance.RULE_CRYPTO: "max_weight_crypto",
        esg.RULE_EMISSIONS: "esg_exclusion",
    }.get(rule, rule)
    ids = [weighting.constraint_evidence[name]] if name in weighting.constraint_evidence else []
    ids.extend(weighting.rationale_evidence(f"hard_constraints.{name}"))
    if not ids:  # règle sans valeur chiffrée ni phrase rattachée : on cite la tolérance déclarée
        tolerance = weighting.fact("tolerance")
        ids.extend([tolerance.evidence_id] if tolerance else [])
    return tuple(dict.fromkeys(ids))


def _rejection_evidence(ticker: str, rule: str, weighting: WeightingResult, evidence: dict) -> tuple[str, ...]:
    """Preuves d'un rejet par une règle : celles de la règle, plus, pour une exclusion ESG, les preuves
    datées du titre qui la fondent (émissions et seuil, ou controverse)."""
    ids = list(_rule_evidence(rule, weighting))
    if rule in (esg.RULE_CONTROVERSY, esg.RULE_EMISSIONS):
        ids.extend(evidence.get(ticker, {}).get("esg_composantes", ()))
    return tuple(dict.fromkeys(ids))


def _metric(metrics: pd.DataFrame, ticker: str, metric: str, window: str = "full") -> tuple[Optional[float], Optional[str]]:
    rows = metrics[(metrics["ticker"] == ticker) & (metrics["metric"] == metric) & (metrics["window"] == window)]
    if rows.empty or pd.isna(rows.iloc[0]["value"]):
        return None, None
    return float(rows.iloc[0]["value"]), rows.iloc[0]["evidence_id"]


def _build_coherence(
    ticker: str, *, ws: Workspace, assets: pd.DataFrame, names: dict[str, str], metrics: pd.DataFrame,
    signals: dict, evidence: dict, weighting: WeightingResult, decision: Decision, ledger: EvidenceLedger,
    ignore: tuple[str, ...], dropped: list[str], assessments: Optional[dict] = None,
) -> CoherenceAnalysis:
    """« Tester une idée » : tensions chiffrées et sourcées, verdict, effet sur le panier simulé, alternatives."""
    as_of = ledger.as_of
    weights = weighting.profile_weights
    prices_src = ws.registry.require_used(SOURCE_PRICES).as_evidence_source()
    risk = _risk_table(metrics)
    window = horizon_label(_horizon(weighting))
    controversial, emitters = _esg_sets(assessments or {})
    report = evaluate_idea(ticker, assets, signals, evidence, weights, as_of, esg_controversial=controversial,
                           esg_emitters=emitters, risk=risk, risk_level=weighting.risk_level, horizon_label=window)
    full = decide(assets, signals, evidence, weights, as_of, esg_controversial=controversial,
                  esg_emitters=emitters, risk=risk, risk_level=weighting.risk_level)
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
        "horizon": median_evidence(
            "horizon", f"Médiane de la pire période glissante de {window} des actifs classés pour ce profil"),
    }
    volatility, volatility_id = _metric(metrics, ticker, "annualized_volatility")
    drawdown, drawdown_id = _metric(metrics, ticker, "max_drawdown")
    asset_class = str(assets.loc[assets["ticker"] == ticker, "asset_class"].iloc[0])
    all_tensions = list(report.tensions) + limit_tensions(
        level=weighting.risk_level, volatility=volatility, max_drawdown=drawdown,
        volatility_evidence=volatility_id, drawdown_evidence=drawdown_id, limit_evidence=weighting.limit_evidence,
        capped_class=is_capped_class(asset_class, weights.constraints),
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
            rule = next((r.rule for r in decision.rejected if r.ticker == ticker and r.rule != RULE_TOLERANCE), "")
            ids: list[Optional[str]] = list(_rejection_evidence(ticker, rule, weighting, evidence))
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


# --- exécution par étapes -------------------------------------------------------------------------
# Le pipeline est découpé en étapes qui partagent un `RunContext`. En local, `run_pipeline` les
# enchaîne dans le même processus. Sur AWS, chaque étape est une fonction Lambda de la machine
# d'états (orchestration/handlers) : le contexte est enregistré sur S3 entre deux étapes.
# Le débat est la seule étape découpée par candidat (état `Map`) : il lit le registre de preuves
# sans jamais y écrire, ce qui permet d'exécuter les candidats en parallèle sans changer les
# identifiants de preuves.
STAGES = ("profil", "validation", "recherche", "dossiers_de_preuves", "debat", "decision", "explication")


@dataclass
class RunContext:
    """État d'une analyse entre deux étapes (sérialisable : enregistré sur S3 sur AWS)."""

    run_id: str
    as_of: date
    profile_id: str
    requested_ticker: Optional[str]
    profile_source: str
    reading_level: str
    max_candidates: Optional[int]
    ledger: EvidenceLedger
    trace: TraceRecorder
    result: RunResult
    profile: Optional[Profile] = None
    persona: Optional[dict] = None  # entrée de profil fictif (absente de personas.json), transmise par l'API
    weighting: Optional[WeightingResult] = None
    metrics: Optional[pd.DataFrame] = None
    candidates: Optional[CandidateList] = None
    signals: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    without_metrics: list = field(default_factory=list)
    esg: dict = field(default_factory=dict)  # ticker → engine.esg.EsgAssessment
    decision: Optional[Decision] = None
    selection: Optional[governance.BasketSelection] = None
    packs: dict = field(default_factory=dict)
    debate_started: Optional[str] = None
    records: dict = field(default_factory=dict)
    coherence: Optional[CoherenceAnalysis] = None
    finished: bool = False

    def detach(self) -> "RunContext":
        """Retire le rappel de progression (non sérialisable) avant l'enregistrement."""
        self.trace.set_on_step(None)
        return self


def _universe(ws: Workspace) -> tuple[pd.DataFrame, dict, dict, tuple]:
    assets = ws.store.assets()
    assets_by_ticker = {str(r["ticker"]): {k: str(r[k]) for k in ("name", "asset_class", "sector")}
                        for _, r in assets.iterrows()}
    names = {ticker: a["name"] for ticker, a in assets_by_ticker.items()}
    ignore = (*names.values(), *names.keys())  # noms contenant des chiffres (« S&P 500 ») et tickers
    return assets, assets_by_ticker, names, ignore


def with_persona(ws: Workspace, persona: Optional[dict]) -> Workspace:
    """Espace de travail dont les personas comprennent un profil fictif transmis avec l'analyse."""
    if not persona or any(p["id"] == persona["id"] for p in ws.personas["personas"]):
        return ws
    personas = {**ws.personas, "personas": [*ws.personas["personas"], persona]}
    return Workspace(settings=ws.settings, store=ws.store, registry=ws.registry, personas=personas,
                     forbidden=ws.forbidden)


def new_context(
    ws: Workspace, client: LLMClient, profile_id: str, *, as_of: Optional[DateLike] = None,
    requested_ticker: Optional[str] = None, profile: Optional[Profile] = None, persona: Optional[dict] = None,
    reading_level: str = "simple", max_candidates: Optional[int] = None,
    on_step: Optional[Callable[[TraceStep], None]] = None, profile_source: str = SOURCE_PROFILE,
) -> RunContext:
    as_of_date = to_timestamp(as_of if as_of is not None else ws.settings.as_of).date()
    requested_ticker = requested_ticker.strip().upper() if requested_ticker else None
    run_id = make_run_id(as_of_date, profile_id, requested_ticker)
    ledger = EvidenceLedger(as_of_date)
    trace = TraceRecorder(run_id, as_of_date, profile_id, on_step=on_step)
    result = RunResult(run_id=run_id, status="echec", as_of=as_of_date, profile_id=profile_id,
                       requested_ticker=requested_ticker, model_id=client.model_id("strong"),
                       trace=trace.to_trace(), ledger=ledger)
    return RunContext(run_id=run_id, as_of=as_of_date, profile_id=profile_id, requested_ticker=requested_ticker,
                      profile_source=profile_source, reading_level=reading_level, max_candidates=max_candidates,
                      ledger=ledger, trace=trace, result=result, profile=profile, persona=persona)


# 1. Profil → ProfileWeights
def stage_profile(ctx: RunContext, ws: Workspace, client: LLMClient) -> None:
    ws = with_persona(ws, ctx.persona)
    _, _, names, _ = _universe(ws)
    if ctx.requested_ticker and ctx.requested_ticker not in names:
        raise UnknownTickerError(f"Titre absent de l'univers analysé : {ctx.requested_ticker}")
    with ctx.trace.step("profil", "llm") as step:
        profile = ctx.profile or ws.profile(ctx.profile_id)
        weighting, info = weigh_profile(profile, template_for(profile, ws.personas), client, ctx.ledger,
                                        ws.registry, forbidden=ws.forbidden, profile_source=ctx.profile_source)
        step.set(**_llm_fields([info]), outputs=weighting.evidence_ids)
        step.note(f"Niveau de risque : {weighting.risk_level} ; thèmes : "
                  f"{', '.join(weighting.preferred_themes) or 'aucun'} ; écarts au gabarit : "
                  f"{', '.join(weighting.deviations) or 'aucun'}.")
    ctx.profile = profile
    ctx.weighting = ctx.result.weighting = weighting


# 2a. Validation : indicateurs déterministes pour tout l'univers, à la date as_of
def stage_validation(ctx: RunContext, ws: Workspace, client: LLMClient) -> None:
    with ctx.trace.step("validation", "code", version=f"validation@{VERSION}", inputs=STARTER_INPUTS) as step:
        before = len(ctx.ledger)
        metrics = compute_metrics_table(ws.store, ctx.as_of, ctx.ledger, ws.registry, ws.settings.quality)
        step.note(f"{len(metrics)} indicateurs calculés, {len(ctx.ledger) - before} preuves créées, "
                  f"aucune donnée publiée après le {ctx.as_of}.")
    ctx.metrics = ctx.result.metrics = metrics


# 2b. Recherche : candidats et preuves qualitatives
def stage_research(ctx: RunContext, ws: Workspace, client: LLMClient) -> None:
    assets, _, _, _ = _universe(ws)
    with ctx.trace.step("recherche", "llm") as step:
        tools = ResearchTools(assets, ctx.as_of, ws.settings.reference_dir, ctx.ledger, ws.registry)
        candidates, info = run_research(ctx.weighting, tools, client, requested_ticker=ctx.requested_ticker,
                                        max_candidates=ctx.max_candidates, forbidden=ws.forbidden)
        step.set(**_llm_fields([info]), tools_called=candidates.tools_called, outputs=candidates.tickers)
        notes = sorted({c["note"] for c in tools.calls if c["note"]})
        step.note(f"{len(candidates.candidates)} candidats. " + " ".join(notes))
        if candidates.dropped:
            step.note(f"Propositions retirées (hors univers) : {', '.join(candidates.dropped)}.")
    ctx.candidates = ctx.result.candidates = candidates


# 3. Dossiers de preuves : jointure, contraintes dures, pré-classement (aucun LLM)
def stage_evidence_packs(ctx: RunContext, ws: Workspace, client: LLMClient) -> None:
    assets, assets_by_ticker, _, _ = _universe(ws)
    weighting, candidates, metrics = ctx.weighting, ctx.candidates, ctx.metrics
    weights = weighting.profile_weights
    with ctx.trace.step("dossiers_de_preuves", "code", version=f"engine@{VERSION}") as step:
        signals, evidence = build_signals(metrics, assets, horizon=_horizon(weighting))
        assessments = _add_esg_evidence(assets, signals, evidence, ctx.ledger, ws.registry, ws.settings.reference_dir)
        _add_signal_evidence(assets, weighting, signals, evidence, ctx.ledger, ws.registry, ws.store,
                             ws.settings.quality.min_common_observations, frozenset(esg.proven(assessments)))
        _add_quality_evidence(assets, signals, evidence, ctx.ledger, ws.registry, ws.settings.reference_dir)
        controversial, emitters = _esg_sets(assessments)
        without_metrics = [t for t in candidates.tickers
                           if any(signals[t].get(c) is None for c in REQUIRED_SIGNALS)]
        classable = [t for t in candidates.tickers if t not in without_metrics]
        decision = decide(assets, signals, evidence, weights, ctx.as_of, candidates=classable,
                          esg_controversial=controversial, esg_emitters=emitters,
                          risk=_risk_table(metrics), risk_level=weighting.risk_level)
        selection = governance.select_basket(() if decision.no_recommendation else decision.ranking,
                                             weights.constraints)
        to_debate = list(dict.fromkeys(
            [*selection.tickers, *(r.ticker for r in selection.displaced),
             *([ctx.requested_ticker] if ctx.requested_ticker and ctx.requested_ticker in classable else [])]))
        cash_id = _add_cash_evidence(ws.store, ctx.ledger, ws.registry) if to_debate else None
        packs = {t: _build_pack(t, assets_by_ticker, metrics, evidence, weighting, candidates, ctx.ledger, cash_id)
                 for t in to_debate}
        step.set(outputs=tuple(to_debate))
        step.note(f"{len(decision.ranking)} candidats classés ; {len(to_debate)} dossiers de preuves.")
        def found(kind: str) -> str:
            return ", ".join(sorted(t for t, a in assessments.items() if a.finding == kind)) or "aucun"

        step.note(f"Critère ESG — controverses documentées : {found('controverse')} ; émetteurs majeurs documentés : "
                  f"{found('emetteur_majeur')} ; fonds à filtre ESG : {found('filtre_esg')} ; preuves non concluantes : "
                  f"{found('non_concluant')} ; actifs sans preuve ESG : {len(assets) - len(assessments)}.")
    control = governance.control_pre_debate(
        universe=len(assets), rejected_by_rule=len(decision.rejected), without_evidence=len(without_metrics),
        candidates=len(decision.ranking))
    ctx.trace.control(control.name, control.passed, control.note)
    ctx.signals, ctx.evidence, ctx.without_metrics, ctx.esg = signals, evidence, without_metrics, assessments
    ctx.decision, ctx.selection, ctx.packs = decision, selection, packs
    ctx.debate_started = ctx.trace.now()


# 4. Débat : Bull ∥ Réaliste ∥ Bear, mêmes preuves, tours 1 et 3
def debate_jobs(ctx: RunContext) -> list[str]:
    """Candidats à débattre, dans l'ordre (un élément de l'état `Map` par candidat sur AWS)."""
    return list(ctx.packs)


def debate_one(ctx: RunContext, ws: Workspace, client: LLMClient, ticker: str,
               max_workers: int = 1) -> tuple[DebateRecord, list[CallInfo]]:
    """Débat d'un candidat. Lit le registre de preuves sans y écrire : exécutable en parallèle."""
    _, _, _, ignore = _universe(ws)
    return run_debate(ctx.packs[ticker], ctx.weighting, client, ctx.ledger, forbidden=ws.forbidden,
                      ignore=ignore, max_workers=max_workers)


def record_debate_failure(ctx: RunContext, error: "BaseException | str") -> None:
    note = error if isinstance(error, str) else f"{type(error).__name__} : {error}"
    ctx.trace.record("debat", "llm", "echec", started_at=ctx.debate_started, note=note)


def record_debate(ctx: RunContext, results: dict[str, tuple[DebateRecord, list[CallInfo]]]) -> None:
    """Rassemble les débats des candidats (dans l'ordre des dossiers) et les inscrit dans la trace."""
    trace, packs, started = ctx.trace, ctx.packs, ctx.debate_started
    records: dict[str, DebateRecord] = {}
    # Une réponse invalide isolée est tolérée (agents.debate.protocol) ; un agent qui n'a répondu pour
    # aucun candidat signale une panne systématique : le débat n'a pas eu lieu, l'analyse échoue.
    if packs:
        for agent in AGENTS:
            silent = [t for t in packs if all(UNANSWERED in turn.open_questions
                                               for turn in results[t][0].round1 if turn.agent == agent)]
            if len(silent) == len(packs):
                message = (f"LLMOutputError : Étape {step_name(agent, 1)} : réponses invalides pour tous les "
                           f"candidats ({len(silent)}).")
                record_debate_failure(ctx, message)
                raise LLMOutputError(message.removeprefix("LLMOutputError : "))
    if packs:
        infos: list[CallInfo] = []
        for ticker in packs:
            record, calls = results[ticker]
            records[ticker] = record
            infos.extend(calls)
        for round_number in (1, 3):
            for agent in AGENTS:
                name = step_name(agent, round_number)
                turns = [t for r in records.values() for t in (r.round1 if round_number == 1 else r.final)
                         if t.agent == agent]
                removed = sum(t.removed_arguments for t in turns)
                trace.record(
                    name, "llm", started_at=started, **_llm_fields(i for i in infos if i.step == name),
                    outputs=tuple(records),
                    evidence_in=tuple(sorted({i for p in packs.values() for i in p.evidence_ids})),
                    note=f"{len(turns)} candidats ; {sum(len(t.arguments) for t in turns)} arguments gardés, "
                         f"{removed} supprimés (preuve absente ou nombre non étayé).",
                )
    else:
        trace.record("debat", "llm", "ignore",
                     note="Aucun candidat à débattre : "
                          + (ctx.decision.reason or "aucun dossier.").removeprefix("Aucune recommandation : "))
    ctx.records = ctx.result.debate = records


def stage_debate(ctx: RunContext, ws: Workspace, client: LLMClient, max_workers: int = 1,
                 candidate_workers: int = 1) -> None:
    """Débat de tous les candidats dans le même processus (exécution locale).

    `candidate_workers` > 1 débat plusieurs candidats en même temps, comme l'état `Map` sur AWS : le
    débat ne fait que lire le registre de preuves, et les résultats sont rassemblés dans l'ordre des
    dossiers, donc le résultat est le même qu'en série.
    """
    jobs = debate_jobs(ctx)
    try:
        if candidate_workers > 1 and len(jobs) > 1:
            with ThreadPoolExecutor(max_workers=min(candidate_workers, len(jobs))) as pool:
                futures = {t: pool.submit(debate_one, ctx, ws, client, t, max_workers) for t in jobs}
                results = {t: futures[t].result() for t in jobs}
        else:
            results = {t: debate_one(ctx, ws, client, t, max_workers=max_workers) for t in jobs}
    except Exception as error:
        record_debate_failure(ctx, error)
        raise
    record_debate(ctx, results)


# 5. Décision : confiance, désaccords, panier, cohérence d'une demande (aucun LLM)
def stage_decision(ctx: RunContext, ws: Workspace, client: LLMClient) -> None:
    assets, _, names, ignore = _universe(ws)
    weighting, selection, records = ctx.weighting, ctx.selection, ctx.records
    weights = weighting.profile_weights
    decision = ctx.decision
    dropped_claims: list[str] = []
    coherence: Optional[CoherenceAnalysis] = None
    with ctx.trace.step("decision", "code", version=f"engine@{VERSION}") as step:
        decision = apply_debate(decision, records.values(), profile_evidence_ids=weighting.evidence_ids)
        updates: dict[str, Any] = {"retained": selection.tickers, "displaced": selection.displaced}
        confidences = [decision.candidate_confidence.get(t) for t in selection.tickers]
        # Confiance faible partout : aucune recommandation, sauf si un avertissement l'explique déjà (critère
        # prioritaire sans donnée) : les pistes sont alors montrées avec cet avertissement.
        if selection.tickers and all(c == "faible" for c in confidences) and not decision.warnings:
            updates.update(no_recommendation=True, reason=LOW_CONFIDENCE_REASON)
        showing = not (decision.no_recommendation or updates.get("no_recommendation"))
        if showing and esg_focused(weights.weights):
            warning = esg.focus_warning(esg.proven(ctx.esg), selection.tickers,
                                        {r.ticker: r.rule for r in decision.rejected},
                                        [c.ticker for c in decision.ranking])
            if warning:
                updates["warnings"] = (*decision.warnings, warning)
        decision = decision.model_copy(update=updates)
        if ctx.requested_ticker:
            coherence = _build_coherence(
                ctx.requested_ticker, ws=ws, assets=assets, names=names, metrics=ctx.metrics, signals=ctx.signals,
                evidence=ctx.evidence, weighting=weighting, decision=decision, ledger=ctx.ledger, ignore=ignore,
                dropped=dropped_claims, assessments=ctx.esg)
            step.note(f"Tester une idée — {ctx.requested_ticker} : {coherence.verdict}, "
                      f"{len(coherence.tensions)} tension(s).")
        step.set(outputs=decision.retained)
        step.note(f"{len(decision.retained)} pistes retenues ; {len(decision.disagreements)} désaccord(s) conservé(s) ; "
                  f"{len(decision.to_review)} à examiner.")
        if dropped_claims:
            step.note("Affirmations retirées par le vérificateur : " + " | ".join(dropped_claims))
    ctx.decision = ctx.result.decision = decision
    ctx.coherence = coherence
    for control in (governance.control_basket(selection, weights.constraints),
                    governance.control_diversification(selection),
                    governance.control_no_recommendation(decision.no_recommendation, decision.reason)):
        ctx.trace.control(control.name, control.passed, control.note)


# 6. Explication : rédaction, vérificateur de fidélité, filtre de formulations
def stage_explanation(ctx: RunContext, ws: Workspace, client: LLMClient) -> None:
    _, _, _, ignore = _universe(ws)
    decision, weighting = ctx.decision, ctx.weighting
    rejected = [
        RejectedItem(ticker=r.ticker, reason=r.reason, kind="contrainte",
                     evidence_ids=(_tolerance_evidence(r.ticker, ctx.metrics, weighting) if r.rule == RULE_TOLERANCE
                                   else _rejection_evidence(r.ticker, r.rule, weighting, ctx.evidence)))
        for r in decision.rejected
        # Le titre soumis par l'utilisateur n'est pas « écarté » en silence : l'analyse de cohérence
        # (verdict, tensions chiffrées, alternatives) en rend compte en entier.
        if not (r.rule == RULE_TOLERANCE and r.ticker == ctx.requested_ticker)
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
        for t in ctx.without_metrics
    )
    simulated_run = client.model_id("strong") == simulated.MODEL_ID
    with ctx.trace.step("explication", "llm") as step:
        explanation, report, infos = explain(
            run_id=ctx.run_id, decision=decision, weighting=weighting, packs=ctx.packs, records=ctx.records,
            rejected=rejected, coherence=ctx.coherence, client=client, ledger=ctx.ledger, forbidden=ws.forbidden,
            ignore=ignore, reading_level=ctx.reading_level, notes=(simulated.NOTE,) if simulated_run else (),
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
    ctx.trace.control(control.name, control.passed, control.note)
    ctx.result.fidelity = report
    if not report.faithful:
        raise RuntimeError(
            "Explication non affichée : le vérificateur de fidélité relève encore "
            f"{len(report.final_issues)} écart(s) : "
            + " | ".join(f"{i.where} ({', '.join(i.codes)})" for i in report.final_issues[:5]))
    ctx.result.explanation, ctx.result.status = explanation, "termine"


def fail(ctx: RunContext, error: "BaseException | str") -> RunResult:
    """Échec propre : visible dans le résultat et dans la trace."""
    ctx.result.status = "echec"
    ctx.result.error = error if isinstance(error, str) else f"{type(error).__name__} : {error}"
    return finish(ctx)


def finish(ctx: RunContext) -> RunResult:
    ctx.result.trace = ctx.trace.to_trace()
    ctx.finished = True
    return ctx.result


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
    candidate_workers: int = 1,
    on_step: Optional[Callable[[TraceStep], None]] = None,
    profile_source: str = SOURCE_PROFILE,
) -> RunResult:
    """Exécute une analyse complète. Un échec d'étape donne `status = "echec"`, trace à l'appui.

    `on_step` est appelé à la fermeture de chaque étape (progression affichée par le mobile).
    `profile_source` : source des phrases du profil (énoncé du case, ou questionnaire de l'application).
    `max_workers` : agents d'un même tour en parallèle ; `candidate_workers` : candidats débattus en parallèle.
    Les étapes sont celles de la machine d'états AWS, enchaînées dans le même processus.
    """
    ws = workspace or Workspace.load()
    client = client or make_client("auto")
    ctx = new_context(ws, client, profile_id, as_of=as_of, requested_ticker=requested_ticker, profile=profile,
                      reading_level=reading_level, max_candidates=max_candidates, on_step=on_step,
                      profile_source=profile_source)
    try:
        stage_profile(ctx, ws, client)
        stage_validation(ctx, ws, client)
        stage_research(ctx, ws, client)
        stage_evidence_packs(ctx, ws, client)
        stage_debate(ctx, ws, client, max_workers=max_workers, candidate_workers=candidate_workers)
        stage_decision(ctx, ws, client)
        stage_explanation(ctx, ws, client)
    except Exception as error:
        return fail(ctx, error)
    return finish(ctx)
