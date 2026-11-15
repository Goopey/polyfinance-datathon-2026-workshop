"""Agents simulés : réponses écrites par des règles Python, sans aucun modèle de langage.

Conception : docs/10_PLAN.md (risque « accès AWS tardif »), docs/06_AWS.md
Sert à exécuter et tester le pipeline complet en local tant que Bedrock n'est pas disponible.
Chaque fonction reçoit exactement la charge utile (`payload`) qu'un modèle recevrait et renvoie
la même forme de sortie : les garde-fous du code (schéma, preuves, fidélité) s'appliquent donc
de la même façon. Les résultats sont déterministes.

Ce ne sont **pas** des modèles : la trace porte `model_id = simule-local-v1` et l'explication
le signale dans « ce que nous ne savons pas ». Les règles ci-dessous sont volontairement
simples ; elles ne remplacent pas le jugement d'un modèle, elles tiennent sa place.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from easytrade.agents.llm_client import FakeLLMClient
from easytrade.engine.signals import THEMES, asset_themes

MODEL_ID = "simule-local-v1"
NOTE = "Débat et rédaction produits par des agents simulés par des règles : aucun modèle de langage n'a été appelé."

_NEGATIVE = ("peu intéress", "pas intéress", "éviter", "exclure", "sans ")
_THEME_KEYWORDS = {
    "technologies": ("technolog", "intelligence artificielle"),
    "cryptoactifs": ("crypto", "spéculatif"),
    "esg": ("esg",),
    "entreprises_etablies": ("établies",),
    "obligations": ("obligation",),
}


def _ref(evidence_id: str) -> str:
    return "{" + evidence_id + "}"


# --- 1. pondération du profil ---------------------------------------------------------------
def profile_weighting(payload: Mapping[str, Any]) -> dict:
    preferred: list[str] = []
    avoided: list[str] = []
    rationale: list[dict] = []

    def because(field: str, text: str, evidence_id: str) -> None:
        rationale.append({"field": field, "because": text, "evidence_ids": [evidence_id]})

    for fact in payload["facts"]:
        text, evidence_id = fact["text"].casefold(), fact["evidence_id"]
        if fact["kind"] == "objectif":
            if "croître" in text or "croissance" in text:
                because("weights.croissance", "L'objectif déclaré mentionne la croissance du capital.", evidence_id)
            if "préserver" in text:
                because("weights.stabilite", "L'objectif déclaré est d'abord de préserver le capital.", evidence_id)
            continue
        if fact["kind"] != "preference":
            continue
        if "diversif" in text:
            because("hard_constraints.max_weight_per_sector",
                    "Le profil souhaite garder une diversification et ne pas miser sur un seul secteur.", evidence_id)
            because("weights.diversification",
                    "Le profil souhaite garder une diversification et ne pas miser sur un seul secteur.", evidence_id)
            continue
        negative = any(marker in text for marker in _NEGATIVE)
        for theme, keywords in _THEME_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                (avoided if negative else preferred).append(theme)
                if theme == "cryptoactifs":
                    because("hard_constraints.max_weight_crypto",
                            "Le profil déclare peu d'intérêt pour ce type de placement." if negative
                            else "Le profil déclare un intérêt pour les cryptoactifs, dans une part limitée.",
                            evidence_id)
                if theme == "esg" and not negative:
                    because("weights.esg", "Le profil accorde une grande importance aux facteurs ESG.", evidence_id)
        if "controverse" in text:
            because("hard_constraints.esg_exclusion",
                    "Le profil souhaite éviter les entreprises liées à des controverses importantes.", evidence_id)
        if "stabilité" in text:
            because("weights.stabilite", "Le profil déclare accorder de l'importance à la stabilité.", evidence_id)
        if "qualité" in text:
            because("weights.qualite", "Le profil déclare accorder de l'importance à la qualité des entreprises.",
                    evidence_id)
    return {
        "weights": dict(payload["template"]["weights"]),
        "constraints": {},
        "preferred_themes": list(dict.fromkeys(preferred)),
        "avoided_themes": list(dict.fromkeys(avoided)),
        "rationale": rationale,
        "missing_information": [],
    }


# --- 2. recherche ---------------------------------------------------------------------------
def research(payload: Mapping[str, Any]) -> dict:
    profile = payload["profile"]
    preferred = set(profile["preferred_themes"])
    wants_esg = profile["weights"].get("esg", 0.0) >= 0.15 or profile["hard_constraints"].get("esg_exclusion")
    candidates: list[dict] = []
    requests: list[dict] = []
    for asset in payload["universe"][: payload["max_candidates"]]:
        ticker = asset["ticker"]
        liked = [t for t in asset_themes(asset["asset_class"], asset["sector"]) if t in preferred]
        if liked:
            reason = f"Se rattache au thème « {THEMES[liked[0]]['label']} » déclaré dans le profil."
        else:
            reason = f"Élargit la comparaison à un autre secteur ({asset['sector']})."
        candidates.append({"ticker": ticker, "reason": reason})
        if wants_esg:
            requests.append({"tool": "preuves_esg", "ticker": ticker})
        if asset["asset_class"] == "equity":
            requests.append({"tool": "relations", "ticker": ticker})
    if payload.get("requested_ticker"):
        requests.append({"tool": "chercher_documents", "ticker": payload["requested_ticker"]})
        requests.append({"tool": "preuves_esg", "ticker": payload["requested_ticker"]})
    return {"candidates": candidates, "tool_requests": requests}


# --- 3. débat -------------------------------------------------------------------------------
def _by_role(payload: Mapping[str, Any]) -> dict[str, tuple[str, Optional[float]]]:
    return {e["role"]: (e["evidence_id"], e["value"]) for e in payload["evidence"]}


def _facts(payload: Mapping[str, Any]) -> dict[str, Any]:
    roles = _by_role(payload)

    def get(role: str) -> tuple[Optional[str], Optional[float]]:
        return roles.get(role, (None, None))

    facts = {name: get(role) for name, role in {
        "ret": "annualized_return:full", "vol": "annualized_volatility:full", "dd": "max_drawdown:full",
        "w1": "worst_rolling_1y:full", "w3": "worst_rolling_3y:full", "y2022": "return_2022:2022",
        "lim_vol": "repere:volatilite", "lim_dd": "repere:perte_max", "pref": "signal:preferences",
        "cash": "macro:taux_directeur_moyen",
    }.items()}
    vol, lim_vol = facts["vol"][1], facts["lim_vol"][1]
    dd, lim_dd = facts["dd"][1], facts["lim_dd"][1]
    facts["over_vol"] = vol is not None and lim_vol is not None and vol > lim_vol
    facts["over_dd"] = dd is not None and lim_dd is not None and dd < lim_dd
    ret, cash = facts["ret"][1], facts["cash"][1]
    # Rendement inférieur au placement sans risque (taux directeur moyen sur la même période).
    facts["below_cash"] = ret is not None and cash is not None and ret <= cash
    facts["types"] = {e["type"] for e in payload["evidence"]}
    return facts


def _argument(text: str, *evidence_ids: Optional[str]) -> dict:
    return {"text": text, "evidence_ids": [i for i in evidence_ids if i], "claim_kind": "FAIT"}


def _round3(payload: Mapping[str, Any]) -> Optional[dict]:
    """Tour 3 : l'agent simulé maintient sa position du tour 1 et garde ses deux premiers arguments."""
    own = payload.get("own_round1")
    if payload.get("round") != 3 or own is None:
        return None
    return {**own, "arguments": own["arguments"][:2]}


