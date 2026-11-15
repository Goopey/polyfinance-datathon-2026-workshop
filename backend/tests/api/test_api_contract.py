"""Contrat mobile ↔ backend, côté backend : chaque route rend exactement ce que le mobile attend.

Référence : mobile/contracts.schema.json, généré depuis mobile/src/types/contracts.ts. Le mobile
valide son serveur fictif contre le même fichier (mobile/tests/contracts.test.ts) : un champ
ajouté, retiré ou renommé d'un seul côté fait échouer l'un des deux jeux de tests.

Les analyses tournent sur les vraies données du jeu de départ, avec les agents simulés (aucun modèle).
"""
import pytest

from tests.api.conftest import cited_evidence_ids

PERSONAS = ("amira", "mateo", "robert")
STEP_IDS = ["profil", "recherche_validation", "debat", "decision", "explication"]


# --- profils ------------------------------------------------------------------------------------
def test_personas_conformes_et_identiques_au_fichier_de_reference(api, contract, personas):
    response = api.get("/personas")
    assert response.status_code == 200
    body = response.json()
    assert body == personas["personas"]
    for persona in body:
        contract("Persona", persona, f"persona {persona['id']}")


@pytest.mark.parametrize("persona_id", PERSONAS)
def test_profil_d_un_persona_conforme(api, contract, personas, persona_id):
    body = api.get(f"/profiles/{persona_id}").json()
    contract("ProfileWeights", body)
    entry = next(p for p in personas["personas"] if p["id"] == persona_id)
    assert body["profile_id"] == persona_id and body["label"] == entry["profil"]["nom"]
    assert body["weights"] == pytest.approx(entry["poids"])
    assert sum(body["weights"].values()) == pytest.approx(1.0)
    constraints = body["hard_constraints"]
    for name in ("max_weight_per_asset", "max_weight_per_sector", "max_weight_crypto", "esg_exclusion", "speculatif"):
        assert constraints[name] == entry["contraintes"][name], name
    assert constraints["excluded_asset_classes"] == (["crypto"] if entry["contraintes"]["max_weight_crypto"] == 0 else [])
    assert body["rationale"], "la justification des valeurs doit être affichable"


def test_profil_inconnu_404(api):
    response = api.get("/profiles/inconnu")
    assert response.status_code == 404 and "inconnu" in response.json()["detail"]


def test_questionnaire_cree_un_profil_fictif_conforme(api, contract):
    draft = {"objectif": "preserver", "horizon": "court", "tolerance": "faible",
             "preferences": ["esg", "diversification"], "exclusions": ["crypto", "speculatif", "controverses"]}
    contract("ProfileDraft", draft)
    response = api.post("/profiles", json=draft)
    assert response.status_code == 200, response.text
    body = response.json()
    contract("ProfileWeights", body)
    assert body["profile_id"].startswith("fictif_") and body["label"] == "Profil fictif"
    # Chaque exclusion du questionnaire devient une règle que le moteur applique.
    constraints = body["hard_constraints"]
    assert constraints["max_weight_crypto"] == 0 and constraints["excluded_asset_classes"] == ["crypto"]
    assert constraints["speculatif"] == "exclu" and constraints["esg_exclusion"] is True
    # Même questionnaire → même profil (identifiant stable, donc analyses reproductibles).
    assert api.post("/profiles", json=draft).json()["profile_id"] == body["profile_id"]
    assert api.get(f"/profiles/{body['profile_id']}").json() == body
    # Un profil fictif n'est pas un persona de l'énoncé.
    assert body["profile_id"] not in [p["id"] for p in api.get("/personas").json()]


def test_profil_fictif_analysable_et_source_du_questionnaire(api, contract, finished_run):
    profile = api.post("/profiles", json={"objectif": "croissance", "horizon": "long", "tolerance": "elevee",
                                          "preferences": ["technologies"], "exclusions": []}).json()
    status = finished_run(profile["profile_id"])
    assert status["status"] == "termine", status["error"]
    contract("RunStatus", status)
    # Les phrases du profil sont attribuées au questionnaire, pas à l'énoncé du case.
    sources = set()
    for evidence_id in cited_evidence_ids(status["result"]):
        evidence = api.get(f"/evidence/{evidence_id}", params={"run_id": status["run_id"]}).json()
        if evidence["type"] == "profile" and evidence["claim_kind"] == "FAIT":
            sources.add(evidence["source"]["source_id"])
    assert sources <= {"profil_questionnaire"}, sources


