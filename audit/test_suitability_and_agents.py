"""Audit — adéquation au profil, cohérence interne, débat et fidélité de l'explication.

Chaque test énonce le comportement *attendu* d'un conseiller prudent. Un test en échec documente un
défaut (voir AUDIT_REPORT.md). Pipeline réel exécuté en mémoire (service de l'API, agents simulés :
aucun accès AWS ici).

Lancer depuis backend/ :  PYTHONPATH=. .venv/Scripts/python.exe -m pytest ../audit -q -p no:cacheprovider
"""
from __future__ import annotations

import re
import time

import pytest

from easytrade.api.service import ApiService
from easytrade.engine.coherence import RISK_LIMITS, tolerance_level
from easytrade.schemas.api import ProfileDraft, RunRequest


@pytest.fixture(scope="module")
def svc():
    return ApiService()


def _run(svc, profile_id, ticker=None):
    rid = svc.start_run(RunRequest(profile_id=profile_id, requested_ticker=ticker))
    for _ in range(900):
        st = svc.run_status(rid)
        if st.status != "en_cours":
            assert st.status == "termine", st.error
            return st, rid
        time.sleep(0.2)
    raise TimeoutError(rid)


def _vol_dd(svc, ticker):
    m = {x.metric: x.value for x in svc.asset_sheet(ticker).metrics}
    return m["volatilite"], m["perte_max"]


def _draft(**kw):
    base = dict(objectif="equilibre", horizon="moyen", tolerance="moderee", preferences=[], exclusions=[])
    return ProfileDraft(**{**base, **kw})


# ---------- contraintes dures ----------------------------------------------------------------------

def test_contraintes_dures_resistent_aux_poids(svc):
    """Une variante de poids extrême ne lève pas l'exclusion crypto de Robert et de Mateo."""
    for base in ("robert", "mateo"):
        pw = svc.create_profile(ProfileDraft(base_persona=base, weights_override={"croissance": 50.0, "stabilite": 0.0, "esg": 0.0}))
        st, _ = _run(svc, pw.profile_id)
        assert pw.hard_constraints.max_weight_crypto == 0.0
        assert not [i.ticker for i in st.result.items if i.asset_class == "crypto"]


def test_poids_negatifs_refuses(svc):
    from easytrade.api.service import InvalidRequest
    with pytest.raises(InvalidRequest):
        svc.create_profile(ProfileDraft(base_persona="robert", weights_override={"croissance": -1.0}))


def test_aucune_recommandation_possible(svc):
    st, _ = _run(svc, "mateo")
    assert st.result.no_recommendation and not st.result.items


# ---------- adéquation : l'objectif, l'horizon et la tolérance doivent compter ---------------------

def _tickers(st):
    return [i.ticker for i in st.result.items]


def test_horizon_change_le_resultat(svc):
    """« Moins de 5 ans » et « plus de 12 ans » ne doivent pas donner exactement la même analyse."""
    court = svc.create_profile(_draft(objectif="preserver", horizon="court", tolerance="faible"))
    long_ = svc.create_profile(_draft(objectif="preserver", horizon="long", tolerance="faible"))
    a, _ = _run(svc, court.profile_id)
    b, _ = _run(svc, long_.profile_id)
    assert court.weights != long_.weights or _tickers(a) != _tickers(b), (
        "horizon sans effet : mêmes poids et mêmes pistes pour 3-5 ans et 12 ans et plus")


def test_objectif_contradictoire_pris_en_compte(svc):
    """« Préserver le capital, moins de 5 ans » ne doit pas recevoir les poids d'un profil de croissance à long terme."""
    prudent = svc.create_profile(_draft(objectif="preserver", horizon="court", tolerance="elevee"))
    croissance = svc.create_profile(_draft(objectif="croissance", horizon="long", tolerance="elevee"))
    assert prudent.weights != croissance.weights, "objectif et horizon ignorés : seuls comptent la tolérance déclarée"