def debate_bull(payload: Mapping[str, Any]) -> dict:
    final = _round3(payload)
    if final is not None:
        return final
    f = _facts(payload)
    arguments: list[dict] = []
    ret_id, ret = f["ret"]
    cash_id = f["cash"][0]
    if ret is not None and ret > 0 and not f["below_cash"]:
        if cash_id:
            arguments.append(_argument(
                f"Rendement annualisé observé de {_ref(ret_id)} sur toute la période disponible, au-dessus du "
                f"taux directeur moyen de la Banque du Canada ({_ref(cash_id)}) sur la période.", ret_id, cash_id))
        else:
            arguments.append(_argument(f"Rendement annualisé observé de {_ref(ret_id)} sur toute la période disponible.", ret_id))
    elif ret is not None and ret > 0 and cash_id:
        arguments.append(_argument(
            f"Rendement annualisé observé de {_ref(ret_id)}, positif mais sous le taux directeur moyen de la "
            f"Banque du Canada ({_ref(cash_id)}) sur la même période.", ret_id, cash_id))
    w3_id, w3 = f["w3"]
    if w3 is not None and w3 > 0:
        arguments.append(_argument(
            f"Sur la période observée, la pire période glissante de 3 ans est restée positive ({_ref(w3_id)}).", w3_id))
    pref_id, pref = f["pref"]
    if pref is not None and pref > 0:
        arguments.append(_argument("Se rattache à un thème d'intérêt déclaré dans le profil.", pref_id))
    vol_id, vol = f["vol"]
    if vol is not None and not f["over_vol"] and f["lim_vol"][0]:
        arguments.append(_argument(
            f"Volatilité annualisée de {_ref(vol_id)}, sous le repère de {_ref(f['lim_vol'][0])} retenu pour ce profil.",
            vol_id, f["lim_vol"][0]))
    # Le Bull plaide pour l'actif, mais n'appuie sans réserve que si le rendement a battu le placement sans risque.
    stance = "appui" if ret is not None and ret > 0 and not f["below_cash"] else "appui_reserve"
    return {"stance": stance, "confidence": "moyenne", "arguments": arguments, "open_questions": []}


