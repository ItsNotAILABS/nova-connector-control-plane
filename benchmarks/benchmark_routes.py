#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "server" / "connector_control_plane.py"

spec = importlib.util.spec_from_file_location("connector_control_plane", SERVER_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

state = module.ConnectorState()
requests = [
    {"task": "build with caffeine", "target_surface": "caffeine mtp", "risk_level": "medium"},
    {"task": "review code with claude", "target_surface": "repo", "risk_level": "low"},
    {"task": "inspect browser service worker", "target_surface": "browser", "risk_level": "medium"},
    {"task": "discover mcp tools", "target_surface": "mcp", "risk_level": "medium"},
]
iterations = 1000
start = time.perf_counter()
for index in range(iterations):
    state.route(requests[index % len(requests)])
elapsed = time.perf_counter() - start
print({
    "benchmark": "connector_route_plan",
    "iterations": iterations,
    "elapsed_seconds": round(elapsed, 6),
    "routes_per_second": round(iterations / elapsed, 2),
})
