"""Vérificateur de fidélité : nombres, citations, dates, formulations, claim_kind.

Conception : docs/05_EXPLICABILITE.md (section 4)
Contrôles appliqués à chaque affirmation (`Claim`) avant affichage :
1. chaque nombre du texte correspond à la valeur d'une preuve citée (tolérance : l'arrondi au
   nombre de décimales écrit dans le texte) ou figure dans l'énoncé de cette preuve
   (« pire période glissante de 3 ans », « année 2022 ») ;
2. l'affirmation cite au moins une preuve, et toutes les preuves citées existent dans le run ;
3. aucune preuve citée n'a `published_at > as_of` ;
4. aucune formulation prescriptive (`explain/wording.py`) ;
5. le `claim_kind` affiché est celui des preuves : SCENARIO l'emporte sur HYPOTHESE, qui
   l'emporte sur FAIT. Un écart est corrigé par le code (et compté), pas supprimé.

Aucun chiffre n'est écrit par un modèle : un agent écrit `{EV-000123}` là où il veut citer une
valeur, et `render_text` y insère la valeur du registre, formatée. Le contrôle 1 reste appliqué
au texte final : un modèle qui écrirait quand même un nombre non étayé voit sa phrase retirée.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable, Optional, Sequence

from pydantic import BaseModel, ConfigDict

from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.explain.wording import find_forbidden
from easytrade.schemas.debate import Claim
from easytrade.schemas.evidence import Evidence
from easytrade.schemas.explanation import Explanation

PLACEHOLDER = re.compile(r"\{\s*(EV-\d+)\s*\}")
EVIDENCE_ID = re.compile(r"EV-\d+")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
NUMBER = re.compile(r"(?<![A-Za-zÀ-ÿ_\d.,])\d+(?:[.,]\d+)?(?![A-Za-zÀ-ÿ_\d])")

# Codes d'écart
NO_EVIDENCE = "sans_preuve"
UNKNOWN_EVIDENCE = "preuve_inconnue"
OUTSIDE_PACK = "preuve_hors_dossier"
FUTURE_EVIDENCE = "preuve_future"
UNSUPPORTED_NUMBER = "nombre_non_etaye"
FORBIDDEN_WORDING = "formulation"

_KIND_RANK = {"FAIT": 0, "HYPOTHESE": 1, "SCENARIO": 2}


# --- mise en forme des valeurs ----------------------------------------------------------------
def _fr(number: float, decimals: int) -> str:
    return f"{number:.{decimals}f}".replace(".", ",")


def format_value(evidence: Evidence) -> Optional[str]:
    """Valeur d'une preuve telle qu'elle est écrite dans un texte ; None si la preuve n'a pas de valeur."""
    if evidence.value is None:
        return None
    value, unit = float(evidence.value), (evidence.unit or "")
    if unit == "%":
        return f"{_fr(value, 1)} %"
    if unit == "ratio":
        return _fr(value, 2)
    text = str(int(value)) if value == int(value) else _fr(value, 1)
    return f"{text} {unit}".strip()


def render_text(text: str, ledger: EvidenceLedger) -> tuple[str, tuple[str, ...]]:
    """Remplace chaque `{EV-…}` par la valeur de la preuve. Retourne (texte, preuves insérées).

    Un marqueur dont la preuve est inconnue ou sans valeur est laissé tel quel : le contrôle
    le signalera (`preuve_inconnue`).
    """
    used: list[str] = []

    def substitute(match: re.Match) -> str:
        evidence_id = match.group(1)
        if evidence_id not in ledger:
            return match.group(0)
        formatted = format_value(ledger.get(evidence_id))
        if formatted is None:
            return match.group(0)
        used.append(evidence_id)
        return formatted

    return PLACEHOLDER.sub(substitute, text), tuple(dict.fromkeys(used))


# --- nombres ----------------------------------------------------------------------------------
def extract_numbers(text: str, ignore: Iterable[str] = ()) -> list[str]:
    """Nombres écrits dans un texte, hors identifiants de preuve, dates ISO et termes ignorés
    (noms d'actifs comme « S&P 500 », tickers)."""
    cleaned = text.replace("\u00a0", " ").replace("\u202f", " ")
    for phrase in sorted((p for p in ignore if p), key=len, reverse=True):
        cleaned = cleaned.replace(phrase, " ")
    cleaned = PLACEHOLDER.sub(" ", cleaned)
    cleaned = EVIDENCE_ID.sub(" ", cleaned)
    cleaned = ISO_DATE.sub(" ", cleaned)
    return NUMBER.findall(cleaned)


