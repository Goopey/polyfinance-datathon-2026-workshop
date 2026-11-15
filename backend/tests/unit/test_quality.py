"""Critère « qualité » : non applicable aux FNB, endettement comparé au secteur, dates de publication,
règle du critère prioritaire.

Conception : docs/03_DECISION_ENGINE.md (section « Qualité »), docs/04_DONNEES.md (section 10)
"""
import math
from datetime import date

import pandas as pd
import pytest

from easytrade.data.fundamentals import FundamentalPoint, latest_known, load_fundamentals
from easytrade.engine.decision import decide
from easytrade.engine.quality import quality_scores
from easytrade.engine.scoring import fit_level, score_candidates
from easytrade.schemas.candidate import Asset
from easytrade.schemas.weights import CRITERIA, ProfileWeights


def _asset(ticker, asset_class="equity", sector="S"):
    return Asset(asset_id=ticker, ticker=ticker, name=ticker, asset_class=asset_class, market="M",
                 currency="CAD", sector=sector)


def _point(ticker, metric, value, year=2025):
    end = date(year, 12, 31)
    return FundamentalPoint(ticker=ticker, metric=metric, value=value, period_end=end, published_at=end,
                            source_id="finnhub", document_url="u", retrieved_at=None)


ROBERT_LIKE = {"croissance": 0.1, "stabilite": 0.3, "diversification": 0.15, "esg": 0.05, "qualite": 0.25,
               "horizon": 0.1, "preferences": 0.05}


# --- « non applicable » -------------------------------------------------------------------------
def test_qualite_non_applicable_a_un_fnb_poids_reparti_sans_penalite():
    eligible = (_asset("ACT"), _asset("FNB", "etf_bond"))
    signals = {"ACT": {c: 1.0 for c in CRITERIA}, "FNB": {c: (None if c == "qualite" else 1.0) for c in CRITERIA}}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}
    scored = {c.ticker: c for c in score_candidates(eligible, signals, evidence, ROBERT_LIKE)}

    fnb = scored["FNB"]
    quality = next(c for c in fnb.criteria if c.criterion == "qualite")
    assert quality.applicable is False and quality.missing is False and quality.contribution == 0.0
    assert "qualite" not in fnb.missing_criteria  # pas compté comme information manquante
    # Le poids de la qualité est réparti sur les autres critères : score = Σ poids × score ÷ poids applicables.
    assert math.isclose(sum(c.contribution for c in fnb.criteria), fnb.fit_score, abs_tol=1e-12)
    others = sum(ROBERT_LIKE[c] for c in CRITERIA if c != "qualite")
    expected = sum(ROBERT_LIKE[c] * cs.score for c, cs in ((x.criterion, x) for x in fnb.criteria) if c != "qualite") / others
    assert math.isclose(fnb.fit_score, expected, abs_tol=1e-12)
    assert fit_level(fnb) in ("élevée", "partielle", "faible")


def test_tous_criteres_applicables_resultat_inchange():
    """Que des actions : poids applicables = 1, contributions = poids × score (comportement d'avant)."""
    eligible = (_asset("A"), _asset("B"))
    signals = {"A": {c: 1.0 for c in CRITERIA}, "B": {c: 2.0 for c in CRITERIA}}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}
    for candidate in score_candidates(eligible, signals, evidence, ROBERT_LIKE):
        for cs in candidate.criteria:
            assert cs.applicable and math.isclose(cs.contribution, cs.weight * cs.score, abs_tol=1e-12)


# --- endettement comparé au secteur -------------------------------------------------------------
def test_endettement_compare_dans_le_secteur_seulement():
    assets = pd.DataFrame([
        {"ticker": "BANQUE1", "asset_class": "equity", "sector": "Financials"},
        {"ticker": "BANQUE2", "asset_class": "equity", "sector": "Financials"},
        {"ticker": "TECH1", "asset_class": "equity", "sector": "Information Technology"},
        {"ticker": "TECH2", "asset_class": "equity", "sector": "Information Technology"},
        {"ticker": "SEULE", "asset_class": "equity", "sector": "Health Care"},
        {"ticker": "FNB", "asset_class": "etf_equity", "sector": "Broad market"},
    ])
    known = {
        "BANQUE1": {"roe": _point("BANQUE1", "roe", 0.15), "totalDebtToEquity": _point("BANQUE1", "totalDebtToEquity", 2.0)},
        "BANQUE2": {"roe": _point("BANQUE2", "roe", 0.15), "totalDebtToEquity": _point("BANQUE2", "totalDebtToEquity", 3.0)},
        "TECH1": {"roe": _point("TECH1", "roe", 0.15), "totalDebtToEquity": _point("TECH1", "totalDebtToEquity", 0.5)},
        "TECH2": {"roe": _point("TECH2", "roe", 0.15), "totalDebtToEquity": _point("TECH2", "totalDebtToEquity", 0.9)},
        "SEULE": {"roe": _point("SEULE", "roe", 0.15), "totalDebtToEquity": _point("SEULE", "totalDebtToEquity", 0.1)},
    }
    scores = quality_scores(assets, known)

    # La banque la moins endettée de son secteur a le même rang que la société tech la moins endettée,
    # même si son ratio (2,0) est quatre fois celui de TECH1 (0,5).
    assert scores["BANQUE1"].score == scores["TECH1"].score
    assert scores["BANQUE1"].leverage_position == 1 and scores["BANQUE2"].leverage_position == 2
    assert scores["BANQUE1"].sector_peers == 2
    # Seule de son secteur : composante d'endettement omise, pas inventée.
    assert "totalDebtToEquity" not in scores["SEULE"].components and scores["SEULE"].leverage_position is None
    assert "FNB" not in scores  # non applicable


