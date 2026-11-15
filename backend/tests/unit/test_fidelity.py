"""Vérificateur de fidélité : nombres et citations.

Conception : docs/05_EXPLICABILITE.md (section 4)
"""
from datetime import date

import pytest

from easytrade.explain import fidelity
from easytrade.explain.fidelity import check_claim, extract_numbers, format_value, render_text
from easytrade.schemas.debate import Claim
from tests.helpers import AS_OF, draft, sample_ledger

FORBIDDEN = ("achetez", "garanti")


@pytest.fixture()
def ledger():
    return sample_ledger()


def check(ledger, text, ids=(), kind="FAIT", **kwargs):
    return check_claim(Claim(text=text, evidence_ids=tuple(ids), claim_kind=kind), ledger, AS_OF, FORBIDDEN, **kwargs)


# --- insertion des valeurs : aucun chiffre écrit par un modèle ---------------------------------
def test_marqueur_remplace_par_la_valeur_du_registre(ledger):
    text, used = render_text("Volatilité de {EV-000001}, perte maximale de {EV-000002}.", ledger)
    assert text == "Volatilité de 35,2 %, perte maximale de -41,6 %."
    assert used == ("EV-000001", "EV-000002")


def test_formats(ledger):
    assert format_value(ledger.get("EV-000001")) == "35,2 %"
    assert format_value(ledger.get("EV-000006")) is None
    other = sample_ledger()
    ratio = other.add(draft("Corrélation", 0.456, unit="ratio"))
    count = other.add(draft("Nombre d'actifs du secteur", 5.0, unit="actif(s)"))
    assert format_value(ratio) == "0,46"
    assert format_value(count) == "5 actif(s)"


def test_marqueur_ajoute_la_preuve_aux_citations(ledger):
    result = check(ledger, "Volatilité annualisée de {EV-000001}.")
    assert result.ok
    assert result.claim.evidence_ids == ("EV-000001",)
    assert result.claim.text == "Volatilité annualisée de 35,2 %."


# --- contrôle 1 : chaque nombre correspond à une preuve citée ---------------------------------
@pytest.mark.parametrize("text", [
    "Volatilité de 35,24 %.",      # valeur exacte
    "Volatilité de 35,2 %.",       # arrondi à une décimale
    "Volatilité de 35 %.",         # arrondi à l'unité
    "Volatilité de 35.2 %.",       # point décimal
])
def test_nombre_etaye_selon_l_arrondi_ecrit(ledger, text):
    assert check(ledger, text, ["EV-000001"]).ok


@pytest.mark.parametrize("text", [
    "Volatilité de 36 %.",         # hors tolérance d'arrondi
    "Volatilité de 35,9 %.",
    "Volatilité de 35 %, soit 12 points de plus que le marché.",  # un nombre inventé parmi d'autres
])
def test_nombre_non_etaye_refuse(ledger, text):
    result = check(ledger, text, ["EV-000001"])
    assert fidelity.UNSUPPORTED_NUMBER in result.issues


def test_signe_ignore_pour_une_perte(ledger):
    # « perte maximale de 42 % » décrit la preuve dont la valeur est -41,6.
    assert check(ledger, "Perte maximale observée de 42 %.", ["EV-000002"]).ok


def test_nombre_de_l_enonce_de_la_preuve_admis(ledger):
    # « 3 ans » figure dans l'énoncé de la preuve : ce n'est pas un chiffre inventé.
    assert check(ledger, "Pire période glissante de 3 ans : -12 %.", ["EV-000003"]).ok
    assert fidelity.UNSUPPORTED_NUMBER in check(ledger, "Pire période glissante de 5 ans : -12 %.", ["EV-000003"]).issues


def test_un_nombre_doit_venir_d_une_preuve_citee_pas_d_une_autre(ledger):
    # 25 est la valeur de EV-000004, qui n'est pas citée ici.
    assert fidelity.UNSUPPORTED_NUMBER in check(ledger, "Repère de 25 %.", ["EV-000001"]).issues


def test_noms_d_actifs_et_dates_ne_sont_pas_des_chiffres():
    assert extract_numbers("SPDR S&P 500 ETF Trust au 2026-11-12, preuve EV-000123", ignore=["SPDR S&P 500 ETF Trust"]) == []
    assert extract_numbers("Hausse de 12,5 % puis 3 %") == ["12,5", "3"]


# --- contrôle 2 : citations ---------------------------------------------------------------------
def test_affirmation_sans_preuve_refusee(ledger):
    assert check(ledger, "Ce titre est stable.").issues == (fidelity.NO_EVIDENCE,)


def test_preuve_inconnue_refusee(ledger):
    assert fidelity.UNKNOWN_EVIDENCE in check(ledger, "Ce titre est stable.", ["EV-999999"]).issues
    assert fidelity.UNKNOWN_EVIDENCE in check(ledger, "Volatilité de {EV-999999}.").issues


def test_marqueur_sur_une_preuve_sans_valeur_refuse(ledger):
    assert fidelity.UNKNOWN_EVIDENCE in check(ledger, "Selon {EV-000006}.").issues


def test_preuve_hors_du_dossier_fourni_refusee(ledger):
    result = check(ledger, "Volatilité de {EV-000001}.", allowed_ids={"EV-000002"})
    assert fidelity.OUTSIDE_PACK in result.issues


# --- contrôle 3 : aucune preuve publiée après as_of ---------------------------------------------
def test_preuve_future_refusee(ledger):
    result = check_claim(Claim(text="Volatilité de {EV-000001}.", evidence_ids=("EV-000001",)), ledger,
                         date(2024, 6, 28), FORBIDDEN)
    assert fidelity.FUTURE_EVIDENCE in result.issues


# --- contrôle 4 : formulations ------------------------------------------------------------------
def test_formulation_prescriptive_refusee(ledger):
    assert fidelity.FORBIDDEN_WORDING in check(ledger, "Achetez : volatilité de {EV-000001}.").issues


# --- contrôle 5 : le claim_kind affiché est celui des preuves -----------------------------------
@pytest.mark.parametrize("ids, expected", [
    (["EV-000001"], "FAIT"),
    (["EV-000001", "EV-000004"], "HYPOTHESE"),
    (["EV-000001", "EV-000004", "EV-000005"], "SCENARIO"),
])
def test_claim_kind_derive_des_preuves(ledger, ids, expected):
    result = check(ledger, "Affirmation sourcée.", ids, kind="FAIT")
    assert result.ok
    assert result.claim.claim_kind == expected
    assert result.kind_corrected == (expected != "FAIT")