def debate_bear(payload: Mapping[str, Any]) -> dict:
    final = _round3(payload)
    if final is not None:
        return final
    f = _facts(payload)
    arguments: list[dict] = []
    vol_id, dd_id = f["vol"][0], f["dd"][0]
    if f["over_vol"]:
        arguments.append(_argument(
            f"Volatilité annualisée de {_ref(vol_id)}, au-dessus du repère de {_ref(f['lim_vol'][0])} retenu pour ce profil.",
            vol_id, f["lim_vol"][0]))
    if f["over_dd"]:
        arguments.append(_argument(
            f"Perte maximale observée de {_ref(dd_id)}, au-delà du repère de {_ref(f['lim_dd'][0])} retenu pour ce profil.",
            dd_id, f["lim_dd"][0]))
    y_id, y2022 = f["y2022"]
    if y2022 is not None and y2022 < 0:
        arguments.append(_argument(f"Rendement négatif sur l'année 2022 : {_ref(y_id)}.", y_id))
    ret_id, ret = f["ret"]
    if ret is not None and ret <= 0:
        arguments.append(_argument(f"Rendement annualisé observé de {_ref(ret_id)} sur toute la période disponible.", ret_id))
    if not arguments and f["dd"][1] is not None:
        arguments.append(_argument(f"Perte maximale observée de {_ref(dd_id)} sur la période disponible.", dd_id))
    questions = []
    if "esg" not in f["types"]:
        questions.append("Aucune preuve ESG datée n'est disponible pour ce titre.")
    if "filing" not in f["types"]:
        questions.append("Aucun document réglementaire n'a été consulté pour ce titre.")
    if f["over_vol"] or f["over_dd"]:
        stance = "opposition"
    elif (y2022 is not None and y2022 < 0) or (ret is not None and ret <= 0):
        stance = "appui_reserve"
    else:
        stance = "appui"
    return {"stance": stance, "confidence": "moyenne", "arguments": arguments, "open_questions": questions}


