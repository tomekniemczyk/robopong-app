# E2E Tests (Playwright, simulation mode)

Full-stack smoke suite that spins up the backend in **simulation mode** and drives both v1 and v2 UIs via headless Chromium. Runs post-deploy to confirm the app actually works end-to-end.

## Running

```bash
# One-time setup
./e2e/setup.sh

# Run the suite
./e2e/run.sh
```

The suite boots the backend on port **8766** (non-default so it doesn't clash with dev) with `SIMULATION=1`, waits for the health endpoint, runs tests, then kills the server.

## Coverage

- `test_v1_smoke.py` — REST/API endpoints, v1 nav, Serves tab, detail panel (SVG, spin bars, responses, buttons), language switching.
- `test_v2_smoke.py` — parity check for v2 (same logic, different CSS).
- `test_serves_flow.py` — full Serves flow in simulation: select serve → run in timer mode → verify training overlay → stop.

## Why simulation mode

Real BLE/USB robots aren't available in CI or during automated post-deploy verification. `SimulationTransport` fakes the hardware while running the full codepath — handshake, drill loops, events — so the UI exercises the same integration points.