def _reference_numbers(evidence: Evidence) -> set[float]:
    """Nombres portés par l'énoncé et la fenêtre d'une preuve (durée, année, nombre d'observations)."""
    numbers = {float(token.replace(",", ".")) for token in extract_numbers(evidence.statement)}
    window = evidence.window
    if window.observations is not None:
        numbers.add(float(window.observations))
    for day in (window.start, window.end, evidence.observed_at):
        if day is not None:
            numbers.add(float(day.year))
    return numbers


def number_supported(token: str, evidences: Sequence[Evidence]) -> bool:
    decimals = len(token.split(",")[-1].split(".")[-1]) if ("," in token or "." in token) else 0
    number = float(token.replace(",", "."))
    tolerance = 0.5 * 10 ** (-decimals) + 1e-9
    for evidence in evidences:
        if evidence.value is not None and abs(abs(float(evidence.value)) - number) <= tolerance:
            return True
        if number in _reference_numbers(evidence):
            return True
    return False


# --- contrôle d'une affirmation ---------------------------------------------------------------
class ClaimCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: Claim                      # texte rendu, preuves dédoublonnées, claim_kind corrigé
    issues: tuple[str, ...] = ()      # codes d'écart ; vide = affirmation fidèle
    details: tuple[str, ...] = ()
    kind_corrected: bool = False

    @property
    def ok(self) -> bool:
        return not self.issues


def expected_kind(evidences: Sequence[Evidence]) -> str:
    if not evidences:
        return "FAIT"
    return max((e.claim_kind for e in evidences), key=_KIND_RANK.__getitem__)


def check_claim(
    claim: Claim,
    ledger: EvidenceLedger,
    as_of: date,
    forbidden: Iterable[str] = (),
    *,
    ignore: Iterable[str] = (),
    allowed_ids: Optional[Iterable[str]] = None,
) -> ClaimCheck:
    """Rend le texte, puis applique les cinq contrôles."""
    text, inserted = render_text(claim.text.strip(), ledger)
    cited = tuple(dict.fromkeys((*claim.evidence_ids, *inserted)))
    issues: list[str] = []
    details: list[str] = []

    def flag(code: str, detail: str) -> None:
        if code not in issues:
            issues.append(code)
        details.append(detail)

    for marker in PLACEHOLDER.findall(text):
        flag(UNKNOWN_EVIDENCE, f"marqueur {{{marker}}} sans valeur dans le registre")
    known = [ledger.get(i) for i in cited if i in ledger]
    for evidence_id in cited:
        if evidence_id not in ledger:
            flag(UNKNOWN_EVIDENCE, f"{evidence_id} absent du registre du run")
    if allowed_ids is not None:
        allowed = set(allowed_ids)
        for evidence_id in cited:
            if evidence_id in ledger and evidence_id not in allowed:
                flag(OUTSIDE_PACK, f"{evidence_id} hors du dossier de preuves fourni")
    if not cited:
        flag(NO_EVIDENCE, "aucune preuve citée")
    for evidence in known:
        if evidence.published_at > as_of:
            flag(FUTURE_EVIDENCE, f"{evidence.evidence_id} publiée le {evidence.published_at}")
    for token in extract_numbers(text, ignore):
        if not number_supported(token, known):
            flag(UNSUPPORTED_NUMBER, f"« {token} » ne correspond à aucune preuve citée")
    for term in find_forbidden(text, forbidden):
        flag(FORBIDDEN_WORDING, f"formulation refusée : « {term} »")

    kind = expected_kind(known) if known else claim.claim_kind
    return ClaimCheck(
        claim=Claim(text=text, evidence_ids=cited, claim_kind=kind),
        issues=tuple(issues),
        details=tuple(details),
        kind_corrected=bool(known) and kind != claim.claim_kind,
    )


