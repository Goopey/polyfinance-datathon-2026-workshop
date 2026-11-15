"""Interpréteur minimal de la machine d'états, pour tester les Lambda dans l'ordre réel, sans AWS.

Couvre le sous-ensemble utilisé par infra/statemachine/pipeline.asl.json : Task, Map (INLINE), Fail,
Retry (sans attente), Catch, ItemsPath, ResultPath. Une ressource `${NomArn}` est appelée par son nom.
Comme sur AWS, une exception levée par une Lambda devient une erreur dont le nom est celui de la classe
et la cause un JSON `{"errorMessage", "errorType"}`.
"""
from __future__ import annotations

import copy
import json
from typing import Any, Callable


class ExecutionFailed(Exception):
    def __init__(self, error: str, cause: str, output: Any = None):
        super().__init__(f"{error} : {cause}")
        self.error, self.cause, self.output = error, cause, output


class _TaskError(Exception):
    def __init__(self, name: str, cause: str):
        super().__init__(name)
        self.name, self.cause = name, cause


def _get(data: Any, path: str) -> Any:
    assert path.startswith("$")
    for part in [p for p in path[1:].split(".") if p]:
        data = data[part]
    return data


def _set(data: Any, path: str, value: Any) -> Any:
    if path == "$":
        return value
    out = copy.deepcopy(data)
    target = out
    parts = [p for p in path[1:].split(".") if p]
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value
    return out


def _matches(rule: dict, name: str) -> bool:
    return "States.ALL" in rule["ErrorEquals"] or name in rule["ErrorEquals"]


class AslRunner:
    def __init__(self, definition: dict, resources: dict[str, Callable[[dict], Any]]):
        self.definition, self.resources = definition, resources
        self.visited: list[str] = []

    def _invoke(self, state: dict, payload: Any) -> Any:
        name = state["Resource"].strip("${}").removesuffix("FunctionArn")
        attempts: dict[int, int] = {}
        while True:
            try:
                return self.resources[name](copy.deepcopy(payload))
            except Exception as error:  # comme une erreur de fonction Lambda
                error_name = type(error).__name__
                for index, rule in enumerate(state.get("Retry", [])):
                    if _matches(rule, error_name) and attempts.get(index, 0) < rule.get("MaxAttempts", 3):
                        attempts[index] = attempts.get(index, 0) + 1
                        break
                else:
                    raise _TaskError(error_name, json.dumps({"errorMessage": str(error), "errorType": error_name},
                                                            ensure_ascii=False)) from error

    def _run_states(self, machine: dict, data: Any) -> Any:
        name = machine["StartAt"]
        while True:
            state = machine["States"][name]
            self.visited.append(name)
            if state["Type"] == "Fail":
                raise ExecutionFailed(state.get("Error", "Fail"), state.get("Cause", ""), data)
            try:
                if state["Type"] == "Task":
                    result = self._invoke(state, data)
                elif state["Type"] == "Map":
                    items = _get(data, state["ItemsPath"])
                    result = [self._run_states(state["ItemProcessor"], item) for item in items]
                else:
                    raise NotImplementedError(state["Type"])
            except _TaskError as error:
                catch = next((c for c in state.get("Catch", []) if _matches(c, error.name)), None)
                if catch is None:
                    raise ExecutionFailed(error.name, error.cause, data) from error
                data = _set(data, catch.get("ResultPath", "$"), {"Error": error.name, "Cause": error.cause})
                name = catch["Next"]
                continue
            data = _set(data, state.get("ResultPath", "$"), result)
            if state.get("End"):
                return data
            name = state["Next"]

    def run(self, payload: dict) -> Any:
        return self._run_states(self.definition, payload)
