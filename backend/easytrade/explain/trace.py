"""Trace d'exécution : étapes observables (entrées, outils, sorties, modèle, statut).

Conception : docs/05_EXPLICABILITE.md (section 3)
Le pipeline ouvre une étape par bloc de travail ; l'étape se ferme avec son statut et sa durée.
Une exception ferme l'étape en `echec` puis se propage : l'échec est visible, jamais masqué.
Sur AWS, la même trace correspond à l'historique d'exécution de la machine d'états.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Callable, Iterable, Iterator, Optional

from easytrade.schemas.trace import RunTrace, TraceStep


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StepHandle:
    """Étape en cours : le code y inscrit ce qu'il a réellement fait."""

    def __init__(self, step: str, kind: str, **fields):
        self.fields: dict = {"step": step, "kind": kind, "status": "ok", **fields}

    def set(self, **fields) -> "StepHandle":
        self.fields.update(fields)
        return self

    def add_outputs(self, outputs: Iterable[str]) -> None:
        self.fields["outputs"] = tuple(self.fields.get("outputs", ())) + tuple(outputs)

    def add_tools(self, tools: Iterable[str]) -> None:
        self.fields["tools_called"] = tuple(self.fields.get("tools_called", ())) + tuple(tools)

    def note(self, text: str) -> None:
        previous = self.fields.get("note", "")
        self.fields["note"] = f"{previous} {text}".strip()


class TraceRecorder:
    def __init__(self, run_id: str, as_of: date, profile_id: str,
                 clock: Optional[Callable[[], datetime]] = None,
                 on_step: Optional[Callable[[TraceStep], None]] = None):
        self.run_id, self.as_of, self.profile_id = run_id, as_of, profile_id
        self._clock = clock or _utc_now
        self._steps: list[TraceStep] = []
        self._on_step = on_step  # appelé à la fermeture de chaque étape (progression suivie par l'API)

    def set_on_step(self, on_step: Optional[Callable[[TraceStep], None]]) -> None:
        """Change le rappel de progression (retiré avant l'enregistrement d'un run entre deux Lambda)."""
        self._on_step = on_step

    def _append(self, step: TraceStep) -> None:
        self._steps.append(step)
        if self._on_step is not None:
            self._on_step(step)

    def _stamp(self) -> str:
        return self._clock().isoformat(timespec="milliseconds")

    @contextmanager
    def step(self, name: str, kind: str = "code", **fields) -> Iterator[StepHandle]:
        handle = StepHandle(name, kind, **fields)
        started = self._stamp()
        try:
            yield handle
        except Exception as error:
            handle.set(status="echec")
            handle.note(f"{type(error).__name__} : {error}")
            raise
        finally:
            self._append(TraceStep(started_at=started, ended_at=self._stamp(), **handle.fields))

    def now(self) -> str:
        return self._stamp()

    def record(self, name: str, kind: str = "code", status: str = "ok", *,
               started_at: Optional[str] = None, **fields) -> TraceStep:
        """Étape instantanée (contrôle de gouvernance, étape ignorée) ou mesurée par l'appelant."""
        stamp = self._stamp()
        step = TraceStep(step=name, kind=kind, status=status, started_at=started_at or stamp, ended_at=stamp,
                         **fields)
        self._append(step)
        return step

    def control(self, name: str, passed: bool, note: str) -> TraceStep:
        """Point de contrôle de gouvernance (docs/08_CONFORMITE.md) : résultat visible dans la trace."""
        return self.record(name, kind="controle", status="ok" if passed else "echec", note=note)

    @property
    def steps(self) -> tuple[TraceStep, ...]:
        return tuple(self._steps)

    def to_trace(self) -> RunTrace:
        return RunTrace(run_id=self.run_id, as_of=self.as_of, profile_id=self.profile_id, steps=self.steps)