def debate_realist(payload: Mapping[str, Any]) -> dict:
    final = _round3(payload)
    if final is not None:
        return final
    f = _facts(payload)
    arguments: list[dict] = []
    (ret_id, ret), (vol_id, vol), (dd_id, dd) = f["ret"], f["vol"], f["dd"]
    if ret is not None and vol is not None:
        arguments.append(_argument(
            f"Rendement annualisé observé de {_ref(ret_id)} pour une volatilité annualisée de {_ref(vol_id)} "
            "sur la même période.", ret_id, vol_id))
    exceeded = int(f["over_vol"]) + int(f["over_dd"])
    if f["below_cash"] and f["cash"][0] and ret is not None:
        arguments.append(_argument(
            f"Sur la période, le rendement annualisé ({_ref(ret_id)}) n'a pas dépassé le taux directeur moyen de la "
            f"Banque du Canada ({_ref(f['cash'][0])}) : le risque pris n'a pas été rémunéré.", ret_id, f["cash"][0]))
    if f["over_dd"]:
        arguments.append(_argument(
            f"La perte maximale observée ({_ref(dd_id)}) dépasse le repère de {_ref(f['lim_dd'][0])} du profil.",
            dd_id, f["lim_dd"][0]))
    elif f["over_vol"]:
        arguments.append(_argument(
            f"La volatilité annualisée ({_ref(vol_id)}) dépasse le repère de {_ref(f['lim_vol'][0])} du profil.",
            vol_id, f["lim_vol"][0]))
    if exceeded == 2 and ret is not None and ret <= 0:
        stance = "opposition"
    elif exceeded or f["below_cash"]:
        stance = "appui_reserve"
    else:
        stance = "appui"
    return {"stance": stance, "confidence": "moyenne", "arguments": arguments, "open_questions": []}


# --- 5. explication -------------------------------------------------------------------------
_WHY = {
    "croissance": "Rendement annualisé observé de {v} sur toute la période disponible.",
    "stabilite": "Volatilité annualisée observée de {v}, un repère pour le critère de stabilité de votre profil.",
    "horizon": "Pire période glissante de {window} observée sur la période : {v}.",
    "diversification": "Corrélation moyenne de {v} avec les autres actifs analysés, un repère pour la diversification.",
    "preferences": "Se rattache à un thème d'intérêt déclaré dans votre profil.",
}


def explanation(payload: Mapping[str, Any]) -> dict:
    items = []
    for item in payload["items"]:
        why = []
        for top in item["top_criteria"]:
            template = _WHY.get(top["criterion"])
            if template:
                text = template.replace("{v}", _ref(top["evidence_id"])).replace("{window}", top.get("window", "3 ans"))
                why.append(_argument(text, top["evidence_id"]))
        items.append({"ticker": item["ticker"], "why": why})
    notes = []
    coherence = payload.get("coherence")
    if coherence:
        roles = {e["role"]: e["evidence_id"] for e in coherence["evidence"]}
        drawdown = roles.get("max_drawdown:full")
        horizon = next((f["evidence_id"] for f in payload["profile"]["facts"] if f["kind"] == "horizon"), None)
        if drawdown:
            notes.append(_argument(
                f"Sur la période observée, ce titre a connu une perte maximale de {_ref(drawdown)}. "
                "Plus l'horizon de placement est court, moins il reste de temps pour traverser un tel recul.",
                drawdown, horizon))
    return {"items": items, "coherence_notes": notes}


def simulated_client() -> FakeLLMClient:
    """Client servi par les agents simulés ci-dessus (aucun appel réseau, résultat déterministe)."""
    return FakeLLMClient(
        responders={
            "profile_weighting": profile_weighting,
            "research": research,
            "debate.bull": debate_bull,
            "debate.realist": debate_realist,
            "debate.bear": debate_bear,
            "explanation": explanation,
        },
        name=MODEL_ID,
    )
