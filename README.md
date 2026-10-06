# NTN Release Quality Gate (demo)

A small, end-to-end system-test pipeline for a **simulated** satellite (NTN) messaging service.
It shows how I'd run a release gate for a direct-to-device satellite service: service-level
acceptance tests, NTN-specific behaviour, requirement traceability, KPIs, AI failure triage,
and a hard ship/block decision in CI.

> This is a simulation built to demonstrate approach. It does not use real satellite links,
> real radio protocols, or any company's systems.

## What's in it

| Layer | File | What it does |
| --- | --- | --- |
| Service under test | `app/main.py` | Device registration (attach), SMS, SOS priority, gateway failover, metrics |
| Satellite link emulator | `app/link.py` | GEO delay (~270 ms one way), jitter, packet loss, retransmissions, two ground gateways |
| Tests | `tests/*.robot` | Robot Framework suites: attach, messaging, degraded link, failover |
| Requirements | `requirements.yaml` | 12 requirements; tests trace to them by tag (e.g. `REQ-SOS-01`) |
| Release gate | `gate.yaml`, `tools/gate.py` | Pass-rate, coverage and KPI thresholds → `PASS` or `BLOCK` |
| AI triage | `tools/triage.py` | Pairs each failure with service logs; Claude suggests root cause (rules fallback offline) |
| Dashboard | `tools/report.py` | One-page HTML: decision, KPIs, triage, traceability, results |
| CI | `.github/workflows/quality-gate.yml` | Runs everything on each push; a blocked gate fails the build |

## Run it locally

```bash
pip install -r requirements.txt
./run_pipeline.sh                              # clean build → RELEASE GATE: PASS
DEMO_BUG=sos_no_priority ./run_pipeline.sh     # SOS loses its retry priority → BLOCK
DEMO_BUG=no_failover ./run_pipeline.sh         # gateway failover broken → BLOCK
open results/dashboard.html
```

Takes about 1–2 minutes. `TIME_SCALE` (default 0.25) speeds up the simulated waits;
reported latencies stay at real GEO values.

Optional: `export ANTHROPIC_API_KEY=...` to switch triage from rules to Claude
(`TRIAGE_MODEL` picks the model).

## Run it in GitHub Actions

Push the repo to GitHub. Every push runs the gate. To show a blocked release, go to
**Actions → Release quality gate → Run workflow** and enter `sos_no_priority` or
`no_failover`. The dashboard is attached to each run as the `release-gate-results` artifact.

## Gate rules (`gate.yaml`)

- 100% of release-critical tests pass
- ≥ 95% of all tests pass
- 100% of critical requirements have at least one test
- SMS p95 latency ≤ 1,500 ms on a clean GEO link
- SOS delivery ≥ 90% at 70% packet loss

`REQ-ROAM-01` (partner-MNO roaming) is deliberately uncovered: it's non-critical, so the
gate passes but the dashboard flags the gap.

## How this maps to a real NTN lab

| Demo | Real lab |
| --- | --- |
| `app/link.py` delay/loss | Satellite channel emulator (delay, Doppler, fading, beam changes) |
| `/admin/*` endpoints | Lab control APIs driving emulators, gateways and device farms |
| One service | Devices + satellite + gateway + cloud vRAN + core + MNO partner networks |
| Rule/AI triage over logs | Triage over device logs, RAN/core protocol traces and observability data |
| GitHub Actions | GCP-hosted test agents and the formal change-control gate before Ops handoff |
