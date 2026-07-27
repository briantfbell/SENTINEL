# Sentinel

A local-first home monitoring and deterrence platform.

Sentinel watches a camera, detects a person, escalates through a series of
audible announcements, records the event, and surfaces all of it on a
wall-mounted touchscreen. Everything runs on hardware in the house. Unplug
the Internet and it keeps working.

It is not a replacement for a commercial alarm system. It is a last line of
defense, and a platform intended to grow for years.

---

## Status

Pre-alpha. See `AGENTS.md` section 10 for the build plan and current slice.

---

## Design principles

- **Local only.** No cloud, no accounts, no outbound traffic.
- **Readable over clever.** Optimized for the engineer who inherits it.
- **Every subsystem independently replaceable.** Cameras, detectors, and
  audio backends sit behind interfaces with working mocks.
- **Testable without hardware.** The full suite runs on a laptop.
- **Portable.** The Pi can be swapped for an Intel mini PC without
  architectural change.

---

## Hardware

| Role    | Component                            | Notes                                                   |
| ------- | ------------------------------------ | ------------------------------------------------------- |
| Server  | Raspberry Pi 5, 8GB                  |                                                         |
| Storage | M.2 HAT+ with 256GB NVMe             | Not an SD card. Continuous recording destroys SD cards. |
| Clock   | ML2020 RTC battery                   | Pi 5 has a built-in RTC. No Internet means no NTP.      |
| Camera  | PoE IP camera with dual RTSP streams | Detect on the substream, record from the main stream.   |
| Network | PoE injector or small PoE switch     |                                                         |
| Audio   | USB DAC plus a powered speaker       | The Pi 5 has no analog audio output.                    |
| Display | Amazon Fire tablet in kiosk mode     | Wall mounted, permanent USB power.                      |

Full bill of materials and wiring in `docs/hardware.md`.

---

## Stack

Python 3.12, FastAPI, Jinja2 plus HTMX, SQLite via SQLAlchemy, OpenCV,
ONNX Runtime, uv, pytest. No JavaScript build step.

---

## Quick start

```bash
# development, mock hardware, works on any machine
uv sync
cp config/sentinel.example.toml config/sentinel.toml
uv run sentinel-admin set-pin
uv run sentinel
```

Dashboard at `http://localhost:8000`.

For a containerized dev environment with mock providers:

```bash
docker compose up
```

Production deployment onto a Pi is documented in `docs/deployment.md`.
Containers are for development and CI only, the Pi runs on the host under
systemd.

---

## Repository layout

```
sentinel/
    config/        Configuration loading and validation
    models/        Domain types, enums, events
    database/      ORM models and repositories
    events/        Async event bus
    state/         State machine and transition table
    rules/         Rule engine
    camera/        Camera providers
    detection/     Person detection providers
    audio/         Audio playback providers
    services/      Orchestration and composition root
    api/           HTTP endpoints
    dashboard/     Templates and static assets
docs/              Architecture, event flow, configuration, decisions
tests/
deploy/            systemd units and kiosk configuration
```

---

## How it behaves

```
DISARMED -> ARMED -> ALERT -> WARNING -> ESCALATED
                       |         |          |
                       +---------+----------+--> COOLDOWN -> ARMED
```

Person detected while armed starts a grace period. Continued presence
triggers the first announcement, then a louder second one. Absence drops the
system into a cooldown before it re-arms, so someone pacing in and out of
frame does not restart the ladder every ten seconds. Disarming wins from any
state.

Full transition table in `docs/state-machine.md`.

---

## Contributing

Read `AGENTS.md` first. It is the authoritative specification, including the
locked architectural decisions and the import contract between layers.
Design choices not covered there get an entry in `docs/DECISIONS.md`.

---

## License

TBD.
