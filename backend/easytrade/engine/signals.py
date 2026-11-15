"""Extraction des signaux par critère depuis la table d'indicateurs et l'univers.

Conception : docs/03_DECISION_ENGINE.md (section « Critères »)
Sépare la *production* des signaux (ici) de leur *normalisation et pondération* (scoring.py).
Chaque signal est **orienté** : une valeur plus haute est toujours meilleure. Le moteur peut
ainsi classer par simple rang centile sans connaître le sens de chaque indicateur.

Couverture actuelle (socle de départ) :
- croissance, stabilite, horizon : dérivés de la table d'indicateurs (P1).
- diversification : approximation par la rareté sectorielle dans l'univers (proxy assumé,
  à remplacer par la corrélation au panier quand le graphe de dépendances sera saisi — bloc G).
- esg : manquant ici ; le pipeline le renseigne avec `engine.esg` (preuves ESG datées : controverse,
  émetteur majeur documenté, fonds à filtre ESG). Sans constat concluant, il reste manquant.
- qualite : manquant ici ; le pipeline le renseigne pour les actions avec `engine.quality`
  (fondamentaux Finnhub publiés à la date d'analyse). « Non applicable » aux FNB et à la crypto.
- preferences : manquant ici ; le pipeline (P3) le renseigne avec `preference_signals`, à partir
  des thèmes que l'agent de pondération a lus dans le profil.

« Manquant » et « non applicable » sont distincts : un critère manquant compte 0 et baisse la
confiance (l'information existe, on ne l'a pas) ; un critère non applicable n'a pas de sens pour la
classe d'actifs (pas de comptes de société pour un FNB) : il est retiré du score de cet actif et son
poids est réparti sur les autres critères, sans pénalité ni bonus (scoring.py).
"""
from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from easytrade.schemas.weights import CRITERIA

# critère -> (nom de l'indicateur, fenêtre, orientation : +1 plus haut = mieux, -1 plus bas = mieux)
METRIC_SIGNALS: dict[str, tuple[str, str, int]] = {
    "croissance": ("annualized_return", "full", +1),
    "stabilite": ("annualized_volatility", "full", -1),
    "horizon": ("worst_rolling_3y", "full", +1),
}

# Critère « horizon » (audit C1) : la fenêtre dépend de l'horizon déclaré. Un investisseur qui aura besoin
# de son capital dans moins de 5 ans n'a pas le temps de traverser un mauvais cycle : on regarde la pire
# année glissante. Au-delà, la pire période glissante de 3 ans. (Les données couvrent 5 ans.)
SHORT_HORIZON_YEARS = 5
HORIZON_METRICS = {"worst_rolling_1y": "1 an", "worst_rolling_3y": "3 ans"}


def horizon_metric(min_years: Optional[int]) -> str:
    """Indicateur du critère horizon pour un horizon minimal déclaré (en années)."""
    return "worst_rolling_1y" if min_years is not None and min_years < SHORT_HORIZON_YEARS else "worst_rolling_3y"


def horizon_label(metric: str) -> str:
    """« 1 an » ou « 3 ans » : durée de la fenêtre glissante, telle qu'écrite dans les textes."""
    return HORIZON_METRICS[metric]
# Critères sans source déterministe dans la table d'indicateurs : signal manquant ici, renseigné
# (ou non) par le pipeline.
UNSOURCED = ("esg", "qualite", "preferences")
# Critère → classes d'actifs pour lesquelles il n'a pas de sens (décision de l'équipe, 2026-11-15).
NOT_APPLICABLE: dict[str, frozenset[str]] = {
    "qualite": frozenset({"etf_equity", "etf_bond", "etf_commodity", "crypto"}),
}


def applicable(criterion: str, asset_class: str) -> bool:
    """Le critère a-t-il un sens pour cette classe d'actifs ? (sinon : retiré du score, sans pénalité)"""
    return asset_class not in NOT_APPLICABLE.get(criterion, frozenset())


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value))


def _metric_lookup(metrics: pd.DataFrame) -> dict[tuple[str, str, str], "pd.Series"]:
    """Index (ticker, metric, window) -> ligne, pour un accès direct."""
    index: dict[tuple[str, str, str], pd.Series] = {}
    for _, row in metrics.iterrows():
        index[(row["ticker"], row["metric"], row["window"])] = row
    return index


def correlation_diversification(aligned_prices: pd.DataFrame, min_common: int) -> dict[str, tuple[float, int]]:
    """Diversification observée (audit H3) : corrélation moyenne des rendements quotidiens d'un actif
    avec chacun des autres actifs de l'univers, sur leurs dates communes (sans remplissage).

    Retourne ticker → (corrélation moyenne, nombre de rendements communs). Le signal orienté du
    critère est l'opposé de cette moyenne : moins un actif bouge avec les autres, plus il diversifie.
    Rien n'est renvoyé si l'historique commun est trop court.
    """
    from easytrade.validation.risk import correlation_matrix

    if aligned_prices.shape[1] < 2:
        return {}
    matrix = correlation_matrix(aligned_prices, min_common)
    n_returns = max(0, len(aligned_prices) - 1)
    out: dict[str, tuple[float, int]] = {}
    for ticker in matrix.columns:
        others = matrix[ticker].drop(index=ticker)
        if others.isna().all():
            continue
        out[str(ticker)] = (float(others.mean()), n_returns)
    return out


def _diversification_signals(assets: pd.DataFrame) -> dict[str, float]:
    """Proxy de diversification : plus un secteur est rare dans l'univers, plus l'apport est élevé.

    Signal = -(nombre d'actifs du même secteur). Le rang centile le ramène ensuite dans [0, 1].
    """
    counts = assets["sector"].value_counts()
    return {row["ticker"]: float(-counts[row["sector"]]) for _, row in assets.iterrows()}


