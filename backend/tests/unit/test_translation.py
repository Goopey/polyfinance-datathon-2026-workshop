"""Traduction anglaise du texte des modèles, et « ce que nous ne savons pas » limité aux faits du code.

Conception : backend/easytrade/agents/translation.py, mobile/src/i18n/translate.ts
Le « vrai modèle » est simulé : les agents simulés rédigent, et une étape `translation` factice rend une
version anglaise dont les nombres sont au format anglais (comme un modèle qui respecte la consigne).
"""
import re

import pytest

from easytrade.agents import simulated, translation
from easytrade.agents.llm_client import LLMUnavailableError
from easytrade.agents.simulated import simulated_client
from easytrade.orchestration.pipeline import run_pipeline


def _to_english_numbers(text: str) -> str:
    text = re.sub(r"(\d)[   ](\d{3})", r"\1,\2", text)  # 1 234 → 1,234
    text = re.sub(r"(\d),(\d{1,2})(?!\d)", r"\1.\2", text)        # 13,1 → 13.1
    return text.replace(" %", "%")


def _faithful(payload):
    return {"items": [{"id": t["id"], "en": "EN " + _to_english_numbers(t["text"])} for t in payload["texts"]]}


def _model_client(translator=_faithful, missing_information=None):
    """Agents simulés + étape de traduction, présenté comme un vrai modèle (traduction activée d'office)."""
    client = simulated_client()
    client.responders["translation"] = translator
    if missing_information is not None:
        def weighting(payload):
            out = simulated.profile_weighting(payload)
            return {**out, "missing_information": missing_information}
        client.responders["profile_weighting"] = weighting
    return client


# --- contrôle des nombres ---------------------------------------------------------------------------
@pytest.mark.parametrize("fr,en,same", [
    ("Volatilité annualisée de 13,1 % sur la période.", "Annualized volatility of 13.1% over the period.", True),
    ("Volatilité annualisée de 13,1 % sur la période.", "Annualized volatility of 13.2% over the period.", False),
    ("Perte maximale de -6,3 %.", "Maximum drawdown of -6.3%.", True),
    ("Émissions de 1 234,5 kt en 2023.", "Emissions of 1,234.5 kt in 2023.", True),
    ("Émissions de 1 234,5 kt en 2023.", "Emissions of 1,234.5 kt.", False),          # nombre retiré
    ("Rendement de 8,0 % en 2022.", "Return of 8.0% in 2022, up 3% since.", False),     # nombre ajouté
])
def test_memes_nombres(fr, en, same):
    assert translation.same_numbers(fr, en) is same


# --- étape de traduction dans le pipeline -------------------------------------------------------------
def test_traduction_jointe_au_resultat(workspace):
    run = run_pipeline("robert", requested_ticker="TSLA", client=_model_client(), workspace=workspace, translate=True)
    explanation = run.explanation
    texts = translation.explanation_texts(explanation)
    assert run.status == "termine"
    assert explanation.translations and set(explanation.translations) <= set(texts)
    why = explanation.items[0].why[0].text
    assert explanation.translations[why].startswith("EN ")
    step = next(s for s in run.trace.steps if s.step == "traduction")
    assert step.status == "ok" and step.kind == "llm"


def test_chiffre_modifie_refuse_phrase_laissee_en_francais(workspace):
    def unfaithful(payload):  # le modèle « arrondit » : tout chiffre change
        return {"items": [{"id": t["id"], "en": "EN " + re.sub(r"\d", "9", t["text"])} for t in payload["texts"]]}

    run = run_pipeline("robert", client=_model_client(unfaithful), workspace=workspace, translate=True)
    translations = run.explanation.translations
    with_numbers = [t for t in translation.explanation_texts(run.explanation) if re.search(r"\d", t)]
    assert with_numbers and not any(t in translations for t in with_numbers)
    assert "refusée" in next(s for s in run.trace.steps if s.step == "traduction").note


def test_numero_inconnu_ignore(workspace):
    def inventive(payload):  # un numéro hors du lot, puis les vraies traductions
        return {"items": [{"id": len(payload["texts"]) + 5, "en": "Never asked."}, *_faithful(payload)["items"]]}

    run = run_pipeline("amira", client=_model_client(inventive), workspace=workspace, translate=True)
    translations = run.explanation.translations
    assert translations and "Never asked." not in translations.values()
    assert all(v.startswith("EN ") for v in translations.values())


def test_traduction_par_lots_numerotes():
    """Plusieurs lots en parallèle ; chaque numéro renvoie à la phrase de son lot, sans recopie du français."""
    texts = [f"Phrase numéro {i} ; volatilité de {i},5 %." for i in range(95)]
    client = _model_client()
    table, infos, refused = translation.translate(texts, client)
    assert len(infos) == 3 and refused == 0  # 40 + 40 + 15
    assert table == {t: "EN " + _to_english_numbers(t) for t in texts}


def test_echec_de_traduction_n_arrete_pas_l_analyse(workspace):
    def down(payload):
        raise LLMUnavailableError("modèle indisponible")

    run = run_pipeline("amira", client=_model_client(down), workspace=workspace, translate=True)
    assert run.status == "termine" and run.explanation.translations == {}
    assert next(s for s in run.trace.steps if s.step == "traduction").status == "echec"


def test_agents_simules_pas_de_traduction(pipeline_run):
    """Les gabarits des agents simulés sont traduits par les règles de l'application : aucune étape."""
    run = pipeline_run("robert")
    assert run.explanation.translations == {}
    assert not any(s.step == "traduction" for s in run.trace.steps)


def test_activation_automatique_selon_le_client():
    assert translation.enabled_for(simulated_client()) is False

    class Bedrockish:
        def model_id(self, tier):
            return "us.anthropic.claude-sonnet-5-5"

    assert translation.enabled_for(Bedrockish()) is True


# --- « Ce que nous ne savons pas » : faits du code seulement --------------------------------------------
def test_ce_que_nous_ne_savons_pas_sans_texte_libre(workspace):
    invented = "Part maximale de cryptoactifs que la personne juge acceptable"
    run = run_pipeline("amira", client=_model_client(missing_information=[invented]), workspace=workspace,
                       translate=False)
    explanation = run.explanation
    assert invented not in explanation.unknowns  # texte libre de l'agent de pondération : retiré
    for item in explanation.items:
        questions = {q for position in item.debate for q in position.open_questions}
        assert not questions & set(item.unknowns)  # questions des agents : dans le débat seulement
        assert len(item.limits) == len(set(item.limits)) <= 4
        assert not any("séances concernées" in limit for limit in item.limits)  # détail propre à une preuve


def test_vue_du_profil_traduite(workspace):
    from easytrade.api.service import ApiService

    class ModelClient:  # même interface qu'un client Bedrock, réponses des agents simulés
        def __init__(self):
            self.inner = _model_client()

        def model_id(self, tier):
            return "us.anthropic.claude-sonnet-5-5"

        def invoke(self, **kwargs):
            return self.inner.invoke(**kwargs)

    view = ApiService(workspace=workspace, client=ModelClient()).profile_view("robert")
    assert view.translations and all(v.startswith("EN ") for v in view.translations.values())
    assert set(view.translations) <= {r.because for r in view.rationale}
    plain = ApiService(workspace=workspace, client=simulated_client()).profile_view("robert")
    assert plain.translations == {}
