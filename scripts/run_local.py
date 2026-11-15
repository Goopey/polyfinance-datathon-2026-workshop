"""Exécute le pipeline en local pour un persona : --persona, --as-of, --ticker (Tester une idée).

Usage (depuis la racine du dépôt, avec l'environnement Python du backend) :
    python scripts/run_local.py --persona amira
    python scripts/run_local.py --persona robert --ticker TSLA
    python scripts/run_local.py --persona amira --as-of 2024-06-28 --save
    python scripts/run_local.py --tous --save          # enregistre les runs des trois personas
    python scripts/run_local.py --persona robert --llm bedrock --max-candidates 3   # essai rapide sur Bedrock

Modèle : `--llm simule` (par défaut si Bedrock n'est pas configuré) exécute des agents simulés
par des règles, sans aucun modèle de langage ; `--llm bedrock` appelle Amazon Bedrock (variables
de `.env.example`). Les artefacts de `--save` vont dans `data/curated/runs/<run_id>/`.
Conception : docs/01_ARCHITECTURE.md
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from easytrade.agents.llm_client import make_client  # noqa: E402
from easytrade.agents.simulated import MODEL_ID as SIMULATED_MODEL_ID  # noqa: E402
from easytrade.orchestration.pipeline import RunResult, Workspace, run_pipeline  # noqa: E402
from easytrade.schemas.debate import STANCE_LABELS  # noqa: E402

PERSONAS = ("amira", "mateo", "robert")


class ProgressClient:
    """Affiche chaque appel au modèle et sa durée (sur stderr) : une analyse réelle fait des dizaines d'appels."""

    def __init__(self, inner):
        self.inner, self.count, self.started = inner, 0, time.monotonic()
        self._lock = threading.Lock()

    def model_id(self, tier):
        return self.inner.model_id(tier)

    def invoke(self, **kwargs):
        start = time.monotonic()
        try:
            return self.inner.invoke(**kwargs)
        finally:
            with self._lock:
                self.count += 1
                print(f"  appel {self.count:3d} · {kwargs['step']:24s} {time.monotonic() - start:6.1f} s "
                      f"(total {time.monotonic() - self.started:5.0f} s)", file=sys.stderr, flush=True)


def _step_closed(step) -> None:
    print(f"  ── étape {step.step} : {step.status}", file=sys.stderr, flush=True)


def _print(result: RunResult, verbose: bool) -> None:
    print("=" * 96)
    print(f"{result.run_id} — statut : {result.status} — modèle : {result.model_id} — preuves : {len(result.ledger)}")
    if result.status != "termine" or result.explanation is None:
        print(f"ÉCHEC : {result.error}")
    else:
        explanation = result.explanation
        print(explanation.headline)
        for text in explanation.missing:
            print(f"  Ce qui manque : {text}")
        for item in explanation.items:
            flags = (" · à examiner" if item.to_review else "") + (" · désaccord" if item.debate_summary.dissent else "")
            print(f"  {item.ticker:8s} adéquation {item.fit:9s} confiance {item.confidence:8s}{flags}  {item.name}")
            if verbose:
                for claim in item.why:
                    print(f"      [{claim.claim_kind}] {claim.text}  ({', '.join(claim.evidence_ids)})")
                for position in item.debate:
                    first = position.arguments[0].text if position.arguments else "aucun argument étayé retenu"
                    print(f"      {position.agent:8s} {STANCE_LABELS[position.stance]} — {first}")
        if explanation.rejected:
            print("  Écartées et pourquoi :")
            for rejected in explanation.rejected:
                print(f"    {rejected.ticker:8s} ({rejected.kind}) {rejected.reason}")
        if explanation.coherence is not None:
            coherence = explanation.coherence
            print(f"  Tester une idée — {coherence.ticker} ({coherence.name}) : {coherence.verdict}")
            for claim in (*coherence.tensions, *coherence.context):
                print(f"    [{claim.claim_kind}] {claim.text}  ({', '.join(claim.evidence_ids)})")
            for alternative in coherence.alternatives:
                print(f"    Alternative {alternative.ticker} : {alternative.why.text}")
        print("  Ce que nous ne savons pas :")
        for text in explanation.unknowns:
            print(f"    - {text}")
        print(f"  {explanation.disclaimer}")
        report = result.fidelity
        if report is not None and report.first_pass_checked:
            print(f"  Fidélité : {report.first_pass_ok}/{report.first_pass_checked} affirmations rédigées fidèles au "
                  f"premier passage ; {report.removed} retirée(s) ; {report.final_checked} recontrôlées dans la sortie.")
    print("  Parcours de l'analyse :")
    for step in result.trace.steps:
        model = f" [{step.model_id}, {step.prompt_version}, {step.attempts} appel(s)]" if step.model_id else ""
        print(f"    {step.status:6s} {step.kind:8s} {step.step}{model} — {step.note}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline EasyTrade en local (simulation, aucune transaction).")
    parser.add_argument("--persona", choices=PERSONAS, default="amira")
    parser.add_argument("--tous", action="store_true", help="exécute les trois personas")
    parser.add_argument("--as-of", dest="as_of", default=None, help="date de référence AAAA-MM-JJ")
    parser.add_argument("--ticker", default=None, help="titre à tester (« Tester une idée »)")
    parser.add_argument("--llm", choices=("auto", "simule", "bedrock"), default="auto")
    parser.add_argument("--niveau", choices=("simple", "avance"), default="simple", help="niveau de lecture")
    parser.add_argument("--save", action="store_true", help="enregistre les artefacts dans data/curated/runs/")
    parser.add_argument("-v", "--verbose", action="store_true", help="affiche les raisons et le débat de chaque piste")
    parser.add_argument("--max-candidates", dest="max_candidates", type=int, default=None,
                        help="limite les candidats présélectionnés (essai rapide, moins d'appels au modèle)")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    workspace = Workspace.load()
    client = make_client(args.llm)
    live = client.model_id("strong") != SIMULATED_MODEL_ID
    if live:  # un vrai modèle : afficher la progression, l'analyse prend plusieurs minutes
        print(f"Modèles : rapide {client.model_id('fast')} · fort {client.model_id('strong')}", file=sys.stderr)
        client = ProgressClient(client)
    failed = 0
    for persona in (PERSONAS if args.tous else (args.persona,)):
        result = run_pipeline(persona, as_of=args.as_of, requested_ticker=args.ticker, client=client,
                              workspace=workspace, reading_level=args.niveau, max_candidates=args.max_candidates,
                              max_workers=3 if live else 1, candidate_workers=4 if live else 1,
                              on_step=_step_closed if live else None)
        _print(result, args.verbose)
        if args.save:
            target = result.save(workspace.settings.curated_dir / "runs")
            print(f"  Artefacts : {target.relative_to(REPO_ROOT)}")
        failed += result.status != "termine"
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
