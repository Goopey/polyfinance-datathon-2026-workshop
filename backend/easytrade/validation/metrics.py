"""Rendement annualisé, volatilité annualisée, perte maximale, pire période glissante.

Conception : docs/02_AGENTS.md (couche de validation), docs/04_DONNEES.md section 1
Règles :
- `adj_close` uniquement (jamais `close`) ; les fractionnements ne sont pas réappliqués.
- Devise : CAD par défaut (`adj_close_cad`) ; `currency="local"` utilise la devise de cotation.
- 252 séances par an (actions, FNB) ou 365 jours (crypto), indiqué dans la preuve.
- Une preuve (`Evidence`, type `metric`) par indicateur, enregistrée dans le registre.
- Les valeurs en pourcentage sont en points de pourcentage. Ce sont des descriptions du passé.
- Python déterministe, aucun aléa, aucun LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import numpy as np
import pandas as pd

from easytrade.config import CRYPTO_ASSET_CLASS, QualityThresholds
from easytrade.data.calendar import align_prices, annualization_factor
from easytrade.data.point_in_time import DateLike, PointInTimeStore, to_timestamp
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.schemas.evidence import EvidenceDraft, EvidenceWindow
from easytrade.schemas.metrics import MetricResult
from easytrade.validation import risk
from easytrade.validation.data_quality import anomaly_notes

VERSION = "v1"
SOURCE_ID = "starter_prices"
WINDOWS = ("full", "3y", "1y")
TRAILING_YEARS = {"3y": 3, "1y": 1}
ROLLING_YEARS = (1, 3)
CALENDAR_YEAR = 2022  # comportement en 2022 : actions et obligations ont reculé ensemble

BASE_LIMITS = "Décrit le passé sur la fenêtre indiquée, pas une prévision. Biais du survivant : univers choisi en 2026."


# --- fonctions pures (prix indexés par date, triés) ------------------------------------------
def daily_returns(prices: pd.Series) -> pd.Series:
    """Rendements simples entre observations consécutives **de l'actif** (calendrier propre à l'actif)."""
    return prices.pct_change().dropna()


def annualized_return(prices: pd.Series, periods_per_year: int) -> Optional[float]:
    """Rendement géométrique annualisé : (P_fin / P_début) ** (periods_per_year / n_rendements) - 1."""
    n = len(prices) - 1
    if n < 1:
        return None
    return float((prices.iloc[-1] / prices.iloc[0]) ** (periods_per_year / n) - 1.0)


def annualized_volatility(prices: pd.Series, periods_per_year: int) -> Optional[float]:
    """Écart-type (ddof=1) des rendements quotidiens × racine de periods_per_year."""
    returns = daily_returns(prices)
    if len(returns) < 2:
        return None
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def period_return(prices: pd.Series, base_date: pd.Timestamp, end_date: pd.Timestamp) -> Optional[float]:
    """Rendement cumulé entre le dernier prix <= base_date et le dernier prix <= end_date."""
    base = prices[prices.index <= base_date]
    end = prices[prices.index <= end_date]
    if base.empty or end.empty or end.index[-1] <= base.index[-1]:
        return None
    return float(end.iloc[-1] / base.iloc[-1] - 1.0)


# --- construction des preuves ---------------------------------------------------------------
@dataclass(frozen=True)
class _Spec:
    name: str
    statement: str
    unit: str
    produced_by: str
    processing: str


SPECS = {
    "annualized_return": _Spec(
        "annualized_return", "Rendement annualisé", "%", f"validation.metrics.annualized_return@{VERSION}",
        "adj_close ; (prix final / prix initial) ^ (périodes par an / nombre de rendements) - 1",
    ),
    "annualized_volatility": _Spec(
        "annualized_volatility", "Volatilité annualisée", "%", f"validation.metrics.annualized_volatility@{VERSION}",
        "adj_close ; écart-type (ddof=1) des rendements quotidiens × racine des périodes par an",
    ),
    "max_drawdown": _Spec(
        "max_drawdown", "Perte maximale sur la fenêtre observée", "%", f"validation.risk.max_drawdown@{VERSION}",
        "adj_close ; maximum du recul depuis un sommet",
    ),
}


def _metric_window_label(window: str) -> str:
    return {"full": "toute la période", "3y": "3 dernières années", "1y": "dernière année"}.get(window, window)


class _Builder:
    """Calcule les indicateurs d'un actif et les inscrit au registre de preuves."""

    def __init__(self, store: PointInTimeStore, as_of: pd.Timestamp, ledger: EvidenceLedger,
                 registry: SourcesRegistry, currency: str, thresholds: QualityThresholds):
        if ledger.as_of != as_of.date():
            raise ValueError(f"Le registre de preuves est à as_of={ledger.as_of}, l'analyse à as_of={as_of.date()}")
        if currency not in ("CAD", "local"):
            raise ValueError("currency doit valoir 'CAD' ou 'local'")
        self.store, self.as_of, self.ledger, self.currency, self.thresholds = store, as_of, ledger, currency, thresholds
        self.source = registry.require_used(SOURCE_ID)
        self.retrieved_at = self.source.date_extraction
        self.notes = anomaly_notes(store.corporate_actions(as_of), thresholds.min_split_ratio)

    def _limits(self, ticker: str, asset_currency: str, asset_class: str, carried_rows: int) -> str:
        parts = [BASE_LIMITS]
        if self.currency == "CAD" and asset_currency == "USD":
            parts.append(
                "Converti en CAD au taux USD/CAD de la Banque du Canada ; dernier taux connu les jours sans taux "
                f"({carried_rows} séances concernées dans la fenêtre)."
            )
        if asset_class == "crypto":
            parts.append("Jours civils UTC, sans clôture de marché ; annualisé sur 365 jours.")
        if ticker in self.notes:
            parts.append(self.notes[ticker])
        return " ".join(parts)

    def _record(self, *, ticker, spec: _Spec, window: str, value_fraction: Optional[float], unit: str, observations: int,
                start, end, asset_currency, asset_class, carried_rows, periods_per_year, note="", scale=100.0,
                statement_suffix="") -> MetricResult:
        currency = "CAD" if self.currency == "CAD" else asset_currency
        value = None if value_fraction is None else float(value_fraction) * scale
        evidence_id = None
        if value is not None:
            statement = f"{spec.statement}{statement_suffix} ({_metric_window_label(window)}, {currency})"
            draft = EvidenceDraft(
                type="metric", claim_kind="FAIT", subject=ticker, statement=statement, value=value, unit=unit,
                currency=currency,
                window=EvidenceWindow(start=start.date(), end=end.date(), observations=int(observations)),
                observed_at=end.date(), published_at=end.date(), retrieved_at=self.retrieved_at,
                source=self.source.as_evidence_source(),
                processing=f"{spec.processing} ; {periods_per_year} périodes par an ; devise : {currency}",
                produced_by=spec.produced_by,
                limits=self._limits(ticker, asset_currency, asset_class, carried_rows),
            )
            evidence_id = self.ledger.add(draft).evidence_id
        return MetricResult(
            as_of=self.as_of.date(), ticker=ticker, metric=spec.name, window=window, value=value, unit=unit,
            currency=currency, observations=int(observations), start=None if start is None else start.date(),
            end=None if end is None else end.date(), evidence_id=evidence_id, note=note,
        )

    def asset_metrics(self, ticker: str, prices: pd.DataFrame) -> list[MetricResult]:
        asset_class = prices["asset_class"].iloc[0]
        asset_currency = prices["currency"].iloc[0]
        ppy = annualization_factor(asset_class)
        column = "adj_close_cad" if self.currency == "CAD" else "adj_close"
        series = prices.set_index("date")[column].sort_index()
        carried = prices.set_index("date")["fx_carried"].sort_index() if asset_currency == "USD" else None
        min_obs = self.thresholds.min_metric_observations
        results: list[MetricResult] = []

        def carried_in(window_prices: pd.Series) -> int:
            return 0 if carried is None else int(carried.loc[window_prices.index].sum())

        def add(spec_name, window, window_prices, compute: Callable[[pd.Series], Optional[float]], *, minimum=min_obs,
                spec=None, scale=100.0, unit="%", suffix=""):
            spec = spec or SPECS[spec_name]
            n_returns = len(window_prices) - 1
            if window_prices.empty:
                results.append(MetricResult(as_of=self.as_of.date(), ticker=ticker, metric=spec.name, window=window,
                                            value=None, unit=unit, currency="CAD" if self.currency == "CAD" else asset_currency,
                                            observations=0, note="Aucune donnée dans la fenêtre"))
                return
            value = compute(window_prices) if n_returns >= minimum else None
            note = "" if value is not None else f"Données insuffisantes : {n_returns} rendements (minimum {minimum})"
            results.append(self._record(
                ticker=ticker, spec=spec, window=window, value_fraction=value, unit=unit, observations=len(window_prices),
                start=window_prices.index[0], end=window_prices.index[-1], asset_currency=asset_currency,
                asset_class=asset_class, carried_rows=carried_in(window_prices), periods_per_year=ppy, note=note,
                scale=scale, statement_suffix=suffix,
            ))

        for window in WINDOWS:
            if window == "full":
                window_prices = series
            else:
                start = self.as_of - pd.DateOffset(years=TRAILING_YEARS[window])
                window_prices = series[series.index >= start]
            add("annualized_return", window, window_prices, lambda s: annualized_return(s, ppy))
            add("annualized_volatility", window, window_prices, lambda s: annualized_volatility(s, ppy))
            add("max_drawdown", window, window_prices, risk.max_drawdown)

        for years in ROLLING_YEARS:
            k = round(years * ppy)
            spec = _Spec(
                f"worst_rolling_{years}y", f"Pire période glissante de {years} an{'s' if years > 1 else ''}", "%",
                f"validation.risk.worst_rolling_return@{VERSION}",
                f"adj_close ; plus faible rendement cumulé sur {k} observations consécutives",
            )
            found = risk.worst_rolling_return(series, k)
            if found is None:
                results.append(MetricResult(
                    as_of=self.as_of.date(), ticker=ticker, metric=spec.name, window="full", value=None, unit="%",
                    currency="CAD" if self.currency == "CAD" else asset_currency, observations=len(series),
                    note=f"Historique trop court : {len(series)} observations pour une fenêtre de {k}",
                ))
                continue
            value, start, end = found
            results.append(self._record(
                ticker=ticker, spec=spec, window="full", value_fraction=value, unit="%", observations=k + 1,
                start=start, end=end, asset_currency=asset_currency, asset_class=asset_class,
                carried_rows=carried_in(series.loc[start:end]), periods_per_year=ppy,
            ))

        base = pd.Timestamp(CALENDAR_YEAR - 1, 12, 31)
        year_end = min(pd.Timestamp(CALENDAR_YEAR, 12, 31), self.as_of)
        value = period_return(series, base, year_end)
        spec = _Spec(f"return_{CALENDAR_YEAR}", f"Rendement de l'année {CALENDAR_YEAR}", "%",
                     f"validation.metrics.period_return@{VERSION}",
                     "adj_close ; rendement cumulé entre le dernier prix de l'année précédente et celui de l'année")
        before_base = series.index[series.index <= base]
        in_period = series.loc[before_base[-1]:year_end] if len(before_base) else series.iloc[0:0]
        year_complete = self.as_of >= pd.Timestamp(CALENDAR_YEAR, 12, 31)
        if value is None or len(in_period) < 2 or not year_complete:
            # Année en cours à la date d'analyse : un cumul partiel n'est pas « le rendement de l'année ».
            results.append(MetricResult(
                as_of=self.as_of.date(), ticker=ticker, metric=spec.name, window=str(CALENDAR_YEAR), value=None, unit="%",
                currency="CAD" if self.currency == "CAD" else asset_currency, observations=0,
                note=(f"Aucune donnée couvrant l'année {CALENDAR_YEAR}" if year_complete
                      else f"Année {CALENDAR_YEAR} incomplète à la date d'analyse"),
            ))
        else:
            results.append(self._record(
                ticker=ticker, spec=spec, window=str(CALENDAR_YEAR), value_fraction=value, unit="%",
                observations=len(in_period), start=in_period.index[0], end=in_period.index[-1],
                asset_currency=asset_currency, asset_class=asset_class, carried_rows=carried_in(in_period), periods_per_year=ppy,
            ))
        return results


