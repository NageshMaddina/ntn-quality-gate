"""Mini satellite messaging service: device registration (attach), SMS,
SOS priority, gateway failover and metrics. A simulation for demonstrating
a system-test quality gate, not a real network."""
import logging
import os
import re
import statistics
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .link import SatelliteLink

# DEMO_BUG lets you inject a regression to show the gate catching it:
#   sos_no_priority  -> SOS gets the same retry budget as normal SMS
#   no_failover      -> a failed gateway is not replaced by the standby
DEMO_BUG = os.getenv("DEMO_BUG", "")

ATTACH_ATTEMPTS = 4
SMS_ATTEMPTS = 3
SOS_ATTEMPTS = 8
MAX_SMS_CHARS = 160
IMSI_RE = re.compile(r"^\d{15}$")

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename="logs/service.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("satsvc")

app = FastAPI(title="NTN Messaging Simulator")
link = SatelliteLink()
devices: dict[str, dict] = {}
metrics: dict = {}


def reset_metrics():
    metrics.clear()
    metrics.update(attach_ok=0, attach_fail=0, sms_delivered=0, sms_failed=0,
                   sos_delivered=0, sos_failed=0, sms_latency=[], sos_latency=[])


reset_metrics()


class RegisterReq(BaseModel):
    imsi: str


class MessageReq(BaseModel):
    from_imsi: str
    to: str
    text: str
    sos: bool = False


class LinkReq(BaseModel):
    one_way_delay_ms: float | None = None
    jitter_ms: float | None = None
    loss_pct: float | None = None
    seed: int | None = None


@app.get("/health")
def health():
    return {"status": "ok", "link_available": link.available, "demo_bug": DEMO_BUG or None}


@app.post("/devices/register")
def register(req: RegisterReq):
    if not IMSI_RE.match(req.imsi):
        log.warning("attach rejected imsi=%s reason=invalid_imsi", req.imsi)
        raise HTTPException(422, "IMSI must be 15 digits")
    ok, attempts, latency = link.transmit(ATTACH_ATTEMPTS)
    if not ok:
        metrics["attach_fail"] += 1
        log.error("attach failed imsi=%s attempts=%s gateway=%s link=%s",
                  req.imsi, attempts, link.active_gateway, link.state())
        raise HTTPException(503, "Satellite link unavailable")
    devices[req.imsi] = {"state": "REGISTERED", "gateway": link.active_gateway}
    metrics["attach_ok"] += 1
    log.info("attach ok imsi=%s attempts=%s latency_ms=%.0f gateway=%s",
             req.imsi, attempts, latency, link.active_gateway)
    return {"imsi": req.imsi, "state": "REGISTERED", "attempts": attempts,
            "latency_ms": round(latency), "gateway": link.active_gateway}


@app.get("/devices/{imsi}")
def get_device(imsi: str):
    if imsi not in devices:
        raise HTTPException(404, "Unknown device")
    return {"imsi": imsi, **devices[imsi]}


@app.post("/messages")
def send_message(req: MessageReq):
    if req.from_imsi not in devices:
        log.warning("sms rejected from=%s reason=not_registered", req.from_imsi)
        raise HTTPException(403, "Device not registered")
    if len(req.text) > MAX_SMS_CHARS:
        raise HTTPException(422, f"Message exceeds {MAX_SMS_CHARS} characters")
    budget = SOS_ATTEMPTS if req.sos and DEMO_BUG != "sos_no_priority" else SMS_ATTEMPTS
    ok, attempts, latency = link.transmit(budget)
    kind = "sos" if req.sos else "sms"
    if not ok:
        metrics[f"{kind}_failed"] += 1
        log.error("%s failed from=%s attempts=%s budget=%s loss_pct=%s gateway=%s available=%s",
                  kind, req.from_imsi, attempts, budget, link.loss_pct,
                  link.active_gateway, link.available)
        raise HTTPException(504, {"status": "FAILED", "attempts": attempts, "budget": budget})
    metrics[f"{kind}_delivered"] += 1
    metrics[f"{kind}_latency"].append(latency)
    log.info("%s delivered from=%s attempts=%s budget=%s latency_ms=%.0f gateway=%s",
             kind, req.from_imsi, attempts, budget, latency, link.active_gateway)
    return {"status": "DELIVERED", "attempts": attempts, "latency_ms": round(latency),
            "gateway": link.active_gateway, "sos": req.sos}


def _p95(values):
    if len(values) < 2:
        return round(values[0]) if values else None
    return round(statistics.quantiles(values, n=20)[18])


@app.get("/metrics")
def get_metrics():
    return {
        "attach_ok": metrics["attach_ok"], "attach_fail": metrics["attach_fail"],
        "sms_delivered": metrics["sms_delivered"], "sms_failed": metrics["sms_failed"],
        "sos_delivered": metrics["sos_delivered"], "sos_failed": metrics["sos_failed"],
        "sms_p95_latency_ms": _p95(metrics["sms_latency"]),
        "sos_p95_latency_ms": _p95(metrics["sos_latency"]),
        "link": link.state(),
    }


# ---- admin / test-control endpoints (a lab would drive an emulator here) ----
@app.post("/admin/reset")
def admin_reset():
    link.reset()
    devices.clear()
    reset_metrics()
    log.info("lab reset")
    return {"status": "reset"}


@app.post("/admin/link")
def admin_link(req: LinkReq):
    link.configure(**req.model_dump())
    log.info("link configured %s", link.state())
    return link.state()


@app.post("/admin/gateways/{name}/fail")
def admin_fail_gateway(name: str):
    if name not in link.gateways:
        raise HTTPException(404, "Unknown gateway")
    link.fail_gateway(name, allow_failover=DEMO_BUG != "no_failover")
    log.warning("gateway failed name=%s active_now=%s available=%s",
                name, link.active_gateway, link.available)
    return link.state()


@app.post("/admin/gateways/{name}/restore")
def admin_restore_gateway(name: str):
    if name not in link.gateways:
        raise HTTPException(404, "Unknown gateway")
    link.restore_gateway(name)
    log.info("gateway restored name=%s active_now=%s", name, link.active_gateway)
    return link.state()
