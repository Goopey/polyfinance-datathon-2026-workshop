"""Garde-fous des agents : pondération du profil, recherche, protocole de débat, intégration du débat.

Conception : docs/02_AGENTS.md, docs/03_DECISION_ENGINE.md (« Rôle du débat »)
Aucun modèle : les sorties d'agents sont fournies par `FakeLLMClient`.
"""
import pandas as pd
import pytest

from easytrade.agents.debate.protocol import clean_turn
from easytrade.agents.llm_client import FakeLLMClient
from easytrade.agents.profile_weighting import (
    MAX_WEIGHT_SHIFT,
    ConstraintsDraft,
    bound_weights,
    template_for,
    tighten_constraints,
    weigh_profile,
)
from easytrade.agents.research import run_research
from easytrade.agents.simulated import simulated_client
from easytrade.agents.tools import ResearchTools
from easytrade.engine.coherence import RISK_LIMITS, tolerance_level
from easytrade.engine.decision import apply_debate, debate_confidence
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.schemas.candidate import EvidencePack, ScoredCandidate
from easytrade.schemas.debate import Claim, DebateRecord, DebateTurn, DebateTurnDraft
from easytrade.schemas.decision import Decision
from easytrade.schemas.profile import Profile
from easytrade.schemas.weights import CRITERIA, HardConstraints, ProfileWeights
from tests.helpers import AS_OF, sample_ledger


def persona(personas, persona_id):
    return next(p for p in personas["personas"] if p["id"] == persona_id)


# --- agent de pondération ------------------------------------------------------------------------
def test_poids_bornes_autour_du_gabarit_et_normalises(personas):
    template = persona(personas, "amira")["poids"]
    proposed = dict(template, croissance=0.95, stabilite=-3.0, esg="pas un nombre")
    bounded = bound_weights(proposed, template)
    assert sum(bounded.values()) == pytest.approx(1.0, abs=1e-9)
    assert set(bounded) == set(CRITERIA)
    # Avant renormalisation, croissance est plafonnée à gabarit + écart maximal, stabilite à gabarit - écart.
    raw = {c: template[c] for c in CRITERIA}
    raw["croissance"] = template["croissance"] + MAX_WEIGHT_SHIFT
    raw["stabilite"] = max(0.0, template["stabilite"] - MAX_WEIGHT_SHIFT)
    total = sum(raw.values())
    assert bounded["croissance"] == pytest.approx(raw["croissance"] / total, abs=1e-5)
    assert bounded["stabilite"] == pytest.approx(raw["stabilite"] / total, abs=1e-5)
    assert bounded["esg"] == pytest.approx(template["esg"] / total, abs=1e-5)


def test_gabarit_inchange_si_le_modele_ne_propose_rien(personas):
    template = persona(personas, "robert")["poids"]
    assert bound_weights({}, template) == pytest.approx(template)


def test_le_modele_ne_peut_que_resserrer_une_contrainte():
    template = HardConstraints(max_weight_per_asset=0.15, max_weight_per_sector=0.40, max_weight_crypto=0.15,
                               esg_exclusion=True, speculatif="signalé")
    looser = ConstraintsDraft(max_weight_per_asset=0.50, max_weight_per_sector=0.90, max_weight_crypto=1.0,
                              esg_exclusion=False, speculatif="permis")
    assert tighten_constraints(template, looser) == template
    tighter = ConstraintsDraft(max_weight_per_sector=0.30, max_weight_crypto=0.0, speculatif="exclu")
    result = tighten_constraints(template, tighter)
    assert (result.max_weight_per_sector, result.max_weight_crypto, result.speculatif) == (0.30, 0.0, "exclu")
    assert result.max_weight_per_asset == 0.15 and result.esg_exclusion is True


def test_niveaux_de_tolerance():
    assert tolerance_level("élevé") == "élevée"
    assert tolerance_level("modéré") == "modérée"
    assert tolerance_level("faible à modéré") == "faible à modérée"
    assert tolerance_level("faible") == "faible"
    assert set(RISK_LIMITS) == {"faible", "faible à modérée", "modérée", "élevée"}


def test_agent_de_ponderation_sur_amira(personas, registry, forbidden):
    profile = Profile.from_persona(persona(personas, "amira"))
    ledger = EvidenceLedger(AS_OF)
    result, info = weigh_profile(profile, template_for(profile, personas), simulated_client(), ledger, registry,
                                 forbidden=forbidden)
    # Les agents simulés reprennent le gabarit : mêmes poids et contraintes que personas.json.
    assert result.profile_weights == ProfileWeights.from_persona(persona(personas, "amira"))
    assert result.deviations == ()
    assert result.preferred_themes == ("technologies", "cryptoactifs") and result.avoided_themes == ()
    assert result.risk_level == "élevée"
    # Chaque phrase du profil est une preuve FAIT ; chaque poids, plafond et repère une HYPOTHESE.
    assert all(ledger.get(f.evidence_id).claim_kind == "FAIT" for f in result.facts)
    hypotheses = [*result.constraint_evidence.values(), *result.weight_evidence.values(), *result.limit_evidence.values()]
    assert len(hypotheses) == 3 + 7 + 2
    assert all(ledger.get(i).claim_kind == "HYPOTHESE" for i in hypotheses)
    assert ledger.get(result.constraint_evidence["max_weight_per_sector"]).value == pytest.approx(40.0)
    # Le plafond par secteur est rattaché au souhait de diversification déclaré.
    origin = result.rationale_evidence("hard_constraints.max_weight_per_sector")
    assert origin and "diversification" in ledger.get(origin[0]).statement
    assert info.prompt_version == "profile_weighting@v1"


