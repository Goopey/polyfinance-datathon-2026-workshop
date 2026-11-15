"""Outils de l'agent de recherche : lister_univers, chercher_documents, preuves_esg, relations, nouvelles. Tous filtrés par as_of.

Conception : docs/02_AGENTS.md (section 2), docs/04_DONNEES.md (sections 4 et 6)
Règles :
- chaque outil filtre sur `published_at ≤ as_of` (`filter_published`) ;
- une ligne ne devient une preuve que si sa source figure au registre avec le statut « utilisé » ;
- chaque appel est journalisé (`calls`) : la trace montre quels outils l'agent a mobilisés ;
- un outil dont la source n'est pas encore branchée répond « rien », avec la raison : l'agent
  et l'utilisateur voient qu'une information manque, au lieu d'une réponse inventée.
État des sources : ESG et relations lisent `data/reference/` (fichiers saisis à la main, vides
tant que le bloc G n'est pas fait) ; documents réglementaires et nouvelles ne sont pas branchés.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from easytrade.data.loaders import load_reference_table
from easytrade.data.point_in_time import DateLike, filter_published, to_timestamp
from easytrade.data.sources_registry import SourcesRegistry
from easytrade.explain.evidence_ledger import EvidenceLedger
from easytrade.schemas.evidence import EvidenceDraft

VERSION = "v1"
ESG_FILE, ESG_DATE = "esg_evidence.csv", "document_date"
EDGES_FILE, EDGES_DATE = "graph_edges.csv", "document_date"
EDGES_SOURCE_BY_TYPE = {"10-K": "sec_edgar", "10-Q": "sec_edgar", "8-K": "sec_edgar", "SEDAR+": "sedar_plus",
                        "finnhub_peers": "finnhub"}  # instantané scripts/fetch_finnhub.py

TOOL_DESCRIPTIONS: dict[str, str] = {
    "lister_univers": "Actifs analysables : ticker, nom, classe d'actifs, secteur, devise. Aucun chiffre.",
    "chercher_documents": "Dépôts réglementaires d'un émetteur (EDGAR, SEDAR+) publiés à la date d'analyse.",
    "preuves_esg": "Signaux ESG et controverses documentés pour un titre, datés.",
    "relations": "Relations sourcées d'une société : fournisseurs, clients, concurrents, partenaires.",
    "nouvelles": "Nouvelles datées d'un émetteur (seulement si une source autorisée est branchée).",
}


class ResearchTools:
    def __init__(self, assets: pd.DataFrame, as_of: DateLike, reference_dir: Path, ledger: EvidenceLedger,
                 registry: SourcesRegistry):
        self._assets = assets
        self._as_of = to_timestamp(as_of)
        self._reference_dir = Path(reference_dir)
        self._ledger = ledger
        self._registry = registry
        self._tables: dict[str, pd.DataFrame] = {}
        self.calls: list[dict[str, Any]] = []

    # --- infrastructure -----------------------------------------------------------------------
    def _log(self, tool: str, ticker: Optional[str], results: list, note: str = "") -> list:
        self.calls.append({"tool": tool, "ticker": ticker, "results": len(results), "note": note})
        return results

    def _table(self, filename: str, date_column: str) -> pd.DataFrame:
        if filename not in self._tables:
            table = load_reference_table(self._reference_dir, filename, date_column)
            self._tables[filename] = filter_published(table.dropna(subset=["published_at"]), self._as_of)
        return self._tables[filename]

    def _source_usable(self, source_id: str) -> bool:
        return source_id in self._registry and self._registry.get(source_id).statut == "utilisé"

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(TOOL_DESCRIPTIONS)

    def summary(self) -> tuple[str, ...]:
        """Outils appelés, pour la trace : « preuves_esg ×31 (0 résultat) »."""
        out: list[str] = []
        for tool in TOOL_DESCRIPTIONS:
            calls = [c for c in self.calls if c["tool"] == tool]
            if calls:
                results = sum(c["results"] for c in calls)
                out.append(f"{tool} ×{len(calls)} ({results} résultat{'s' if results > 1 else ''})")
        return tuple(out)

    def dispatch(self, tool: str, ticker: Optional[str] = None) -> list:
        """Exécute un outil demandé par l'agent. Outil inconnu : erreur (le code l'ignore et le note)."""
        handlers: dict[str, Callable[..., list]] = {
            "lister_univers": lambda _ticker=None: self.lister_univers(),
            "chercher_documents": self.chercher_documents,
            "preuves_esg": self.preuves_esg,
            "relations": self.relations,
            "nouvelles": self.nouvelles,
        }
        if tool not in handlers:
            raise KeyError(f"Outil inconnu : {tool}")
        return handlers[tool](ticker)

    # --- outils -------------------------------------------------------------------------------
    def lister_univers(self) -> list[dict]:
        rows = [
            {"ticker": str(r["ticker"]), "name": str(r["name"]), "asset_class": str(r["asset_class"]),
             "sector": str(r["sector"]), "currency": str(r["currency"])}
            for _, r in self._assets.iterrows()
        ]
        return self._log("lister_univers", None, rows)

    def chercher_documents(self, ticker: Optional[str]) -> list[dict]:
        return self._log("chercher_documents", ticker, [],
                         "Dépôts réglementaires non branchés (sources sec_edgar et sedar_plus au statut « prévu »).")

    def nouvelles(self, ticker: Optional[str]) -> list[dict]:
        return self._log("nouvelles", ticker, [], "Aucune source de nouvelles autorisée n'est branchée.")

    def preuves_esg(self, ticker: Optional[str]) -> list[dict]:
        table = self._table(ESG_FILE, ESG_DATE)
        rows = table[table["ticker"] == ticker] if len(table) else table
        out: list[dict] = []
        skipped = 0
        for _, row in rows.iterrows():
            if not self._source_usable(row["source_id"]):
                skipped += 1
                continue
            source = self._registry.get(row["source_id"])
            day = row["published_at"].date()
            evidence = self._ledger.add(EvidenceDraft(
                type="esg", claim_kind=row["claim_kind"] or "FAIT", subject=str(ticker),
                statement=f"{row['signal_type']} : {row['summary']}".strip(" :"),
                observed_at=day, published_at=day,
                retrieved_at=pd.Timestamp(row["retrieved_at"]).date() if row["retrieved_at"] else None,
                source=source.as_evidence_source(),
                processing=f"Saisie manuelle depuis « {row['document_title']} » ({row['document_url']}) ; extrait : {row['excerpt']}",
                produced_by=f"agents.tools.preuves_esg@{VERSION}",
                limits="Information publiée par l'émetteur ou un tiers cité ; couverture ESG partielle.",
            ))
            out.append({"evidence_id": evidence.evidence_id, "signal_type": row["signal_type"],
                        "summary": row["summary"], "document_date": str(day)})
        note = f"{skipped} ligne(s) ignorée(s) : source absente du registre ou non « utilisé »." if skipped else ""
        return self._log("preuves_esg", ticker, out, note)

    def relations(self, ticker: Optional[str]) -> list[dict]:
        table = self._table(EDGES_FILE, EDGES_DATE)
        rows = table[(table["source"] == ticker) | (table["target"] == ticker)] if len(table) else table
        out: list[dict] = []
        skipped = 0
        for _, row in rows.iterrows():
            source_id = EDGES_SOURCE_BY_TYPE.get(row["document_type"], "")
            if not self._source_usable(source_id):
                skipped += 1
                continue
            day = row["published_at"].date()
            evidence = self._ledger.add(EvidenceDraft(
                type="relation", claim_kind=row["claim_kind"] or "FAIT", subject=f"{row['source']}→{row['target']}",
                statement=f"{row['source']} — {row['relation']} — {row['target']}",
                observed_at=day, published_at=day,
                source=self._registry.get(source_id).as_evidence_source(),
                processing=(
                    f"{row['document_type']} {row['document_id']}, section {row['section']} ({row['document_url']}) ; "
                    f"extrait : {row['excerpt']} ; saisie : {row['extracted_by']}"
                ),
                produced_by=f"agents.tools.relations@{VERSION}",
                limits="Relation décrite dans le document cité, à sa date ; elle peut avoir changé depuis.",
            ))
            out.append({"evidence_id": evidence.evidence_id, "source": row["source"], "target": row["target"],
                        "relation": row["relation"], "document_date": str(day)})
        note = f"{skipped} arête(s) ignorée(s) : source absente du registre ou non « utilisé »." if skipped else ""
        return self._log("relations", ticker, out, note)
