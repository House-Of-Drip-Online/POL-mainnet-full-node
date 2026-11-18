#!/usr/bin/env python3
"""Offline commissioning aggregator; never imported by runtime admission.

Consumes captured rpc_gate observations. It grants no node, route or financial
authority and makes no RPC calls. Collection cadence belongs to the independent
commissioning job and must be recorded with its evidence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def evaluate_witness(observations, required_passes=25):
    if not isinstance(required_passes,int) or isinstance(required_passes,bool) or required_passes<1:
        raise ValueError("INVALID_WITNESS_PASS_COUNT")
    count=0
    previous=None
    examined=0
    for row in observations:
        if "summary" in row:
            continue
        examined+=1
        pin=row.get("canonicalComparisonBlock")
        source_chain=row.get("chainId",row.get("sourceChainId"))
        valid=(row.get("schema") in {"omega.polygon137.rpc-gate.v1","omega.polygon137.native-cycle-witness.v1"} and
               source_chain==137 and row.get("status")=="PASS" and not row.get("failures") and
               isinstance(pin,int) and not isinstance(pin,bool) and pin>0 and
               (previous is None or pin>previous))
        count=count+1 if valid else 0
        previous=pin if valid else None
        if count>=required_passes:
            break
    return {"schema":"omega.commissioning.header-witness.v1",
            "context":"COMMISSIONING","scope":"CANONICAL_HTTP_HEADERS_ONLY",
            "required_consecutive_passes":required_passes,"consecutive_passes":count,
            "observations_examined":examined,"witness_passed":count>=required_passes,
            "blocks_operational_admission":False,"execution_authorized":False,
            "wss_certified":False,"native_pool_state_certified":False,
            "evidence_authentication_verified":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",type=Path,required=True)
    parser.add_argument("--profile",type=Path,default=Path(__file__).parent/"config/profiles/commissioning.json")
    args=parser.parse_args()
    profile=json.loads(args.profile.read_text())
    if profile.get("context")!="COMMISSIONING" or profile.get("blocks_operational_admission") is not False:
        raise ValueError("COMMISSIONING_PROFILE_REQUIRED")
    rows=[json.loads(line) for line in args.observations.read_text().splitlines() if line.strip()]
    result=evaluate_witness(rows,profile["required_consecutive_passes"])
    print(json.dumps(result,sort_keys=True))
    return 0 if result["witness_passed"] else 2


if __name__=="__main__":
    raise SystemExit(main())
