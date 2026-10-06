#!/usr/bin/env bash
# Runs the full quality gate locally: start service -> tests -> gate -> triage -> dashboard.
# Usage:  ./run_pipeline.sh                 (clean build, should ship)
#         DEMO_BUG=sos_no_priority ./run_pipeline.sh   (injected regression, should block)
#         DEMO_BUG=no_failover ./run_pipeline.sh
set -u
export TIME_SCALE="${TIME_SCALE:-0.25}"   # speeds up simulated delays; reported latency stays real
rm -rf results logs && mkdir -p results logs

python3 -m uvicorn app.main:app --port 8000 --log-level warning &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 30); do curl -sf http://127.0.0.1:8000/health >/dev/null && break; sleep 0.5; done

python3 -m robot --outputdir results --consolewidth 90 tests || true
python3 tools/gate.py; GATE=$?
python3 tools/triage.py
python3 tools/report.py
cp logs/service.log results/ 2>/dev/null || true
exit $GATE
