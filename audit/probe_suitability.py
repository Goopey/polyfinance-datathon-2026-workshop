"""Audit — sonde d'adéquation : exécute le pipeline réel (service de l'API, agents simulés) pour les
personas officiels et des profils adverses, et écrit les résultats bruts dans audit/out/suitability.json.

Lancer depuis backend/ : .venv/Scripts/python.exe ../audit/probe_suitability.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from easytrade.api.service import ApiService
from easytrade.engine.coherence import RISK_LIMITS, tolerance_level
from easytrade.schemas.api import ProfileDraft, RunRequest

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
svc = ApiService()


def run(profile_id: str, ticker: str | None = None) -> dict:
    rid = svc.start_run(RunRequest(profile_id=profile_id, requested_ticker=ticker))
    for _ in range(600):
        st = svc.run_status(rid)
        if st.status != "en_cours":
            return st.model_dump(mode="json")
        time.sleep(0.2)
    raise TimeoutError(rid)


def metrics_of(ticker: str) -> dict:
    sheet = svc.asset_sheet(ticker)
    return {m.metric: m.value for m in sheet.metrics}


def summarize(profile_id: str, status: dict) -> dict:
    entry = svc._entry(profile_id)
    level = tolerance_level(entry["profil"]["tolerance_risque"])
    max_vol, max_dd = RISK_LIMITS[level]
    res = status["result"]
    items = []
    for it in res["items"]:
        m = metrics_of(it["ticker"])
        items.append({
            "ticker": it["ticker"], "class": it["asset_class"], "sector": it["sector"], "fit": it["fit"],
            "confidence": it["confidence"], "to_review": it["to_review"],
            "score": round(sum(it["contributions"].values()) * 100, 1),
            "vol": round(m.get("volatilite", float("nan")), 1), "dd": round(m.get("perte_max", float("nan")), 1),
            "over_vol": m.get("volatilite", 0) > max_vol, "over_dd": m.get("perte_max", 0) < max_dd,
            "stances": {d["agent"]: d["stance"] for d in it["debate"]}, "dissent": it["debate_summary"]["dissent"],
        })
    return {
        "profile_id": profile_id, "tolerance": entry["profil"]["tolerance_risque"], "level": level,
        "limits": {"vol": max_vol, "dd": max_dd}, "weights": svc.profile_view(profile_id).weights,
        "constraints": entry["contraintes"], "status": status["status"], "headline": res["headline"],
        "no_recommendation": res["no_recommendation"], "missing": res["missing"],
        "items": items, "rejected": [(r["ticker"], r["kind"]) for r in res["rejected"]],
    }


results: dict = {}
for pid in ("amira", "mateo", "robert"):
    results[pid] = summarize(pid, run(pid))

# Profils adverses (questionnaire) : objectif et horizon contradictoires avec la tolérance.
ADVERSARIAL = {
    "preserver_court_elevee": dict(objectif="preserver", horizon="court", tolerance="elevee", preferences=[], exclusions=[]),
    "croissance_long_elevee": dict(objectif="croissance", horizon="long", tolerance="elevee", preferences=[], exclusions=[]),
    "preserver_long_faible": dict(objectif="preserver", horizon="long", tolerance="faible", preferences=[], exclusions=[]),
    "preserver_court_faible": dict(objectif="preserver", horizon="court", tolerance="faible", preferences=[], exclusions=[]),
    "elevee_sans_crypto": dict(objectif="croissance", horizon="long", tolerance="elevee", preferences=[], exclusions=["crypto"]),
    "esg_controverses": dict(objectif="equilibre", horizon="moyen", tolerance="moderee", preferences=["esg"], exclusions=["controverses"]),
}
for name, draft in ADVERSARIAL.items():
    pw = svc.create_profile(ProfileDraft(**draft))
    results[name] = summarize(pw.profile_id, run(pw.profile_id))
    results[name]["draft"] = draft

# Variantes de poids : contrainte dure intacte même avec un poids extrême.
pw = svc.create_profile(ProfileDraft(base_persona="robert", weights_override={"croissance": 5.0, "stabilite": 0.0}))
results["robert_croissance_extreme"] = summarize(pw.profile_id, run(pw.profile_id))
pw = svc.create_profile(ProfileDraft(base_persona="mateo", weights_override={"esg": 0.0}))
results["mateo_sans_esg"] = summarize(pw.profile_id, run(pw.profile_id))

# Tester une idée : Robert + titres volatils ; Amira + BTC.
results["tests"] = {}
for pid, t in (("robert", "TSLA"), ("robert", "NVDA"), ("robert", "BTC-USD"), ("amira", "BTC-USD"), ("robert", "ZST.TO")):
    st = run(pid, t)
    c = st["result"]["coherence"]
    results["tests"][f"{pid}+{t}"] = {"verdict": c["verdict"], "tensions": [x["text"] for x in c["tensions"]],
                                     "alternatives": [a["ticker"] for a in c["alternatives"]]}

(OUT / "suitability.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in results.items():
    if k == "tests":
        continue
    print(f"\n== {k} [{v['level']}; limites vol {v['limits']['vol']} / pp {v['limits']['dd']}] → {v['headline']}")
    print("   poids:", {a: round(b, 2) for a, b in v["weights"].items()})
    for it in v["items"]:
        flag = ("VOL>" if it["over_vol"] else "") + ("DD<" if it["over_dd"] else "")
        print(f"   {it['ticker']:8} {it['class']:13} score={it['score']:5} fit={it['fit']:9} conf={it['confidence']:7} "
              f"vol={it['vol']:5} dd={it['dd']:6} {flag:7} review={it['to_review']} {it['stances']}")
print("\n== tests", json.dumps(results["tests"], ensure_ascii=False, indent=1))
