"""Indicateurs de risque : perte maximale, pire période glissante, corrélations.

Conception : docs/02_AGENTS.md (couche de validation)
Fonctions pures et déterministes. Les prix en entrée sont des `adj_close` (voir metrics.py),
indexés par date et triés. Les résultats sont des fractions (-0,25 pour -25 %).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def max_drawdown(prices: pd.Series) -> Optional[float]:
    """Plus grand recul depuis un sommet (valeur <= 0). Le premier prix compte comme sommet initial."""
    if len(prices) < 2:
        return None
    values = prices.to_numpy(dtype=float)
    running_peak = np.maximum.accumulate(values)
    return float((values / running_peak - 1.0).min())


def worst_rolling_return(prices: pd.Series, window_observations: int) -> Optional[tuple[float, pd.Timestamp, pd.Timestamp]]:
    """Pire rendement cumulé sur `window_observations` rendements consécutifs.

    Retourne (rendement, date de début, date de fin) ou None si l'historique est trop court.
    La fenêtre est mesurée en observations propres à l'actif (252 par an pour les actions,
    365 pour la crypto).
    """
    if window_observations < 1 or len(prices) <= window_observations:
        return None
    values = prices.to_numpy(dtype=float)
    rolling = values[window_observations:] / values[:-window_observations] - 1.0
    i = int(np.argmin(rolling))  # première occurrence du minimum : résultat déterministe
    return float(rolling[i]), prices.index[i], prices.index[i + window_observations]


def correlation(prices_a: pd.Series, prices_b: pd.Series, min_common: int) -> Optional[tuple[float, int]]:
    """Corrélation des rendements quotidiens sur les **dates communes** aux deux séries.

    Les rendements sont calculés après alignement : ils couvrent le même intervalle pour les deux
    actifs, même si leurs calendriers diffèrent. Retourne (corrélation, nombre de rendements).
    """
    both = pd.concat([prices_a.rename("a"), prices_b.rename("b")], axis=1, join="inner").sort_index()
    returns = both.pct_change().dropna()
    if len(returns) < min_common:
        return None
    return float(returns["a"].corr(returns["b"])), int(len(returns))


def basket_volatility(aligned_prices: pd.DataFrame, weights: dict[str, float],
                      periods_per_year: int) -> Optional[tuple[float, int]]:
    """Volatilité annualisée d'un panier à parts fixes, rééquilibré à chaque séance.

    `aligned_prices` : prix alignés sur les dates communes (`align_prices`), dans la même devise.
    Le rendement du panier est la moyenne pondérée des rendements quotidiens : les corrélations
    entre actifs sont donc prises en compte. Retourne (volatilité en fraction, nombre de rendements).
    """
    returns = aligned_prices.pct_change().dropna()
    if len(returns) < 2:
        return None
    total = sum(weights.values())
    w = np.array([weights[column] / total for column in returns.columns], dtype=float)
    basket = returns.to_numpy(dtype=float) @ w
    return float(np.std(basket, ddof=1) * np.sqrt(periods_per_year)), int(len(returns))


def correlation_matrix(aligned_prices: pd.DataFrame, min_common: int) -> pd.DataFrame:
    """Matrice de corrélation des rendements d'un tableau de prix déjà aligné (`align_prices`)."""
    returns = aligned_prices.pct_change().dropna()
    if len(returns) < min_common:
        return pd.DataFrame(np.nan, index=aligned_prices.columns, columns=aligned_prices.columns)
    return returns.corr()
