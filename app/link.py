"""Simulated GEO satellite link: propagation delay, jitter, packet loss,
retransmissions, and ground gateways with failover.

Numbers are illustrative: a GEO satellite at ~35,786 km gives roughly
270 ms one-way through a transparent (bent-pipe) payload.
"""
import os
import random
import threading
import time

TIME_SCALE = float(os.getenv("TIME_SCALE", "1.0"))  # <1.0 makes tests run faster


class SatelliteLink:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self, seed: int = 42):
        with self._lock:
            self.one_way_delay_ms = 270.0
            self.jitter_ms = 20.0
            self.loss_pct = 0.0
            self.rng = random.Random(seed)
            self.gateways = {"gw-primary": True, "gw-secondary": True}
            self.active_gateway = "gw-primary"
            self.failover_count = 0

    def configure(self, one_way_delay_ms=None, jitter_ms=None, loss_pct=None, seed=None):
        with self._lock:
            if one_way_delay_ms is not None:
                self.one_way_delay_ms = float(one_way_delay_ms)
            if jitter_ms is not None:
                self.jitter_ms = float(jitter_ms)
            if loss_pct is not None:
                self.loss_pct = float(loss_pct)
            if seed is not None:
                self.rng = random.Random(seed)

    # ---- gateways -------------------------------------------------------
    def fail_gateway(self, name: str, allow_failover: bool = True):
        with self._lock:
            self.gateways[name] = False
            if self.active_gateway == name and allow_failover:
                for gw, up in self.gateways.items():
                    if up:
                        self.active_gateway = gw
                        self.failover_count += 1
                        break

    def restore_gateway(self, name: str):
        with self._lock:
            self.gateways[name] = True
            if not self.gateways.get(self.active_gateway, False):
                self.active_gateway = name

    @property
    def available(self) -> bool:
        return self.gateways.get(self.active_gateway, False)

    # ---- transmission ---------------------------------------------------
    def transmit(self, max_attempts: int):
        """Send one packet and wait for its ACK, retransmitting on loss.

        Returns (delivered, attempts, simulated_latency_ms)."""
        if not self.available:
            return False, 0, 0.0
        latency = 0.0
        for attempt in range(1, max_attempts + 1):
            with self._lock:
                rtt = 2 * (self.one_way_delay_ms + self.rng.uniform(-self.jitter_ms, self.jitter_ms))
                lost = self.rng.random() * 100 < self.loss_pct
            latency += rtt
            time.sleep(rtt * TIME_SCALE / 1000)
            if not lost:
                return True, attempt, latency
        return False, max_attempts, latency

    def state(self):
        return {
            "one_way_delay_ms": self.one_way_delay_ms,
            "jitter_ms": self.jitter_ms,
            "loss_pct": self.loss_pct,
            "gateways": dict(self.gateways),
            "active_gateway": self.active_gateway,
            "failover_count": self.failover_count,
        }
