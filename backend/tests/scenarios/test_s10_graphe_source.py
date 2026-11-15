"""S10 — Chaque arête est sourcée ou étiquetée hypothèse.

Conception : docs/09_SCENARIOS_TEST.md, docs/04_DONNEES.md (section 6)
Passe par l'API (`GET /assets/{ticker}/graph`), donc par ce que l'application affiche.
"""
import pytest

from easytrade.agents.simulated import simulated_client
from easytrade.api.service import ApiService


@pytest.fixture(scope="module")
def service(workspace):
    return ApiService(workspace=workspace, client=simulated_client())


@pytest.mark.scenario("S10")
def test_s10_chaque_arete_affichee_porte_une_preuve_datee(service):
    as_of = service.default_as_of
    shown = 0
    for asset in service.assets():
        graph = service.graph(asset.ticker)
        for edge in graph.edges:
            shown += 1
            assert edge.evidence_id, f"{edge.source}→{edge.target} : arête sans preuve"
            evidence = service.evidence(edge.evidence_id)
            assert evidence.type == "relation"
            assert evidence.claim_kind == edge.claim_kind  # « Hypothèse » affichée si la preuve l'est
            assert evidence.published_at <= as_of  # aucune relation connue seulement après la date d'analyse
            assert evidence.source.source_id and evidence.processing  # document ou source citée
            if edge.claim_kind == "FAIT":
                assert "http" in evidence.processing, "un FAIT cite son document"
    assert shown > 0, "aucune arête affichée"


@pytest.mark.scenario("S10")
def test_s10_graphe_centre_sur_le_titre_et_noeuds_hors_univers_en_contexte(service):
    graph = service.graph("RY.TO")
    ids = {node.id for node in graph.nodes}
    assert graph.center == "RY.TO" and "TD.TO" in ids
    assert all(graph.center in (edge.source, edge.target) for edge in graph.edges)  # profondeur 1
    outside = [node for node in graph.nodes if not node.in_universe]
    assert outside, "les comparables hors univers sont affichés comme contexte"


@pytest.mark.scenario("S10")
def test_s10_aucune_relation_avant_sa_date(workspace):
    """À une date antérieure à la date d'effet des comparables, le graphe est vide : pas de fuite du futur."""
    from easytrade.agents.tools import ResearchTools
    from easytrade.explain.evidence_ledger import EvidenceLedger

    tools = ResearchTools(workspace.store.assets(), "2023-06-30", workspace.settings.reference_dir,
                          EvidenceLedger(__import__("datetime").date(2023, 6, 30)), workspace.registry)
    assert tools.relations("RY.TO") == []
