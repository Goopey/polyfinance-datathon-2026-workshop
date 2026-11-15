"""Critère `esg` du moteur (engine/esg.py) : constats, score absolu, exclusions, confiance par piste.

Conception : docs/03_DECISION_ENGINE.md (section « Critère ESG »)
"""
import pandas as pd
import pytest

from easytrade.engine import esg
from easytrade.engine.constraints import screen_assets
from easytrade.engine.decision import apply_debate, decide
from easytrade.engine.scoring import score_candidates
from easytrade.ingestion.esg import SIGNAL_TYPE, format_emissions
from easytrade.schemas.candidate import Asset
from easytrade.schemas.weights import CRITERIA, ProfileWeights

MATEO = {
    "id": "mateo",
    "poids": {"croissance": 0.15, "stabilite": 0.2, "diversification": 0.15,
              "esg": 0.25, "qualite": 0.15, "horizon": 0.05, "preferences": 0.05},
    "contraintes": {"max_weight_per_asset": 0.1, "max_weight_per_sector": 0.3,
                    "max_weight_crypto": 0.0, "esg_exclusion": True, "speculatif": "exclu"},
}


def _row(evidence_id, summary, signal_type=SIGNAL_TYPE):
    return {"evidence_id": evidence_id, "signal_type": signal_type, "summary": summary}


def test_type_de_signal_identique_au_chargeur():
    assert esg.EMISSIONS_SIGNAL == SIGNAL_TYPE


@pytest.mark.parametrize("tonnes", [15_923.4, 80_512.0, 157_049.9, 749_600.0, 999_949.0, 1_662_001.0,
                                    18_570_000.0, 37_880_412.7])
def test_lecture_des_emissions_inverse_du_formatage(tonnes):
    text = f"{format_emissions(tonnes)} déclarées en 2023 par 2 installations américaines."
    parsed = esg.parse_emissions(text)
    # Le résumé arrondit (2 décimales en Mt, 1 en kt) : l'écart reste sous la demi-unité affichée.
    assert parsed == pytest.approx(tonnes, abs=5_000 if tonnes >= 1_000_000 else 50)


@pytest.mark.parametrize("text", ["", "Environ 12 Mt CO2e", "12 Mt", "1.5 Mt CO2e déclarées", "n/d"])
def test_lecture_des_emissions_refuse_les_autres_formes(text):
    assert esg.parse_emissions(text) is None


def test_constats():
    assets = [{"ticker": t, "sector": s} for t, s in [
        ("BIG", "Energy"), ("EDGE", "Energy"), ("LOW", "Utilities"), ("BAD", "Health Care"),
        ("FUND", "Broad market (U.S., ESG-screened)"), ("NONE", "Financials"),
    ]]
    rows = {
        "BIG": [_row("E1", "37,88 Mt CO2e déclarées"), _row("E2", "157,0 kt CO2e déclarées")],
        "EDGE": [_row("E3", "10,00 Mt CO2e déclarées")],
        "LOW": [_row("E4", "157,0 kt CO2e déclarées")],
        "BAD": [_row("E5", "Ligne", "Controverse environnementale"), _row("E6", "15,0 kt CO2e déclarées")],
    }
    found = esg.assess(assets, rows)
    assert found["BIG"].finding == "emetteur_majeur" and found["BIG"].basis_ids == ("E1",)
    assert found["BIG"].evidence_ids == ("E1", "E2") and found["BIG"].tonnes == pytest.approx(37_880_000)
    assert found["EDGE"].finding == "emetteur_majeur"  # seuil inclus
    assert found["LOW"].finding == "non_concluant" and found["LOW"].score is None
    assert found["BAD"].finding == "controverse" and found["BAD"].basis_ids == ("E5",)  # priorité à la controverse
    assert found["FUND"].finding == "filtre_esg" and found["FUND"].score == 1.0
    assert "NONE" not in found  # aucune preuve : aucun constat (manquant), jamais « zéro »
    assert esg.exclusions(found) == {"BIG": "esg_emissions", "EDGE": "esg_emissions", "BAD": "esg_exclusion"}


