"""Ressources d'exécution sur AWS (et leurs équivalents locaux pour les tests).

Conception : docs/06_AWS.md
- Données : au démarrage à froid d'une Lambda, le jeu de départ et les données de référence sont
  copiés de S3 (`EASYTRADE_DATA_BUCKET`) vers /tmp ; le code lit ensuite les mêmes fichiers qu'en local.
- Contexte d'un run : enregistré entre deux étapes de la machine d'états (`StateStore`), avec les
  artefacts JSON du run (mêmes fichiers que `RunResult.save` en local).
- Table des runs : état et progression d'une analyse, profils fictifs créés par l'application (`RunTable`).

Le contexte est sérialisé avec `pickle`. Il n'est écrit et lu que par nos propres fonctions, dans un
compartiment privé dont l'accès est limité par IAM : aucune donnée extérieure n'est désérialisée.

Variables d'environnement :
    EASYTRADE_DATA_BUCKET, EASYTRADE_DATA_PREFIX (défaut « data/ »)  données sur S3
    EASYTRADE_STATE_BUCKET (défaut : EASYTRADE_DATA_BUCKET)          contexte et artefacts des runs
    EASYTRADE_TABLE                                                  table DynamoDB
    EASYTRADE_STATE_DIR, EASYTRADE_TABLE_DIR                         équivalents locaux (tests)
"""
from __future__ import annotations

import json
import os
import pickle
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional, Protocol

from easytrade.agents.llm_client import LLMClient, make_client
from easytrade.config import load_settings
from easytrade.orchestration.pipeline import RunResult, Workspace
from easytrade.schemas.trace import TraceStep

LOCAL_DATA_DIR = Path(tempfile.gettempdir()) / "easytrade-data"
DATA_PARTS = ("raw/starter/", "reference/")
RUNS_PREFIX = "runs/"
FINAL_STATUSES = ("termine", "echec")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _boto(service: str) -> Any:
    import boto3  # import tardif : le dépôt fonctionne sans AWS

    return boto3.client(service, region_name=os.environ.get("AWS_REGION"))


# --- données ------------------------------------------------------------------------------------
def ensure_data() -> Optional[Path]:
    """Copie les données de S3 vers /tmp au premier appel (démarrage à froid). Sans compartiment : rien."""
    bucket = os.environ.get("EASYTRADE_DATA_BUCKET")
    if not bucket:
        return None
    prefix = os.environ.get("EASYTRADE_DATA_PREFIX", "data/")
    marker = LOCAL_DATA_DIR / ".complet"
    if not marker.exists():
        s3 = _boto("s3")
        paginator = s3.get_paginator("list_objects_v2")
        for part in DATA_PARTS:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix + part):
                for item in page.get("Contents", []):
                    target = LOCAL_DATA_DIR / item["Key"][len(prefix):]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    s3.download_file(bucket, item["Key"], str(target))
        marker.touch()
    os.environ["EASYTRADE_DATA_DIR"] = str(LOCAL_DATA_DIR)
    return LOCAL_DATA_DIR


@lru_cache(maxsize=1)
def workspace() -> Workspace:
    """Espace de travail partagé par les invocations d'un même conteneur Lambda."""
    ensure_data()
    return Workspace.load(load_settings())


@lru_cache(maxsize=1)
def llm() -> LLMClient:
    """Bedrock quand BEDROCK_MODEL_ID_FAST / _STRONG sont définis, sinon agents simulés (et la trace le dit)."""
    return make_client("auto")


# --- contexte et artefacts des runs -------------------------------------------------------------
class StateStore(Protocol):
    def save(self, run_id: str, name: str, obj: Any) -> None: ...
    def load(self, run_id: str, name: str) -> Any: ...
    def exists(self, run_id: str, name: str) -> bool: ...
    def save_artifacts(self, result: RunResult) -> None: ...


class LocalStateStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, run_id: str, name: str) -> Path:
        return self.root / RUNS_PREFIX / run_id / f"{name}.pkl"

    def save(self, run_id: str, name: str, obj: Any) -> None:
        path = self._path(run_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(obj))

    def load(self, run_id: str, name: str) -> Any:
        return pickle.loads(self._path(run_id, name).read_bytes())

    def exists(self, run_id: str, name: str) -> bool:
        return self._path(run_id, name).exists()

    def save_artifacts(self, result: RunResult) -> None:
        result.save(self.root / RUNS_PREFIX)


