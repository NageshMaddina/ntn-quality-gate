"""Builds results/dashboard.html: one page a release manager can read in a minute."""
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

RESULTS = Path("results")


def esc(v):
    return html.escape(str(v))


def main():
    gate = json.loads((RESULTS / "gate.json").read_text())
    triage = json.loads((RESULTS / "triage.json").read_text()) if (RESULTS / "triage.json").exists() else []
    tests = gate["tests"]
    passed = sum(t["status"] == "PASS" for t in tests)
    decision = gate["decision"]
    build = os.getenv("GITHUB_SHA", "local")[:7]
    bug = os.getenv("DEMO_BUG") or "none"
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    checks = "".join(
        f"<tr><td>{esc(c['check'])}</td><td class=num>{esc(c['value'])}</td>"
        f"<td class=num>{esc(c['target'])}</td><td><span class='pill {'ok' if c['ok'] else 'bad'}'>"
        f"{'Pass' if c['ok'] else 'Fail'}</span></td></tr>" for c in gate["checks"])

    status_cls = {"PASS": "ok", "FAIL": "bad", "NOT COVERED": "warn"}
    trace = "".join(
        f"<tr><td class=mono>{esc(r['id'])}</td><td>{esc(r['title'])}"
        f"{' <span class=crit>critical</span>' if r.get('critical') else ''}</td>"
        f"<td>{esc(', '.join(r['tests']) or '—')}</td>"
        f"<td><span class='pill {status_cls[r['status']]}'>{esc(r['status'].title())}</span></td></tr>"
        for r in gate["traceability"])

    tri = "".join(
        f"<div class=card><div class=row><strong>{esc(f['test'])}</strong>"
        f"<span class='pill bad'>{esc(f['severity'])}</span></div>"
        f"<p>{esc(f['likely_root_cause'])}</p>"
        f"<p class=muted>Component: {esc(f['component'])} · Next step: {esc(f['next_step'])}</p>"
        f"<p class=muted small>Triage engine: {esc(f['engine'])}</p></div>" for f in triage
    ) or "<p class=muted>No failures in this run.</p>"

    test_rows = "".join(
        f"<tr><td>{esc(t['suite'])}</td><td>{esc(t['name'])}</td><td class=num>{t['elapsed_s']}s</td>"
        f"<td><span class='pill {'ok' if t['status'] == 'PASS' else 'bad'}'>{esc(t['status'].title())}</span></td></tr>"
        for t in tests)

    k = gate.get("kpis", {})
    tiles = [
        ("Tests passed", f"{passed}/{len(tests)}"),
        ("SMS p95 latency", f"{k.get('sms_p95_latency_ms', '—')} ms"),
        ("SOS delivery @ 70% loss", f"{k.get('sos_delivery_pct_at_70_loss', '—')}%"),
        ("Requirements covered",
         f"{sum(r['status'] != 'NOT COVERED' for r in gate['traceability'])}/{len(gate['traceability'])}"),
    ]
    tile_html = "".join(f"<div class=tile><div class=muted small>{esc(a)}</div><div class=big>{esc(b)}</div></div>"
                        for a, b in tiles)

    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>NTN Release Gate</title>
<style>
:root{{--bg:#f7f7f5;--panel:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e3e2dd;
--ok:#1f7a4d;--okbg:#e3f3ea;--bad:#b42318;--badbg:#fdeceb;--warn:#8a5a00;--warnbg:#fdf3dc;--accent:#2b5fd9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--panel:#1e1e1c;--ink:#ecebe6;--muted:#a3a29b;--line:#33332f;
--ok:#5fd39a;--okbg:#173327;--bad:#ff8a80;--badbg:#3a1a18;--warn:#f2c46b;--warnbg:#3a2e14;--accent:#8fb0ff}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}}
main{{max-width:1040px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;margin:0}} h2{{font-size:16px;margin:32px 0 10px}}
.muted{{color:var(--muted)}} .small{{font-size:12.5px}} .mono{{font-family:ui-monospace,Menlo,monospace;font-size:13px;white-space:nowrap}}
.hero{{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between;
background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px}}
.badge{{font-size:20px;font-weight:700;padding:10px 18px;border-radius:10px}}
.badge.PASS{{background:var(--okbg);color:var(--ok)}} .badge.BLOCK{{background:var(--badbg);color:var(--bad)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:16px}}
.tile,.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.card{{margin-bottom:10px}} .card p{{margin:6px 0 0}} .row{{display:flex;justify-content:space-between;gap:12px;align-items:center}}
.big{{font-size:22px;font-weight:650;margin-top:2px}}
.wrap{{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px}}
table{{border-collapse:collapse;width:100%;min-width:560px}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:12.5px;color:var(--muted);font-weight:600}} tr:last-child td{{border-bottom:0}}
.num{{white-space:nowrap}}
.pill{{display:inline-block;font-size:12.5px;font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap}}
.pill.ok{{background:var(--okbg);color:var(--ok)}} .pill.bad{{background:var(--badbg);color:var(--bad)}}
.pill.warn{{background:var(--warnbg);color:var(--warn)}}
.crit{{font-size:11px;color:var(--accent);border:1px solid currentColor;border-radius:4px;padding:0 4px;margin-left:4px}}
a{{color:var(--accent)}}
</style></head><body><main>
<div class=hero><div><h1>NTN messaging service — release gate</h1>
<div class="muted small">Build {esc(build)} · {esc(when)} · injected bug: {esc(bug)} · simulated GEO link</div></div>
<div class="badge {decision}">{'Ship it' if decision == 'PASS' else 'Release blocked'}</div></div>
<div class=tiles>{tile_html}</div>
<h2>Gate checks</h2><div class=wrap><table><tr><th>Check</th><th>Value</th><th>Target</th><th>Result</th></tr>{checks}</table></div>
<h2>Failure triage</h2>{tri}
<h2>Requirement traceability</h2><div class=wrap><table><tr><th>ID</th><th>Requirement</th><th>Covered by</th><th>Status</th></tr>{trace}</table></div>
<h2>Test results</h2><div class=wrap><table><tr><th>Suite</th><th>Test</th><th>Time</th><th>Result</th></tr>{test_rows}</table></div>
<p class="muted small">Full Robot Framework trace: <a href="log.html">log.html</a> · <a href="report.html">report.html</a></p>
</main></body></html>"""
    (RESULTS / "dashboard.html").write_text(page)
    print(f"Dashboard: {RESULTS / 'dashboard.html'}")


if __name__ == "__main__":
    main()
