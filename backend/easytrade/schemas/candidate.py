"""Candidate, CriterionScore, ScoredCandidate, Rejection : actifs évalués et preuves rattachées.

Conception : docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md
Un `ScoredCandidate` conserve la contribution de chaque critère (`poids × score`) : c'est elle
qui alimente le graphique « pourquoi ce classement » de l'application.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict

ASSET_COLUMNS = ("asset_id", "ticker", "name", "asset_class", "market", "currency", "sector")


class Asset(BaseModel):
    """Une ligne de l'univers (data/raw/starter/assets_universe.csv)."""

    model_config = ConfigDict(frozen=True)

    asset_id: str
    ticker: str
    name: str
    asset_class: str
    market: str
    currency: str
    sector: str

    @classmethod
    def from_row(cls, row: "pd.Series") -> "Asset":
        return cls(**{column: str(row[column]) for column in ASSET_COLUMNS})


class CriterionScore(BaseModel):
    """Score d'un critère pour un actif, avec sa contribution au score d'adéquation."""

    model_config = ConfigDict(frozen=True)

    criterion: str
    signal: Optional[float]      # signal orienté (plus haut = meilleur), None si manquant
    score: float                 # rang centile dans l'univers, [0, 1] ; 0 si manquant
    weight: float
    contribution: float          # weight × score
    missing: bool = False
    evidence_id: Optional[str] = None


class ScoredCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    sector: str
    asset_class: str
    fit_score: float                         # Σ contributions ∈ [0, 1]
    criteria: tuple[CriterionScore, ...]
    missing_criteria: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()              # ex. « spéculatif signalé »


class Rejection(BaseModel):
    """Actif écarté par une contrainte dure, avec le motif montré à l'utilisateur."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    rule: str                                # identifiant de la contrainte
    reason: str                              # texte lisible