def build_signals(
    metrics: pd.DataFrame,
    assets: pd.DataFrame,
    *,
    horizon: str = "worst_rolling_3y",
) -> tuple[dict[str, dict[str, Optional[float]]], dict[str, dict[str, Optional[str]]]]:
    """Signaux orientés et identifiants de preuve, par ticker puis par critère.

    Retourne (signals, evidence) où :
    - signals[ticker][critere] est un flottant orienté (plus haut = mieux) ou None (manquant) ;
    - evidence[ticker][critere] est l'`evidence_id` de l'indicateur utilisé, ou None.
    `horizon` : indicateur du critère horizon (`horizon_metric`), selon l'horizon déclaré du profil.
    Le critère diversification reçoit ici le proxy sectoriel ; le pipeline le remplace par la
    corrélation moyenne observée (`correlation_diversification`).
    """
    if horizon not in HORIZON_METRICS:
        raise ValueError(f"Indicateur d'horizon inconnu : {horizon}")
    metric_signals = {**METRIC_SIGNALS, "horizon": (horizon, "full", +1)}
    lookup = _metric_lookup(metrics)
    diversification = _diversification_signals(assets)
    tickers = [str(t) for t in assets["ticker"].tolist()]

    signals: dict[str, dict[str, Optional[float]]] = {}
    evidence: dict[str, dict[str, Optional[str]]] = {}
    for ticker in tickers:
        per_criterion: dict[str, Optional[float]] = {}
        per_evidence: dict[str, Optional[str]] = {}
        for criterion in CRITERIA:
            if criterion in metric_signals:
                metric, window, orientation = metric_signals[criterion]
                row = lookup.get((ticker, metric, window))
                value = row["value"] if row is not None else None
                if row is not None and _is_number(value):
                    per_criterion[criterion] = orientation * float(value)
                    ev = row.get("evidence_id")
                    per_evidence[criterion] = ev if isinstance(ev, str) and ev else None
                else:
                    per_criterion[criterion] = None
                    per_evidence[criterion] = None
            elif criterion == "diversification":
                per_criterion[criterion] = diversification.get(ticker)
                per_evidence[criterion] = None  # proxy, pas de preuve dédiée (voir bloc G)
            else:  # esg, qualite, preferences : non sourcés
                per_criterion[criterion] = None
                per_evidence[criterion] = None
        signals[ticker] = per_criterion
        evidence[ticker] = per_evidence
    return signals, evidence


# --- critère « preferences » : thèmes déclarés dans le profil ----------------------------------
# Vocabulaire fermé de thèmes (hypothèse de l'équipe, docs/03_DECISION_ENGINE.md). L'agent de
# pondération lit le profil et choisit des thèmes dans cette liste ; le rattachement d'un actif
# à un thème est fait ici, par le code, à partir de la classe d'actifs et du secteur de l'univers.
THEMES: dict[str, dict] = {
    "technologies": {
        "label": "technologies",
        "sectors": frozenset({
            "Information Technology", "Communication Services", "Broad market (U.S. growth/tech-heavy)",
        }),
        "asset_classes": frozenset(),
    },
    "cryptoactifs": {"label": "cryptoactifs", "sectors": frozenset(), "asset_classes": frozenset({"crypto"})},
    "entreprises_etablies": {
        "label": "entreprises établies",
        "sectors": frozenset({
            "Financials", "Utilities", "Consumer Staples", "Health Care", "Industrials", "Energy",
        }),
        "asset_classes": frozenset(),
    },
    "indiciel_diversifie": {
        "label": "fonds indiciels diversifiés",
        "sectors": frozenset({
            "Broad market (Canada)", "Broad market (U.S.)", "Broad market (U.S., ESG-screened)",
        }),
        "asset_classes": frozenset(),
    },
    "obligations": {"label": "obligations", "sectors": frozenset(), "asset_classes": frozenset({"etf_bond"})},
    "or": {"label": "or", "sectors": frozenset(), "asset_classes": frozenset({"etf_commodity"})},
    "esg": {
        "label": "filtre ESG",
        "sectors": frozenset({"Broad market (U.S., ESG-screened)"}),
        "asset_classes": frozenset(),
    },
}


def asset_themes(asset_class: str, sector: str) -> tuple[str, ...]:
    """Thèmes auxquels un actif se rattache (ordre de `THEMES`)."""
    return tuple(
        theme for theme, spec in THEMES.items()
        if asset_class in spec["asset_classes"] or sector in spec["sectors"]
    )


def preference_signals(
    assets: pd.DataFrame, preferred: tuple[str, ...], avoided: tuple[str, ...] = ()
) -> dict[str, tuple[float, tuple[str, ...], tuple[str, ...]]]:
    """Signal « preferences » par ticker : (thèmes préférés touchés − thèmes évités touchés,
    thèmes préférés touchés, thèmes évités touchés). Un actif sans thème touché vaut 0 : le
    critère est couvert pour tout l'univers, il n'est pas « manquant »."""
    out: dict[str, tuple[float, tuple[str, ...], tuple[str, ...]]] = {}
    for _, row in assets.iterrows():
        themes = asset_themes(str(row["asset_class"]), str(row["sector"]))
        liked = tuple(t for t in themes if t in preferred)
        disliked = tuple(t for t in themes if t in avoided)
        out[str(row["ticker"])] = (float(len(liked) - len(disliked)), liked, disliked)
    return out


def sector_counts(assets: pd.DataFrame) -> dict[str, int]:
    """Nombre d'actifs de l'univers par secteur (base du proxy de diversification)."""
    return {str(sector): int(count) for sector, count in assets["sector"].value_counts().items()}
