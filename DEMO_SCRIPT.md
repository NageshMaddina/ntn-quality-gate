# 5-minute walkthrough (for the interview)

1. **The problem (30 s).** "A satellite service has failure modes terrestrial testing misses:
   ~540 ms round trips, heavy packet loss, gateway outages, SOS that must get through.
   The System Test gate has to prove those before a release reaches Operations."
2. **Requirements → tests (60 s).** Open `requirements.yaml`, then a `.robot` file. Point to the
   `REQ-` tags: every critical requirement is traced to a test.
3. **Green run (60 s).** Show a passing GitHub Actions run and its dashboard: Ship it, p95 latency
   ~580 ms, SOS 100% at 70% loss, REQ-ROAM-01 flagged as a known coverage gap.
4. **Inject a regression (90 s).** Run the workflow with `sos_no_priority`. The gate blocks:
   SOS delivery drops to ~68%, and triage names the cause (SOS lost its retry priority).
5. **Map to the real job (60 s).** Use the table at the end of the README: the link emulator
   becomes channel emulators, the admin API becomes lab control, GitHub Actions becomes
   GCP agents plus change control, and triage scales to RAN/core traces.

Likely follow-ups: why those thresholds? (agreed with product and Ops per release) ·
how do you avoid flaky tests on a lossy link? (seeded loss, statistical thresholds, many samples) ·
what would you add next? (Doppler and LEO handover, device farm, MNO partner test kit).