def test_profil_prudent_sans_piste_hors_reperes(svc):
    """Robert (tolérance faible à modérée) : aucune piste ne dépasse à la fois son repère de volatilité et de perte."""
    st, _ = _run(svc, "robert")
    max_vol, max_dd = RISK_LIMITS[tolerance_level("faible à modéré")]
    both = [t for t in _tickers(st) if (lambda v, d: v > max_vol and d < max_dd)(*_vol_dd(svc, t))]
    assert not both, f"pistes au-delà des deux repères de Robert : {both}"


def test_variante_de_poids_ne_contourne_pas_la_tolerance(svc):
    """Changer les poids ne doit pas faire d'un titre deux fois plus volatil que le repère la piste n° 1 « adéquation élevée »."""
    pw = svc.create_profile(ProfileDraft(base_persona="robert", weights_override={"croissance": 5.0, "stabilite": 0.0}))
    st, _ = _run(svc, pw.profile_id)
    top = st.result.items[0]
    vol, _dd = _vol_dd(svc, top.ticker)
    max_vol = RISK_LIMITS[tolerance_level("faible à modéré")][0]
    assert not (vol > 2 * max_vol and top.fit == "élevée"), f"{top.ticker} : volatilité {vol:.0f} % pour un repère de {max_vol:.0f} %"


def test_classement_et_tester_une_idee_coherents(svc):
    """Un titre classé n° 1 « adéquation élevée » ne peut pas être jugé « incohérent avec le profil » pour le même profil."""
    pw = svc.create_profile(ProfileDraft(base_persona="robert", weights_override={"croissance": 5.0, "stabilite": 0.0}))
    st, _ = _run(svc, pw.profile_id)
    top = st.result.items[0]
    test, _ = _run(svc, pw.profile_id, top.ticker)
    assert not (top.fit == "élevée" and test.result.coherence.verdict == "incohérent avec le profil"), (
        f"{top.ticker} : n° 1 « élevée » dans les pistes, « incohérent » dans Tester une idée")


def test_profils_officiels_differencies(svc):
    """Amira (risque élevé, 15 ans+) et Robert (faible à modéré, 3-5 ans) ne doivent pas recevoir les mêmes titres."""
    a, _ = _run(svc, "amira")
    r, _ = _run(svc, "robert")
    assert not set(_tickers(a)) <= set(_tickers(r)), f"toutes les pistes d'Amira figurent chez Robert : {sorted(_tickers(a))}"


# ---------- débat --------------------------------------------------------------------------------

def test_le_bull_peut_s_opposer_ou_reserver(svc):
    """Un agent qui appuie 100 % des titres n'apporte aucune information."""
    stances = []
    for pid in ("amira", "robert"):
        st, _ = _run(svc, pid)
        stances += [d.stance for i in st.result.items for d in i.debate if d.agent == "bull"]
    assert any(s != "appui" for s in stances), f"Bull : {len(stances)} appuis sur {len(stances)}"


def test_desaccord_signifie_une_opposition(svc):
    """« Désaccord » ne devrait apparaître que si au moins un agent s'oppose."""
    st, _ = _run(svc, "robert")
    soft = [i.ticker for i in st.result.items
            if i.debate_summary.dissent and all(d.stance != "opposition" for d in i.debate)]
    assert not soft, f"désaccord affiché sans opposition : {soft}"


# ---------- fidélité de l'explication : chaque chiffre vient d'une preuve citée --------------------

NUM = re.compile(r"-?\d+(?:,\d+)?(?=\s?%)")


def _fr(x: str) -> float:
    return float(x.replace(",", "."))


def test_chiffres_des_affirmations_issus_des_preuves(svc):
    checked, bad = 0, []
    for pid in ("amira", "robert"):
        st, rid = _run(svc, pid)
        claims = [c for i in st.result.items for c in (*i.why, *(a for d in i.debate for a in d.arguments))]
        for c in claims:
            values = []
            for eid in c.evidence_ids:
                ev = svc.evidence(eid, rid)
                if ev.value is not None:
                    values.append(ev.value)
            for n in NUM.findall(c.text):
                checked += 1
                x = _fr(n)
                if not any(abs(abs(x) - abs(v)) <= 0.051 for v in values):
                    bad.append(f"{c.text!r} cite {c.evidence_ids} = {values}")
    assert checked > 50
    assert not bad, "\n".join(bad[:10])