def test_poids_modifies_creent_une_variante_normalisee(api, contract, finished_run):
    weights = dict(api.get("/profiles/amira").json()["weights"], esg=0.60)
    response = api.post("/profiles", json={"base_persona": "amira", "objectif": "equilibre", "horizon": "moyen",
                                           "tolerance": "moderee", "preferences": [], "exclusions": [],
                                           "weights_override": weights})
    assert response.status_code == 200, response.text
    body = response.json()
    contract("ProfileWeights", body)
    assert body["profile_id"].startswith("amira_") and body["label"] == "Amira (poids modifiés)"
    assert sum(body["weights"].values()) == pytest.approx(1.0)
    assert body["weights"]["esg"] > api.get("/profiles/amira").json()["weights"]["esg"]
    # Les règles du persona d'origine sont conservées, et la variante s'analyse.
    assert body["hard_constraints"] == api.get("/profiles/amira").json()["hard_constraints"]
    assert finished_run(body["profile_id"])["status"] == "termine"


@pytest.mark.parametrize("body, status", [
    ({"exclusions": ["actions"]}, 422),                       # exclusion que le moteur n'applique pas
    ({"preferences": ["momentum"]}, 422),
    ({"tolerance": "extreme"}, 422),
    ({"champ_inconnu": 1}, 422),
    ({"base_persona": "amira", "weights_override": {"inconnu": 0.5}}, 422),
    ({"base_persona": "amira", "weights_override": {"esg": -1}}, 422),
    ({"base_persona": "personne"}, 404),
])
def test_demandes_de_profil_invalides_refusees(api, body, status):
    assert api.post("/profiles", json=body).status_code == status


# --- analyses -----------------------------------------------------------------------------------
@pytest.mark.parametrize("persona_id", PERSONAS)
def test_analyse_d_un_persona_conforme_et_fidele_au_pipeline(api, contract, finished_run, pipeline_run, persona_id):
    status = finished_run(persona_id)
    contract("RunStatus", status, f"run {persona_id}")
    assert status["status"] == "termine" and status["error"] is None
    assert [s["id"] for s in status["steps"]] == STEP_IDS and {s["status"] for s in status["steps"]} == {"ok"}
    # L'API n'ajoute ni ne retire rien : le résultat est celui du pipeline local.
    expected = pipeline_run(persona_id)
    assert status["run_id"] == expected.run_id
    assert status["result"] == expected.explanation.model_dump(mode="json")
    assert "Simulation" in status["result"]["disclaimer"]


def test_etat_en_cours_conforme(api, contract):
    """Juste après le lancement, la réponse est déjà conforme (étapes en attente, résultat absent ou présent)."""
    profile = api.post("/profiles", json={"tolerance": "moderee", "preferences": ["stabilite"]}).json()
    run_id = api.post("/runs", json={"profile_id": profile["profile_id"]}).json()["run_id"]
    status = api.get(f"/runs/{run_id}").json()
    contract("RunStatus", status)
    assert status["status"] in ("en_cours", "termine")
    assert (status["result"] is None) == (status["status"] == "en_cours")
    contract("Trace", api.get(f"/runs/{run_id}/trace").json())


def test_meme_demande_meme_analyse(api, finished_run):
    first = finished_run("amira")
    assert api.post("/runs", json={"profile_id": "amira"}).json()["run_id"] == first["run_id"]
    assert api.get(f"/runs/{first['run_id']}").json() == first


def test_tester_une_idee_robert(api, contract, finished_run):
    status = finished_run("robert", "tsla")  # la casse du symbole est normalisée
    contract("RunStatus", status)
    assert status["requested_ticker"] == "TSLA" and status["run_id"].endswith("_TSLA")
    coherence = status["result"]["coherence"]
    assert coherence["ticker"] == "TSLA" and coherence["verdict"] == "incohérent avec le profil"
    assert coherence["tensions"] and all(claim["evidence_ids"] for claim in coherence["tensions"])
    assert finished_run("robert")["result"]["coherence"] is None


def test_aucune_recommandation_est_une_reponse_valide(contract, finished_run):
    status = finished_run("mateo")
    contract("RunStatus", status)
    result = status["result"]
    if result["no_recommendation"]:
        assert result["items"] == [] and result["missing"], "« aucune recommandation » doit dire ce qui manque"
    else:
        assert result["items"]


