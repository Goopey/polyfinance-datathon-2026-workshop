"""Indicateurs déterministes recoupés par calcul indépendant.

Conception : docs/02_AGENTS.md
Les valeurs en pourcentage sont exprimées en points de pourcentage (12,3 pour 12,3 %).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MetricResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: date
    ticker: str
    metric: str
    window: str
    value: Optional[float]
    unit: str
    currency: str
    observations: int
    start: Optional[date] = None
    end: Optional[date] = None
    evidence_id: Optional[str] = None
    note: str = ""  # raison si `value` est None (données insuffisantes)