def compute_metrics_table(
    store: PointInTimeStore,
    as_of: DateLike,
    ledger: EvidenceLedger,
    registry: SourcesRegistry,
    thresholds: Optional[QualityThresholds] = None,
    *,
    currency: str = "CAD",
    tickers: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Table des indicateurs `(as_of, ticker, metric, window)` avec `evidence_id` pour chaque valeur calculée."""
    as_of_ts = to_timestamp(as_of)
    thresholds = thresholds or QualityThresholds()
    builder = _Builder(store, as_of_ts, ledger, registry, currency, thresholds)
    prices = store.prices(as_of_ts, tickers)
    rows: list[MetricResult] = []
    for ticker, group in prices.groupby("ticker", sort=True):
        rows.extend(builder.asset_metrics(ticker, group.sort_values("date", kind="mergesort")))
    columns = list(MetricResult.model_fields)
    return pd.DataFrame([r.model_dump() for r in rows], columns=columns)


def basket_volatility_metric(
    store: PointInTimeStore, as_of: DateLike, ledger: EvidenceLedger, registry: SourcesRegistry,
    weights: dict[str, float], label: str, thresholds: Optional[QualityThresholds] = None,
) -> MetricResult:
    """Volatilité annualisée d'un panier **simulé** (parts fixes), en CAD, avec preuve `SCENARIO`.

    `weights` : part de chaque ticker (normalisées ici). `label` décrit le panier dans l'énoncé
    de la preuve (« 10 pistes retenues, parts égales »). Dates communes à tous les actifs, sans
    remplissage ; 252 périodes par an, sauf panier entièrement en crypto (365).
    """
    as_of_ts = to_timestamp(as_of)
    thresholds = thresholds or QualityThresholds()
    builder = _Builder(store, as_of_ts, ledger, registry, "CAD", thresholds)
    tickers = sorted(weights)
    prices = store.prices(as_of_ts, tickers)
    wide = align_prices(prices, tickers, "adj_close_cad")
    classes = set(prices["asset_class"].unique())
    ppy = annualization_factor(CRYPTO_ASSET_CLASS) if classes == {CRYPTO_ASSET_CLASS} else annualization_factor("")
    result = risk.basket_volatility(wide, weights, ppy) if len(wide) > thresholds.min_common_observations else None
    metric = "basket_volatility"
    if result is None:
        return MetricResult(as_of=as_of_ts.date(), ticker="PANIER", metric=metric, window="full", value=None,
                            unit="%", currency="CAD", observations=int(len(wide)),
                            note="Dates communes insuffisantes pour le panier simulé")
    value, n = result
    draft = EvidenceDraft(
        type="metric", claim_kind="SCENARIO", subject="PANIER",
        statement=f"Volatilité annualisée d'un panier simulé ({label})", value=value * 100.0, unit="%",
        currency="CAD",
        window=EvidenceWindow(start=wide.index[0].date(), end=wide.index[-1].date(), observations=n + 1),
        observed_at=wide.index[-1].date(), published_at=wide.index[-1].date(), retrieved_at=builder.retrieved_at,
        source=builder.source.as_evidence_source(),
        processing=(
            "adj_close en CAD ; dates communes à tous les actifs du panier (sans remplissage) ; parts fixes "
            f"rééquilibrées à chaque séance ; écart-type (ddof=1) × racine de {ppy} ; composition : "
            + ", ".join(f"{t} {weights[t] / sum(weights.values()) * 100:.1f} %" for t in tickers)
        ),
        produced_by=f"validation.risk.basket_volatility@{VERSION}",
        limits=BASE_LIMITS + " Panier fictif : aucune transaction, aucun frais, parts fixes.",
    )
    evidence_id = ledger.add(draft).evidence_id
    return MetricResult(
        as_of=as_of_ts.date(), ticker="PANIER", metric=metric, window="full", value=value * 100.0, unit="%",
        currency="CAD", observations=n + 1, start=wide.index[0].date(), end=wide.index[-1].date(),
        evidence_id=evidence_id,
    )


def correlation_metric(
    store: PointInTimeStore, as_of: DateLike, ledger: EvidenceLedger, registry: SourcesRegistry,
    ticker_a: str, ticker_b: str, thresholds: Optional[QualityThresholds] = None, currency: str = "CAD",
) -> MetricResult:
    """Corrélation des rendements quotidiens de deux actifs sur leurs dates communes, avec preuve."""
    as_of_ts = to_timestamp(as_of)
    thresholds = thresholds or QualityThresholds()
    builder = _Builder(store, as_of_ts, ledger, registry, currency, thresholds)
    column = "adj_close_cad" if currency == "CAD" else "adj_close"
    prices = store.prices(as_of_ts, [ticker_a, ticker_b])
    wide = align_prices(prices, [ticker_a, ticker_b], column)
    out_currency = "CAD" if currency == "CAD" else "local"
    result = risk.correlation(wide[ticker_a], wide[ticker_b], thresholds.min_common_observations) if len(wide) else None
    metric = f"correlation_{ticker_b}"
    if result is None:
        return MetricResult(as_of=as_of_ts.date(), ticker=ticker_a, metric=metric, window="full", value=None,
                            unit="ratio", currency=out_currency, observations=int(len(wide)),
                            note="Dates communes insuffisantes")
    value, n = result
    draft = EvidenceDraft(
        type="metric", claim_kind="FAIT", subject=f"{ticker_a}/{ticker_b}",
        statement=f"Corrélation des rendements quotidiens ({out_currency})", value=value, unit="ratio",
        currency=out_currency,
        window=EvidenceWindow(start=wide.index[0].date(), end=wide.index[-1].date(), observations=n),
        observed_at=wide.index[-1].date(), published_at=wide.index[-1].date(), retrieved_at=builder.retrieved_at,
        source=builder.source.as_evidence_source(),
        processing="adj_close ; rendements calculés sur les dates communes aux deux actifs (sans remplissage)",
        produced_by=f"validation.risk.correlation@{VERSION}",
        limits=BASE_LIMITS + " Les dates où un des deux marchés est fermé sont exclues.",
    )
    evidence_id = ledger.add(draft).evidence_id
    return MetricResult(
        as_of=as_of_ts.date(), ticker=ticker_a, metric=metric, window="full", value=value, unit="ratio",
        currency=out_currency, observations=n, start=wide.index[0].date(), end=wide.index[-1].date(),
        evidence_id=evidence_id,
    )
