"""Collecte toutes les chaînes affichables renvoyées par l'API locale (corpus du test de traduction EN).

Usage (API lancée sur le port 8000) :
    python scripts/harvest_backend_strings.py tests/fixtures/backend_strings.json
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Pas « localhost » : sous Windows, la résolution IPv6 coûte 2 s par appel. 2e argument facultatif : port.
API = f"http://127.0.0.1:{sys.argv[2] if len(sys.argv) > 2 else 8000}"
OUT = sys.argv[1]

def get(path):
    with urllib.request.urlopen(API + path, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

strings = {}  # texte -> ensemble de chemins
SKIP_KEYS = {"ticker", "run_id", "profile_id", "evidence_id", "evidence_ids", "as_of", "id", "center", "source", "target",
             "day", "start", "end", "period", "observed_at", "published_at", "retrieved_at", "date_extraction", "url",
             "source_id", "status", "kind", "claim_kind", "fit", "confidence", "stance", "agent", "verdict", "relation",
             "asset_class", "currency", "label_key", "step", "type", "unit", "metric", "field", "requested_ticker",
             "excluded_asset_classes", "speculatif", "statut", "not_applicable", "started_at", "ended_at", "input_hash",
             "prompt_version", "model_id", "produced_by", "tools_called", "outputs", "code_version"}

def walk(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in SKIP_KEYS:
                continue
            walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for v in node:
            walk(v, f"{path}[]")
    elif isinstance(node, str) and node.strip():
        strings.setdefault(node, set()).add(path)

def ev_ids(node, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "evidence_id" and isinstance(v, str):
                acc.add(v)
            elif k == "evidence_ids" and isinstance(v, list):
                acc.update(x for x in v if isinstance(x, str))
            else:
                ev_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            ev_ids(v, acc)

personas = get("/personas"); walk(personas, "personas")
pids = [p["id"] for p in personas]
for p in pids:
    walk(get(f"/profiles/{p}"), "profile")

# Profils du questionnaire : quelques combinaisons représentatives + variantes de poids.
drafts = []
for obj in ("preserver", "equilibre", "croissance"):
    for hz in ("court", "moyen", "long"):
        for tol in ("faible", "moderee", "elevee"):
            drafts.append({"objectif": obj, "horizon": hz, "tolerance": tol,
                           "preferences": ["esg", "technologies", "stabilite", "diversification"][: (len(drafts) % 5)],
                           "exclusions": ["crypto", "speculatif", "controverses"][: (len(drafts) % 4)]})
created = []
for d in drafts:
    pw = post("/profiles", d); walk(pw, "profile"); created.append(pw["profile_id"])
for p in pids:
    pw = post("/profiles", {"base_persona": p, "objectif": "equilibre", "horizon": "moyen", "tolerance": "moderee",
                            "preferences": [], "exclusions": [], "weights_override": {"croissance": 0.5}})
    walk(pw, "profile"); created.append(pw["profile_id"])

assets = get("/assets"); walk(assets, "assets")
tickers = [a["ticker"] for a in assets]

requests_ = [(p, None) for p in pids + created[:6] + created[-3:]] + [(p, t) for p in pids for t in tickers]
run_ids = []
for p, t in requests_:
    body = {"profile_id": p, **({"requested_ticker": t} if t else {})}
    run_ids.append(post("/runs", body)["run_id"])
print("runs lancés", len(run_ids), flush=True)

def wait(rid):
    for _ in range(600):
        s = get(f"/runs/{rid}")
        if s["status"] != "en_cours":
            return s
        time.sleep(1)
    raise RuntimeError(rid)

results = {}
for i, rid in enumerate(run_ids):
    results[rid] = wait(rid)
    if i % 10 == 0:
        print("terminé", i, rid, results[rid]["status"], flush=True)

all_ev = {}
for rid, s in results.items():
    walk(s, "run")
    walk(get(f"/runs/{rid}/trace"), "trace")
    acc = set(); ev_ids(s, acc); all_ev[rid] = acc

# Fiches, graphes, cours dans le contexte d'un run par profil de base.
for p in pids:
    rid = f"run_2026-11-12_{p}"
    for t in tickers:
        sheet = get(f"/assets/{t}?profile_id={p}&run_id={rid}"); walk(sheet, "sheet")
        g = get(f"/assets/{t}/graph?run_id={rid}"); walk(g, "graph")
        try:
            pr = get(f"/assets/{t}/prices?run_id={rid}")
        except Exception:
            pr = {}
        acc = set(); ev_ids(sheet, acc); ev_ids(g, acc); ev_ids(pr, acc)
        all_ev.setdefault(rid, set()).update(acc)
    walk(get(f"/data?run_id={rid}"), "data")
walk(get("/data"), "data")

def fetch_ev(args):
    rid, eid = args
    try:
        return get(f"/evidence/{eid}?run_id={rid}")
    except Exception as e:
        return None

jobs = [(rid, eid) for rid, ids in all_ev.items() for eid in ids]
print("preuves", len(jobs), flush=True)
with ThreadPoolExecutor(8) as ex:
    for ev in ex.map(fetch_ev, jobs):
        if ev:
            walk(ev, "evidence")
            # le nom de la source est sous source.name : SKIP_KEYS saute « source » ; on le reprend
            src = ev.get("source") or {}
            if isinstance(src, dict) and src.get("name"):
                strings.setdefault(src["name"], set()).add("evidence.source.name")

out = [{"text": k, "paths": sorted(v)} for k, v in sorted(strings.items())]
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("chaînes uniques", len(out))