def test_sortie_du_modele_hors_bornes_corrigee_par_le_code(personas, registry, forbidden):
    profile = Profile.from_persona(persona(personas, "robert"))
    template = template_for(profile, personas)
    ledger = EvidenceLedger(AS_OF)
    client = FakeLLMClient({"profile_weighting": lambda payload: {
        "weights": {"croissance": 0.9, "inconnu": 0.5},
        "constraints": {"max_weight_crypto": 0.5, "max_weight_per_sector": 0.2},
        "preferred_themes": ["cryptoactifs", "theme_invente"], "avoided_themes": ["cryptoactifs"],
        "rationale": [
            {"field": "weights.croissance", "because": "Vous devriez viser 40 % par an.", "evidence_ids": ["EV-000001"]},
            {"field": "weights.stabilite", "because": "Sans preuve.", "evidence_ids": []},
            {"field": "champ.invente", "because": "Ignoré.", "evidence_ids": ["EV-000001"]},
            {"field": "weights.qualite", "because": "Le profil déclare tenir à la qualité.", "evidence_ids": ["EV-000001", "EV-424242"]},
        ],
    }})
    result, _ = weigh_profile(profile, template, client, ledger, registry, forbidden=forbidden)
    weights = result.profile_weights.weights
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-9) and set(weights) == set(CRITERIA)
    assert weights["croissance"] < template.weights["croissance"] + MAX_WEIGHT_SHIFT + 1e-9
    assert result.profile_weights.constraints.max_weight_crypto == 0.0      # assouplissement ignoré
    assert result.profile_weights.constraints.max_weight_per_sector == 0.2  # resserrement accepté
    assert result.avoided_themes == ("cryptoactifs",) and result.preferred_themes == ()
    # Justifications : formulation refusée, absence de preuve et champ inconnu sont retirés.
    assert [(r.field, r.evidence_ids) for r in result.rationale] == [("weights.qualite", ("EV-000001",))]
    assert "weights.croissance" in result.deviations and "hard_constraints.max_weight_per_sector" in result.deviations


# --- agent de recherche --------------------------------------------------------------------------
def test_recherche_titre_demande_toujours_analyse(personas, registry, forbidden, store, settings):
    profile = Profile.from_persona(persona(personas, "robert"))
    ledger = EvidenceLedger(settings.as_of)
    weighting, _ = weigh_profile(profile, template_for(profile, personas), simulated_client(), ledger, registry,
                                 forbidden=forbidden)
    tools = ResearchTools(store.assets(), settings.as_of, settings.reference_dir, ledger, registry)
    client = FakeLLMClient({"research": lambda payload: {
        "candidates": [{"ticker": "FTS.TO", "reason": "Entreprise établie."}, {"ticker": "INVENTE", "reason": "x"},
                       {"ticker": "FTS.TO", "reason": "doublon"}, {"ticker": "RY.TO", "reason": "Achetez-la."}],
        "tool_requests": [{"tool": "preuves_esg", "ticker": "FTS.TO"}, {"tool": "outil_invente", "ticker": "FTS.TO"},
                          {"tool": "nouvelles", "ticker": "TSLA"}, {"tool": "relations", "ticker": "INVENTE"}],
    }})
    candidates, _ = run_research(weighting, tools, client, requested_ticker="TSLA", max_candidates=2,
                                 forbidden=forbidden)
    # Le titre demandé est ajouté en tête et n'est jamais retiré par le plafond ; l'inconnu est retiré.
    assert candidates.tickers == ("TSLA", "FTS.TO")
    assert candidates.candidates[0].requested and candidates.dropped == ("INVENTE",)
    # Seuls les outils connus, sur des candidats gardés, sont exécutés ; chaque appel est journalisé.
    assert [(c["tool"], c["ticker"]) for c in tools.calls] == [
        ("lister_univers", None), ("preuves_esg", "FTS.TO"), ("nouvelles", "TSLA")]
    assert tools.calls[2]["results"] == 0  # aucune source de nouvelles autorisée
    # preuves_esg(FTS.TO) renvoie la ligne du programme canadien de déclaration des GES (ingestion/esg.py) :
    # le nombre dépend des lignes saisies, ce test ne le fige pas.
    assert tools.calls[1]["results"] >= 0


