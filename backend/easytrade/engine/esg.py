"""Critère `esg` : ce que les preuves ESG datées permettent de conclure, et rien de plus.

Conception : docs/03_DECISION_ENGINE.md (section « Critère ESG »), docs/04_DONNEES.md (section 12)

Les preuves disponibles (`data/reference/esg_evidence.csv`) sont des émissions directes de GES
**absolues** et, pour la plupart, des **bornes inférieures** : périmètre national (installations
américaines seulement pour l'EPA, canadiennes pour ECCC), rattachement par nom d'exploitant au
Canada (filiales sous un autre nom omises). Une borne inférieure peut établir qu'une société émet
**beaucoup** ; elle ne peut jamais établir qu'elle émet **peu**. D'où quatre constats, et seulement
ceux-là :

- `controverse` : une ligne dont le type de signal commence par « Controverse » (saisie manuelle
  sourcée, CONTRIBUTING.md). Écarte l'actif pour un profil qui exclut les controverses.
- `emetteur_majeur` : émissions directes documentées ≥ `MAJOR_EMITTER_TONNES`. Le seuil est une
  hypothèse de l'équipe ; comme la valeur est une borne inférieure, le constat reste vrai si le
  périmètre réel est plus large. Écarte l'actif pour un profil qui demande d'éviter les entreprises
  à fort impact environnemental (`esg_exclusion`) ; score ESG nul (connu) pour les autres profils.
- `filtre_esg` : fonds dont la classification de l'univers indique un filtre ESG (ESGV). Score ESG
  maximal ; le filtre de l'émetteur n'est pas vérifié par l'équipe (limite affichée).
- `non_concluant` : émissions sous le seuil. Les preuves restent visibles (fiche, débat), mais le
  critère est **manquant** : une borne inférieure basse ne prouve pas un faible impact.

Un actif sans aucune ligne n'a pas de constat : critère manquant, jamais un bon score.

Le score de ce critère est **absolu** (0 ou 1), pas un rang centile : sur deux catégories, le rang
centile donnerait à un émetteur majeur documenté un score supérieur à celui d'un actif inconnu
(engine/scoring.py, `ABSOLUTE_CRITERIA`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal, Mapping, Optional

from easytrade.engine.signals import THEMES

EMISSIONS_SIGNAL = "Émissions directes de GES"  # = ingestion.esg.SIGNAL_TYPE (vérifié par les tests)
CONTROVERSY_PREFIX = "controverse"
# Seuil d'émetteur majeur (hypothèse de l'équipe, docs/03) : 10 Mt CO2e par an. Un ordre de grandeur au-dessus
# des écarts de méthode entre sources (potentiels de réchauffement AR4 / AR5 : quelques pour cent) ; les
# valeurs étant des bornes inférieures, un dépassement est concluant.
MAJOR_EMITTER_TONNES = 10_000_000.0
ESG_SCREENED_SECTORS = THEMES["esg"]["sectors"]

RULE_CONTROVERSY = "esg_exclusion"
RULE_EMISSIONS = "esg_emissions"
EMISSIONS_REASON = (
    "Écarté : émissions directes de gaz à effet de serre documentées au-dessus du seuil d'émetteur majeur "
    "retenu par EasyTrade ; votre profil demande d'éviter les entreprises à fort impact environnemental."
)

SCORE_SCREENED = 1.0
SCORE_CONCERN = 0.0

Finding = Literal["controverse", "emetteur_majeur", "filtre_esg", "non_concluant"]

_QUANTITY = re.compile(r"^\s*(\d+(?:,\d+)?) (Mt|kt) CO2e\b")
_UNIT = {"Mt": 1_000_000.0, "kt": 1_000.0}


def parse_emissions(summary: str) -> Optional[float]:
    """Tonnes CO2e en tête du résumé d'une ligne d'émissions (« 37,88 Mt CO2e déclarées… »).

    Inverse de `ingestion.esg.format_emissions` (aller-retour vérifié par les tests). Toute autre
    forme renvoie None : la ligne reste une preuve affichée, sans conclusion chiffrée.
    """
    match = _QUANTITY.match(summary or "")
    if not match:
        return None
    return float(match.group(1).replace(",", ".")) * _UNIT[match.group(2)]


@dataclass(frozen=True)
class EsgAssessment:
    ticker: str
    finding: Finding
    evidence_ids: tuple[str, ...]     # preuves ESG datées du titre (toutes, pour la fiche et le débat)
    basis_ids: tuple[str, ...] = ()   # preuves qui fondent le constat (sous-ensemble de evidence_ids)
    tonnes: Optional[float] = None    # plus grande borne inférieure documentée, s'il y en a une

    @property
    def score(self) -> Optional[float]:
        """Score du critère `esg` (absolu) ; None = manquant."""
        if self.finding == "filtre_esg":
            return SCORE_SCREENED
        if self.finding in ("controverse", "emetteur_majeur"):
            return SCORE_CONCERN
        return None

    @property
    def exclusion_rule(self) -> Optional[str]:
        """Règle d'exclusion déclenchée pour un profil qui exclut les controverses (`esg_exclusion`)."""
        return {"controverse": RULE_CONTROVERSY, "emetteur_majeur": RULE_EMISSIONS}.get(self.finding)


def assess(
    assets: Iterable[Mapping[str, str]],
    rows: Mapping[str, Iterable[Mapping[str, str]]],
) -> dict[str, EsgAssessment]:
    """Constat ESG par ticker.

    `assets` : lignes de l'univers (ticker, sector). `rows` : ticker → preuves ESG publiées à la date
    d'analyse, sources « utilisé » (sortie de `agents.tools.ResearchTools.preuves_esg` : evidence_id,
    signal_type, summary). Un ticker sans constat est absent du résultat.
    """
    out: dict[str, EsgAssessment] = {}
    for asset in assets:
        ticker = str(asset["ticker"])
        mine = list(rows.get(ticker, ()))
        ids = tuple(str(r["evidence_id"]) for r in mine)
        controversies = tuple(str(r["evidence_id"]) for r in mine
                              if str(r["signal_type"]).strip().casefold().startswith(CONTROVERSY_PREFIX))
        emissions = [(parse_emissions(str(r["summary"])), str(r["evidence_id"])) for r in mine
                     if str(r["signal_type"]) == EMISSIONS_SIGNAL]
        emissions = [(t, i) for t, i in emissions if t is not None]
        # Plusieurs sources : la plus grande borne inférieure (sans additionner des périmètres et des
        # méthodes différents).
        tonnes, tonnes_id = max(emissions, key=lambda item: (item[0], item[1])) if emissions else (None, None)
        if controversies:
            out[ticker] = EsgAssessment(ticker, "controverse", ids, controversies, tonnes)
        elif tonnes is not None and tonnes >= MAJOR_EMITTER_TONNES:
            out[ticker] = EsgAssessment(ticker, "emetteur_majeur", ids, (tonnes_id,), tonnes)
        elif str(asset["sector"]) in ESG_SCREENED_SECTORS:
            out[ticker] = EsgAssessment(ticker, "filtre_esg", ids, (), tonnes)
        elif ids:
            out[ticker] = EsgAssessment(ticker, "non_concluant", ids, (), tonnes)
    return out


def exclusions(assessments: Mapping[str, EsgAssessment]) -> dict[str, str]:
    """ticker → règle d'exclusion ESG (appliquée seulement si le profil a `esg_exclusion`)."""
    return {t: a.exclusion_rule for t, a in assessments.items() if a.exclusion_rule}
