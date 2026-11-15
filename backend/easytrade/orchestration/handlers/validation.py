"""Lambda : couche de validation financière (indicateurs déterministes, aucune IA).

Conception : docs/06_AWS.md
"""
from easytrade.orchestration.handlers.common import stage_handler
from easytrade.orchestration.pipeline import stage_validation

handler = stage_handler("validation", stage_validation)