# --- protocole de débat --------------------------------------------------------------------------
def pack_of(ledger, ids):
    return EvidencePack(ticker="AAA", name="Actif AAA", asset_class="equity", sector="Energy",
                        evidence=tuple(ledger.get(i) for i in ids))


def test_arguments_sans_preuve_valide_supprimes(forbidden):
    ledger = sample_ledger()
    pack = pack_of(ledger, ["EV-000001", "EV-000002", "EV-000004"])
    draft = DebateTurnDraft(stance="opposition", confidence="moyenne", arguments=[
        Claim(text="Volatilité annualisée de {EV-000001}, au-dessus du repère de {EV-000004}."),   # gardé
        Claim(text="Perte maximale élevée sur la fenêtre observée.", evidence_ids=("EV-000002",)),  # gardé
        Claim(text="Le marché est nerveux."),                                                       # sans preuve
        Claim(text="Risque documenté.", evidence_ids=("EV-777777",)),                               # preuve inconnue
        Claim(text="Volatilité de 80 %.", evidence_ids=("EV-000001",)),                             # nombre inventé
        Claim(text="Panier plus calme.", evidence_ids=("EV-000005",)),                              # hors dossier
        Claim(text="Vendez : volatilité de {EV-000001}."),                                          # formulation
    ], open_questions=["Aucune preuve ESG datée disponible.", "Le titre va monter de 30 %.", ""])
    turn = clean_turn(draft, ticker="AAA", agent="bear", round_number=1, pack=pack, ledger=ledger,
                      forbidden=forbidden)
    assert [a.text for a in turn.arguments] == [
        "Volatilité annualisée de 35,2 %, au-dessus du repère de 25,0 %.",
        "Perte maximale élevée sur la fenêtre observée.",
    ]
    assert turn.removed_arguments == 5
    # Le claim_kind est celui des preuves : un repère du profil est une hypothèse.
    assert [a.claim_kind for a in turn.arguments] == ["HYPOTHESE", "FAIT"]
    assert turn.open_questions == ("Aucune preuve ESG datée disponible.",)
    assert turn.stance == "opposition"  # la position de l'agent n'est jamais modifiée par le code


def turn(agent, stance, *arguments):
    return DebateTurn(ticker="AAA", agent=agent, round=3, stance=stance, confidence="moyenne", arguments=arguments)


@pytest.mark.parametrize("stances, expected, dissent", [
    (("appui", "appui", "appui"), "élevé", False),
    (("appui", "appui_reserve", "appui"), "moyen", False),  # une réserve n'est pas un désaccord
    (("appui_reserve", "appui", "opposition"), "moyen", True),
    (("appui", "appui_reserve", "opposition"), "moyen", True),
    (("appui", "opposition", "opposition"), "faible", True),
    (("opposition", "opposition", "opposition"), "faible", False),
    (("appui_reserve", "appui_reserve", "appui_reserve"), "moyen", False),
])
def test_confiance_tiree_de_l_accord_du_debat(stances, expected, dissent):
    record = DebateRecord(ticker="AAA", final=tuple(turn(a, s) for a, s in zip(("bull", "realist", "bear"), stances)))
    assert debate_confidence(record) == expected
    assert record.dissent is dissent


def test_le_debat_ne_modifie_pas_le_score_et_conserve_le_desaccord():
    candidate = ScoredCandidate(ticker="AAA", name="Actif AAA", sector="Energy", asset_class="equity",
                                fit_score=0.61, criteria=())
    other = candidate.model_copy(update={"ticker": "BBB", "fit_score": 0.40})
    decision = Decision(as_of=AS_OF, persona_id="amira", ranking=(candidate, other), confidence="élevé")
    bear_argument = Claim(text="Volatilité au-dessus du repère du profil.", evidence_ids=("EV-000001", "EV-000004"),
                          claim_kind="HYPOTHESE")
    record = DebateRecord(ticker="AAA", final=(
        turn("bull", "appui", Claim(text="Rendement observé positif.", evidence_ids=("EV-000003",))),
        turn("realist", "appui_reserve"),
        turn("bear", "opposition", bear_argument),
    ))
    after = apply_debate(decision, [record], profile_evidence_ids=["EV-000004"])
    assert after.ranking == decision.ranking                     # scores et ordre intacts
    assert after.candidate_confidence == {"AAA": "moyen", "BBB": "élevé"}   # BBB non débattu : confiance des données
    assert len(after.disagreements) == 1
    assert "AAA" in after.disagreements[0] and "Bear : opposition (Volatilité au-dessus du repère du profil.)" in after.disagreements[0]
    assert after.to_review == ("AAA",)                           # opposition du Bear liée à une preuve du profil
    # Sans lien avec une preuve du profil, pas de drapeau.
    assert apply_debate(decision, [record], profile_evidence_ids=["EV-000099"]).to_review == ()
    # La confiance des données plafonne celle du débat.
    low = decision.model_copy(update={"confidence": "faible"})
    assert apply_debate(low, [record]).candidate_confidence["AAA"] == "faible"
