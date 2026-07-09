#!/usr/bin/env python3
"""NOVA Connector Control Plane development server.

The server is dependency-free and receipt-first. It does not invoke external AI
systems directly. It routes connector tasks, records proof gates, and creates
artifact import receipts for later persistence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "connectors.json"

ROUTE_HINTS = {
    "caffeine": "caffeine-mtp-bridge",
    "grok": "grok-build-bridge",
    "claude": "claude-code-bridge",
    "cursor": "cursor-ide-bridge",
    "antigravity": "antigravity-terminal-bridge",
    "terminal": "antigravity-terminal-bridge",
    "browser": "browser-workbench-bridge",
    "service worker": "browser-workbench-bridge",
    "mcp": "generic-mcp-gateway",
    "oauth": "chatgpt-app-oauth-bridge",
    "chatgpt": "chatgpt-app-oauth-bridge",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ConnectorState:
    def __init__(self) -> None:
        self.registry = load_json(REGISTRY_PATH)
        self.connectors = {item["id"]: item for item in self.registry.get("connectors", [])}

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "nova-connector-control-plane",
            "time": utc_now(),
            "connector_count": len(self.connectors),
        }

    def describe(self, connector_id: str) -> tuple[int, dict[str, Any]]:
        connector = self.connectors.get(connector_id)
        if not connector:
            return 404, {"status": "not_found", "known_connectors": sorted(self.connectors)}
        return 200, {"status": "ok", "connector": connector}

    def route(self, request: dict[str, Any]) -> dict[str, Any]:
        haystack = f"{request.get('task', '')} {request.get('target_surface', '')}".lower()
        connector_id = "generic-mcp-gateway"
        for hint, candidate in ROUTE_HINTS.items():
            if hint in haystack:
                connector_id = candidate
                break
        connector = self.connectors[connector_id]
        return {
            "schema": "nova.connector.route_plan.v1",
            "status": "planned",
            "connector_id": connector_id,
            "connector_name": connector.get("name"),
            "surface": connector.get("surface"),
            "risk_level": request.get("risk_level", "unknown"),
            "permission_boundary": request.get("permission_boundary", "operator approval required before execution"),
            "proof_gates": connector.get("proof_gates", []),
            "next_gate": "submit bounded task or import artifact receipt",
        }

    def import_artifact(self, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        connector_id = request.get("connector_id")
        if connector_id not in self.connectors:
            return 404, {"status": "rejected", "reason": "unknown_connector_id", "known_connectors": sorted(self.connectors)}
        artifact = {
            "connector_id": connector_id,
            "artifact_url": request.get("artifact_url", ""),
            "sha256": request.get("sha256", ""),
            "validation_status": request.get("validation_status", "unverified"),
            "time": utc_now(),
        }
        return 202, {
            "schema": "nova.connector.artifact_import_receipt.v1",
            "status": "accepted_for_review",
            "artifact": artifact,
            "receipt_hash": stable_hash(artifact),
            "next_gate": "operator validation before NOVA import",
        }


class Handler(BaseHTTPRequestHandler):
    state: ConnectorState

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        print(f"[{utc_now()}] {self.address_string()} {format % args}")

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json(200, self.state.health())
        elif path == "/connectors":
            self.send_json(200, self.state.registry)
        elif path.startswith("/connectors/"):
            status, payload = self.state.describe(path.removeprefix("/connectors/").strip("/"))
            self.send_json(status, payload)
        else:
            self.send_json(404, {"paths": ["/health", "/connectors", "/connectors/{id}", "POST /route", "POST /artifacts/import"]})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self.read_json_body()
        except json.JSONDecodeError as exc:
            self.send_json(400, {"status": "rejected", "reason": "invalid_json", "detail": str(exc)})
            return
        if path == "/route":
            self.send_json(200, self.state.route(body))
        elif path == "/artifacts/import":
            status, payload = self.state.import_artifact(body)
            self.send_json(status, payload)
        else:
            self.send_json(404, {"paths": ["POST /route", "POST /artifacts/import"]})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NOVA Connector Control Plane")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    Handler.state = ConnectorState()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"NOVA Connector Control Plane listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