def test_fichier_de_reference_constats_attendus(workspace):
    """Garde-fou sur les données du dépôt à la date par défaut : seuls XOM et CNQ.TO dépassent le seuil."""
    from easytrade.agents.tools import ResearchTools
    from easytrade.explain.evidence_ledger import EvidenceLedger

    assets = workspace.store.assets()
    ledger = EvidenceLedger(workspace.settings.as_of)
    tools = ResearchTools(assets, ledger.as_of, workspace.settings.reference_dir, ledger, workspace.registry)
    found = esg.assess(assets[["ticker", "sector"]].to_dict("records"),
                       {t: tools.preuves_esg(t) for t in assets["ticker"]})
    by_kind = {k: sorted(t for t, a in found.items() if a.finding == k)
               for k in ("emetteur_majeur", "filtre_esg", "non_concluant", "controverse")}
    assert by_kind == {"emetteur_majeur": ["CNQ.TO", "XOM"], "filtre_esg": ["ESGV"],
                       "non_concluant": ["ENB.TO", "FTS.TO", "GOOGL", "PG", "TSLA"], "controverse": []}


def _assets(*tickers):
    return tuple(Asset(asset_id=t, ticker=t, name=t, asset_class="equity", market="X", currency="CAD",
                       sector="Energy") for t in tickers)


def test_score_absolu_une_preoccupation_documentee_ne_depasse_jamais_un_inconnu():
    signals = {t: {c: 1.0 for c in CRITERIA} for t in ("BIG", "UNKNOWN", "FUND")}
    signals["BIG"]["esg"], signals["UNKNOWN"]["esg"], signals["FUND"]["esg"] = 0.0, None, 1.0
    weights = ProfileWeights.from_persona(MATEO).weights
    scored = {c.ticker: c for c in score_candidates(_assets("BIG", "UNKNOWN", "FUND"), signals, {}, weights)}
    esg_of = {t: next(k for k in c.criteria if k.criterion == "esg") for t, c in scored.items()}
    assert (esg_of["BIG"].score, esg_of["BIG"].missing) == (0.0, False)   # connu, défavorable
    assert (esg_of["UNKNOWN"].score, esg_of["UNKNOWN"].missing) == (0.0, True)
    assert esg_of["FUND"].score == 1.0
    assert scored["BIG"].fit_score <= scored["UNKNOWN"].fit_score < scored["FUND"].fit_score


def test_emetteur_majeur_ecarte_seulement_si_le_profil_l_exclut():
    universe = pd.DataFrame([{"asset_id": "A20", "ticker": "XOM", "name": "Exxon", "asset_class": "equity",
                              "market": "NYSE", "currency": "USD", "sector": "Energy"}])
    mateo = ProfileWeights.from_persona(MATEO).constraints
    result = screen_assets(universe, mateo, esg_emitters=frozenset({"XOM"}))
    assert [(r.ticker, r.rule) for r in result.rejected] == [("XOM", "esg_emissions")]
    assert "fort impact environnemental" in result.rejected[0].reason
    other = mateo.model_copy(update={"esg_exclusion": False})
    assert screen_assets(universe, other, esg_emitters=frozenset({"XOM"})).rejected == ()


def test_confiance_par_piste_selon_ses_criteres_manquants():
    universe = pd.DataFrame([
        {"asset_id": f"A{i}", "ticker": t, "name": t, "asset_class": "equity", "market": "X", "currency": "CAD",
         "sector": s} for i, (t, s) in enumerate([("WITH", "Energy"), ("WITHOUT", "Utilities")])
    ])
    signals = {t: {c: 1.0 for c in CRITERIA} for t in ("WITH", "WITHOUT")}
    signals["WITH"]["esg"], signals["WITHOUT"]["esg"] = 1.0, None
    decision = apply_debate(decide(universe, signals, {}, ProfileWeights.from_persona(MATEO), "2026-11-12"), [])
    assert decision.confidence == "élevé"  # critère couvert pour au moins une piste
    assert decision.candidate_confidence == {"WITH": "élevé", "WITHOUT": "moyen"}  # ESG à 25 % manquant
