"""Garde-fous de panier et points de contrôle.

Conception : docs/03_DECISION_ENGINE.md (« Garde-fous de panier »), docs/08_CONFORMITE.md
"""
import pytest

from easytrade.engine import governance
from easytrade.engine.governance import basket_shares, basket_size, concentration_group, select_basket
from easytrade.engine.scoring import fit_level
from easytrade.schemas.candidate import CriterionScore, ScoredCandidate
from easytrade.schemas.weights import HardConstraints

AMIRA = HardConstraints(max_weight_per_asset=0.15, max_weight_per_sector=0.40, max_weight_crypto=0.15)
ROBERT = HardConstraints(max_weight_per_asset=0.10, max_weight_per_sector=0.30, max_weight_crypto=0.0)


def candidate(ticker, sector, score, asset_class="equity"):
    return ScoredCandidate(ticker=ticker, name=ticker, sector=sector, asset_class=asset_class, fit_score=score,
                           criteria=())


def ranking(*specs):
    return [candidate(t, s, 1.0 - i / 100, c) for i, (t, s, c) in enumerate(specs)]


def test_taille_du_panier_tiree_de_la_part_maximale_par_actif():
    assert basket_size(AMIRA) == 7     # 1/7 = 14,3 % ≤ 15 %
    assert basket_size(ROBERT) == 10   # 1/10 = 10 %


def test_groupes_de_concentration():
    assert concentration_group("Information Technology") == "Technologies"
    assert concentration_group("Broad market (U.S. growth/tech-heavy)") == "Technologies"
    assert concentration_group("Bonds (U.S. long Treasury)") == "Obligations"
    assert concentration_group("Energy") == "Energy"


def test_troisieme_piste_technologique_declassee_avec_motif():
    order = ranking(
        ("T1", "Information Technology", "equity"), ("T2", "Communication Services", "equity"),
        ("T3", "Broad market (U.S. growth/tech-heavy)", "etf_equity"), ("C1", "Crypto asset", "crypto"),
        ("C2", "Crypto asset", "crypto"), ("E1", "Energy", "equity"), ("F1", "Financials", "equity"),
        ("G1", "Gold", "etf_commodity"), ("U1", "Utilities", "equity"), ("H1", "Health Care", "equity"),
    )
    selection = select_basket(order, AMIRA)
    assert (selection.size, selection.max_per_sector, selection.max_crypto) == (7, 2, 1)
    assert selection.tickers == ("T1", "T2", "C1", "E1", "F1", "G1", "U1")
    assert [(r.ticker, r.rule) for r in selection.displaced] == [
        ("T3", governance.RULE_SECTOR), ("C2", governance.RULE_CRYPTO)]
    assert "concentration" in selection.displaced[0].reason and "40 %" in selection.displaced[0].reason
    assert "« Technologies »" in selection.displaced[0].reason
    assert "15 %" in selection.displaced[1].reason
    # Plafonds tenus sur le panier simulé à parts égales.
    shares = basket_shares(selection.retained)
    assert shares["per_asset"] <= AMIRA.max_weight_per_asset
    assert max(shares["per_sector"].values()) <= AMIRA.max_weight_per_sector
    assert shares["crypto"] <= AMIRA.max_weight_crypto
    assert governance.control_basket(selection, AMIRA).passed
    assert governance.control_diversification(selection).passed


def test_classement_respecte_sans_concentration():
    order = ranking(*((f"A{i}", f"Secteur {i}", "equity") for i in range(12)))
    selection = select_basket(order, ROBERT)
    assert selection.tickers == tuple(f"A{i}" for i in range(10)) and selection.displaced == ()


def test_panier_incomplet_signale_par_le_controle():
    selection = select_basket(ranking(("A", "Energy", "equity"), ("B", "Gold", "etf_commodity")), AMIRA)
    control = governance.control_basket(selection, AMIRA)
    assert not control.passed and "panier incomplet" in control.note
    assert not governance.control_diversification(selection).passed


def test_deterministe():
    order = ranking(*((f"A{i}", "Energy" if i % 2 else "Gold", "equity") for i in range(12)))
    assert select_basket(order, AMIRA) == select_basket(order, AMIRA)


def test_controle_avant_affichage():
    ok = governance.control_display(checked=40, first_pass_ok=20, first_pass_checked=20, removed=0, remaining_issues=0)
    bad = governance.control_display(checked=40, first_pass_ok=18, first_pass_checked=20, removed=2, remaining_issues=1)
    assert ok.passed and "20/20" in ok.note
    assert not bad.passed


def test_aucune_recommandation_sans_prefixe_double():
    deja = governance.control_no_recommendation(True, "Aucune recommandation : le critère le plus important manque.")
    brut = governance.control_no_recommendation(True, "Preuves insuffisantes.")
    assert deja.note == "Aucune recommandation : le critère le plus important manque."
    assert brut.note == "Aucune recommandation : Preuves insuffisantes."
    assert governance.control_no_recommendation(False, "").note == "Des pistes sont présentées."


def scored(score, *criteria):
    return ScoredCandidate(ticker="A", name="A", sector="Energy", asset_class="equity", fit_score=score,
                           criteria=tuple(criteria))


def criterion(name, weight, score, missing=False):
    return CriterionScore(criterion=name, signal=None if missing else 1.0, score=score, weight=weight,
                          contribution=weight * score, missing=missing)


@pytest.mark.parametrize("score, expected", [(0.9, "élevée"), (0.55, "partielle"), (0.2, "faible")])
def test_adequation_rapportee_aux_criteres_couverts(score, expected):
    # 0,5 de poids couvert, 0,5 manquant : le libellé se lit sur la partie couverte.
    item = scored(0.5 * score, criterion("croissance", 0.5, score), criterion("esg", 0.5, 0.0, missing=True))
    assert fit_level(item) == expected


def test_adequation_faible_sans_aucun_critere_couvert():
    assert fit_level(scored(0.0, criterion("esg", 1.0, 0.0, missing=True))) == "faible"