class S3StateStore:
    def __init__(self, bucket: str, client: Any = None):
        self.bucket, self._client = bucket, client

    @property
    def s3(self) -> Any:
        if self._client is None:
            self._client = _boto("s3")
        return self._client

    @staticmethod
    def _key(run_id: str, name: str) -> str:
        return f"{RUNS_PREFIX}{run_id}/{name}.pkl"

    def save(self, run_id: str, name: str, obj: Any) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=self._key(run_id, name), Body=pickle.dumps(obj))

    def load(self, run_id: str, name: str) -> Any:
        return pickle.loads(self.s3.get_object(Bucket=self.bucket, Key=self._key(run_id, name))["Body"].read())

    def exists(self, run_id: str, name: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self._key(run_id, name))
            return True
        except Exception:
            return False

    def save_artifacts(self, result: RunResult) -> None:
        """Mêmes fichiers JSON qu'en local (run.json, trace.json, evidence.json, explanation.json…)."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = result.save(Path(tmp))
            for path in sorted(folder.iterdir()):
                self.s3.upload_file(str(path), self.bucket, f"{RUNS_PREFIX}{result.run_id}/{path.name}",
                                    ExtraArgs={"ContentType": "application/json"})


def state_store() -> StateStore:
    local = os.environ.get("EASYTRADE_STATE_DIR")
    if local:
        return LocalStateStore(Path(local))
    bucket = os.environ.get("EASYTRADE_STATE_BUCKET") or os.environ.get("EASYTRADE_DATA_BUCKET")
    if not bucket:
        raise RuntimeError("Aucun stockage de run : définir EASYTRADE_STATE_BUCKET ou EASYTRADE_STATE_DIR.")
    return S3StateStore(bucket)


# --- table des runs et des profils fictifs ------------------------------------------------------
def steps_payload(steps: Iterable[TraceStep]) -> str:
    return json.dumps([s.model_dump(mode="json") for s in steps], ensure_ascii=False)


def steps_from_payload(payload: Optional[str]) -> list[TraceStep]:
    return [TraceStep(**s) for s in json.loads(payload or "[]")]


class RunTable(Protocol):
    def get_run(self, run_id: str) -> Optional[dict]: ...
    def put_run(self, item: dict) -> None: ...
    def update_run(self, run_id: str, **fields: Any) -> None: ...
    def get_profile(self, profile_id: str) -> Optional[dict]: ...
    def put_profile(self, entry: dict) -> None: ...
    def get_view(self, profile_id: str) -> Optional[str]: ...
    def put_view(self, profile_id: str, payload: str) -> None: ...


class LocalRunTable:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _read(self, key: str) -> Optional[dict]:
        path = self.root / f"{key}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def _write(self, key: str, item: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{key}.json").write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")

    def get_run(self, run_id: str) -> Optional[dict]:
        return self._read(f"RUN_{run_id}")

    def put_run(self, item: dict) -> None:
        self._write(f"RUN_{item['run_id']}", {**item, "updated_at": _now()})

    def update_run(self, run_id: str, **fields: Any) -> None:
        item = self.get_run(run_id) or {"run_id": run_id}
        self._write(f"RUN_{run_id}", {**item, **fields, "updated_at": _now()})

    def get_profile(self, profile_id: str) -> Optional[dict]:
        item = self._read(f"PROFILE_{profile_id}")
        return item["entry"] if item else None

    def put_profile(self, entry: dict) -> None:
        self._write(f"PROFILE_{entry['id']}", {"entry": entry})

    def get_view(self, profile_id: str) -> Optional[str]:
        item = self._read(f"VIEW_{profile_id}")
        return item["view"] if item else None

    def put_view(self, profile_id: str, payload: str) -> None:
        self._write(f"VIEW_{profile_id}", {"view": payload})


class DynamoRunTable:
    """Une seule table : clé `pk` = « RUN#<id> », « PROFILE#<id> » (profil fictif) ou « VIEW#<id> » (vue du profil
    pondérée par l'agent, calculée une fois). Valeurs complexes en JSON (pas de Decimal)."""

    def __init__(self, table_name: str, client: Any = None):
        self.table_name, self._client = table_name, client

    @property
    def db(self) -> Any:
        if self._client is None:
            self._client = _boto("dynamodb")
        return self._client

    @staticmethod
    def _attr(value: Any) -> dict:
        return {"NULL": True} if value is None else {"S": str(value)}

    @staticmethod
    def _plain(item: dict) -> dict:
        return {k: (None if "NULL" in v else v["S"]) for k, v in item.items() if k != "pk"}

    def get_run(self, run_id: str) -> Optional[dict]:
        item = self.db.get_item(TableName=self.table_name, Key={"pk": {"S": f"RUN#{run_id}"}}, ConsistentRead=True)
        return self._plain(item["Item"]) if "Item" in item else None

    def put_run(self, item: dict) -> None:
        fields = {**item, "updated_at": _now()}
        self.db.put_item(TableName=self.table_name,
                         Item={"pk": {"S": f"RUN#{item['run_id']}"}, **{k: self._attr(v) for k, v in fields.items()}})

    def update_run(self, run_id: str, **fields: Any) -> None:
        fields = {**fields, "updated_at": _now()}
        names = {f"#f{i}": key for i, key in enumerate(fields)}
        values = {f":v{i}": self._attr(value) for i, value in enumerate(fields.values())}
        self.db.update_item(
            TableName=self.table_name, Key={"pk": {"S": f"RUN#{run_id}"}},
            UpdateExpression="SET " + ", ".join(f"#f{i} = :v{i}" for i in range(len(fields))),
            ExpressionAttributeNames=names, ExpressionAttributeValues=values,
        )

    def get_profile(self, profile_id: str) -> Optional[dict]:
        item = self.db.get_item(TableName=self.table_name, Key={"pk": {"S": f"PROFILE#{profile_id}"}})
        return json.loads(item["Item"]["entry"]["S"]) if "Item" in item else None

    def put_profile(self, entry: dict) -> None:
        self.db.put_item(TableName=self.table_name, Item={
            "pk": {"S": f"PROFILE#{entry['id']}"}, "entry": {"S": json.dumps(entry, ensure_ascii=False)},
        })

    def get_view(self, profile_id: str) -> Optional[str]:
        item = self.db.get_item(TableName=self.table_name, Key={"pk": {"S": f"VIEW#{profile_id}"}})
        return item["Item"]["view"]["S"] if "Item" in item else None

    def put_view(self, profile_id: str, payload: str) -> None:
        self.db.put_item(TableName=self.table_name, Item={"pk": {"S": f"VIEW#{profile_id}"}, "view": {"S": payload}})


def run_table() -> RunTable:
    local = os.environ.get("EASYTRADE_TABLE_DIR")
    if local:
        return LocalRunTable(Path(local))
    name = os.environ.get("EASYTRADE_TABLE")
    if not name:
        raise RuntimeError("Aucune table des runs : définir EASYTRADE_TABLE ou EASYTRADE_TABLE_DIR.")
    return DynamoRunTable(name)