def test_analyse_a_une_date_passee_sans_fuite_du_futur(api, contract, finished_run):
    status = finished_run("amira", as_of="2024-06-28")
    contract("RunStatus", status)
    assert status["status"] == "termine", status["error"]
    assert status["as_of"] == "2024-06-28" and "2024-06-28" in status["run_id"]
    for evidence_id in cited_evidence_ids(status["result"]):
        evidence = api.get(f"/evidence/{evidence_id}", params={"run_id": status["run_id"]}).json()
        assert evidence["published_at"] <= "2024-06-28", evidence_id


@pytest.mark.parametrize("body, status", [
    ({"profile_id": "inconnu"}, 404),
    ({"profile_id": "amira", "requested_ticker": "NOPE"}, 404),
    ({"profile_id": "amira", "as_of": "pas-une-date"}, 422),
    ({"profile_id": "amira", "ordre": "achat"}, 422),  # aucun champ hors contrat
    ({}, 422),
])
def test_demandes_d_analyse_invalides_refusees(api, body, status):
    assert api.post("/runs", json=body).status_code == status


def test_analyse_inconnue_404(api):
    assert api.get("/runs/run_inconnu").status_code == 404
    assert api.get("/runs/run_inconnu/trace").status_code == 404
    assert api.get("/evidence/EV-000001", params={"run_id": "run_inconnu"}).status_code == 404


def test_trace_conforme_et_controles_de_gouvernance(api, contract, finished_run, pipeline_run):
    status = finished_run("robert", "tsla")
    trace = api.get(f"/runs/{status['run_id']}/trace").json()
    contract("Trace", trace)
    # Mêmes étapes, dans le même ordre, que le pipeline local (seuls les horodatages diffèrent).
    expected = pipeline_run("robert", "TSLA").trace.steps
    assert [(s["step"], s["kind"], s["status"]) for s in trace["steps"]] == [(s.step, s.kind, s.status) for s in expected]
    kinds = {s["kind"] for s in trace["steps"]}
    assert kinds == {"code", "llm", "controle"}
    controls = [s["step"] for s in trace["steps"] if s["kind"] == "controle"]
    assert {"controle.avant_debat", "controle.avant_affichage"} <= set(controls)
    assert all(s["note"] for s in trace["steps"] if s["kind"] == "controle")


# --- preuves ------------------------------------------------------------------------------------
@pytest.mark.parametrize("persona_id, ticker", [("amira", None), ("robert", "tsla")])
def test_toute_preuve_citee_est_servie_pour_son_analyse(api, contract, finished_run, persona_id, ticker):
    status = finished_run(persona_id, ticker)
    ids = cited_evidence_ids(status["result"])
    assert len(ids) > 10
    for evidence_id in ids:
        response = api.get(f"/evidence/{evidence_id}", params={"run_id": status["run_id"]})
        assert response.status_code == 200, evidence_id
        evidence = response.json()
        contract("Evidence", evidence, evidence_id)
        assert evidence["evidence_id"] == evidence_id
        assert evidence["published_at"] <= status["as_of"]


def test_les_identifiants_de_preuves_sont_propres_a_une_analyse(api, service, finished_run):
    """`EV-000050` ne désigne pas la même preuve dans deux analyses : le mobile doit transmettre `run_id`."""
    amira, robert = finished_run("amira"), finished_run("robert")
    ledger_a = service._runs[amira["run_id"]].result.ledger
    ledger_r = service._runs[robert["run_id"]].result.ledger
    differing = next(i for i in ledger_a.ids() if i in ledger_r and ledger_a.get(i) != ledger_r.get(i))
    from_a = api.get(f"/evidence/{differing}", params={"run_id": amira["run_id"]}).json()
    from_r = api.get(f"/evidence/{differing}", params={"run_id": robert["run_id"]}).json()
    assert from_a == ledger_a.get(differing).model_dump(mode="json")
    assert from_r == ledger_r.get(differing).model_dump(mode="json")
    assert from_a != from_r


def test_preuve_inconnue_404(api, finished_run):
    run_id = finished_run("amira")["run_id"]
    assert api.get("/evidence/EV-999999", params={"run_id": run_id}).status_code == 404
    assert api.get("/evidence/EV-999999").status_code == 404


# --- actifs, graphe, données --------------------------------------------------------------------
def test_univers_conforme(api, contract):
    assets = api.get("/assets").json()
    assert len(assets) == 31
    for asset in assets:
        contract("AssetSummary", asset)


