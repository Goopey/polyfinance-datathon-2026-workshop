"""S11 — Le désaccord du débat est conservé.

Conception : docs/09_SCENARIOS_TEST.md, docs/02_AGENTS.md (section 3)
Donné : un candidat sur lequel les positions finales divergent (Bull : appui ; Réaliste : appui
avec réserve ; Bear : opposition). Les positions sont imposées par un faux client, pour que le
test porte sur ce que le code fait du désaccord, pas sur le jugement d'un modèle.
"""
import pytest

from easytrade.agents.simulated import simulated_client
from easytrade.orchestration.pipeline import run_pipeline

STANCES = {"bull": "appui", "realist": "appui_reserve", "bear": "opposition"}


def _role(payload, role):
    return next(e["evidence_id"] for e in payload["evidence"] if e["role"] == role)


def _agent(agent):
    def respond(payload):
        volatility = _role(payload, "annualized_volatility:full")
        arguments = {
            "bull": [{"text": "Rendement annualisé observé de {%s}." % _role(payload, "annualized_return:full")}],
            "realist": [{"text": "Volatilité annualisée observée de {%s}." % volatility}],
            "bear": [
                {"text": "Volatilité annualisée de {%s}, à rapprocher du repère de {%s} du profil."
                         % (volatility, _role(payload, "repere:volatilite"))},
                {"text": "Les analystes anticipent une chute de 40 %.", "evidence_ids": [volatility]},  # nombre inventé
                {"text": "Risque de réputation documenté.", "evidence_ids": ["EV-999999"]},              # preuve inconnue
            ],
        }[agent]
        return {"stance": STANCES[agent], "confidence": "moyenne", "arguments": arguments,
                "open_questions": ["Aucune preuve ESG datée disponible."] if agent == "bear" else []}
    return respond


@pytest.fixture(scope="module")
def run(workspace):
    client = simulated_client()
    for agent in STANCES:
        client.responders[f"debate.{agent}"] = _agent(agent)
    result = run_pipeline("amira", client=client, workspace=workspace)
    assert result.status == "termine", result.error
    return result


@pytest.mark.scenario("S11")
def test_s11_desaccord_dans_la_decision(run):
    decision = run.decision
    assert decision.retained
    for ticker in decision.retained:
        assert run.debate[ticker].dissent
        entries = [d for d in decision.disagreements if d.startswith(f"{ticker} — ")]
        assert len(entries) == 1
        # Recopié tel quel : les trois positions et l'argument de chacun.
        assert "Bull : appui (" in entries[0] and "Réaliste : appui avec réserve (" in entries[0]
        assert "Bear : opposition (" in entries[0]
        assert decision.candidate_confidence[ticker] != "élevé"


@pytest.mark.scenario("S11")
def test_s11_desaccord_dans_l_explication(run):
    for item in run.explanation.items:
        assert item.debate_summary.dissent is True
        assert item.confidence != "élevée"
        assert {p.agent: p.stance for p in item.debate} == STANCES
        assert item.debate_summary.bear.startswith("Opposition — ")
        assert item.risks and "Aucune preuve ESG datée disponible." in item.unknowns
        assert item.to_review  # opposition du Bear appuyée sur un repère du profil


@pytest.mark.scenario("S11")
def test_s11_le_debat_ne_change_ni_le_classement_ni_les_pistes(run, pipeline_run):
    reference = pipeline_run("amira")
    assert [c.ticker for c in run.decision.ranking] == [c.ticker for c in reference.decision.ranking]
    assert [c.fit_score for c in run.decision.ranking] == [c.fit_score for c in reference.decision.ranking]
    assert run.decision.retained == reference.decision.retained


@pytest.mark.scenario("S11")
def test_s11_arguments_sans_preuve_valide_supprimes(run):
    for record in run.debate.values():
        bear = record.position("bear")
        assert len(bear.arguments) == 1 and bear.removed_arguments == 2
        assert "40" not in bear.arguments[0].text and "EV-999999" not in bear.model_dump_json()
    step = next(s for s in run.trace.steps if s.step == "debate.bear.round3")
    assert "supprimés" in step.note and step.prompt_version == "bear@v1"


@pytest.mark.scenario("S11")
def test_s11_oppositions_majoritaires_aucune_piste_forcee(workspace):
    # Si le débat s'oppose à toutes les pistes, la confiance est faible partout : aucune recommandation.
    client = simulated_client()
    for agent, stance in (("bull", "appui"), ("realist", "opposition"), ("bear", "opposition")):
        client.responders[f"debate.{agent}"] = (
            lambda payload, stance=stance: {"stance": stance, "confidence": "moyenne", "arguments": [
                {"text": "Volatilité annualisée observée de {%s}." % _role(payload, "annualized_volatility:full")}]})
    result = run_pipeline("amira", client=client, workspace=workspace)
    assert result.status == "termine", result.error
    assert result.decision.no_recommendation and result.explanation.no_recommendation
    assert result.explanation.items == () and "Confiance faible" in result.explanation.missing[0]
    assert len(result.decision.disagreements) == len(result.debate)  # le désaccord reste consigné
