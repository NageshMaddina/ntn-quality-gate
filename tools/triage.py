"""AI failure triage: for each failed test, pair the failure with the
service log lines around it and ask an LLM for a likely root cause.

With ANTHROPIC_API_KEY set it calls Claude; without it, it falls back to
simple rules so the pipeline still works offline."""
import json
import os
from pathlib import Path

RESULTS = Path("results")
LOG = Path("logs/service.log")
MODEL = os.getenv("TRIAGE_MODEL", "claude-sonnet-4-5")

PROMPT = """You are triaging a failed system test for a satellite (NTN) messaging service.
Test: {name}
Requirements: {reqs}
Failure message: {message}
Relevant service log lines:
{logs}

Reply in JSON with keys: likely_root_cause (one sentence), component (device, satellite link,
gateway, RAN, core, or test), severity (blocker, major, minor), next_step (one sentence)."""


def relevant_logs(limit=25):
    if not LOG.exists():
        return []
    lines = LOG.read_text().splitlines()
    hits = [l for l in lines if " ERROR " in l or " WARNING " in l]
    return hits[-limit:]


def rule_based(test, logs):
    msg = test["message"].lower()
    text = " ".join(logs).lower()
    if "sos" in msg or "sos" in test["name"].lower():
        budget_hint = "budget=3" in text and "sos failed" in text
        return {
            "likely_root_cause": "SOS messages are exhausting a 3-attempt retransmission budget; "
                                 "SOS priority (extended retry budget) appears to be missing."
                                 if budget_hint else
                                 "SOS delivery fell below target under packet loss.",
            "component": "core", "severity": "blocker",
            "next_step": "Check the SOS retry/priority configuration in the messaging service.",
        }
    if "gateway" in test["name"].lower() or "interrupted" in msg:
        return {
            "likely_root_cause": "Traffic stayed on a failed ground gateway; failover to the standby did not occur."
                                 if "available=false" in text else
                                 "Gateway failover did not behave as specified.",
            "component": "gateway", "severity": "blocker",
            "next_step": "Review gateway health detection and failover logic.",
        }
    if "latency" in msg:
        return {"likely_root_cause": "End-to-end latency exceeded budget; check link delay settings or added retransmissions.",
                "component": "satellite link", "severity": "major",
                "next_step": "Compare per-attempt latency in logs with the expected GEO round trip."}
    return {"likely_root_cause": "Unclassified failure; review the Robot log.",
            "component": "test", "severity": "major", "next_step": "Open results/log.html for the full trace."}


def claude_triage(test, logs):
    import anthropic
    client = anthropic.Anthropic()
    reqs = [t for t in test["tags"] if t.startswith("REQ-")]
    resp = client.messages.create(
        model=MODEL, max_tokens=400,
        messages=[{"role": "user", "content": PROMPT.format(
            name=test["name"], reqs=", ".join(reqs), message=test["message"],
            logs="\n".join(logs) or "(none)")}],
    )
    text = resp.content[0].text
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def main():
    gate = json.loads((RESULTS / "gate.json").read_text())
    failed = [t for t in gate["tests"] if t["status"] != "PASS"]
    logs = relevant_logs()
    use_ai = bool(os.getenv("ANTHROPIC_API_KEY"))
    findings = []
    for t in failed:
        try:
            result = claude_triage(t, logs) if use_ai else rule_based(t, logs)
            engine = f"claude ({MODEL})" if use_ai else "rules (offline fallback)"
        except Exception as exc:  # never let triage break the pipeline
            result, engine = rule_based(t, logs), f"rules (AI call failed: {exc.__class__.__name__})"
        findings.append({"test": t["name"], "engine": engine, **result})
    (RESULTS / "triage.json").write_text(json.dumps(findings, indent=2))
    for f in findings:
        print(f"TRIAGE [{f['severity']}] {f['test']}: {f['likely_root_cause']}")
    if not findings:
        print("TRIAGE: no failures to triage")


if __name__ == "__main__":
    main()
