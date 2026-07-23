# Human and AI Workflows

## Human Operator Flow

1. Validate registry: `python tools/connectorctl.py validate`.
2. List connectors: `python tools/connectorctl.py list`.
3. Pick the connector based on task and risk.
4. Run the API server: `python server/connector_control_plane.py --port 8770`.
5. Submit a route plan using `examples/route-plan.json`.
6. Review proof gates before invoking any external worker.
7. Import artifacts only with URL, SHA-256, validation status, and operator approval.

## AI Worker Flow

1. Read `nova-connector-control-plane.manifest.json`.
2. Read `data/connectors.json`.
3. Call or emulate `POST /route` to select a connector.
4. Preserve the returned permission boundary and proof gates.
5. Never claim external execution unless an artifact receipt exists.

## Proof Outputs

- Route plan
- Artifact import receipt
- Connector ID
- Permission boundary
- Proof gates
- Receipt hash

## Live Test Commands

```bash
python tools/connectorctl.py validate
python tests/smoke_test.py
python benchmarks/benchmark_routes.py
python server/connector_control_plane.py --port 8770
```
