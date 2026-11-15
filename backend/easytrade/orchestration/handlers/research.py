"""Lambda : étape 2, recherche (agent et outils filtrés par la date de référence).

Conception : docs/06_AWS.md
"""
from easytrade.orchestration.handlers.common import stage_handler
from easytrade.orchestration.pipeline import stage_research

handler = stage_handler("recherche", stage_research)
