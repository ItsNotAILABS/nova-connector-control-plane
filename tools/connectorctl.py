#!/usr/bin/env python3
"""connectorctl: local CLI for the NOVA Connector Control Plane."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "connectors.json"


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def validate() -> int:
    registry = load_registry()
    connectors = registry.get("connectors", [])
    errors: list[str] = []
    seen: set[str] = set()
    for index, connector in enumerate(connectors):
        label = f"connectors[{index}]"
        for field in ("id", "name", "surface", "authority", "inputs", "outputs", "proof_gates"):
            if field not in connector:
                errors.append(f"{label} missing {field}")
        connector_id = connector.get("id")
        if connector_id in seen:
            errors.append(f"duplicate connector id: {connector_id}")
        if connector_id:
            seen.add(connector_id)
    if errors:
        print("connectorctl validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"connectorctl validation passed: {len(connectors)} connectors")
    return 0


def list_connectors() -> int:
    for connector in load_registry().get("connectors", []):
        print(f"{connector['id']}\t{connector['surface']}\t{connector['name']}")
    return 0


def describe(connector_id: str) -> int:
    registry = load_registry()
    for connector in registry.get("connectors", []):
        if connector.get("id") == connector_id:
            print(json.dumps(connector, indent=2, sort_keys=True))
            return 0
    print(f"unknown connector: {connector_id}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NOVA connector control CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("list")
    describe_parser = sub.add_parser("describe")
    describe_parser.add_argument("connector_id")
    args = parser.parse_args()
    if args.command == "validate":
        return validate()
    if args.command == "list":
        return list_connectors()
    if args.command == "describe":
        return describe(args.connector_id)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
