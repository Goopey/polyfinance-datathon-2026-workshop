"""Pipeline local : déterminisme, trace, échec propre, cohérence temporelle, « aucune recommandation ».

Conception : docs/01_ARCHITECTURE.md, docs/05_EXPLICABILITE.md (section 3)
Données réelles du jeu de départ ; agents simulés ou faux client (aucun modèle).
"""
import json
from datetime import date

import pytest

from easytrade.agents.simulated import MODEL_ID, NOTE, simulated_client
from easytrade.orchestration.pipeline import run_pipeline


def test_deux_executions_identiques(workspace, pipeline_run):
    first = pipeline_run("robert", "TSLA")
    second = run_pipeline("robert", requested_ticker="TSLA", client=simulated_client(), workspace=workspace)
    assert second.explanation == first.explanation
    assert second.decision == first.decision
    assert second.ledger.to_records() == first.ledger.to_records()  # mêmes identifiants de preuves


def test_trace_observable_dans_l_ordre(pipeline_run):
    run = pipeline_run("amira")
    steps = [s.step for s in run.trace.steps]
    assert steps == [
        "profil", "validation", "recherche", "dossiers_de_preuves", "controle.avant_debat",
        "debate.bull.round1", "debate.realist.round1", "debate.bear.round1",
        "debate.bull.round3", "debate.realist.round3", "debate.bear.round3",
        "decision", "controle.plafonds_panier", "controle.diversification", "controle.aucune_recommandation",
        "explication", "controle.avant_affichage",
    ]
    by_name = {s.step: s for s in run.trace.steps}
    assert all(s.status == "ok" for s in run.trace.steps)
    # Étapes de code : aucun modèle. Étapes LLM : modèle et version du prompt enregistrés.
    for name in ("validation", "dossiers_de_preuves", "decision"):
        assert by_name[name].kind == "code" and by_name[name].model_id is None
    for name, prompt in (("profil", "profile_weighting@v1"), ("recherche", "research@v1"),
                         ("debate.bear.round1", "bear@v1"), ("explication", "explanation@v1")):
        assert by_name[name].kind == "llm"
        assert (by_name[name].model_id, by_name[name].prompt_version) == (MODEL_ID, prompt)
    assert any(t.startswith("preuves_esg") or t.startswith("relations") for t in by_name["recherche"].tools_called)
    assert by_name["validation"].inputs and by_name["debate.bear.round1"].evidence_in
    # La trace ne contient que des actions observables : aucun champ de raisonnement.
    assert not {"reasoning", "thinking", "raisonnement"} & set(by_name["explication"].model_dump())


def test_agents_simules_signales_a_l_utilisateur(pipeline_run):
    run = pipeline_run("amira")
    assert run.model_id == MODEL_ID
    assert NOTE in run.explanation.unknowns


def test_mateo_aucune_recommandation_tant_que_l_esg_n_est_pas_source(pipeline_run):
    run = pipeline_run("mateo")
    explanation = run.explanation
    assert run.status == "termine" and explanation.no_recommendation and explanation.items == ()
    assert "ESG" in explanation.missing[0]
    assert {r.ticker for r in explanation.rejected} == {"BTC-USD", "ETH-USD"}  # aucune piste crypto
    by_name = {s.step: s for s in run.trace.steps}
    assert by_name["debat"].status == "ignore"
    assert by_name["explication"].kind == "code" and by_name["explication"].model_id is None
    assert "Aucune recommandation" in by_name["controle.aucune_recommandation"].note


def test_aucune_preuve_posterieure_a_une_date_passee(pipeline_run):
    as_of = "2024-06-28"
    run = pipeline_run("amira", None, as_of)
    assert run.status == "termine", run.error
    assert run.as_of == date(2024, 6, 28) and run.run_id == "run_2024-06-28_amira"
    assert all(e.published_at <= run.as_of for e in run.ledger)
    assert all((e.window.end is None or e.window.end <= run.as_of) for e in run.ledger)
    # Moins de trois ans d'historique à cette date : la pire période glissante de 3 ans n'existe pas,
    # le critère « horizon » est signalé manquant au lieu d'être inventé.
    assert "historique de prix insuffisant" in run.decision.missing_info


def test_sortie_de_modele_invalide_echec_propre(workspace):
    client = simulated_client()
    client.responders["debate.bear"] = [{"stance": "peut-être"}]  # invalide, y compris après la relance
    result = run_pipeline("amira", client=client, workspace=workspace)
    assert result.status == "echec" and result.explanation is None
    assert "LLMOutputError" in result.error and "debate.bear.round1" in result.error
    last = result.trace.steps[-1]
    assert (last.step, last.status) == ("debat", "echec")
    assert len([c for c in client.calls if c["step"] == "debate.bear.round1"]) == 2  # une seule relance


def test_titre_inconnu_refuse_sans_analyse(workspace):
    result = run_pipeline("robert", requested_ticker="ZZZZ", client=simulated_client(), workspace=workspace)
    assert result.status == "echec" and "UnknownTickerError" in result.error
    assert result.trace.steps == ()


def test_artefacts_enregistres(pipeline_run, tmp_path):
    run = pipeline_run("robert", "TSLA")
    target = run.save(tmp_path)
    assert target.name == "run_2026-11-12_robert_TSLA"
    names = {p.name for p in target.iterdir()}
    assert {"run.json", "explanation.json", "decision.json", "trace.json", "evidence.json", "debate.json",
            "fidelity.json", "profile_weights.json"} <= names
    explanation = json.loads((target / "explanation.json").read_text(encoding="utf-8"))
    evidence = {e["evidence_id"] for e in json.loads((target / "evidence.json").read_text(encoding="utf-8"))}
    # Le contrat attendu par le mobile (mobile/src/types/contracts.ts) et des preuves toutes résolubles.
    assert {"run_id", "as_of", "profile_id", "headline", "no_recommendation", "missing", "items", "rejected",
            "coherence", "unknowns", "disclaimer"} == set(explanation)
    assert {"ticker", "name", "asset_class", "sector", "fit", "confidence", "to_review", "why", "contributions",
            "not_applicable", "debate", "debate_summary", "risks", "limits", "unknowns"} == set(explanation["items"][0])
    cited = {i for item in explanation["items"] for claim in item["why"] for i in claim["evidence_ids"]}
    assert cited and cited <= evidence
