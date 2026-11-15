"""S3 — Robert : la demande incohérente est remise en question.

Conception : docs/09_SCENARIOS_TEST.md
Robert (tolérance faible à modérée, horizon de 3 à 5 ans) soumet un titre très médiatisé et
volatil de l'univers. Pipeline complet en local, données réelles, agents simulés.
"""
import re

import pytest

from easytrade.engine.signals import asset_themes

TICKERS = ("TSLA", "NVDA")


@pytest.fixture(scope="module", params=TICKERS)
def run(request, pipeline_run):
    result = pipeline_run("robert", request.param)
    assert result.status == "termine", result.error
    return result


@pytest.mark.scenario("S3")
def test_s03_1_le_titre_est_analyse_pas_ignore(run):
    ticker = run.requested_ticker
    assert run.explanation.coherence is not None and run.explanation.coherence.ticker == ticker
    assert ticker in run.candidates.tickers and run.candidates.candidates[0].requested
    assert ticker in run.debate, "le titre demandé n'a pas été débattu"
    assert {t.agent for t in run.debate[ticker].final} == {"bull", "realist", "bear"}


@pytest.mark.scenario("S3")
def test_s03_2_verdict_et_tensions_chiffrees(run):
    coherence = run.explanation.coherence
    assert coherence.verdict != "cohérent"
    assert coherence.verdict == "incohérent avec le profil"
    texts = [claim.text for claim in coherence.tensions]
    volatility = [t for t in texts if "Volatilité" in t]
    drawdown = [t for t in texts if "Perte maximale" in t]
    assert volatility and drawdown, texts
    # Chaque tension est chiffrée et sourcée.
    for claim in coherence.tensions:
        assert re.search(r"\d", claim.text), claim.text
        assert claim.evidence_ids and all(i in run.ledger for i in claim.evidence_ids)
    # Les repères de risque cités sont ceux du niveau de tolérance de Robert, étiquetés hypothèse.
    limits = set(run.weighting.limit_evidence.values())
    assert any(limits & set(c.evidence_ids) and c.claim_kind == "HYPOTHESE" for c in coherence.tensions)


@pytest.mark.scenario("S3")
def test_s03_2_horizon_de_3_a_5_ans(pipeline_run):
    run = pipeline_run("robert", "TSLA")
    coherence = run.explanation.coherence
    assert any("3 ans" in claim.text for claim in coherence.tensions), [c.text for c in coherence.tensions]
    # La mise en contexte rattache le risque à l'horizon déclaré du profil.
    horizon = run.weighting.fact("horizon")
    assert "3 à 5 ans" in horizon.text
    assert any(horizon.evidence_id in claim.evidence_ids for claim in coherence.context)


@pytest.mark.scenario("S3")
def test_s03_3_effet_sur_le_panier_simule(run):
    scenarios = [c for c in run.explanation.coherence.context if c.claim_kind == "SCENARIO"]
    assert len(scenarios) == 1
    before, _, after = (run.ledger.get(i) for i in scenarios[0].evidence_ids)
    assert before.claim_kind == after.claim_kind == "SCENARIO"
    # Ajouter un titre plus volatil au panier simulé en augmente la volatilité observée.
    assert after.value > before.value
    assert run.requested_ticker in after.statement


@pytest.mark.scenario("S3")
def test_s03_4_ni_acquiescement_automatique_ni_refus_sec(run):
    ticker = run.requested_ticker
    explanation = run.explanation
    assert ticker not in {i.ticker for i in explanation.items}       # pas présenté comme une piste, sans réserve
    assert ticker not in {r.ticker for r in explanation.rejected}    # pas écarté en silence par une règle
    coherence = explanation.coherence
    assert len(coherence.tensions) >= 2 and coherence.context        # le risque est expliqué et mis en contexte
    assert any(c.claim_kind == "FAIT" for c in coherence.context)
    # Le désaccord du débat sur ce titre est conservé dans la décision.
    assert any(d.startswith(ticker) for d in run.decision.disagreements)
    # Les alternatives proposées présentent moins de tension, preuve à l'appui.
    asset_vol = next(run.ledger.get(i).value for c in coherence.tensions for i in c.evidence_ids
                     if "Volatilité annualisée (" in run.ledger.get(i).statement and run.ledger.get(i).subject == ticker)
    for alternative in coherence.alternatives:
        assert run.ledger.get(alternative.why.evidence_ids[0]).value < asset_vol


@pytest.mark.scenario("S3")
def test_s03_5_pistes_par_defaut_etablies_sans_crypto(run):
    items = run.explanation.items
    assert items and all(i.asset_class != "crypto" for i in items)
    crypto = [r for r in run.explanation.rejected if r.ticker in ("BTC-USD", "ETH-USD")]
    assert len(crypto) == 2 and all(r.kind == "contrainte" for r in crypto)
    # Actifs établis : entreprises établies, fonds indiciels diversifiés, obligations ou or.
    # Décision de l'équipe (2026-11-15) : depuis le critère « qualité », une société rentable et peu
    # endettée classée « technologies » par la table des thèmes (GOOGL) est une piste légitime pour
    # Robert. On exige donc une majorité d'actifs établis, aucun actif spéculatif. La présence de QQQ
    # (indice à forte pondération technologique, 10e piste) est suivie dans la tâche de calibrage C7.
    established = {"entreprises_etablies", "indiciel_diversifie", "obligations", "or"}
    settled = [i for i in items if established & set(asset_themes(i.asset_class, i.sector))]
    assert len(settled) > len(items) / 2, [i.ticker for i in items if i not in settled]
    assert not any("spéculatif" in flag for i in items for flag in getattr(i, "flags", ()))


@pytest.mark.scenario("S3")
def test_s03_une_demande_coherente_n_est_pas_refusee(pipeline_run):
    # Contre-épreuve : un titre établi et peu volatil n'est pas jugé incohérent.
    run = pipeline_run("robert", "FTS.TO")
    assert run.explanation.coherence.verdict in ("cohérent", "cohérent avec réserve")


@pytest.mark.scenario("S3")
def test_s03_un_cryptoactif_demande_est_analyse_meme_s_il_est_exclu(pipeline_run):
    run = pipeline_run("robert", "BTC-USD")
    coherence = run.explanation.coherence
    assert coherence.verdict == "incohérent avec le profil"
    assert any("crypto" in c.text.lower() for c in coherence.tensions)
    assert "BTC-USD" in run.debate
