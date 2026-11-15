"""Précalcule les analyses des agents pour que l'application réponde en moins d'une seconde.

Conception : docs/06_AWS.md (section « Précalcul »), ADR 0001 (les LLM argumentent, le code décide)
Le pipeline est déterministe et l'identifiant d'un run ne dépend que de la date, du profil et du titre
demandé (`run_2026-11-12_robert_TSLA`). L'API réutilise un run terminé de même identifiant : lancer ici
chaque combinaison une fois suffit pour que toutes les demandes suivantes soient servies sans attendre.

Ce script appelle l'API déployée (ou locale) :
- vues des profils des personas (`GET /profiles/{id}`, pondération par l'agent, gardée dans la table) ;
- analyse par défaut de chaque persona ;
- « Tester une idée » pour chaque persona × chaque titre de l'univers (`--tickers all`, défaut).
Relancer le script ne refait que ce qui manque ou a échoué.

    python scripts/precompute.py --api <ApiUrl>                      # tout (3 + 3 × 31 analyses)
    python scripts/precompute.py --api <ApiUrl> --tickers none       # seulement les 3 analyses par défaut
    python scripts/precompute.py --api <ApiUrl> --tickers TSLA,NVDA --concurrency 2

Coût indicatif sur Bedrock : 0,35 à 0,60 $ par analyse (estimation) ; environ 35 à 60 $ pour tout.
La concurrence reste basse (3 par défaut) pour ne pas dépasser les quotas Bedrock du compte d'atelier.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

FINAL = ("termine", "echec")
Request = Callable[[str, str, Optional[dict]], Any]


def http_client(base_url: str, timeout: float = 60.0) -> Request:
    base = base_url.rstrip("/")

    def request(method: str, path: str, body: Optional[dict] = None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"{method} {path} : HTTP {error.code} {error.read().decode('utf-8', 'replace')[:300]}") from error

    return request


def run_job(request: Request, profile_id: str, ticker: Optional[str], *, poll: float, timeout: float,
            sleep: Callable[[float], None] = time.sleep) -> dict:
    started = time.monotonic()
    body = {"profile_id": profile_id, **({"requested_ticker": ticker} if ticker else {})}
    run_id = request("POST", "/runs", body)["run_id"]
    while True:
        status = request("GET", f"/runs/{run_id}", None)
        if status["status"] in FINAL:
            return {"run_id": run_id, "status": status["status"], "error": status.get("error"),
                    "seconds": time.monotonic() - started}
        if time.monotonic() - started > timeout:
            return {"run_id": run_id, "status": "delai", "error": f"pas fini après {timeout:.0f} s",
                    "seconds": time.monotonic() - started}
        sleep(poll)


def precompute(request: Request, *, tickers: str = "all", concurrency: int = 3, poll: float = 10.0,
               timeout: float = 1200.0, log: Callable[[str], None] = print,
               sleep: Callable[[float], None] = time.sleep) -> list[dict]:
    personas = [p["id"] for p in request("GET", "/personas", None)]
    for persona in personas:
        started = time.monotonic()
        request("GET", f"/profiles/{persona}", None)
        log(f"profil {persona} : prêt ({time.monotonic() - started:.1f} s)")

    if tickers == "all":
        chosen = [a["ticker"] for a in request("GET", "/assets", None)]
    elif tickers == "none":
        chosen = []
    else:
        chosen = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    jobs = [(p, None) for p in personas] + [(p, t) for p in personas for t in chosen]
    log(f"{len(jobs)} analyses à préparer ({len(personas)} profils × {len(chosen)} titres + défaut), "
        f"{concurrency} à la fois")

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = {pool.submit(run_job, request, p, t, poll=poll, timeout=timeout, sleep=sleep): (p, t)
                   for p, t in jobs}
        for done, future in enumerate(as_completed(futures), start=1):
            persona, ticker = futures[future]
            try:
                result = future.result()
            except Exception as error:  # erreur HTTP : notée, le reste continue
                result = {"run_id": f"{persona}/{ticker or '-'}", "status": "erreur", "error": str(error), "seconds": 0.0}
            results.append(result)
            note = "" if result["status"] == "termine" else f" — {result['error']}"
            log(f"[{done:3d}/{len(jobs)}] {result['run_id']:40s} {result['status']:8s} {result['seconds']:6.0f} s{note}")
    return results


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Précalcule les analyses des agents (EasyTrade).")
    parser.add_argument("--api", default=os.environ.get("EASYTRADE_API_URL"),
                        help="URL de l'API (sortie EasyTradeApi.ApiUrl), ou variable EASYTRADE_API_URL")
    parser.add_argument("--tickers", default="all", help="all (défaut), none, ou liste séparée par des virgules")
    parser.add_argument("--concurrency", type=int, default=3, help="analyses en parallèle (quotas Bedrock)")
    parser.add_argument("--poll", type=float, default=10.0, help="intervalle d'interrogation, en secondes")
    args = parser.parse_args(argv)
    if not args.api:
        parser.error("--api requis (URL de l'API déployée, ex. https://abc123.execute-api.us-east-1.amazonaws.com)")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    request = http_client(args.api)
    started = time.monotonic()
    results = precompute(request, tickers=args.tickers, concurrency=args.concurrency, poll=args.poll)
    failed = [r for r in results if r["status"] != "termine"]
    print(f"\n{len(results) - len(failed)}/{len(results)} analyses prêtes en {(time.monotonic() - started) / 60:.1f} min.")
    if results and not failed:  # une demande précalculée doit maintenant répondre tout de suite
        t0 = time.monotonic()
        request("GET", f"/runs/{results[0]['run_id']}", None)
        print(f"Lecture d'une analyse précalculée : {time.monotonic() - t0:.2f} s.")
    for result in failed:
        print(f"  À relancer : {result['run_id']} ({result['status']}) {result['error']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
