"""Candidate, CriterionScore, ScoredCandidate, Rejection : actifs évalués et preuves rattachées.

Conception : docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md
Un `ScoredCandidate` conserve la contribution de chaque critère (`poids × score`) : c'est elle
qui alimente le graphique « pourquoi ce classement » de l'application.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict

from easytrade.schemas.evidence import Evidence

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
    weight: float                # poids du profil (tel que déclaré)
    contribution: float          # weight × score ÷ poids des critères applicables (= weight × score si tous le sont)
    missing: bool = False
    evidence_id: Optional[str] = None
    applicable: bool = True      # False : critère sans objet pour la classe d'actifs (ex. qualité d'un FNB)


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


class Candidate(BaseModel):
    """Candidat présélectionné par l'agent de recherche, avec ses premières preuves qualitatives."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    reason: str = ""                         # motif de présélection (texte court, sans chiffre)
    evidence_ids: tuple[str, ...] = ()       # preuves qualitatives rapportées par les outils
    requested: bool = False                  # titre soumis par l'utilisateur : toujours analysé


class CandidateList(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidates: tuple[Candidate, ...] = ()
    dropped: tuple[str, ...] = ()            # propositions retirées par le code (ticker inconnu)
    tools_called: tuple[str, ...] = ()

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(c.ticker for c in self.candidates)


class EvidencePack(BaseModel):
    """Dossier de preuves d'un candidat : identique pour les trois agents du débat."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    asset_class: str
    sector: str
    evidence: tuple[Evidence, ...] = ()      # métriques + preuves qualitatives + preuves du profil
    roles: dict[str, str] = {}               # evidence_id -> rôle (« annualized_volatility:full », « repere:volatilite »)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(e.evidence_id for e in self.evidence)
