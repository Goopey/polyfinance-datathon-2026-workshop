"""Interface unique vers le modèle (Bedrock). Sortie structurée validée ; une relance ; faux client pour les tests.

Conception : docs/06_AWS.md, docs/02_AGENTS.md (règles communes)
- Tous les agents passent par `structured_call` : la sortie est un JSON validé par un schéma
  Pydantic. Une sortie invalide est relancée **une fois** avec le motif du rejet, puis l'étape
  échoue proprement (`LLMOutputError`).
- `BedrockClient` : API Converse d'Amazon Bedrock, sortie structurée par appel d'outil forcé.
  `boto3` n'est importé qu'à l'utilisation : le reste du dépôt fonctionne sans AWS.
- `FakeLLMClient` : réponses fournies par des fonctions Python, pour les tests et pour le
  pipeline local sans modèle (`agents/simulated.py`).
On enregistre les actions observables (étape, modèle, version du prompt, nombre d'appels),
jamais le raisonnement interne du modèle.
"""
from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
TIER_FAST = "fast"      # tours de débat
TIER_STRONG = "strong"  # profil, recherche, explication
MAX_ATTEMPTS = 2        # un appel + une relance

T = TypeVar("T", bound=BaseModel)


class LLMOutputError(RuntimeError):
    """Sortie de modèle invalide après la relance : l'étape échoue, visible dans la trace."""


class LLMUnavailableError(RuntimeError):
    """Le modèle n'est pas configuré ou pas joignable (identifiants, région, modèle)."""


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str

    @property
    def tag(self) -> str:
        return f"{self.name}@{self.version}"


def load_prompt(name: str) -> Prompt:
    """Lit `agents/prompts/<name>.md`. La version est la ligne « Version : vN »."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    match = re.search(r"^Version\s*:\s*(v\d+)", text, flags=re.MULTILINE)
    return Prompt(name=name, version=match.group(1) if match else "v0", text=text)


@dataclass(frozen=True)
class CallInfo:
    """Ce que la trace retient d'un appel : aucune donnée de raisonnement."""

    step: str
    model_id: str
    prompt_version: str
    attempts: int


class LLMClient(Protocol):
    def model_id(self, tier: str) -> str: ...

    def invoke(self, *, step: str, system: str, payload: Mapping[str, Any], schema: Type[BaseModel],
               tier: str, feedback: Optional[str] = None) -> Any:
        """Renvoie la sortie brute du modèle : un objet JSON (dict) ou sa forme texte."""
        ...


def _parse(raw: Any, schema: Type[T]) -> T:
    if isinstance(raw, BaseModel):
        raw = raw.model_dump(mode="json")
    if isinstance(raw, (str, bytes)):
        raw = json.loads(raw)
    return schema.model_validate(raw)


def structured_call(
    client: LLMClient,
    *,
    step: str,
    prompt: Prompt,
    payload: Mapping[str, Any],
    schema: Type[T],
    tier: str = TIER_FAST,
) -> tuple[T, CallInfo]:
    """Appelle le modèle et valide sa sortie. Une relance avec le motif, puis `LLMOutputError`."""
    feedback: Optional[str] = None
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = client.invoke(step=step, system=prompt.text, payload=payload, schema=schema, tier=tier,
                            feedback=feedback)
        try:
            parsed = _parse(raw, schema)
        except (ValidationError, json.JSONDecodeError, TypeError) as error:
            last_error = str(error)
            feedback = (
                "Ta sortie précédente a été rejetée car elle ne respecte pas le schéma JSON demandé. "
                f"Motif : {last_error[:600]} Renvoie uniquement un objet JSON conforme."
            )
            continue
        return parsed, CallInfo(step=step, model_id=client.model_id(tier), prompt_version=prompt.tag,
                                attempts=attempt)
    raise LLMOutputError(f"Étape {step} : sortie invalide après {MAX_ATTEMPTS} essais. {last_error[:300]}")


# --- faux client ------------------------------------------------------------------------------
Responder = Callable[[Mapping[str, Any]], Any]


@dataclass
class FakeLLMClient:
    """Client sans modèle : chaque étape est servie par une fonction `payload -> sortie`.

    `responders` associe un nom d'étape (ou un préfixe, ex. `debate.bear`) à une fonction ou à
    une liste de sorties servies dans l'ordre (utile pour tester la relance). `*` sert de repli.
    Les appels sont enregistrés dans `calls` pour les assertions des tests.
    """

    responders: dict[str, Union[Responder, list]] = field(default_factory=dict)
    name: str = "faux-client"
    calls: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def model_id(self, tier: str) -> str:
        return self.name

    def _find(self, step: str) -> Union[Responder, list]:
        best = None
        for key in self.responders:
            if key != "*" and (step == key or step.startswith(key + ".")) and (best is None or len(key) > len(best)):
                best = key
        if best is None and "*" in self.responders:
            best = "*"
        if best is None:
            raise LLMUnavailableError(f"Faux client : aucune réponse prévue pour l'étape {step}")
        return self.responders[best]

    def invoke(self, *, step, system, payload, schema, tier, feedback=None) -> Any:
        with self._lock:
            self.calls.append({"step": step, "tier": tier, "feedback": feedback})
            responder = self._find(step)
            if isinstance(responder, list):
                if not responder:
                    raise LLMUnavailableError(f"Faux client : plus de réponse pour l'étape {step}")
                return responder.pop(0) if len(responder) > 1 else responder[0]
        return responder(payload)


