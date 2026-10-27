#!/usr/bin/env python
"""A/B evaluation harness for the KYB decision pipeline.

Two things in one:

  1. Offline scenario table (default): runs a fixed set of representative
     businesses through the deterministic risk engine under config **A**
     (enrichment OFF — footprint legitimacy only) and config **B** (enrichment
     ON — LLM-judge web-presence score). Prints a comparison and ASSERTS the
     invariants that must always hold:
        * a registry outage/not-found is NEVER a reject   (outage != reject)
        * a web-only case (registry unconfirmed) NEVER auto-approves
        * a registry-confirmed clean business still approves (no regression)

  2. Live mode (``--live "Apple Inc" --state CA``): drives the real app via
     TestClient for a real company under A vs B and prints the two reports.
     Best-effort — needs network + keys; enrichment is a no-op without them.

Run from apps/api::  python scripts/ab_eval.py            # offline invariants
                     python scripts/ab_eval.py --live "Apple Inc" --state CA
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.risk.engine import compute_risk  # noqa: E402

# name -> (identity_confidence, web_legitimacy, signals, officers, ownership_known,
#          judge_presence_score_for_B)
_SCENARIOS = {
    "confirmed-real-co": (0.98, 95, ["NO_VERIFIED_UBO"], 3, True, 96),
    "mid-real-co":       (0.86, 78, [], 1, True, 82),
    "registry-outage":   (None, 90, ["REGISTRY_UNAVAILABLE"], 0, False, 92),
    "not-in-registry":   (None, 70, ["REGISTRY_NOT_FOUND"], 0, False, 74),
    "ghost-parked-site": (None, 10, ["REGISTRY_NOT_FOUND", "PARKED_OR_PLACEHOLDER"],
                          0, False, 8),
}


def _run(scn, enrichment_on: bool):
    conf, legit, sigs, officers, own_known, judge = scn
    return compute_risk(
        identity_confidence=conf,
        web_legitimacy=legit,
        signal_codes=sigs,
        officers_count=officers,
        psc_supported=False,
        ownership_known=own_known,
        web_presence_score=(judge if enrichment_on else None),
    )


def offline_table() -> int:
    print(f"{'scenario':<20} {'cfg':<3} {'risk':>4} {'rating':<7} "
          f"{'decision':<9} reasons")
    print("-" * 78)
    failures = 0
    for name, scn in _SCENARIOS.items():
        for cfg, on in (("A", False), ("B", True)):
            r = _run(scn, on)
            reasons = ",".join(r.reason_codes) or "-"
            print(f"{name:<20} {cfg:<3} {r.overall_risk:>4} {r.rating:<7} "
                  f"{r.decision:<9} {reasons}")

            # ---- invariants (must hold under BOTH configs) ----
            if name in ("registry-outage", "not-in-registry") \
                    and r.decision == "reject":
                print(f"   !! INVARIANT FAILED: {name}/{cfg} rejected on "
                      f"unconfirmed registry")
                failures += 1
            if scn[0] is None and r.decision == "approve":
                print(f"   !! INVARIANT FAILED: {name}/{cfg} auto-approved "
                      f"without registry confirmation")
                failures += 1
        # confirmed clean business must still approve
        if name == "confirmed-real-co" and _run(scn, True).decision != "approve":
            print("   !! INVARIANT FAILED: confirmed clean business not approved")
            failures += 1
        print()

    if failures:
        print(f"FAILED: {failures} invariant violation(s).")
        return 1
    print("OK: all A/B invariants hold (outage != reject, web-only != approve).")
    return 0


def live(name: str, state: str | None) -> int:
    from fastapi.testclient import TestClient

    results = {}
    for cfg, enrich in (("A (enrichment off)", "false"), ("B (enrichment on)", "true")):
        os.environ["ENABLE_ENRICHMENT"] = enrich
        # Re-import settings/app fresh so the toggle takes effect.
        for mod in [m for m in list(sys.modules) if m.startswith("app")]:
            del sys.modules[mod]
        from app.config import settings  # noqa: F401
        from app.main import app

        with TestClient(app) as c:
            payload = {"legal_name": name}
            if state:
                payload["state"] = state
            created = c.post("/kyb/cases", json=payload).json()
            cid = created["business"]["id"]
            report = c.get(f"/kyb/cases/{cid}/report").json()
            results[cfg] = report

    for cfg, rep in results.items():
        scores = {s["type"]: (s["score"], s["rating"]) for s in rep["scores"]}
        print(f"\n=== {cfg} ===")
        print(f"  verified: {rep['verified']}")
        print(f"  scores:   {scores}")
        print(f"  decision: {rep['decision']['action']}")
        if rep.get("enrichment"):
            e = rep["enrichment"]
            print(f"  hq: {e.get('hq')} | employees: {e.get('employee_range')} "
                  f"| presence: {e.get('presence_score')}")
            if e.get("recent_news"):
                print(f"  news: {len(e['recent_news'])} item(s)")
        print(f"  warnings: {rep.get('warnings')}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", metavar="NAME", help="run a real company live")
    ap.add_argument("--state", help="US state for the live run, e.g. CA")
    args = ap.parse_args()

    if args.live:
        raise SystemExit(live(args.live, args.state))
    # Offline mode must be deterministic + network-free.
    os.environ.setdefault("ENABLE_ENRICHMENT", "false")
    raise SystemExit(offline_table())
