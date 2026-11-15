"""S8 — Aucune formulation prescriptive ; mention de simulation ; aucune route d'ordre.

Conception : docs/09_SCENARIOS_TEST.md, docs/08_CONFORMITE.md
Points 1 et 2 : vérifiés sur les sorties du pipeline local (données réelles, agents simulés).
Point 3 (aucune route d'ordre) : vérifié sur les routes réelles de l'API (easytrade/api/).
"""
import pytest

from easytrade.explain.wording import scan
from easytrade.schemas.explanation import DISCLAIMER

RUNS = [("amira", None), ("mateo", None), ("robert", None), ("robert", "TSLA"), ("robert", "BTC-USD")]


@pytest.fixture(scope="module", params=RUNS, ids=lambda p: "-".join(x for x in p if x))
def run(request, pipeline_run):
    result = pipeline_run(*request.param)
    assert result.status == "termine", result.error
    return result


@pytest.mark.scenario("S8")
def test_s08_1_aucune_formulation_refusee_dans_les_sorties(run, forbidden):
    assert {"achetez", "vendez", "vous devriez", "garanti", "sans risque", "rendement attendu"} <= set(forbidden)
    assert scan(run.explanation.model_dump(mode="json"), forbidden) == []
    # Le débat et les désaccords conservés sont aussi des sorties montrées à l'utilisateur.
    assert scan([r.model_dump(mode="json") for r in run.debate.values()], forbidden) == []
    assert scan(list(run.decision.disagreements), forbidden) == []
    assert scan(run.trace.model_dump(mode="json"), forbidden) == []


@pytest.mark.scenario("S8")
def test_s08_2_mention_de_simulation_dans_chaque_explication(run):
    assert run.explanation.disclaimer == DISCLAIMER
    assert "Simulation" in run.explanation.disclaimer and "pas un conseil financier" in run.explanation.disclaimer


@pytest.mark.scenario("S8")
def test_s08_aucune_prevision_ni_prix_cible(run):
    text = run.explanation.model_dump_json().lower()
    for term in ("prix cible", "rendement attendu", "va monter", "va baisser", "prévoit que"):
        assert term not in text


@pytest.mark.scenario("S8")
def test_s08_3_aucune_route_d_ordre():
    pytest.importorskip("fastapi")
    from easytrade.api.app import app

    openapi = app.openapi()
    routes = [(method.upper(), path) for path, methods in openapi["paths"].items() for method in methods]
    assert routes, "aucune route déclarée"
    # Lecture seule, sauf deux créations : un profil fictif et une analyse simulée.
    writes = sorted(path for method, path in routes if method not in {"GET", "HEAD", "OPTIONS"})
    assert writes == ["/profiles", "/runs"]
    forbidden = ("order", "ordre", "trade", "buy", "sell", "achat", "vente", "execute", "account", "compte",
                 "portfolio", "broker", "courtage", "payment", "paiement")
    for _, path in routes:
        assert not any(word in path.lower() for word in forbidden), path
    # Les corps acceptés ne contiennent aucun champ de transaction (montant, quantité, compte).
    schemas = openapi["components"]["schemas"]
    for name in ("RunRequest", "ProfileDraft"):
        fields = set(schemas[name]["properties"])
        assert not fields & {"amount", "montant", "quantity", "quantite", "account", "compte", "side", "price", "prix"}, name
        assert schemas[name].get("additionalProperties") is False, f"{name} doit refuser les champs hors contrat"
