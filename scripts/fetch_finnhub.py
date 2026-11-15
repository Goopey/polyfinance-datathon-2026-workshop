"""Instantané Finnhub : sociétés comparables (graphe), fondamentaux annuels (« qualité »), sentiment.

Conception : docs/04_DONNEES.md (sections 6, 10 et 11), ADR 0002 (instantané daté, pas d'appel en direct)
Lance une seule fois, puis versionne les fichiers produits ; l'application et les Lambda lisent ces
fichiers, jamais l'API Finnhub (pas de clé sur AWS, démonstration reproductible).

    python scripts/fetch_finnhub.py                    # tout ; clé lue dans FINNHUB_API_KEY ou dans .env
    python scripts/fetch_finnhub.py --only sentiment   # une partie : peers, fundamentals, sentiment

Produit dans data/reference/ :
- graph_edges.csv   : arêtes CONCURRENT (sociétés du même secteur selon Finnhub), claim_kind HYPOTHESE :
                      la classification n'est pas datée ; on suppose qu'elle était la même à la date
                      d'analyse (date d'effet), la date réelle de relevé est écrite dans l'extrait ;
- fundamentals.csv  : séries annuelles roe, totalDebtToEquity, netMargin, avec la date de fin d'exercice
                      (la date de publication supposée est calculée à la lecture, config.py) ;
- sentiment.csv     : recommandations d'analystes (mensuelles) et sentiment des initiés (indice MSPR mensuel,
                      actions américaines), avec leur mois (date de publication supposée : config.py).
Couverture : les 20 actions de l'univers ; les 10 canadiennes via leur cotation américaine (offre
gratuite). Ni FNB ni crypto (pas de comptes de société).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "data" / "reference"
UNIVERSE = REPO / "data" / "raw" / "starter" / "assets_universe.csv"
API = "https://finnhub.io/api/v1"
EFFECTIVE_DATE = "2026-11-12"  # date d'analyse du jeu de départ : date d'effet supposée des comparables
MAX_PEERS = 5
METRICS = ("roe", "totalDebtToEquity", "netMargin")
FIRST_PERIOD = "2018-01-01"  # exercices plus anciens inutiles (fenêtre de prix : 2021 à 2026)
FIRST_SENTIMENT = "2025-01-01"  # sentiment : les 2 dernières années suffisent
PARTS = ("peers", "fundamentals", "sentiment")
# Cotation américaine des titres de la Bourse de Toronto (accès gratuit par ce symbole).
US_LISTING = {"RY.TO": "RY", "TD.TO": "TD", "MFC.TO": "MFC", "ENB.TO": "ENB", "CNQ.TO": "CNQ",
              "CNR.TO": "CNI", "FTS.TO": "FTS", "SHOP.TO": "SHOP", "ATD.TO": "ANCTF", "CSU.TO": "CNSWF"}
EDGE_COLUMNS = ["source", "target", "relation", "claim_kind", "document_type", "document_id", "section",
                "document_date", "document_url", "excerpt", "extracted_by", "reviewed_by"]
FUNDAMENTAL_COLUMNS = ["ticker", "metric", "value", "period_end", "frequency", "source_id", "document_url",
                       "retrieved_at"]
SENTIMENT_COLUMNS = ["ticker", "kind", "period", "strong_buy", "buy", "hold", "sell", "strong_sell", "mspr",
                     "change", "source_id", "document_url", "retrieved_at"]


def api_key() -> str:
    key = os.environ.get("FINNHUB_API_KEY", "")
    env = REPO / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith("FINNHUB_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise SystemExit("Clé absente : renseigner FINNHUB_API_KEY dans .env")
    return key


def get(path: str, key: str):
    url = f"{API}{path}{'&' if '?' in path else '?'}token={key}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:  # limite de 60 appels / minute
                time.sleep(20)
                continue
            raise RuntimeError(f"Finnhub {path.split('?')[0]} : HTTP {error.code}") from error
    raise RuntimeError("Finnhub : trop de tentatives")


def write(filename: str, columns: list[str], rows: list[dict]) -> None:
    with open(REFERENCE / filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pause", type=float, default=1.1, help="secondes entre deux appels (offre gratuite)")
    parser.add_argument("--only", default=",".join(PARTS), help="parties à relever : " + ", ".join(PARTS))
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parts = {p.strip() for p in args.only.split(",") if p.strip()}
    if not parts <= set(PARTS):
        parser.error(f"--only : choisir parmi {', '.join(PARTS)}")
    key, today = api_key(), date.today().isoformat()

    with open(UNIVERSE, encoding="utf-8") as f:
        equities = [row["ticker"] for row in csv.DictReader(f) if row["asset_class"] == "equity"]
    to_universe = {us: tsx for tsx, us in US_LISTING.items()}

    def call(path: str):
        result = get(path, key)
        time.sleep(args.pause)
        return result

    edges: dict[frozenset, dict] = {}
    fundamentals: list[dict] = []
    sentiment: list[dict] = []
    for ticker in equities:
        symbol = US_LISTING.get(ticker, ticker)
        report = []
        if "peers" in parts:
            kept: list[str] = []
            for peer in call(f"/stock/peers?symbol={symbol}"):
                peer = to_universe.get(peer, peer)  # « SHOP » (New York) → « SHOP.TO » (univers)
                if peer not in (ticker, symbol) and peer not in kept:
                    kept.append(peer)
            for peer in kept[:MAX_PEERS]:
                pair = frozenset((ticker, peer))
                if pair in edges:  # relation symétrique : une seule arête par paire
                    continue
                edges[pair] = {
                    "source": ticker, "target": peer, "relation": "CONCURRENT", "claim_kind": "HYPOTHESE",
                    "document_type": "finnhub_peers", "document_id": f"stock/peers?symbol={symbol}",
                    "section": "sociétés comparables (même secteur)", "document_date": EFFECTIVE_DATE,
                    "document_url": f"{API}/stock/peers?symbol={symbol}",
                    "excerpt": (f"Finnhub classe {peer} parmi les sociétés comparables à {ticker} (relevé le {today}). "
                                f"Hypothèse : classification identique au {EFFECTIVE_DATE}."),
                    "extracted_by": "script:fetch_finnhub", "reviewed_by": "",
                }
            report.append(f"{len(kept[:MAX_PEERS])} comparables")

        if "fundamentals" in parts:
            annual = call(f"/stock/metric?symbol={symbol}&metric=all").get("series", {}).get("annual", {})
            before = len(fundamentals)
            for metric in METRICS:
                for point in annual.get(metric, []):
                    if point.get("v") is None or point.get("period", "") < FIRST_PERIOD:
                        continue
                    fundamentals.append({
                        "ticker": ticker, "metric": metric, "value": point["v"], "period_end": point["period"],
                        "frequency": "annual", "source_id": "finnhub",
                        "document_url": f"{API}/stock/metric?symbol={symbol}&metric=all", "retrieved_at": today,
                    })
            report.append(f"{len(fundamentals) - before} points annuels")

        if "sentiment" in parts:
            before = len(sentiment)
            for rec in call(f"/stock/recommendation?symbol={symbol}"):
                if rec.get("period", "") >= FIRST_SENTIMENT:
                    sentiment.append({
                        "ticker": ticker, "kind": "analystes", "period": rec["period"],
                        **{k: rec.get(c, 0) for k, c in (("strong_buy", "strongBuy"), ("buy", "buy"), ("hold", "hold"),
                                                          ("sell", "sell"), ("strong_sell", "strongSell"))},
                        "mspr": "", "change": "", "source_id": "finnhub",
                        "document_url": f"{API}/stock/recommendation?symbol={symbol}", "retrieved_at": today,
                    })
            insiders = call(f"/stock/insider-sentiment?symbol={symbol}&from={FIRST_SENTIMENT}&to={today}")
            for point in (insiders or {}).get("data", []):
                sentiment.append({
                    "ticker": ticker, "kind": "inities", "period": f"{point['year']:04d}-{point['month']:02d}-01",
                    "strong_buy": "", "buy": "", "hold": "", "sell": "", "strong_sell": "",
                    "mspr": point.get("mspr"), "change": point.get("change"), "source_id": "finnhub",
                    "document_url": f"{API}/stock/insider-sentiment?symbol={symbol}", "retrieved_at": today,
                })
            report.append(f"{len(sentiment) - before} mois de sentiment")
        print(f"{ticker:8s} ({symbol:6s}) : " + ", ".join(report))

    if "peers" in parts:
        write("graph_edges.csv", EDGE_COLUMNS, sorted(edges.values(), key=lambda r: (r["source"], r["target"])))
        print(f"{len(edges)} arêtes → data/reference/graph_edges.csv")
    if "fundamentals" in parts:
        write("fundamentals.csv", FUNDAMENTAL_COLUMNS,
              sorted(fundamentals, key=lambda r: (r["ticker"], r["metric"], r["period_end"])))
        print(f"{len(fundamentals)} points → data/reference/fundamentals.csv")
    if "sentiment" in parts:
        write("sentiment.csv", SENTIMENT_COLUMNS, sorted(sentiment, key=lambda r: (r["ticker"], r["kind"], r["period"])))
        print(f"{len(sentiment)} lignes → data/reference/sentiment.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
