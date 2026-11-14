"""S9 — Calculs exacts et rejouables.
Conception : docs/09_SCENARIOS_TEST.md

Le calcul indépendant n'utilise ni pandas ni numpy : modules `csv`, `bisect`, `math`, `statistics`.
"""
import bisect
import csv
import math
import statistics

import pytest

from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.validation.metrics import compute_metrics_table

TEMOINS = [("XIU.TO", 252), ("AAPL", 252), ("BTC-USD", 365)]  # CAD, USD converti, crypto


def _calcul_independant(starter_dir, ticker, periodes_par_an):
    with open(starter_dir / "prices_daily.csv", encoding="utf-8", newline="") as f:
        lignes = sorted((r["date"], float(r["adj_close"]), r["currency"]) for r in csv.DictReader(f) if r["ticker"] == ticker)
    with open(starter_dir / "fx_usdcad_daily.csv", encoding="utf-8", newline="") as f:
        taux = sorted((r["date"], float(r["usdcad"])) for r in csv.DictReader(f))
    dates_fx = [d for d, _ in taux]

    prix = []
    for date, adj, devise in lignes:
        if devise == "USD":
            i = bisect.bisect_right(dates_fx, date) - 1  # dernier taux connu à la date ou avant
            adj *= taux[i][1]
        prix.append(adj)

    rendements = [prix[i] / prix[i - 1] - 1 for i in range(1, len(prix))]
    n = len(rendements)
    rendement_annualise = (prix[-1] / prix[0]) ** (periodes_par_an / n) - 1
    volatilite = statistics.stdev(rendements) * math.sqrt(periodes_par_an)
    sommet, perte = prix[0], 0.0
    for p in prix:
        sommet = max(sommet, p)
        perte = min(perte, p / sommet - 1)
    return {"annualized_return": rendement_annualise * 100, "annualized_volatility": volatilite * 100, "max_drawdown": perte * 100}


def _executer(store, registry, settings):
    ledger = EvidenceLedger(settings.as_of)
    table = compute_metrics_table(store, settings.as_of, ledger, registry, settings.quality)
    return table, ledger


@pytest.mark.scenario("S9")
def test_s09_1_deux_executions_identiques(store, registry, settings):
    table_1, ledger_1 = _executer(store, registry, settings)
    table_2, ledger_2 = _executer(store, registry, settings)
    assert table_1.equals(table_2)
    assert ledger_1.ids() == ledger_2.ids()
    assert ledger_1.to_records() == ledger_2.to_records()

    # Même résultat depuis un magasin rechargé : aucune dépendance à un état en mémoire.
    from easytrade.data.point_in_time import PointInTimeStore

    table_3, ledger_3 = (lambda s: _executer(s, registry, settings))(PointInTimeStore.from_settings(settings))
    assert table_1.equals(table_3) and ledger_1.to_records() == ledger_3.to_records()


@pytest.mark.scenario("S9")
@pytest.mark.parametrize("ticker,periodes", TEMOINS)
def test_s09_2_recoupement_par_calcul_independant(ticker, periodes, store, registry, settings):
    attendu = _calcul_independant(settings.starter_dir, ticker, periodes)
    table, ledger = _executer(store, registry, settings)
    lignes = table[(table["ticker"] == ticker) & (table["window"] == "full")].set_index("metric")
    for metrique, valeur in attendu.items():
        assert lignes.loc[metrique, "value"] == pytest.approx(valeur, rel=1e-9, abs=1e-9), (ticker, metrique)
        # La preuve porte la même valeur que la table.
        assert ledger.get(lignes.loc[metrique, "evidence_id"]).value == lignes.loc[metrique, "value"]
