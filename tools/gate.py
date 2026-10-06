"""Release gate: reads Robot Framework results, the requirement list and
recorded KPIs, then decides PASS (ship) or BLOCK. Exit code 1 blocks CI."""
import json
import sys
from pathlib import Path

import yaml
from robot.api import ExecutionResult, ResultVisitor

RESULTS = Path("results")


class Collector(ResultVisitor):
    def __init__(self):
        self.tests = []

    def visit_test(self, test):
        self.tests.append({
            "name": test.name,
            "suite": test.parent.name,
            "status": test.status,
            "message": test.message,
            "tags": list(test.tags),
            "elapsed_s": round(test.elapsed_time.total_seconds(), 2),
        })


def main():
    cfg = yaml.safe_load(Path("gate.yaml").read_text())
    reqs = yaml.safe_load(Path("requirements.yaml").read_text())
    kpis = json.loads((RESULTS / "kpis.json").read_text()) if (RESULTS / "kpis.json").exists() else {}

    collector = Collector()
    ExecutionResult(str(RESULTS / "output.xml")).visit(collector)
    tests = collector.tests

    def pass_rate(ts):
        return round(100 * sum(t["status"] == "PASS" for t in ts) / len(ts), 1) if ts else 100.0

    critical_tests = [t for t in tests if "critical" in t["tags"]]

    # Requirement traceability: which tests cover each requirement, and its status.
    trace = []
    for r in reqs:
        covering = [t for t in tests if r["id"] in t["tags"]]
        if not covering:
            status = "NOT COVERED"
        elif all(t["status"] == "PASS" for t in covering):
            status = "PASS"
        else:
            status = "FAIL"
        trace.append({**r, "tests": [t["name"] for t in covering], "status": status})

    crit_reqs = [r for r in trace if r.get("critical")]
    crit_cov = round(100 * sum(r["status"] != "NOT COVERED" for r in crit_reqs) / len(crit_reqs), 1)

    checks = [
        {"check": "Critical test pass rate", "value": pass_rate(critical_tests),
         "target": f">= {cfg['critical_pass_rate_pct']}%",
         "ok": pass_rate(critical_tests) >= cfg["critical_pass_rate_pct"]},
        {"check": "Overall test pass rate", "value": pass_rate(tests),
         "target": f">= {cfg['overall_pass_rate_pct']}%",
         "ok": pass_rate(tests) >= cfg["overall_pass_rate_pct"]},
        {"check": "Critical requirement coverage", "value": crit_cov,
         "target": f">= {cfg['critical_requirement_coverage_pct']}%",
         "ok": crit_cov >= cfg["critical_requirement_coverage_pct"]},
    ]
    for name, rule in cfg.get("kpis", {}).items():
        value = kpis.get(name)
        if "max" in rule:
            ok, target = value is not None and value <= rule["max"], f"<= {rule['max']}"
        else:
            ok, target = value is not None and value >= rule["min"], f">= {rule['min']}"
        checks.append({"check": f"KPI {name}", "value": value, "target": target, "ok": ok})

    decision = "PASS" if all(c["ok"] for c in checks) else "BLOCK"
    out = {"decision": decision, "checks": checks, "tests": tests,
           "traceability": trace, "kpis": kpis}
    (RESULTS / "gate.json").write_text(json.dumps(out, indent=2))

    print(f"\nRELEASE GATE: {decision}")
    for c in checks:
        print(f"  [{'OK ' if c['ok'] else 'XX '}] {c['check']}: {c['value']} (target {c['target']})")
    gaps = [r["id"] for r in trace if r["status"] == "NOT COVERED"]
    if gaps:
        print(f"  Coverage gaps (non-critical): {', '.join(gaps)}")
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
