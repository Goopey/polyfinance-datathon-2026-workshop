"""Filtre de formulations prescriptives (data/reference/forbidden_wording.txt).

Conception : docs/08_CONFORMITE.md, docs/07_UX_UI.md (table de rédaction)
La liste est un fichier de référence versionné : une formulation par ligne, `#` pour un
commentaire. La recherche est insensible à la casse et se fait par sous-chaîne (« garanti »
attrape aussi « garantie »). Le filtre s'applique à toute sortie montrée à l'utilisateur.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Iterator

FILENAME = "forbidden_wording.txt"


def _normalize(text: str) -> str:
    return text.casefold().replace("\u2019", "'").replace("\u00a0", " ").replace("\u202f", " ")


def load_forbidden(reference_dir: Path) -> tuple[str, ...]:
    """Lit la liste des formulations refusées. Lève une erreur si le fichier est absent ou vide."""
    terms: list[str] = []
    with open(Path(reference_dir) / FILENAME, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(_normalize(line))
    if not terms:
        raise ValueError(f"Liste de formulations refusées vide : {reference_dir / FILENAME}")
    return tuple(terms)


def find_forbidden(text: str, terms: Iterable[str]) -> list[str]:
    """Formulations refusées présentes dans `text` (liste vide si le texte est conforme)."""
    haystack = _normalize(text)
    return [term for term in terms if term in haystack]


def is_clean(text: str, terms: Iterable[str]) -> bool:
    return not find_forbidden(text, terms)


def iter_strings(value: Any) -> Iterator[str]:
    """Toutes les chaînes d'une structure JSON (dictionnaires, listes), valeurs seulement."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_strings(item)


def scan(value: Any, terms: Iterable[str]) -> list[tuple[str, str]]:
    """(formulation refusée, texte fautif) pour chaque occurrence dans une sortie JSON."""
    terms = tuple(terms)
    return [(term, text) for text in iter_strings(value) for term in find_forbidden(text, terms)]
