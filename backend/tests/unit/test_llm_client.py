"""Client LLM : sortie structurée validée, une relance, échec propre.

Conception : docs/02_AGENTS.md (règles communes), docs/06_AWS.md
Aucun appel réseau : `FakeLLMClient` pour le protocole, un faux client `bedrock-runtime` pour
vérifier la forme de la requête Converse.
"""
import pytest
from pydantic import BaseModel

from easytrade.agents.llm_client import (
    BedrockClient,
    FakeLLMClient,
    LLMOutputError,
    LLMUnavailableError,
    Prompt,
    load_prompt,
    make_client,
    structured_call,
)

PROMPT = Prompt(name="test", version="v1", text="Consigne de test.")


class Answer(BaseModel):
    stance: str
    score: int


def call(client, step="etape"):
    return structured_call(client, step=step, prompt=PROMPT, payload={"x": 1}, schema=Answer)


def test_sortie_valide_au_premier_appel():
    client = FakeLLMClient({"etape": lambda payload: {"stance": "appui", "score": payload["x"]}}, name="faux")
    answer, info = call(client)
    assert answer == Answer(stance="appui", score=1)
    assert (info.model_id, info.prompt_version, info.attempts) == ("faux", "test@v1", 1)


def test_sortie_texte_json_acceptee():
    client = FakeLLMClient({"etape": ['{"stance": "appui", "score": 2}']})
    assert call(client)[0].score == 2


def test_une_relance_avec_le_motif_puis_succes():
    client = FakeLLMClient({"etape": [{"stance": "appui"}, {"stance": "appui", "score": 3}]})
    answer, info = call(client)
    assert answer.score == 3 and info.attempts == 2
    # Le deuxième appel reçoit le motif du rejet ; le premier n'en reçoit pas.
    assert client.calls[0]["feedback"] is None
    assert "rejetée" in client.calls[1]["feedback"] and "score" in client.calls[1]["feedback"]


@pytest.mark.parametrize("bad", [{"stance": "appui"}, "ceci n'est pas du JSON", None, [1, 2]])
def test_echec_propre_apres_une_seule_relance(bad):
    client = FakeLLMClient({"etape": [bad]})
    with pytest.raises(LLMOutputError):
        call(client)
    assert len(client.calls) == 2  # un appel + une relance, jamais plus


def test_faux_client_prefixe_et_repli():
    client = FakeLLMClient({
        "debate": lambda p: {"stance": "debat", "score": 0},
        "debate.bear": lambda p: {"stance": "bear", "score": 0},
        "*": lambda p: {"stance": "repli", "score": 0},
    })
    assert call(client, "debate.bear.round1")[0].stance == "bear"   # préfixe le plus long
    assert call(client, "debate.bull.round1")[0].stance == "debat"
    assert call(client, "autre")[0].stance == "repli"
    with pytest.raises(LLMUnavailableError):
        call(FakeLLMClient({}), "inconnue")


def test_prompts_versionnes():
    for name in ("profile_weighting", "research", "bull", "realist", "bear", "explanation"):
        prompt = load_prompt(name)
        assert prompt.version == "v1" and prompt.tag == f"{name}@v1"
        assert "## Règles" in prompt.text and "Aucune formulation prescriptive" in prompt.text
        if name not in ("profile_weighting", "research"):
            assert "{EV-" in prompt.text  # les agents qui rédigent placent un marqueur, jamais un chiffre


def test_client_simule_par_defaut_sans_bedrock(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID_FAST", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID_STRONG", raising=False)
    assert make_client("auto").model_id("fast") == "simule-local-v1"
    with pytest.raises(LLMUnavailableError):
        BedrockClient().model_id("fast")


class _FakeRuntime:
    def __init__(self, content):
        self.content, self.requests = content, []

    def converse(self, **request):
        self.requests.append(request)
        return {"output": {"message": {"content": self.content}}}


def test_bedrock_requete_converse_et_sortie_par_outil():
    runtime = _FakeRuntime([{"toolUse": {"name": "rendre_sortie", "input": {"stance": "appui", "score": 4}}}])
    client = BedrockClient(model_fast="modele-rapide", model_strong="modele-fort", guardrail_id="gr-1", client=runtime)
    answer, info = structured_call(client, step="etape", prompt=PROMPT, payload={"x": 1}, schema=Answer, tier="fast")
    assert answer.score == 4 and info.model_id == "modele-rapide"
    request = runtime.requests[0]
    assert request["modelId"] == "modele-rapide"
    assert request["system"] == [{"text": "Consigne de test."}]
    # Modèles Claude actuels : `temperature` et `toolChoice` forcé sont refusés (HTTP 400).
    assert "temperature" not in request["inferenceConfig"]
    assert request["inferenceConfig"]["maxTokens"] >= 16000  # place pour le raisonnement du modèle
    tool = request["toolConfig"]["tools"][0]["toolSpec"]
    assert tool["inputSchema"]["json"]["required"] == ["stance", "score"]
    assert "toolChoice" not in request["toolConfig"]
    assert tool["name"] in request["messages"][0]["content"][0]["text"]  # consigne d'appel de l'outil
    assert request["guardrailConfig"]["guardrailIdentifier"] == "gr-1"


def test_bedrock_sortie_vide_relancee_puis_echec():
    runtime = _FakeRuntime([])
    client = BedrockClient(model_fast="m", model_strong="m", client=runtime)
    with pytest.raises(LLMOutputError):
        call(client)
    assert len(runtime.requests) == 2
    assert "rejetée" in runtime.requests[1]["messages"][0]["content"][0]["text"]


def test_bedrock_raisonnement_ignore_sortie_par_outil():
    """Le modèle raisonne d'abord (bloc `reasoningContent`), puis appelle l'outil : seul l'outil compte."""
    runtime = _FakeRuntime([
        {"reasoningContent": {"reasoningText": {"text": "Je compare les preuves."}}},
        {"toolUse": {"name": "rendre_sortie", "input": {"stance": "appui", "score": 2}}},
    ])
    client = BedrockClient(model_fast="m", model_strong="m", client=runtime)
    answer, _ = structured_call(client, step="etape", prompt=PROMPT, payload={}, schema=Answer, tier="fast")
    assert answer.score == 2 and len(runtime.requests) == 1


def test_bedrock_reponse_texte_sans_outil_relancee():
    """Sans `toolChoice` forcé, le modèle peut répondre en texte : la validation le rejette et relance."""
    runtime = _FakeRuntime([{"text": "Voici mon analyse, sans JSON."}])
    client = BedrockClient(model_fast="m", model_strong="m", client=runtime)
    with pytest.raises(LLMOutputError):
        call(client)
    assert len(runtime.requests) == 2
