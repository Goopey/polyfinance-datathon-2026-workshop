"""Aucune arête sans document cité ou étiquette HYPOTHESE.

Conception : docs/04_DONNEES.md (section 6)
Vérifie le fichier data/reference/graph_edges.csv tel qu'il est versionné.
"""
import pandas as pd
import pytest

from easytrade.agents.tools import EDGES_SOURCE_BY_TYPE

RELATIONS = {"FOURNISSEUR", "CLIENT", "CONCURRENT", "PARTENAIRE"}


@pytest.fixture(scope="module")
def edges(data_dir):
    return pd.read_csv(data_dir / "reference" / "graph_edges.csv", dtype=str, keep_default_na=False)


def test_graph_edges_non_vide(edges):
    assert len(edges) > 0, "aucune arête : lancer scripts/fetch_finnhub.py"


def test_chaque_arete_est_sourcee_ou_hypothese(edges, registry):
    problems = []
    for index, row in edges.iterrows():
        where = f"ligne {index + 2} ({row['source']} → {row['target']})"
        if row["relation"] not in RELATIONS:
            problems.append(f"{where} : relation inconnue {row['relation']}")
        if row["claim_kind"] not in ("FAIT", "HYPOTHESE"):
            problems.append(f"{where} : claim_kind invalide {row['claim_kind']!r}")
        if row["claim_kind"] == "FAIT" and not (row["document_id"] and row["document_url"] and row["excerpt"]):
            problems.append(f"{where} : FAIT sans document cité (identifiant, URL, extrait)")
        source_id = EDGES_SOURCE_BY_TYPE.get(row["document_type"])
        if source_id is None:
            problems.append(f"{where} : type de document sans source connue {row['document_type']!r}")
        elif registry.get(source_id).statut != "utilisé":
            problems.append(f"{where} : source {source_id} non « utilisé » dans le registre")
        if pd.isna(pd.to_datetime(row["document_date"], errors="coerce")):
            problems.append(f"{where} : date de document illisible {row['document_date']!r}")
        if not row["excerpt"]:
            problems.append(f"{where} : extrait justificatif manquant")
    assert not problems, "\n".join(problems)


def test_pas_de_boucle_ni_de_doublon(edges):
    pairs = [frozenset((s, t)) for s, t in zip(edges["source"], edges["target"])]
    assert all(len(pair) == 2 for pair in pairs), "arête d'une société vers elle-même"
    assert len(pairs) == len(set(pairs)), "paire en double (une relation symétrique n'a qu'une arête)"