def text_is_supported(text: str, evidences: Sequence[Evidence], forbidden: Iterable[str] = (),
                      ignore: Iterable[str] = ()) -> bool:
    """Chaîne libre (question ouverte) : aucune formulation refusée, aucun nombre non étayé."""
    if find_forbidden(text, forbidden):
        return False
    return all(number_supported(token, evidences) for token in extract_numbers(text, ignore))


# --- rapport ----------------------------------------------------------------------------------
class FidelityIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    where: str
    text: str
    codes: tuple[str, ...]
    details: tuple[str, ...] = ()


class FidelityReport(BaseModel):
    """Résultat du contrôle des affirmations rédigées par l'agent d'explication.

    `first_pass_*` : avant toute relance (indicateur présenté au jury, scénario S6).
    `removed` : affirmations retirées après la relance. `final_issues` : écarts restant dans la
    sortie affichée (doit être vide).
    """

    model_config = ConfigDict(frozen=True)

    first_pass_checked: int = 0
    first_pass_ok: int = 0
    retried: bool = False
    removed: int = 0
    kind_corrected: int = 0
    fallbacks: int = 0                # pistes dont l'explication a été recomposée par le code
    final_checked: int = 0
    issues: tuple[FidelityIssue, ...] = ()
    final_issues: tuple[FidelityIssue, ...] = ()

    @property
    def first_pass_rate(self) -> Optional[float]:
        return None if not self.first_pass_checked else self.first_pass_ok / self.first_pass_checked

    @property
    def faithful(self) -> bool:
        return not self.final_issues


def explanation_claims(explanation: Explanation) -> list[tuple[str, Claim]]:
    """Toutes les affirmations sourcées d'une `Explanation`, avec leur emplacement."""
    claims: list[tuple[str, Claim]] = []
    for item in explanation.items:
        for index, claim in enumerate(item.why):
            claims.append((f"items.{item.ticker}.why[{index}]", claim))
        for position in item.debate:
            for index, claim in enumerate(position.arguments):
                claims.append((f"items.{item.ticker}.debate.{position.agent}[{index}]", claim))
    for rejected in explanation.rejected:
        if rejected.kind == "preuves" and not rejected.evidence_ids:
            continue  # écarté faute de données : il n'existe, par définition, aucune preuve à citer
        claims.append((f"rejected.{rejected.ticker}",
                       Claim(text=rejected.reason, evidence_ids=rejected.evidence_ids, claim_kind="HYPOTHESE")))
    if explanation.coherence is not None:
        coherence = explanation.coherence
        for index, claim in enumerate(coherence.tensions):
            claims.append((f"coherence.tensions[{index}]", claim))
        for index, claim in enumerate(coherence.context):
            claims.append((f"coherence.context[{index}]", claim))
        for alternative in coherence.alternatives:
            claims.append((f"coherence.alternatives.{alternative.ticker}", alternative.why))
    return claims


def verify_explanation(
    explanation: Explanation,
    ledger: EvidenceLedger,
    forbidden: Iterable[str] = (),
    *,
    ignore: Iterable[str] = (),
) -> tuple[int, tuple[FidelityIssue, ...]]:
    """Contrôle indépendant de la sortie affichée : (affirmations contrôlées, écarts).

    Rejoue les cinq contrôles sur chaque affirmation, vérifie le `claim_kind` affiché, puis
    cherche les formulations refusées dans toutes les chaînes de la sortie.
    """
    from easytrade.explain.wording import scan

    forbidden = tuple(forbidden)
    issues: list[FidelityIssue] = []
    claims = explanation_claims(explanation)
    for where, claim in claims:
        check = check_claim(claim, ledger, explanation.as_of, forbidden, ignore=ignore)
        codes, details = list(check.issues), list(check.details)
        if check.kind_corrected and not where.startswith("rejected."):
            codes.append("claim_kind")
            details.append(f"affiché {claim.claim_kind}, attendu {check.claim.claim_kind}")
        if codes:
            issues.append(FidelityIssue(where=where, text=claim.text, codes=tuple(codes), details=tuple(details)))
    for term, text in scan(explanation.model_dump(mode="json"), forbidden):
        issues.append(FidelityIssue(where="texte", text=text, codes=(FORBIDDEN_WORDING,),
                                    details=(f"formulation refusée : « {term} »",)))
    return len(claims), tuple(issues)