def test_fiches_de_tout_l_univers_conformes_et_coherentes_avec_les_preuves(api, contract, finished_run):
    from easytrade.engine.coherence import RISK_LIMITS

    status = finished_run("robert")
    run_id = status["run_id"]
    max_vol, max_loss = RISK_LIMITS["faible à modérée"]
    for asset in api.get("/assets").json():
        ticker = asset["ticker"]
        sheet = api.get(f"/assets/{ticker}", params={"run_id": run_id}).json()
        contract("AssetSheet", sheet, f"fiche {ticker}")
        assert sheet["as_of"] == status["as_of"] and sheet["metrics"], ticker
        for metric in sheet["metrics"]:
            # Le chiffre affiché est exactement celui de la preuve vers laquelle il pointe.
            evidence = api.get(f"/evidence/{metric['evidence_id']}", params={"run_id": run_id}).json()
            assert evidence["subject"] == ticker and evidence["value"] == metric["value"], (ticker, metric["metric"])
            assert metric["universe_min"] <= metric["value"] <= metric["universe_max"]
        limits = {m["metric"]: m["profile_limit"] for m in sheet["metrics"]}
        assert limits.get("volatilite") == max_vol and limits.get("perte_max") == max_loss
        assert all(v is None for k, v in limits.items() if k not in ("volatilite", "perte_max"))


def test_fiche_hors_analyse(api, contract):
    sheet = api.get("/assets/AAPL").json()
    contract("AssetSheet", sheet)
    assert all(m["profile_limit"] is None for m in sheet["metrics"])
    for metric in sheet["metrics"]:
        evidence = api.get(f"/evidence/{metric['evidence_id']}").json()  # registre hors analyse
        assert evidence["subject"] == "AAPL" and evidence["value"] == metric["value"]
    with_profile = api.get("/assets/AAPL", params={"profile_id": "amira"}).json()
    assert {m["metric"]: m["profile_limit"] for m in with_profile["metrics"]}["volatilite"] == 45.0


def test_actif_inconnu_404(api):
    assert api.get("/assets/NOPE").status_code == 404
    assert api.get("/assets/NOPE/graph").status_code == 404
    assert api.get("/assets/AAPL", params={"profile_id": "inconnu"}).status_code == 404


def test_graphe_conforme_et_source(api, contract, finished_run):
    """S10 : toute arête servie porte une preuve. Tant que `graph_edges.csv` est vide, le graphe n'a que son centre."""
    run_id = finished_run("amira")["run_id"]
    for ticker in ("NVDA", "RY.TO", "BTC-USD"):
        graph = api.get(f"/assets/{ticker}/graph", params={"run_id": run_id}).json()
        contract("DependencyGraph", graph, f"graphe {ticker}")
        assert graph["center"] == ticker and graph["nodes"][0] == {
            "id": ticker, "label": graph["nodes"][0]["label"], "in_universe": True}
        for edge in graph["edges"]:
            assert edge["evidence_id"], edge
            assert api.get(f"/evidence/{edge['evidence_id']}", params={"run_id": run_id}).status_code == 200


def test_graphe_traduction_des_aretes(service, contract, monkeypatch):
    """Traduction d'arêtes sourcées (fait, hypothèse, nœud hors univers, relation hors contrat ignorée)."""
    from tests.helpers import draft

    context = service._context(None)
    fact = context.ledger.add(draft("NVDA — FOURNISSEUR — TSM", None, None, evidence_type="relation", subject="TSM→NVDA"))
    guess = context.ledger.add(draft("NVDA — CONCURRENT — AAPL", None, None, claim_kind="HYPOTHESE",
                                     evidence_type="relation", subject="NVDA→AAPL"))

    class Tools:
        def relations(self, ticker):
            return [
                {"evidence_id": fact.evidence_id, "source": "TSM", "target": "NVDA", "relation": "FOURNISSEUR"},
                {"evidence_id": guess.evidence_id, "source": "NVDA", "target": "AAPL", "relation": "CONCURRENT"},
                {"evidence_id": guess.evidence_id, "source": "NVDA", "target": "MSFT", "relation": "ACCORD_POTENTIEL"},
            ]

    monkeypatch.setattr(service, "_tools", lambda _context: Tools())
    graph = service.graph("NVDA").model_dump(mode="json")
    contract("DependencyGraph", graph)
    assert [(e["source"], e["target"], e["relation"], e["claim_kind"]) for e in graph["edges"]] == [
        ("TSM", "NVDA", "FOURNISSEUR", "FAIT"), ("NVDA", "AAPL", "CONCURRENT", "HYPOTHESE")]
    assert all(e["evidence_id"] for e in graph["edges"])
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert list(nodes) == ["NVDA", "TSM", "AAPL"]
    assert nodes["NVDA"]["in_universe"] and nodes["AAPL"]["in_universe"] and not nodes["TSM"]["in_universe"]
    assert nodes["NVDA"]["label"] == service._names["NVDA"] and nodes["TSM"]["label"] == "TSM"


