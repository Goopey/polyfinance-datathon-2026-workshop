"""Configuration : chemins, date de référence, seuils et interrupteurs.

Conception : docs/06_AWS.md, docs/04_DONNEES.md
Les valeurs viennent des variables d'environnement (voir .env.example). Aucun secret en dur.
Les seuils et délais ci-dessous sont des **hypothèses de l'équipe** (claim_kind = HYPOTHESE) :
toute modification doit être notée dans docs/04_DONNEES.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AS_OF = "2026-11-12"

# Annualisation : 252 séances (actions, FNB), 365 jours (crypto, jours civils UTC).
TRADING_DAYS_PER_YEAR = 252
CRYPTO_DAYS_PER_YEAR = 365
CRYPTO_ASSET_CLASS = "crypto"

# Délai de publication prudent des séries macro mensuelles, après la fin du mois de référence.
# (mois, jours) ajoutés au premier jour du mois de référence. Hypothèse prudente : valeur
# supérieure ou égale à la date de publication réelle habituelle.
MACRO_PUBLICATION_LAG: dict[str, tuple[int, int]] = {
    "CPIAUCSL": (1, 15),  # IPC américain : publié vers le 10-15 du mois suivant
    "UNRATE": (1, 7),  # Chômage américain : premier vendredi du mois suivant
    "STATIC_TOTALCPICHANGE": (1, 25),  # IPC canadien : publié vers la troisième semaine du mois suivant
}
# Séries quotidiennes : publication au plus tard le jour ouvrable suivant (jours).
MACRO_DAILY_LAG_DAYS: dict[str, int] = {
    "BD.CDN.2YR.DQ.YLD": 0,
    "BD.CDN.10YR.DQ.YLD": 0,
    "V39079": 0,
    "DFF": 1,
    "DGS2": 1,
    "DGS10": 1,
}
# Fondamentaux annuels (Finnhub, docs/04_DONNEES.md) : date de publication supposée = fin de
# l'exercice + ce délai. Hypothèse prudente (comptes annuels déposés en général sous 60 à 90 jours) :
# un exercice n'est utilisé que s'il était très probablement public à la date d'analyse.
FUNDAMENTALS_ANNUAL_LAG_DAYS = 90
# Sentiment mensuel (Finnhub, docs/04_DONNEES.md section 11) : un mois n'est connu qu'une fois terminé
# (recommandations d'analystes), plus un délai pour les déclarations d'initiés (formulaires 4, 2 jours
# ouvrables, agrégés par Finnhub). Hypothèses prudentes.
SENTIMENT_ANALYST_LAG_DAYS = 0
SENTIMENT_INSIDER_LAG_DAYS = 5


@dataclass(frozen=True)
class QualityThresholds:
    """Seuils des contrôles de qualité (hypothèses, voir docs/04_DONNEES.md section 7)."""

    max_gap_sessions: int = 5  # trou toléré : séances consécutives manquantes
    max_daily_move: float = 0.25  # variation sur une journée au-delà de laquelle on signale
    min_observations: int = 252  # nombre minimal d'observations par actif
    min_split_ratio: float = 1.5  # un fractionnement plus petit est jugé suspect (ex. CNQ.TO 1,021)
    min_common_observations: int = 60  # corrélation : séances communes minimales
    min_metric_observations: int = 30  # en dessous, l'indicateur est « non calculé » (volatilité, rendement)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = REPO_ROOT / "data"
    as_of: date = date.fromisoformat(DEFAULT_AS_OF)
    env: str = "local"
    quality: QualityThresholds = field(default_factory=QualityThresholds)
    enable_alpaca: bool = False
    enable_finnhub: bool = False

    @property
    def starter_dir(self) -> Path:
        return self.data_dir / "raw" / "starter"

    @property
    def reference_dir(self) -> Path:
        return self.data_dir / "reference"

    @property
    def curated_dir(self) -> Path:
        return self.data_dir / "curated"


def _flag(name: str) -> bool:
    return os.environ.get(name, "false").strip().lower() in {"1", "true", "yes"}


def load_settings() -> Settings:
    """Lit l'environnement. `EASYTRADE_DATA_DIR` relatif est résolu depuis la racine du dépôt."""
    data_dir = Path(os.environ.get("EASYTRADE_DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir
    return Settings(
        data_dir=data_dir,
        as_of=date.fromisoformat(os.environ.get("EASYTRADE_AS_OF", DEFAULT_AS_OF)),
        env=os.environ.get("EASYTRADE_ENV", "local"),
        enable_alpaca=_flag("ENABLE_ALPACA"),
        enable_finnhub=_flag("ENABLE_FINNHUB"),
    )
