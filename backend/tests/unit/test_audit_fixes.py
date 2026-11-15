"""Correctifs issus de l'audit (AUDIT_REPORT.md) : chaque règle nouvelle a son test.

C1 : objectif et horizon comptent ; C2 : tolérance au risque appliquée comme règle, partagée avec
« Tester une idée » ; H2 : désaccord = au moins une opposition ; H3 : diversification mesurée par la
corrélation ; M1 / M2 : dates d'analyse et rendement 2022.
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from easytrade.api.service import ApiService, InvalidRequest
from easytrade.engine.coherence import limit_tensions, verdict_from
from easytrade.engine.constraints import RISK_FLAG, RULE_TOLERANCE, risk_breach, screen_assets
from easytrade.engine.signals import correlation_diversification, horizon_label, horizon_metric
from easytrade.schemas.api import ProfileDraft, RunRequest
from easytrade.schemas.debate import DebateRecord, DebateTurn
from easytrade.schemas.weights import HardConstraints

UNIVERSE = pd.DataFrame([
    {"asset_id": f"T{i}", "ticker": t, "name": n, "asset_class": c, "sector": s, "market": m, "currency": cur}
    for i, (t, n, c, s, m, cur) in enumerate([
        ("CALME", "Calme", "etf_bond", "Bonds", "TSX", "CAD"),
        ("MOYEN", "Moyen", "equity", "Energy", "US", "USD"),
        ("DEUX", "Deux", "equity", "Tech", "US", "USD"),
        ("SEVERE", "Sévère", "equity", "Tech", "US", "USD"),
        ("BTC", "Bitcoin", "crypto", "Crypto", "CRYPTO", "USD"),
    ])
])
# (volatilité %, perte maximale %) ; repères « faible à modérée » : 22 % / -25 %, « élevée » : 45 % / -50 %.
RISK = {"CALME": (5.0, -8.0), "MOYEN": (24.0, -20.0), "DEUX": (30.0, -30.0), "SEVERE": (70.0, -80.0),
        "BTC": (50.0, -74.0)}
PRUDENT = HardConstraints(max_weight_per_asset=0.1, max_weight_per_sector=0.3, max_weight_crypto=0.0)
OFFENSIF = HardConstraints(max_weight_per_asset=0.15, max_weight_per_sector=0.4, max_weight_crypto=0.15)


def _screen(constraints, level):
    result = screen_assets(UNIVERSE, constraints, risk=RISK, risk_level=level)
    return {a.ticker for a in result.eligible}, {r.ticker: r for r in result.rejected}, result.flags


# ---------- C2 : tolérance au risque ----------------------------------------------------------------

def test_profil_prudent_ecarte_les_deux_reperes_et_le_severe():
    eligible, rejected, flags = _screen(PRUDENT, "faible à modérée")
    assert eligible == {"CALME", "MOYEN"}
    assert rejected["DEUX"].rule == RULE_TOLERANCE      # deux repères dépassés
    assert rejected["SEVERE"].rule == RULE_TOLERANCE    # dépassement sévère
    assert rejected["BTC"].rule == "max_weight_crypto"  # la règle crypto passe avant
    assert flags["MOYEN"] == (RISK_FLAG,)               # un repère dépassé : admissible, signalé
    assert "CALME" not in flags
    reason = rejected["DEUX"].reason
    assert "30,0 %" in reason and "22 %" in reason and "25 %" in reason


def test_un_depassement_reste_visible_a_l_arrondi():
    """18,4 % contre un repère de 18 % : écrit « 18,4 % », jamais « 18 % pour un repère de 18 % »."""
    from easytrade.engine.constraints import tolerance_reason
    reason = tolerance_reason("faible", 18.4, -26.0)
    assert "18,4 % pour un repère de 18 %" in reason and "26,0 % pour un repère de 20 %" in reason


def test_profil_offensif_accepte_un_depassement_modere_jamais_severe():
    eligible, rejected, flags = _screen(OFFENSIF, "élevée")
    assert "SEVERE" not in eligible and rejected["SEVERE"].rule == RULE_TOLERANCE  # 70 % > 1,5 × 45 % = 67,5 %
    assert {"CALME", "MOYEN", "DEUX", "BTC"} <= eligible
    assert flags["BTC"] == (RISK_FLAG,)  # poche crypto plafonnée : gardée avec réserve


def test_sans_donnees_de_risque_la_regle_ne_s_applique_pas():
    result = screen_assets(UNIVERSE, PRUDENT)
    assert {r.rule for r in result.rejected} == {"max_weight_crypto"}


@pytest.mark.parametrize("level, ticker", [("faible à modérée", t) for t in RISK if t != "BTC"]
                         + [("élevée", t) for t in RISK])
def test_tester_une_idee_et_classement_concordent(level, ticker):
    """Verdict « incohérent » ⇔ actif écarté par la règle de tolérance du classement."""
    constraints = OFFENSIF if level == "élevée" else PRUDENT
    _, rejected, _ = _screen(constraints, level)
    volatility, drawdown = RISK[ticker]
    capped = ticker == "BTC" and constraints.max_weight_crypto > 0
    verdict = verdict_from(limit_tensions(level=level, volatility=volatility, max_drawdown=drawdown,
                                          capped_class=capped))
    excluded = ticker in rejected and rejected[ticker].rule == RULE_TOLERANCE
    assert (verdict == "incohérent avec le profil") == excluded, (ticker, verdict)


def test_seuil_severe_exact():
    assert not risk_breach("faible à modérée", 33.0, -10.0).excluded  # 1,5 × 22 = 33 : pas au-delà
    assert risk_breach("faible à modérée", 33.1, -10.0).excluded


# ---------- C1 : objectif et horizon --------------------------------------------------------------

def test_horizon_choisit_la_fenetre_du_critere():
    assert horizon_metric(3) == "worst_rolling_1y" and horizon_label("worst_rolling_1y") == "1 an"
    assert horizon_metric(5) == "worst_rolling_3y" and horizon_metric(15) == "worst_rolling_3y"
    assert horizon_metric(None) == "worst_rolling_3y"


@pytest.fixture(scope="module")
def service():
    return ApiService()


def _draft(**answers):
    return ProfileDraft(**{**dict(objectif="equilibre", horizon="moyen", tolerance="moderee",
                                  preferences=[], exclusions=[]), **answers})


def test_objectif_et_horizon_changent_les_poids(service):
    court = service.create_profile(_draft(horizon="court"))
    long_ = service.create_profile(_draft(horizon="long"))
    preserver = service.create_profile(_draft(objectif="preserver", tolerance="faible"))
    croissance = service.create_profile(_draft(objectif="croissance", tolerance="faible"))
    assert court.weights != long_.weights
    assert court.weights["horizon"] > long_.weights["horizon"]
    assert preserver.weights["stabilite"] > croissance.weights["stabilite"]
    assert preserver.weights["croissance"] < croissance.weights["croissance"]
    for view in (court, long_, preserver, croissance):
        assert abs(sum(view.weights.values()) - 1.0) < 1e-6 and min(view.weights.values()) >= 0


def test_reponses_contradictoires_lecture_prudente_et_expliquee(service):
    view = service.create_profile(_draft(objectif="preserver", horizon="court", tolerance="elevee"))
    assert "risque faible" in view.summary  # « préserver » plafonne la tolérance appliquée
    reasons = [r.because for r in view.rationale if r.field == "tolerance"]
    assert any("préserver le capital" in r and "« élevé » déclarée" in r for r in reasons), reasons
    coherent = service.create_profile(_draft(objectif="croissance", horizon="long", tolerance="elevee"))
    assert "risque élevé" in coherent.summary
    assert not [r for r in coherent.rationale if r.field == "tolerance"]


# ---------- M1 : dates d'analyse ------------------------------------------------------------------

@pytest.mark.parametrize("as_of", [date(2030, 1, 1), date(2022, 3, 1), date(2019, 1, 1)])
def test_date_d_analyse_hors_donnees_refusee(service, as_of):
    with pytest.raises(InvalidRequest):
        service.start_run(RunRequest(profile_id="robert", as_of=as_of))


def test_date_d_analyse_valide_acceptee(service):
    assert service.start_run(RunRequest(profile_id="robert", as_of=date(2023, 6, 30))).startswith("run_2023-06-30")


# ---------- M2 : rendement 2022 -------------------------------------------------------------------

def test_rendement_2022_absent_tant_que_l_annee_n_est_pas_finie(workspace):
    from easytrade.explain.evidence_ledger import EvidenceLedger
    from easytrade.validation.metrics import compute_metrics_table

    for as_of, present in ((date(2022, 6, 30), False), (date(2023, 1, 31), True)):
        table = compute_metrics_table(workspace.store, as_of, EvidenceLedger(as_of), workspace.registry,
                                      workspace.settings.quality, tickers=["SPY"])
        row = table[table["metric"] == "return_2022"].iloc[0]
        assert (row["value"] is not None and not pd.isna(row["value"])) is present, (as_of, row["note"])


# ---------- H2 : désaccord ------------------------------------------------------------------------

def _record(*stances):
    return DebateRecord(ticker="AAA", final=tuple(
        DebateTurn(ticker="AAA", agent=a, round=3, stance=s, confidence="moyenne")
        for a, s in zip(("bull", "realist", "bear"), stances)))


def test_desaccord_exige_une_opposition():
    assert not _record("appui", "appui_reserve", "appui_reserve").dissent
    assert _record("appui", "appui", "opposition").dissent
    assert not _record("opposition", "opposition", "opposition").dissent


# ---------- H3 : diversification mesurée ----------------------------------------------------------

def test_diversification_par_correlation():
    rng = np.random.default_rng(7)
    days = pd.bdate_range("2024-01-01", periods=300)
    market = rng.normal(0, 0.01, len(days))
    prices = pd.DataFrame({
        "A": 100 * np.cumprod(1 + market + rng.normal(0, 0.002, len(days))),
        "B": 100 * np.cumprod(1 + market + rng.normal(0, 0.002, len(days))),
        "OR": 100 * np.cumprod(1 + rng.normal(0, 0.01, len(days))),  # indépendant du marché
    }, index=days)
    corr = correlation_diversification(prices, min_common=60)
    assert corr["A"][0] > 0.4 and corr["B"][0] > 0.4
    assert corr["OR"][0] < corr["A"][0]  # l'actif indépendant diversifie davantage
    assert corr["A"][1] == len(days) - 1
    assert correlation_diversification(prices.iloc[:10], min_common=60) == {}  # historique trop court
