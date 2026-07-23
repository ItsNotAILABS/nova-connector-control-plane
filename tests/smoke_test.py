#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "server" / "connector_control_plane.py"


def load_server():
    spec = importlib.util.spec_from_file_location("connector_control_plane", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_registry_shape() -> None:
    data = json.loads((ROOT / "data" / "connectors.json").read_text(encoding="utf-8"))
    connectors = data.get("connectors", [])
    assert len(connectors) >= 8
    for connector in connectors:
        for field in ("id", "name", "surface", "authority", "inputs", "outputs", "proof_gates"):
            assert connector.get(field), f"missing {field} in {connector}"


def test_route_and_import_receipt() -> None:
    module = load_server()
    state = module.ConnectorState()
    route = state.route({"task": "build with caffeine", "target_surface": "caffeine mtp", "risk_level": "medium"})
    assert route["connector_id"] == "caffeine-mtp-bridge"
    status, receipt = state.import_artifact({
        "connector_id": "caffeine-mtp-bridge",
        "artifact_url": "https://example.invalid/app.zip",
        "sha256": "0" * 64,
        "validation_status": "example",
    })
    assert status == 202
    assert receipt["receipt_hash"]


if __name__ == "__main__":
    test_registry_shape()
    test_route_and_import_receipt()
    print("connector control plane smoke tests passed")