# --- Amazon Bedrock ---------------------------------------------------------------------------
class BedrockClient:
    """Amazon Bedrock, API Converse. La sortie structurée passe par un outil que le modèle est invité à appeler.

    Compatibilité avec les modèles Claude actuels (Opus 5.5, Sonnet 5.5, Haiku 5.5) :
    - pas de `temperature` (valeur non par défaut refusée) ;
    - pas de `toolChoice` forcé (refusé par Opus 5.5 et Sonnet 5.5) : choix automatique et consigne dans le
      message ; une réponse sans appel d'outil est rejetée par la validation, donc relancée une fois ;
    - `max_tokens` assez grand pour le raisonnement du modèle (activé par défaut) ; les blocs
      `reasoningContent` sont ignorés à la lecture.

    Configuration par variables d'environnement (voir `.env.example`) : `AWS_REGION`,
    `BEDROCK_MODEL_ID_FAST`, `BEDROCK_MODEL_ID_STRONG`, `BEDROCK_GUARDRAIL_ID` (optionnel).
    Non exécuté dans les tests : dépend du compte AWS du datathon (avancement.md, tâche A2).
    """

    TOOL_NAME = "rendre_sortie"

    def __init__(self, *, region: Optional[str] = None, model_fast: Optional[str] = None,
                 model_strong: Optional[str] = None, guardrail_id: Optional[str] = None,
                 guardrail_version: str = "DRAFT", max_tokens: int = 16000, client: Any = None):
        self.region = region or os.environ.get("AWS_REGION") or None
        self.models = {
            TIER_FAST: model_fast or os.environ.get("BEDROCK_MODEL_ID_FAST", ""),
            TIER_STRONG: model_strong or os.environ.get("BEDROCK_MODEL_ID_STRONG", ""),
        }
        self.guardrail_id = guardrail_id or os.environ.get("BEDROCK_GUARDRAIL_ID") or None
        self.guardrail_version = guardrail_version
        self.max_tokens = max_tokens
        self._client = client

    @classmethod
    def configured(cls) -> bool:
        return bool(os.environ.get("BEDROCK_MODEL_ID_FAST") and os.environ.get("BEDROCK_MODEL_ID_STRONG"))

    def model_id(self, tier: str) -> str:
        model = self.models.get(tier) or self.models[TIER_STRONG] or self.models[TIER_FAST]
        if not model:
            raise LLMUnavailableError(
                "Aucun modèle Bedrock configuré : renseigner BEDROCK_MODEL_ID_FAST et BEDROCK_MODEL_ID_STRONG."
            )
        return model

    def _runtime(self) -> Any:
        if self._client is None:
            try:
                import boto3  # import tardif : le dépôt fonctionne sans AWS
            except ImportError as error:
                raise LLMUnavailableError("boto3 n'est pas installé (pip install boto3).") from error
            from botocore.config import Config

            # Délai de lecture large : un modèle qui raisonne avant de répondre dépasse souvent les 60 s
            # par défaut, ce qui déclenchait des relances silencieuses (exécution qui semble figée).
            self._client = boto3.client("bedrock-runtime", region_name=self.region, config=Config(
                connect_timeout=10, read_timeout=300, retries={"max_attempts": 3, "mode": "standard"}))
        return self._client

    def invoke(self, *, step, system, payload, schema, tier, feedback=None) -> Any:
        user = (
            "Données d'entrée (JSON) :\n" + json.dumps(payload, ensure_ascii=False, default=str)
            + f"\n\nRéponds uniquement en appelant l'outil `{self.TOOL_NAME}` avec un objet conforme au schéma, "
            "sans texte autour."
        )
        if feedback:
            user += "\n\n" + feedback
        request: dict[str, Any] = {
            "modelId": self.model_id(tier),
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": [{"text": user}]}],
            # Ni `temperature` ni `toolChoice` forcé : refusés par les modèles Claude actuels (voir la classe).
            "inferenceConfig": {"maxTokens": self.max_tokens},
            "toolConfig": {
                "tools": [{"toolSpec": {
                    "name": self.TOOL_NAME,
                    "description": "Rend la sortie structurée de l'étape.",
                    "inputSchema": {"json": schema.model_json_schema()},
                }}],
            },
        }
        if self.guardrail_id:
            request["guardrailConfig"] = {
                "guardrailIdentifier": self.guardrail_id, "guardrailVersion": self.guardrail_version,
            }
        try:
            response = self._runtime().converse(**request)
        except LLMUnavailableError:
            raise
        except Exception as error:  # identifiants, région, modèle non ouvert, quota
            raise LLMUnavailableError(f"Appel Bedrock impossible ({step}) : {error}") from error
        for block in response.get("output", {}).get("message", {}).get("content", []):
            if "toolUse" in block:
                return block["toolUse"].get("input")
        for block in response.get("output", {}).get("message", {}).get("content", []):
            if "text" in block:
                return block["text"]
        return None  # sortie vide : rejetée par la validation, donc relancée


def make_client(kind: str = "auto") -> LLMClient:
    """`simule` : agents simulés, sans modèle. `bedrock` : Amazon Bedrock. `auto` : Bedrock s'il est configuré."""
    if kind not in ("auto", "simule", "bedrock"):
        raise ValueError("kind doit valoir 'auto', 'simule' ou 'bedrock'")
    if kind == "bedrock" or (kind == "auto" and BedrockClient.configured()):
        return BedrockClient()
    from easytrade.agents.simulated import simulated_client

    return simulated_client()