def test_donnees_sources_et_controles_qualite(api, contract, registry):
    body = api.get("/data").json()
    contract("DataOverview", body)
    assert [s["source_id"] for s in body["sources"]] == [r.source_id for r in registry.records()]
    assert {"starter_prices", "profil_questionnaire"} <= {s["source_id"] for s in body["sources"] if s["statut"] == "utilisé"}
    assert len(body["quality"]) == 8
    assert {c["status"] for c in body["quality"]} <= {"ok", "avertissement", "erreur"}
    warned = [c for c in body["quality"] if c["status"] == "avertissement"]
    assert warned and all(c["details"] for c in warned), "un avertissement doit dire ce qu'il a trouvé"


# --- étapes affichées ---------------------------------------------------------------------------
def _step(name, status="ok"):
    from easytrade.schemas.trace import TraceStep

    return TraceStep(step=name, kind="code", status=status, started_at="t0", ended_at="t1")


@pytest.mark.parametrize("recorded, finished, expected", [
    ([], None, ["en_cours", "attente", "attente", "attente", "attente"]),
    (["profil", "validation"], None, ["ok", "en_cours", "attente", "attente", "attente"]),
    (["profil", "validation", "recherche", "dossiers_de_preuves"], None, ["ok", "ok", "en_cours", "attente", "attente"]),
    (["profil", "recherche", "debate.bull.round1", "decision"], None, ["ok", "ok", "ok", "ok", "en_cours"]),
    (["profil", "recherche", "debat", "decision", "explication"], "termine", ["ok"] * 5),
    (["profil"], "echec", ["ok", "echec", "attente", "attente", "attente"]),
])
def test_etapes_affichees(recorded, finished, expected):
    from easytrade.api.service import ApiService

    steps = ApiService._display_steps([_step(name) for name in recorded], finished)
    assert [s.id for s in steps] == STEP_IDS
    assert [s.status for s in steps] == expected


def test_etape_en_echec_visible():
    from easytrade.api.service import ApiService

    steps = ApiService._display_steps([_step("profil"), _step("recherche"), _step("debat", "echec")], "echec")
    assert [s.status for s in steps] == ["ok", "ok", "echec", "attente", "attente"]


# --- surface de l'API ---------------------------------------------------------------------------
def test_routes_exposees():
    """La table de docs/01_ARCHITECTURE.md est la surface complète de l'API."""
    from easytrade.api.app import app

    routes = sorted((method.upper(), path) for path, methods in app.openapi()["paths"].items() for method in methods)
    assert routes == [
        ("GET", "/assets"), ("GET", "/assets/{ticker}"), ("GET", "/assets/{ticker}/graph"), ("GET", "/data"),
        ("GET", "/evidence/{evidence_id}"), ("GET", "/health"), ("GET", "/personas"),
        ("GET", "/profiles/{profile_id}"), ("GET", "/runs/{run_id}"), ("GET", "/runs/{run_id}/trace"),
        ("POST", "/profiles"), ("POST", "/runs"),
    ]


def test_cors_pour_l_application_web(api):
    response = api.get("/health", headers={"Origin": "http://localhost:8081"})
    assert response.json() == {"status": "ok", "simulation": True}
    assert response.headers.get("access-control-allow-origin") in ("*", "http://localhost:8081")


# --- le validateur lui-même ---------------------------------------------------------------------
def test_le_validateur_du_contrat_refuse_un_ecart(contract, finished_run):
    """Garde-fou : ces tests ne passent pas « à vide ». Un champ en trop, en moins ou mal typé est refusé."""
    import copy

    good = finished_run("amira")
    contract("RunStatus", good)
    extra = {**good, "champ_hors_contrat": 1}
    missing = {k: v for k, v in good.items() if k != "steps"}
    wrong_value = copy.deepcopy(good)
    wrong_value["result"]["items"][0]["confidence"] = "élevé"  # le mobile attend le féminin : « élevée »
    nested_extra = copy.deepcopy(good)
    nested_extra["result"]["items"][0]["score"] = 0.5
    for label, payload in (("champ en trop", extra), ("champ manquant", missing), ("valeur hors énumération", wrong_value),
                           ("champ en trop dans une piste", nested_extra)):
        with pytest.raises(AssertionError, match="non conforme"):
            contract("RunStatus", payload, label)
