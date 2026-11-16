"""Traduction anglaise des textes d'une analyse rédigés par les modèles (étape finale, après l'explication).

Conception : prompts/translation.md, mobile/src/i18n/translate.ts
Pourquoi : le backend rédige en français. L'application traduit les textes produits par le code avec des
règles (gabarits connus), mais le texte libre des modèles (raisons, arguments du débat, motifs du profil)
ne peut pas être prévu par des règles : sans cette étape, il resterait en français en mode anglais.

Fonctionnement : les phrases distinctes du résultat sont numérotées et envoyées au modèle rapide par lots
(en parallèle) ; il rend pour chaque numéro une version anglaise. Le numéro évite au modèle de recopier la
phrase française, qu'il pourrait altérer (espaces insécables, guillemets). Le code n'accepte une traduction que si :
- le numéro fait bien partie du lot (aucun texte inventé) ;
- les nombres sont identiques des deux côtés (au format anglais près) : un chiffre modifié ferait mentir
  le vérificateur de fidélité, la phrase reste alors en français.
Le résultat est une table `français → anglais` jointe au résultat ; l'application la consulte quand ses
règles ne couvrent pas une phrase. Un échec de traduction n'arrête jamais l'analyse.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from pydantic import BaseModel, Field

from easytrade.agents.llm_client import TIER_FAST, CallInfo, FakeLLMClient, LLMClient, load_prompt, structured_call
from easytrade.schemas.explanation import Explanation

STEP = "translation"
CHUNK = 40    # phrases par appel : sortie bornée, relance peu coûteuse
WORKERS = 3   # lots traduits en parallèle (comme les agents du débat)

_EN_NUMBER = re.compile(r"[-−+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-−+]?\d+(?:\.\d+)?")
_FR_NUMBER = re.compile(r"[-−+]?\d{1,3}(?:[   ]\d{3})+(?:,\d+)?|[-−+]?\d+(?:,\d+)?")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_EVIDENCE_ID = re.compile(r"EV-\d+")


class TranslatedText(BaseModel):
    id: int
    en: str


class TranslationDraft(BaseModel):
    items: list[TranslatedText] = Field(default_factory=list)


def _cleaned(text: str, ignore: Iterable[str]) -> str:
    """Sans noms d'actifs (« S&P 500 »), symboles, dates ISO ni identifiants de preuve."""
    for phrase in sorted((p for p in ignore if p), key=len, reverse=True):
        text = text.replace(phrase, " ")
    return _EVIDENCE_ID.sub(" ", _ISO_DATE.sub(" ", text))


def _fr_values(text: str, ignore: Iterable[str]) -> list[float]:
    """Nombres au format français, séparateur de milliers compris (« 1 234,5 »)."""
    return sorted(round(float(re.sub(r"[   ]", "", m).replace(",", ".").replace("−", "-")), 6)
                  for m in _FR_NUMBER.findall(_cleaned(text, ignore)))


def _en_values(text: str, ignore: Iterable[str]) -> list[float]:
    return sorted(round(float(m.replace(",", "").replace("−", "-")), 6)
                  for m in _EN_NUMBER.findall(_cleaned(text, ignore)))


def same_numbers(fr: str, en: str, ignore: Iterable[str] = ()) -> bool:
    """Mêmes nombres des deux côtés (format français « 13,1 » contre anglais « 13.1 »), signes compris."""
    ignore = tuple(ignore)
    return [abs(v) for v in _fr_values(fr, ignore)] == sorted(abs(v) for v in _en_values(en, ignore))


def enabled_for(client: LLMClient) -> bool:
    """Vrai modèle seulement : les gabarits des agents simulés (et des faux clients de test) sont
    traduits par les règles de l'application."""
    from easytrade.agents import simulated  # import tardif : simulated dépend des schémas des agents

    return client.model_id("strong") != simulated.MODEL_ID and not isinstance(client, FakeLLMClient)


def explanation_texts(explanation: Explanation) -> list[str]:
    """Toutes les phrases affichées du résultat, sans doublon, dans l'ordre de l'écran."""
    texts: list[str] = [explanation.headline, *explanation.missing, *explanation.warnings, *explanation.unknowns]
    for item in explanation.items:
        texts.extend(claim.text for claim in item.why)
        texts.extend(item.risks)
        texts.extend(item.limits)
        texts.extend(item.unknowns)
        summary = item.debate_summary
        texts.extend((summary.bull, summary.realist, summary.bear))
        for position in item.debate:
            texts.extend(claim.text for claim in position.arguments)
            texts.extend(position.open_questions)
    texts.extend(rejected.reason for rejected in explanation.rejected)
    coherence = explanation.coherence
    if coherence is not None:
        texts.extend(claim.text for claim in (*coherence.tensions, *coherence.context))
        texts.extend(alternative.why.text for alternative in coherence.alternatives)
    return list(dict.fromkeys(t.strip() for t in texts if t and t.strip()))


def translate(texts: Iterable[str], client: LLMClient, *,
              ignore: Iterable[str] = ()) -> tuple[dict[str, str], list[CallInfo], int]:
    """Traduit par lots. Rend (table français → anglais, appels, nombre de traductions refusées)."""
    texts = list(dict.fromkeys(t for t in texts if t))
    ignore = tuple(ignore)
    prompt = load_prompt(STEP)
    batches = [texts[start:start + CHUNK] for start in range(0, len(texts), CHUNK)]

    def call(batch: list[str]):
        payload = {"texts": [{"id": i, "text": text} for i, text in enumerate(batch)]}
        return structured_call(client, step=STEP, prompt=prompt, payload=payload, schema=TranslationDraft,
                               tier=TIER_FAST)

    with ThreadPoolExecutor(max_workers=max(1, min(WORKERS, len(batches)))) as pool:
        answers = list(pool.map(call, batches))  # un lot en échec (après relance) fait échouer l'étape

    table: dict[str, str] = {}
    infos: list[CallInfo] = []
    refused = 0
    for batch, (draft, info) in zip(batches, answers):
        infos.append(info)
        for pair in draft.items:
            if not 0 <= pair.id < len(batch) or batch[pair.id] in table:
                continue  # numéro inconnu ou déjà traduit : ignoré
            source, target = batch[pair.id], pair.en.strip()
            if target and same_numbers(source, target, ignore):
                table[source] = target
            else:
                refused += 1
    return table, infos, refused
