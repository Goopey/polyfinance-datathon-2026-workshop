"""Service de l'API : exécute le pipeline, garde les runs, traduit vers les contrats du mobile.

Conception : docs/01_ARCHITECTURE.md (API), mobile/src/types/contracts.ts
Rôle : la couche de présentation entre le pipeline (schémas internes) et le mobile (contrats de
`schemas/api.py`). Aucune décision n'est prise ici : le service appelle `run_pipeline`, puis
recopie ce que le moteur et les agents ont produit.

Points à connaître :
- Les identifiants de preuves sont propres à un run (`EV-000412` ne désigne pas la même preuve
  dans deux runs). Toute lecture de preuve, de fiche ou de graphe précise donc son `run_id` ;
  sans run, on lit un registre « hors run » calculé à la même date.
- Les runs et les profils fictifs sont gardés en mémoire du processus (développement local).
  Sur AWS (P4), ce stockage passe à DynamoDB / S3 : seule cette classe change.
- Un profil fictif devient une entrée de persona (mêmes clés que `personas.json`) : le pipeline
  le traite comme un persona, sans cas particulier.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import pandas as pd

from easytrade.agents.llm_client import LLMClient, make_client
from easytrade.agents.profile_weighting import SOURCE_PROFILE, WeightingResult, weigh_profile
from easytrade.agents.simulated import MODEL_ID as SIMULATED_MODEL_ID
from easytrade.agents.tools import ResearchTools
from easytrade.data.point_in_time import to_timestamp
from easytrade.engine.coherence import RISK_LIMITS, tolerance_level
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.orchestration.pipeline import RunResult, Workspace, make_run_id, run_pipeline
from easytrade.schemas.api import (
    RUN_STEPS,
    AnalystSentiment,
    AssetMetricView,
    AssetSheet,
    AssetSummary,
    DataOverview,
    DependencyGraph,
    GraphEdge,
    GraphNode,
    HardConstraintsView,
    InsiderSentiment,
    PricePoint,
    PriceSeries,
    ProfileDraft,
    ProfileWeightsView,
    QualityCheck,
    RationaleView,
    RunRequest,
    RunStatusView,
    RunStepView,
    SentimentView,
    SourceInfo,
)
from easytrade.data.sentiment import latest_sentiment, load_sentiment, sentiment_label
from easytrade.schemas.debate import Claim
from easytrade.schemas.evidence import EvidenceDraft
from easytrade.schemas.evidence import Evidence
from easytrade.schemas.profile import Profile
from easytrade.schemas.trace import RunTrace, TraceStep
from easytrade.schemas.weights import CRITERIA, ProfileWeights
from easytrade.validation.data_quality import build_quality_report
from easytrade.validation.metrics import compute_metrics_table

SOURCE_QUESTIONNAIRE = "profil_questionnaire"

# --- questionnaire → profil fictif (hypothèses de l'équipe, docs/03_DECISION_ENGINE.md) --------
TEMPLATE_BY_TOLERANCE = {"faible": "robert", "moderee": "mateo", "elevee": "amira"}
TOLERANCE_LABEL = {"faible": "faible", "moderee": "modéré", "elevee": "élevé"}
HORIZON_YEARS: dict[str, tuple[int, Optional[int]]] = {"court": (3, 5), "moyen": (5, 12), "long": (12, None)}
OBJECTIF_TEXT = {
    "preserver": "Préserver son capital.",
    "equilibre": "Faire croître son capital de façon équilibrée.",
    "croissance": "Faire croître son capital à long terme.",
}
PREFERENCE_TEXT = {
    "esg": "Accorde une grande importance aux facteurs ESG",
    "technologies": "Intéressé par les technologies et l'innovation",
    "stabilite": "Accorde de l'importance à la stabilité et préfère les entreprises établies",
    "diversification": "Souhaite maintenir une certaine diversification et éviter de miser exclusivement sur un seul secteur",
}
# Exclusion → (phrase du profil, resserrement d'une contrainte dure). Seules les règles que le moteur
# sait appliquer sont proposées : une exclusion non appliquée serait une promesse non tenue.
EXCLUSION_RULES: dict[str, tuple[str, dict[str, Any]]] = {
    "crypto": ("Peu intéressé par les cryptoactifs", {"max_weight_crypto": 0.0}),
    "speculatif": ("Peu intéressé par les placements hautement spéculatifs", {"speculatif": "exclu"}),
    "controverses": (
        "Souhaite éviter les entreprises liées à des controverses environnementales ou sociales importantes",
        {"esg_exclusion": True},
    ),
}

# --- fiche d'un actif : indicateurs affichés -----------------------------------------------------
# (identifiant mobile, libellé, indicateur, fenêtre, libellé de fenêtre, repère du profil, mode Avancé)
SHEET_METRICS: tuple[tuple[str, str, str, str, str, Optional[int], bool], ...] = (
    ("volatilite", "Volatilité", "annualized_volatility", "full", "toute la période disponible", 0, False),
    ("perte_max", "Perte maximale", "max_drawdown", "full", "toute la période disponible", 1, False),
    ("pire_periode", "Pire période de 3 ans", "worst_rolling_3y", "full", "toute la période, fenêtres glissantes de 3 ans", None, False),
    ("rendement_annualise", "Rendement annualisé observé", "annualized_return", "full", "toute la période disponible", None, True),
    ("rendement_2022", "Rendement sur l'année 2022", "return_2022", "2022", "l'année 2022", None, True),
)
SIGNAL_TYPES = ("esg", "news", "filing")
RELATIONS = ("FOURNISSEUR", "CLIENT", "CONCURRENT", "PARTENAIRE")
QUALITY_STATUS = {"pass": "ok", "warn": "avertissement", "fail": "erreur"}
MAX_QUALITY_DETAILS = 8


SOURCE_SENTIMENT = "finnhub"
MONTHS_FR = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
             "novembre", "décembre")


def _month_fr(day: date) -> str:
    return f"{MONTHS_FR[day.month - 1]} {day.year}"


class NotFound(LookupError):
    """Ressource absente : profil, run, actif ou preuve inconnus (HTTP 404)."""


class InvalidRequest(ValueError):
    """Demande invalide (HTTP 422)."""


@dataclass
class RunEntry:
    run_id: str
    profile_id: str
    as_of: date
    requested_ticker: Optional[str]
    steps: list[TraceStep] = field(default_factory=list)  # alimentée pendant l'exécution
    result: Optional[RunResult] = None


@dataclass
class EvidenceContext:
    """Registre de preuves et table d'indicateurs d'un run, ou « hors run » à une date donnée."""

    as_of: date
    ledger: EvidenceLedger
    metrics: pd.DataFrame


def _horizon_text(low: int, high: Optional[int]) -> str:
    return f"{low} ans et plus" if high is None else f"{low} à {high} ans"


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise InvalidRequest("Les poids doivent avoir une somme strictement positive.")
    out = {c: round(weights[c] / total, 6) for c in CRITERIA}
    largest = max(out, key=out.get)
    out[largest] = round(out[largest] + (1.0 - sum(out.values())), 6)
    return out


class ApiService:
    def __init__(self, workspace: Optional[Workspace] = None, client: Optional[LLMClient] = None,
                 max_workers: int = 2):
        base = workspace or Workspace.load()
        self._base_personas: list[dict] = list(base.personas["personas"])
        # Copie privée des personas : les profils fictifs y sont ajoutés, `personas.json` n'est jamais modifié.
        self._personas: dict = {**base.personas, "personas": list(self._base_personas)}
        self.ws = Workspace(settings=base.settings, store=base.store, registry=base.registry,
                            personas=self._personas, forbidden=base.forbidden)
        self.client = client or make_client("auto")
        self._assets = self.ws.store.assets()
        self._names = {str(r["ticker"]): str(r["name"]) for _, r in self._assets.iterrows()}
        self._runs: dict[str, RunEntry] = {}
        self._contexts: dict[date, EvidenceContext] = {}
        self._profile_views: dict[str, ProfileWeightsView] = {}
        self._quality: dict[date, list[QualityCheck]] = {}
        self._sentiment_table = load_sentiment(self.ws.settings.reference_dir)
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="easytrade-run")

    @property
    def default_as_of(self) -> date:
        return self.ws.settings.as_of

    # --- profils ------------------------------------------------------------------------------
    def personas(self) -> list[dict]:
        """Les personas de l'énoncé (les profils fictifs créés par questionnaire n'y figurent pas)."""
        return self._base_personas

    def _entry(self, profile_id: str) -> dict:
        with self._lock:
            for entry in self._personas["personas"]:
                if entry["id"] == profile_id:
                    return entry
        raise NotFound(f"Profil inconnu : {profile_id}")

    def _profile_source(self, entry: dict) -> str:
        return entry.get("_source", SOURCE_PROFILE)

    def _weigh(self, entry: dict) -> WeightingResult:
        """Exécute l'agent de pondération sur un registre jetable : même résultat que dans un run."""
        result, _ = weigh_profile(
            Profile.from_persona(entry), ProfileWeights.from_persona(entry), self.client,
            EvidenceLedger(self.default_as_of), self.ws.registry, forbidden=self.ws.forbidden,
            profile_source=self._profile_source(entry),
        )
        return result

    def profile_view(self, profile_id: str) -> ProfileWeightsView:
        with self._lock:
            cached = self._profile_views.get(profile_id)
        if cached is not None:
            return cached
        entry = self._entry(profile_id)
        weighting = self._weigh(entry)
        weights, constraints = weighting.profile_weights.weights, weighting.profile_weights.constraints
        profil = entry["profil"]
        horizon = _horizon_text(profil["horizon_annees"]["min"], profil["horizon_annees"].get("max"))
        label = entry.get("_label", profil["nom"])
        age = f", {profil['age']} ans" if profil.get("age") else ""
        view = ProfileWeightsView(
            profile_id=profile_id,
            label=label,
            summary=f"{label}{age} · risque {profil['tolerance_risque']} · horizon {horizon}",
            hard_constraints=HardConstraintsView(
                max_weight_per_asset=constraints.max_weight_per_asset,
                max_weight_per_sector=constraints.max_weight_per_sector,
                max_weight_crypto=constraints.max_weight_crypto,
                excluded_asset_classes=["crypto"] if constraints.max_weight_crypto == 0 else [],
                esg_exclusion=constraints.esg_exclusion,
                speculatif=constraints.speculatif,
            ),
            weights={c: weights[c] for c in CRITERIA},
            rationale=[
                *(RationaleView(field=r.field, because=r.because, claim_kind=r.claim_kind) for r in weighting.rationale),
                *([RationaleView(field="weights", because="Poids modifiés à la main sur l'écran de résumé.")]
                  if entry.get("_modified") else []),
                RationaleView(field="weights", because="Poids, plafonds et repères de risque : valeurs de départ "
                                                       "fixées par l'équipe, à calibrer."),
            ],
            missing_information=list(weighting.missing_information),
        )
        with self._lock:
            self._profile_views[profile_id] = view
        return view

    def create_profile(self, draft: ProfileDraft) -> ProfileWeightsView:
        """Crée un profil fictif (questionnaire) ou une variante d'un profil existant (poids modifiés)."""
        unknown = [p for p in draft.preferences if p not in PREFERENCE_TEXT]
        unknown += [e for e in draft.exclusions if e not in EXCLUSION_RULES]
        if unknown:
            raise InvalidRequest(f"Choix non pris en charge : {', '.join(unknown)}")
        if draft.weights_override is not None:
            extra = set(draft.weights_override) - set(CRITERIA)
            if extra or any(v < 0 for v in draft.weights_override.values()):
                raise InvalidRequest("weights_override : critères inconnus ou poids négatifs.")
        digest = hashlib.sha1(
            json.dumps(draft.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:8]

        if draft.base_persona:
            base = self._entry(draft.base_persona)
            entry = copy.deepcopy(base)
            root = base.get("_root", base["id"])
            entry.update(id=f"{root}_{digest}", _root=root)
            if draft.weights_override is not None:
                entry["poids"] = _normalize_weights({**base["poids"], **draft.weights_override})
                entry["_label"] = f"{base['profil']['nom']} (poids modifiés)"
                entry["_modified"] = True
        else:
            template = copy.deepcopy(self._entry(TEMPLATE_BY_TOLERANCE[draft.tolerance]))
            low, high = HORIZON_YEARS[draft.horizon]
            constraints = dict(template["contraintes"])
            preferences = [PREFERENCE_TEXT[p] for p in draft.preferences]
            for exclusion in draft.exclusions:
                sentence, tightening = EXCLUSION_RULES[exclusion]
                preferences.append(sentence)
                constraints.update(tightening)
            weights = dict(template["poids"])
            if draft.weights_override is not None:
                weights = _normalize_weights({**weights, **draft.weights_override})
            entry = {
                "id": f"fictif_{digest}",
                "_root": "fictif",
                "_label": "Profil fictif",
                "_source": SOURCE_QUESTIONNAIRE,
                "_modified": draft.weights_override is not None,
                "profil": {
                    "nom": "Profil fictif",
                    "experience": "",
                    "tolerance_risque": TOLERANCE_LABEL[draft.tolerance],
                    "horizon_annees": {"min": low, "max": high},
                    "objectif": OBJECTIF_TEXT[draft.objectif],
                    "preferences": preferences,
                },
                "poids": weights,
                "contraintes": constraints,
            }
        ProfileWeights.from_persona(entry)  # valide les bornes et la somme des poids
        with self._lock:
            if not any(e["id"] == entry["id"] for e in self._personas["personas"]):
                self._personas["personas"].append(entry)
        return self.profile_view(entry["id"])

    # --- runs ---------------------------------------------------------------------------------
    def _prepare_run(self, request: RunRequest) -> tuple[dict, Optional[str], date, str]:
        """Valide une demande d'analyse : (entrée du profil, titre demandé, date, identifiant du run)."""
        entry = self._entry(request.profile_id)
        ticker = request.requested_ticker.strip().upper() if request.requested_ticker else None
        if ticker and ticker not in self._names:
            raise NotFound(f"Titre absent de l'univers analysé : {ticker}")
        as_of = request.as_of or self.default_as_of
        return entry, ticker, as_of, make_run_id(as_of, request.profile_id, ticker)

    def start_run(self, request: RunRequest) -> str:
        entry, ticker, as_of, run_id = self._prepare_run(request)
        with self._lock:
            existing = self._runs.get(run_id)
            # Le pipeline est déterministe : un run identique déjà lancé ou terminé est réutilisé.
            if existing is not None and (existing.result is None or existing.result.status == "termine"):
                return run_id
            run = RunEntry(run_id=run_id, profile_id=request.profile_id, as_of=as_of, requested_ticker=ticker)
            self._runs[run_id] = run
        self._executor.submit(self._execute, run, self._profile_source(entry))
        return run_id

    def _execute(self, run: RunEntry, profile_source: str) -> None:
        try:
            result = run_pipeline(
                run.profile_id, as_of=run.as_of, requested_ticker=run.requested_ticker, client=self.client,
                workspace=self.ws, on_step=run.steps.append, profile_source=profile_source,
                # Vrai modèle : candidats et agents débattus en parallèle (agents simulés : en série).
                **({} if self.client.model_id("strong") == SIMULATED_MODEL_ID else {"max_workers": 3, "candidate_workers": 4}),
            )
        except Exception as error:  # run_pipeline rend déjà un échec propre ; ceci couvre le reste
            result = RunResult(
                run_id=run.run_id, status="echec", as_of=run.as_of, profile_id=run.profile_id,
                requested_ticker=run.requested_ticker, model_id=self.client.model_id("strong"),
                trace=RunTrace(run_id=run.run_id, as_of=run.as_of, profile_id=run.profile_id, steps=tuple(run.steps)),
                ledger=EvidenceLedger(run.as_of), error=f"{type(error).__name__} : {error}",
            )
        with self._lock:
            run.result = result

    def _run(self, run_id: str) -> RunEntry:
        with self._lock:
            run = self._runs.get(run_id)
        if run is None:
            raise NotFound(f"Analyse inconnue : {run_id}")
        return run

    @staticmethod
    def _display_steps(steps: list[TraceStep], finished: Optional[str]) -> list[RunStepView]:
        """Ramène les étapes de la trace aux cinq étapes affichées par le mobile."""
        closed = {
            "profil": [s for s in steps if s.step == "profil"],
            "recherche_validation": [s for s in steps if s.step == "recherche"],
            "debat": [s for s in steps if s.step == "debat" or s.step.startswith("debate.")],
            "decision": [s for s in steps if s.step == "decision"],
            "explication": [s for s in steps if s.step == "explication"],
        }
        out: list[RunStepView] = []
        pending_marked = False
        for step_id in RUN_STEPS:
            recorded = closed[step_id]
            if finished == "termine":
                status = "ok"
            elif recorded and any(s.status == "echec" for s in recorded):
                status = "echec"
                pending_marked = True  # les étapes suivantes n'ont pas eu lieu : « en attente », pas « échec »
            elif recorded:
                status = "ok"
            elif not pending_marked:
                status = "echec" if finished == "echec" else "en_cours"
                pending_marked = True
            else:
                status = "attente"
            out.append(RunStepView(id=step_id, status=status))
        return out

    def run_status(self, run_id: str) -> RunStatusView:
        run = self._run(run_id)
        result = run.result
        finished = result.status if result is not None else None
        return RunStatusView(
            run_id=run.run_id, profile_id=run.profile_id, as_of=run.as_of, requested_ticker=run.requested_ticker,
            status=finished or "en_cours",
            steps=self._display_steps(list(run.steps), finished),
            error=result.error if result is not None else None,
            result=result.explanation if result is not None else None,
        )

    def trace(self, run_id: str) -> RunTrace:
        run = self._run(run_id)
        if run.result is not None:
            return run.result.trace
        return RunTrace(run_id=run.run_id, as_of=run.as_of, profile_id=run.profile_id, steps=tuple(run.steps))

    # --- preuves, fiches, graphe --------------------------------------------------------------
    def _context(self, run_id: Optional[str]) -> EvidenceContext:
        if run_id:
            run = self._run(run_id)
            if run.result is not None and run.result.metrics is not None:
                return EvidenceContext(as_of=run.as_of, ledger=run.result.ledger, metrics=run.result.metrics)
            as_of = run.as_of  # run en cours ou échoué avant la validation : registre hors run, même date
        else:
            as_of = self.default_as_of
        with self._lock:
            context = self._contexts.get(as_of)
            if context is None:
                ledger = EvidenceLedger(as_of)
                metrics = compute_metrics_table(self.ws.store, as_of, ledger, self.ws.registry, self.ws.settings.quality)
                context = self._contexts[as_of] = EvidenceContext(as_of=as_of, ledger=ledger, metrics=metrics)
        return context

    def evidence(self, evidence_id: str, run_id: Optional[str] = None) -> Evidence:
        context = self._context(run_id)
        if evidence_id not in context.ledger:
            where = f"l'analyse {run_id}" if run_id else "le registre hors analyse"
            raise NotFound(f"Preuve inconnue dans {where} : {evidence_id}")
        return context.ledger.get(evidence_id)

    def assets(self) -> list[AssetSummary]:
        return [self._summary(row) for _, row in self._assets.iterrows()]

    @staticmethod
    def _summary(row: pd.Series) -> AssetSummary:
        return AssetSummary(ticker=str(row["ticker"]), name=str(row["name"]), asset_class=str(row["asset_class"]),
                            sector=str(row["sector"]) or None, currency=str(row["currency"]))

    def _asset_row(self, ticker: str) -> pd.Series:
        rows = self._assets[self._assets["ticker"] == ticker]
        if rows.empty:
            raise NotFound(f"Titre absent de l'univers analysé : {ticker}")
        return rows.iloc[0]

    def _tools(self, context: EvidenceContext) -> ResearchTools:
        return ResearchTools(self._assets, context.as_of, self.ws.settings.reference_dir, context.ledger,
                             self.ws.registry)

    def asset_sheet(self, ticker: str, profile_id: Optional[str] = None, run_id: Optional[str] = None) -> AssetSheet:
        row = self._asset_row(ticker)
        context = self._context(run_id)
        if profile_id is None and run_id:
            profile_id = self._run(run_id).profile_id
        limits: Optional[tuple[float, float]] = None
        if profile_id:
            level = tolerance_level(self._entry(profile_id)["profil"]["tolerance_risque"])
            limits = RISK_LIMITS[level]

        table = context.metrics[context.metrics["value"].notna() & context.metrics["evidence_id"].notna()]
        metrics: list[AssetMetricView] = []
        for metric_id, label, metric, window, window_label, limit_index, advanced in SHEET_METRICS:
            universe = table[(table["metric"] == metric) & (table["window"] == window)]
            own = universe[universe["ticker"] == ticker]
            if own.empty:
                continue  # indicateur non calculé (historique insuffisant) : absent, jamais remplacé par zéro
            metrics.append(AssetMetricView(
                metric=metric_id, label=label, value=float(own.iloc[0]["value"]), unit=str(own.iloc[0]["unit"]),
                window=window_label, evidence_id=str(own.iloc[0]["evidence_id"]),
                universe_min=float(universe["value"].min()), universe_max=float(universe["value"].max()),
                profile_limit=limits[limit_index] if limits is not None and limit_index is not None else None,
                advanced=advanced,
            ))

        self._tools(context).preuves_esg(ticker)  # charge les preuves ESG datées du titre dans le registre
        signals = [
            Claim(text=evidence.statement, evidence_ids=(evidence.evidence_id,), claim_kind=evidence.claim_kind)
            for evidence in context.ledger
            if evidence.subject == ticker and evidence.type in SIGNAL_TYPES
        ]
        summary = self._summary(row)
        return AssetSheet(**summary.model_dump(), as_of=context.as_of, metrics=metrics, signals=signals,
                          sentiment=self._sentiment(ticker, context))

    # --- sentiment et cours -------------------------------------------------------------------
    def _sentiment(self, ticker: str, context: EvidenceContext) -> Optional[SentimentView]:
        """Dernier mois publié à la date de la fiche ; chaque chiffre devient une preuve du registre."""
        if SOURCE_SENTIMENT not in self.ws.registry or self.ws.registry.get(SOURCE_SENTIMENT).statut != "utilisé":
            return None
        analysts, insiders = latest_sentiment(self._sentiment_table, ticker, context.as_of)
        if analysts is None and insiders is None:
            return None
        source = self.ws.registry.require_used(SOURCE_SENTIMENT).as_evidence_source()
        analyst_view = insider_view = None
        if analysts is not None:
            c = analysts.counts
            evidence = context.ledger.add(EvidenceDraft(
                type="metric", claim_kind="FAIT", subject=ticker,
                statement=(f"Recommandations d'analystes, {_month_fr(analysts.period)} : {c['strong_buy']} achat fort, "
                           f"{c['buy']} achat, {c['hold']} conserver, {c['sell']} vente, {c['strong_sell']} vente forte"),
                value=round(analysts.balance, 2), unit="ratio", observed_at=analysts.period,
                published_at=analysts.published_at, retrieved_at=analysts.retrieved_at, source=source,
                processing=(f"Finnhub ({analysts.document_url}) ; solde = (achats − ventes) ÷ total des "
                            "recommandations ; mois connu une fois terminé"),
                produced_by="data.sentiment@v1",
                limits="Opinions d'analystes, pas une prévision ; affiché seulement, sans effet sur le score.",
            ))
            analyst_view = AnalystSentiment(period=analysts.period, **c, balance=round(analysts.balance, 2),
                                            evidence_id=evidence.evidence_id)
        if insiders is not None:
            evidence = context.ledger.add(EvidenceDraft(
                type="metric", claim_kind="FAIT", subject=ticker,
                statement=f"Indice de sentiment des initiés (MSPR, de -100 à +100), {_month_fr(insiders.period)}",
                value=round(insiders.mspr, 1), unit="indice", observed_at=insiders.period,
                published_at=insiders.published_at, retrieved_at=insiders.retrieved_at, source=source,
                processing=(f"Finnhub ({insiders.document_url}) ; achats et ventes des dirigeants déclarés "
                            "(formulaires 4), agrégés par mois"),
                produced_by="data.sentiment@v1",
                limits="Sociétés américaines seulement ; une vente d'initié a souvent une raison personnelle.",
            ))
            insider_view = InsiderSentiment(period=insiders.period, mspr=round(insiders.mspr, 1),
                                            evidence_id=evidence.evidence_id)
        return SentimentView(label=sentiment_label(analysts, insiders), analysts=analyst_view, insiders=insider_view)

    def price_series(self, ticker: str, run_id: Optional[str] = None) -> PriceSeries:
        """Cours ajustés en CAD jusqu'à la date d'analyse : dernier jour de cotation de chaque semaine."""
        self._asset_row(ticker)
        context = self._context(run_id)
        prices = self.ws.store.prices(context.as_of, [ticker])
        series = prices.set_index("date")["adj_close_cad"].dropna().sort_index()
        if series.empty:
            raise NotFound(f"Aucun cours publié pour {ticker} au {context.as_of}")
        weekly = series.groupby(series.index.to_period("W-FRI")).tail(1)  # vraies dates, jamais après as_of
        if weekly.index[-1] != series.index[-1]:
            weekly = pd.concat([weekly, series.iloc[-1:]])
        rows = context.metrics[(context.metrics["ticker"] == ticker) & (context.metrics["metric"] == "annualized_return")
                               & (context.metrics["window"] == "full") & context.metrics["evidence_id"].notna()]
        return PriceSeries(
            ticker=ticker, as_of=context.as_of, start=weekly.index[0].date(), end=weekly.index[-1].date(),
            points=[PricePoint(day=d.date(), value=round(float(v), 4)) for d, v in weekly.items()],
            change_pct=round((float(series.iloc[-1]) / float(series.iloc[0]) - 1.0) * 100.0, 2),
            evidence_id=str(rows.iloc[0]["evidence_id"]) if len(rows) else None,
        )

    def graph(self, ticker: str, run_id: Optional[str] = None) -> DependencyGraph:
        """Sous-graphe de profondeur 1. Une arête n'est servie que si elle a une preuve (scénario S10)."""
        self._asset_row(ticker)
        context = self._context(run_id)
        edges: list[GraphEdge] = []
        node_ids = [ticker]
        for relation in self._tools(context).relations(ticker):
            if relation["relation"] not in RELATIONS:
                continue
            evidence = context.ledger.get(relation["evidence_id"])
            edges.append(GraphEdge(
                source=relation["source"], target=relation["target"], relation=relation["relation"],
                claim_kind="HYPOTHESE" if evidence.claim_kind == "HYPOTHESE" else "FAIT",
                evidence_id=evidence.evidence_id,
            ))
            node_ids.extend([relation["source"], relation["target"]])
        nodes = [GraphNode(id=n, label=self._names.get(n, n), in_universe=n in self._names)
                 for n in dict.fromkeys(node_ids)]
        return DependencyGraph(center=ticker, nodes=nodes, edges=edges)

    # --- données ------------------------------------------------------------------------------
    @staticmethod
    def _detail_text(detail: Any) -> str:
        if isinstance(detail, dict):
            return " · ".join(f"{key} : {value}" for key, value in detail.items())
        return str(detail)

    def data_overview(self, run_id: Optional[str] = None) -> DataOverview:
        as_of = self._run(run_id).as_of if run_id else self.default_as_of
        with self._lock:
            quality = self._quality.get(as_of)
        if quality is None:
            report = build_quality_report(self.ws.store, to_timestamp(as_of), self.ws.settings.quality)
            quality = []
            for check in report["checks"]:
                raw = check["details"]
                if isinstance(raw, dict):  # certains contrôles détaillent par clé (ex. par actif)
                    raw = [f"{key} : {self._detail_text(value)}" for key, value in raw.items()]
                elif not isinstance(raw, (list, tuple)):
                    raw = [raw]
                details = [self._detail_text(d) for d in raw[:MAX_QUALITY_DETAILS]]
                if len(raw) > MAX_QUALITY_DETAILS:
                    details.append(f"… et {len(raw) - MAX_QUALITY_DETAILS} autre(s)")
                if raw and check["note"]:
                    details.append(check["note"])
                quality.append(QualityCheck(check=check["title"], status=QUALITY_STATUS[check["status"]], details=details))
            with self._lock:
                self._quality[as_of] = quality
        sources = [
            SourceInfo(source_id=r.source_id, nom=r.nom, type_de_donnee=r.type_de_donnee,
                       date_extraction=r.date_extraction, limites=r.limites or "—", statut=r.statut)
            for r in self.ws.registry.records()
        ]
        return DataOverview(as_of=as_of, sources=sources, quality=quality)
