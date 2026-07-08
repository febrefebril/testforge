#!/usr/bin/env python3
"""TestForge — Revisao de sugestoes de healing pendentes."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testforge.evidence import EvidenceStore


REVIEW_DECISIONS = [
    "APPROVE",
    "REJECT_FALSE_HEAL",
    "REJECT_NOT_RECOVERABLE",
    "REJECT_ORACLE_WEAK",
    "INCONCLUSIVE",
]


def main():
    store = EvidenceStore()

    if "--pending" in sys.argv or len(sys.argv) == 1:
        pending = store.list_pending_reviews()
        if not pending:
            print("Nenhuma revisao pendente.")
            return
        print(f"{'ID RUN':30s} {'ALERTAS':>6s}  {'DATA'}")
        print("-" * 60)
        for p in pending:
            started = p.get("started_at", "")[:19] if p.get("started_at") else "—"
            print(f"{p['run_id']:30s} {p['alert_count']:>6d}  {started}")

    elif "--run" in sys.argv:
        idx = sys.argv.index("--run")
        run_id = sys.argv[idx + 1]
        manifest = store.get_manifest(run_id)
        if not manifest:
            print(f"Run {run_id} nao encontrado")
            return

        print(f"Run: {run_id}")
        print(f"Steps: {manifest.get('step_count', 0)}")
        print(f"Screenshots: {manifest.get('screenshot_count', 0)}")
        print()

        alerts = store.get_sensitive_alerts(run_id)
        if alerts:
            print(f"[AVISO] {len(alerts)} alertas de dados sensiveis:")
            for a in alerts:
                print(f"  - {a.get('type', '?')}: {a.get('field', '?')}")

        screenshots = store.get_screenshots(run_id)
        print(f"\n[FOTO] {len(screenshots)} screenshots disponiveis")

    elif "--decide" in sys.argv:
        print("Decisoes disponiveis:", ", ".join(REVIEW_DECISIONS))
        print("Uso: python scripts/review.py --decide RUN_ID DECISION")
    else:
        store = EvidenceStore()
        runs = store.list_runs()
        print(f"{len(runs)} runs disponiveis:")
        for r in runs:
            m = store.get_manifest(r) or {}
            print(f"  {r} — {m.get('step_count', 0)} steps")


if __name__ == "__main__":
    main()