# --- dates de publication -----------------------------------------------------------------------
def test_exercice_lu_seulement_apres_son_delai_de_publication(tmp_path):
    (tmp_path / "fundamentals.csv").write_text(
        "ticker,metric,value,period_end,frequency,source_id,document_url,retrieved_at\n"
        "X,roe,0.10,2024-12-31,annual,finnhub,u,2026-11-15\n"
        "X,roe,0.20,2025-12-31,annual,finnhub,u,2026-11-15\n", encoding="utf-8")
    table = load_fundamentals(tmp_path)
    assert latest_known(table, "2026-03-30")["X"]["roe"].value == 0.10  # 2025 clos le 31/12 : public vers le 31/03
    assert latest_known(table, "2026-03-31")["X"]["roe"].value == 0.20
    assert latest_known(table, "2025-03-01") == {}


# --- critère prioritaire sans donnée → aucune recommandation ------------------------------------
def _universe():
    return pd.DataFrame([
        {"asset_id": t, "ticker": t, "name": t, "asset_class": "equity", "market": "M", "currency": "CAD", "sector": s}
        for t, s in (("A", "S1"), ("B", "S2"))
    ])


def _persona(weights):
    return ProfileWeights.from_persona({"id": "p", "poids": weights, "contraintes": {
        "max_weight_per_asset": 0.5, "max_weight_per_sector": 1.0, "max_weight_crypto": 0.0,
        "esg_exclusion": False, "speculatif": "permis"}})


def test_critere_prioritaire_sans_donnee_avertissement():
    """Décision de l'équipe (2026-11-15) : le critère prioritaire sans donnée ne bloque plus ; il est signalé."""
    mateo_like = {"croissance": 0.15, "stabilite": 0.2, "diversification": 0.15, "esg": 0.25, "qualite": 0.15,
                  "horizon": 0.05, "preferences": 0.05}
    signals = {t: {c: (None if c == "esg" else v) for c in CRITERIA} for t, v in (("A", 1.0), ("B", 2.0))}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}
    decision = decide(_universe(), signals, evidence, _persona(mateo_like), "2026-11-12")
    assert not decision.no_recommendation and decision.ranking
    assert len(decision.warnings) == 1 and "ESG" in decision.warnings[0] and "25 %" in decision.warnings[0]


def test_critere_secondaire_manquant_ne_bloque_pas():
    signals = {t: {c: (None if c == "esg" else v) for c in CRITERIA} for t, v in (("A", 1.0), ("B", 2.0))}
    evidence = {t: {c: None for c in CRITERIA} for t in signals}
    decision = decide(_universe(), signals, evidence, _persona(ROBERT_LIKE), "2026-11-12")
    assert not decision.no_recommendation  # ESG à 5 % pour ce profil : affiché comme manquant, sans bloquer
    assert decision.warnings == ()  # critère secondaire : pas d'avertissement


# --- dans le pipeline -----------------------------------------------------------------------------
def test_pipeline_preuves_de_qualite(pipeline_run):
    run = pipeline_run("robert")
    by_ticker = {c.ticker: c for c in run.decision.ranking}
    jnj = next(c for c in by_ticker["JNJ"].criteria if c.criterion == "qualite")
    composite = run.ledger.get(jnj.evidence_id)
    assert jnj.applicable and composite.claim_kind == "HYPOTHESE" and "méthode EasyTrade" in composite.statement
    assert composite.published_at <= run.as_of
    facts = [e for e in run.ledger if e.subject == "JNJ" and e.source.source_id == "finnhub"]
    assert facts and all(e.claim_kind == "FAIT" and e.published_at <= run.as_of for e in facts)
    spy = next(c for c in by_ticker["SPY"].criteria if c.criterion == "qualite")
    assert spy.applicable is False and spy.evidence_id is None


def test_pipeline_aucune_qualite_avant_publication(pipeline_run):
    """S5 appliqué aux fondamentaux : à une date passée, aucun chiffre publié plus tard n'est utilisé."""
    run = pipeline_run("robert", None, "2023-06-30")
    finnhub = [e for e in run.ledger if e.source.source_id == "finnhub"]
    assert finnhub and all(e.published_at <= date(2023, 6, 30) for e in finnhub)
