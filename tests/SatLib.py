"""Helper keywords for the Robot suites."""
import json
import statistics
from pathlib import Path

KPI_FILE = Path("results/kpis.json")


def record_kpi(name, value):
    """Persist a KPI so the release gate and dashboard can read it."""
    KPI_FILE.parent.mkdir(exist_ok=True)
    data = json.loads(KPI_FILE.read_text()) if KPI_FILE.exists() else {}
    data[name] = float(value)
    KPI_FILE.write_text(json.dumps(data, indent=2))


def p95_of(values):
    values = [float(v) for v in values]
    if len(values) < 2:
        return values[0]
    return round(statistics.quantiles(values, n=20)[18], 1)


def make_imsi(n):
    """Build a 15-digit test IMSI (test PLMN 001-01)."""
    return f"00101{int(n):010d}"
