"""Filtre de formulations prescriptives.

Conception : docs/08_CONFORMITE.md
"""
import pytest

from easytrade.explain.wording import find_forbidden, is_clean, load_forbidden, scan


def test_liste_de_reference_chargee(forbidden):
    # La liste vient du fichier versionné ; les commentaires et lignes vides sont ignorés.
    assert "achetez" in forbidden
    assert "rendement attendu" in forbidden
    assert not any(term.startswith("#") for term in forbidden)


@pytest.mark.parametrize("text", [
    "Achetez ce titre dès maintenant.",
    "VOUS DEVRIEZ renforcer cette position.",
    "Un placement sans risque.",
    "Le rendement attendu est élevé.",
    "Capital garanti.",
    "Performance garantie sur cinq ans.",   # sous-chaîne : « garanti » attrape « garantie »
    "Le prix cible est atteint.",
    "Le titre va monter.",
])
def test_formulations_prescriptives_detectees(forbidden, text):
    assert find_forbidden(text, forbidden)
    assert not is_clean(text, forbidden)


@pytest.mark.parametrize("text", [
    "Piste cohérente avec votre profil.",
    "Rendement observé de 12,3 % du 2021-11-12 au 2026-11-12.",
    "Adéquation élevée avec le profil ; à examiner.",
    "Simulation à des fins pédagogiques. Ceci n'est pas un conseil financier.",
])
def test_formulations_admises(forbidden, text):
    assert is_clean(text, forbidden)


def test_apostrophe_typographique_et_espace_insecable(forbidden):
    # « nous recommandons d'acheter » doit être reconnu quelle que soit la typographie.
    assert find_forbidden("Nous recommandons d’acheter ce fonds.", forbidden)
    assert find_forbidden("Un placement sans risque.", forbidden)


def test_scan_parcourt_toute_une_sortie_json(forbidden):
    payload = {"headline": "Trois pistes", "items": [{"why": [{"text": "Achetez vite"}], "risks": ("ok",)}]}
    hits = scan(payload, forbidden)
    assert hits == [("achetez", "Achetez vite")]


def test_liste_vide_refusee(tmp_path):
    (tmp_path / "forbidden_wording.txt").write_text("# seulement un commentaire\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_forbidden(tmp_path)
