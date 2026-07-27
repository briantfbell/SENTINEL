# AGENTS.md

Build instructions for coding agents working in this repository.

Read this file completely before writing any code. It is the authoritative
specification. Where this file and the README disagree, this file wins.

---

## 1. Mission

Sentinel is a local-first home monitoring and deterrence platform.

It detects a person on camera, escalates through a series of audible
announcements, records the event, and shows all of it on a wall-mounted
touchscreen dashboard. It runs entirely on hardware in the house and
functions with the Internet cable unplugged.

This is not a commercial alarm system and does not try to be one. It is a
last line of defense and, equally, a long-lived software platform that will
have capabilities added to it for years.

**The single most important property of this codebase is that an engineer
who has never seen it can read one subsystem in isolation and understand it.**
Optimize for that above all else, including performance, brevity, and
cleverness.

---

## 2. Hard rules

These are non-negotiable. Violating any of them is a defect regardless of
whether tests pass.

1. **No network calls leave the LAN.** No telemetry, no cloud APIs, no CDN
   links in templates, no font or script fetched from the Internet at
   runtime. Vendor everything.
2. **No hardware required to run the test suite.** Every provider has a mock.
   `uv run pytest` must pass on a laptop with no camera, no speaker, and no
   network.
3. **The repository is always runnable.** Every commit leaves `uv run sentinel`
   in a working state. Never scaffold empty modules ahead of the feature that
   needs them.
4. **No dependency outside the approved list** in section 5 without asking.
   See section 13.
5. **No global mutable state.** No module-level singletons holding runtime
   state, no `global` keyword. Dependencies are passed in.
6. **Dependencies point downward only.** See the import contract in section 6.
   A circular import is a design error, not an import-order problem.
7. **Type hints and docstrings on every public function, method, and class.**
   Docstrings explain why and what, not a restatement of the signature.
8. **No clever code.** If a reviewer would need to pause, rewrite it longer
   and plainer. Explicit `if` chains beat comprehensions that do three things.

---

## 3. Non-goals

Do not build these. Do not add abstractions "in preparation" for them beyond
what is already specified. Speculative generality is the failure mode this
section exists to prevent.

- Multiple cameras (design the interface to allow it, implement exactly one)
- Face recognition, package detection, object tracking, license plates
- Zigbee, Z-Wave, smart lights, any home automation integration
- Mobile push notifications, email, SMS, any outbound alerting
- Remote access, port forwarding, VPN, tunnels, reverse proxies
- User accounts, roles, permissions, multi-tenancy
- A plugin system or dynamic module loading
- AI-generated event summaries
- A visual rule editor
- UPS monitoring, SSD archive tiering, multiple tablets
- Any message broker (Redis, MQTT, RabbitMQ, Kafka)
- Any ORM migration framework beyond what section 8 specifies
- A JavaScript build step of any kind

The MVP is done when section 10 is complete. Stop there.

---

## 4. Locked decisions

Each of these was decided deliberately. Do not revisit them, do not
"improve" them, and do not silently substitute an alternative. If you
believe one is wrong, stop and ask (section 13).

### 4.1 Frontend: Jinja2 templates plus HTMX

Rationale: the display is an Amazon Fire tablet running the Silk browser on
weak hardware, unattended for months. Server-rendered HTML with HTMX
partial-swap polling gives one source of truth, no bundler, no node_modules,
no client-side state to desynchronize. React is prohibited.

HTMX is vendored into `sentinel/dashboard/static/vendor/`. CSS is hand
written. No Tailwind, no framework, no build step, no CDN.

### 4.2 Live video: snapshot polling behind a StreamProvider interface

RTSP does not play natively in a browser. The MVP dashboard polls a JPEG
snapshot endpoint on an interval defined in config (default 1000ms) and
swaps the image.

This is deliberately the least impressive option because it is the one that
cannot break. The `StreamProvider` protocol must be shaped so that a
WebRTC implementation backed by go2rtc can be dropped in later without
touching the dashboard's contract beyond the URL it points at.

Do not implement MJPEG streaming, HLS, or WebRTC in the MVP.

### 4.3 Detection: motion gate, then ONNX Runtime with YOLOv8n

Running a detector on every frame will saturate the Pi. The pipeline is:

1. Pull a frame from the camera **substream** (low resolution).
2. Frame-difference against a rolling background. If motion below threshold,
   discard. This is cheap and rejects the overwhelming majority of frames.
3. On motion, downscale to the model input size and run inference.
4. Rate-limit inference to `detection.max_inference_fps` (default 3)
   regardless of motion.

Runtime is `onnxruntime` loading a `yolov8n.onnx` file from disk. The
`ultralytics` package is **prohibited as a runtime dependency** because it is
AGPL-licensed and this repository may be published. Model weights live in
`models/` on disk and are not committed to git.

The `Detector` protocol has at minimum a `MockDetector` and an
`OnnxPersonDetector`. Nothing outside `sentinel/detection/` may import
`onnxruntime`, `cv2`, or reference a model file path.

### 4.4 Detection semantics

A raw model hit is not an event. The detector emits `PersonDetected` only
when all of the following hold, all configurable:

| Parameter              | Default | Meaning                                        |
| ---------------------- | ------- | ---------------------------------------------- |
| `confidence_threshold` | 0.55    | Minimum box confidence to count as a hit       |
| `consecutive_frames`   | 3       | Consecutive qualifying frames before firing    |
| `absence_seconds`      | 8       | Continuous no-hit duration before `PersonGone` |
| `min_box_area_ratio`   | 0.01    | Reject boxes smaller than 1% of frame          |

Without this hysteresis the event stream flaps and the state machine
thrashes. Implement it inside the detection layer as a small, separately
tested `DetectionDebouncer` class that takes raw frame results and emits
domain events. This class must be testable with no model and no camera.

### 4.5 State machine and rule engine have separate jobs

- The **state machine** owns the system mode and the set of legal
  transitions. It is the only thing permitted to change state. It is a pure
  function of (current state, event) and performs no I/O.
- The **rule engine** decides what actions to fire in response to
  (event, state). It reads state and never writes it.

If both could change state you would have two sources of truth and an
unfindable bug. Enforce this: the state machine exposes no public setter,
only `handle(event) -> TransitionResult`.

### 4.6 Authentication is server-side

The PIN keypad is a UI affordance, not a security control. Anyone on the
Wi-Fi can reach the API directly.

- PIN is stored as an Argon2 hash in the config file, never in plaintext,
  never in the database, never in a template.
- Verification happens in the API layer only.
- Successful verification issues an opaque session token stored server-side
  with a TTL from config (default 900s), returned as an HttpOnly, SameSite
  strict cookie.
- Every state-changing endpoint requires a valid session.
- Failed attempts are counted **server-side, keyed by client IP**, with
  lockout after `auth.max_attempts` (default 5) for `auth.lockout_seconds`
  (default 300). Client-side counters are worthless.
- The server binds to the LAN interface only, never 0.0.0.0 in the shipped
  config.
- A CLI command `uv run sentinel-admin set-pin` generates the hash. The PIN
  never appears in shell history as an argument, prompt for it.

### 4.7 Docker for development, systemd for production

Container device passthrough for ALSA audio and camera access on a Pi is a
well-known time sink, and it is not worth paying for the MVP.

- `docker compose up` runs the app with **mock providers only**, for
  development and CI. No device mappings. This must work on any laptop.
- Production runs on the Pi host directly, managed by a systemd unit,
  dependencies installed with `uv sync`. Ship the unit file in `deploy/`.
- Document both paths in `docs/deployment.md`. Do not pretend the container
  path supports real hardware.

### 4.8 Storage and retention

Recordings and snapshots go to a configured path on the NVMe drive, never
the boot partition's default location without an explicit config value.
A retention job prunes clips older than `storage.retention_days` (default 14)
and enforces `storage.max_gb` (default 50) by deleting oldest-first. This is
in the MVP, not deferred. A disk that fills up silently takes the whole
system down.

SQLite runs in WAL mode.

---

## 5. Technology

Approved runtime dependencies. Anything not on this list requires asking.

| Purpose                 | Package                                                          |
| ----------------------- | ---------------------------------------------------------------- |
| Language                | Python 3.12+                                                     |
| Package manager         | uv                                                               |
| Web framework           | fastapi, uvicorn                                                 |
| Templates               | jinja2                                                           |
| Frontend                | htmx (vendored JS, not a Python dep)                             |
| Validation and settings | pydantic, pydantic-settings                                      |
| Database                | sqlalchemy (2.x style), sqlite3 (stdlib)                         |
| Vision                  | opencv-python-headless                                           |
| Inference               | onnxruntime                                                      |
| Password hashing        | argon2-cffi                                                      |
| Config format           | tomllib (stdlib)                                                 |
| Audio                   | sounddevice or subprocess to aplay, decide in slice 6 and log it |

Dev dependencies: pytest, pytest-asyncio, pytest-cov, ruff, mypy.

Use `asyncio` for the API, the event bus, and I/O waiting. Use threads for
the camera capture and inference loops, which are blocking and CPU-bound,
and hand results to the event bus via a thread-safe queue. Do not run
OpenCV capture inside the event loop.

---

## 6. Architecture and import contract

```
sentinel/
    config/        Config loading and validation
    models/        Domain types: enums, events, DTOs
    database/      Engine, session, ORM models, repositories
    events/        Async event bus, subscription registry
    state/         State machine, transition table
    rules/         Rule engine, rule definitions
    camera/        CameraProvider protocol and implementations
    detection/     Detector protocol, debouncer, implementations
    audio/         AudioPlayer protocol and implementations
    services/      Orchestration and wiring, the only layer that composes
    api/           FastAPI routers, dependencies, schemas
    dashboard/     Jinja templates, static assets, view helpers
docs/
tests/
deploy/
```

**Import contract.** Each layer may import only from layers above it in
this list. This is what actually prevents circular imports.

| Layer       | May import                                          |
| ----------- | --------------------------------------------------- |
| `config`    | nothing internal                                    |
| `models`    | `config`                                            |
| `database`  | `config`, `models`                                  |
| `events`    | `config`, `models`                                  |
| `state`     | `config`, `models`, `events`                        |
| `rules`     | `config`, `models`, `events`, `state` (read-only)   |
| `camera`    | `config`, `models`, `events`                        |
| `detection` | `config`, `models`, `events`                        |
| `audio`     | `config`, `models`, `events`                        |
| `services`  | all of the above                                    |
| `api`       | `config`, `models`, `services`, `state` (read-only) |
| `dashboard` | `config`, `models`                                  |

Specific prohibitions:

- `camera`, `detection`, and `audio` must never import `state` or `rules`.
  They emit events and know nothing about what the system does with them.
- `api` must never instantiate or call a provider directly. It goes through
  `services`.
- Nothing outside `database` imports `sqlalchemy`.
- Nothing outside `camera` and `detection` imports `cv2`.

Add a test in `tests/test_architecture.py` that walks the AST of every
module and asserts the contract. This is not optional, it is how the rule
survives contact with future contributors.

Wiring happens in exactly one place: a composition root in
`sentinel/services/container.py` that reads config, constructs concrete
providers, and injects them. Everything else receives its dependencies.

---

## 7. Domain model

### 7.1 States

```python
class SystemState(StrEnum):
    DISARMED   = "disarmed"    # monitoring off, no events processed
    ARMED      = "armed"       # monitoring, nothing detected
    ALERT      = "alert"       # person detected, grace period running
    WARNING    = "warning"     # first announcement playing or played
    ESCALATED  = "escalated"   # second announcement, higher volume
    COOLDOWN   = "cooldown"    # person gone, settling before re-arming
```

`COOLDOWN` exists so a person walking in and out of frame does not restart
the full escalation ladder every ten seconds.

### 7.2 Transition table

This table is the specification. Implement it as data, a dict or a list of
`Transition` records, not as nested `if` statements. Any (state, event)
pair not in this table is an **illegal transition and must raise**, never
silently pass.

| From      | Event           | To          | Actions                                   |
| --------- | --------------- | ----------- | ----------------------------------------- |
| DISARMED  | SystemArmed     | ARMED       | log, refresh dashboard                    |
| DISARMED  | PersonDetected  | DISARMED    | log only, no actions                      |
| ARMED     | PersonDetected  | ALERT       | start recording, start grace timer        |
| ARMED     | CameraOffline   | ARMED       | log health warning                        |
| ALERT     | GraceExpired    | WARNING     | play announcement 1, start warning timer  |
| ALERT     | PersonGone      | COOLDOWN    | start cooldown timer                      |
| ALERT     | PersonDetected  | ALERT       | refresh presence, no re-entry actions     |
| WARNING   | WarningExpired  | ESCALATED   | play announcement 2 at escalated volume   |
| WARNING   | PersonGone      | COOLDOWN    | stop audio, start cooldown timer          |
| WARNING   | PersonDetected  | WARNING     | refresh presence                          |
| ESCALATED | PersonGone      | COOLDOWN    | stop audio, start cooldown timer          |
| ESCALATED | PersonDetected  | ESCALATED   | refresh presence                          |
| COOLDOWN  | PersonDetected  | ALERT       | restart grace timer                       |
| COOLDOWN  | CooldownExpired | ARMED       | stop recording, finalize clip             |
| _any_     | SystemDisarmed  | DISARMED    | stop audio, stop recording, cancel timers |
| _any_     | CameraOffline   | _unchanged_ | log, set health degraded                  |

`SystemDisarmed` is valid from every state and always wins. Model it as an
explicit wildcard rule, not as a special case buried in the handler.

### 7.3 Events

Events are frozen Pydantic models with `timestamp`, `source`, `severity`,
and event-specific `metadata`. They are immutable and serializable.

- Detection: `PersonDetected`, `PersonGone`
- System: `SystemArmed`, `SystemDisarmed`
- Camera: `CameraOnline`, `CameraOffline`, `RecordingStarted`, `RecordingStopped`
- Audio: `AnnouncementStarted`, `AnnouncementFinished`
- Timer: `GraceExpired`, `WarningExpired`, `CooldownExpired`
- Auth: `PinAccepted`, `PinRejected`, `LockoutStarted`
- Health: `DiskSpaceLow`, `DetectorLagging`

Timers are first-class. A `TimerService` schedules a future event on the
bus and supports cancellation. Never use `sleep` inside a handler and never
bury a duration in a rule.

### 7.4 Rules

A rule is a small object with a `matches(event, state) -> bool` and an
`actions(event, state) -> list[Action]`. Rules are registered in one
registry module. Actions are declarative descriptions (`PlayAnnouncement`,
`StartRecording`, `SetVolume`, `LogEvent`) that an executor in `services`
dispatches to the right provider. Rules never call a provider directly,
which is what makes them testable with zero mocks.

---

## 8. Data and configuration

### 8.1 Configuration

`config/sentinel.toml`, loaded with `tomllib`, validated by a nested
Pydantic `Settings` model. Environment variables may override with a
`SENTINEL__` prefix and double-underscore nesting. Ship
`config/sentinel.example.toml` with every key documented by a comment.

No magic numbers anywhere in the codebase. Every threshold, timeout, path,
and volume is a config key. Config is validated at startup and the process
exits with a readable error on a bad value, never a stack trace.

Required sections: `system`, `auth`, `camera`, `detection`, `audio`,
`storage`, `database`, `dashboard`, `logging`.

### 8.2 Database

SQLite via SQLAlchemy 2.x declarative, WAL mode.

Tables: `events` (id, timestamp, type, source, severity, state_at_time,
metadata JSON), `recordings` (id, started_at, ended_at, path, trigger_event_id,
size_bytes), `state_transitions` (id, timestamp, from_state, to_state,
trigger_event_id), `sessions` (token_hash, created_at, expires_at, client_ip).

Index `events.timestamp`, `events.type`, and `events.severity`. The log must
be searchable by time range, type, and severity from the API.

Schema is created by a versioned `schema_version` table and hand-written
migration functions in `database/migrations/`. Do not add Alembic for the MVP.

---

## 9. Testing

`uv run pytest` must pass with no hardware, no network, and no model file.

Required coverage, by behavior not percentage:

- **State machine**: every row of the transition table, plus an explicit
  test that each illegal (state, event) pair raises.
- **Rule engine**: each rule matches when it should and produces the right
  actions. No mocks needed if section 7.4 is honored.
- **Detection debouncer**: fires after N consecutive frames, does not fire
  at N-1, emits `PersonGone` after the absence window, ignores low
  confidence and undersized boxes.
- **Config**: valid file loads, each invalid case produces a clear error.
- **Auth**: correct PIN issues a session, wrong PIN increments the counter,
  lockout engages and expires, expired sessions are rejected, protected
  endpoints reject unauthenticated requests.
- **API**: every endpoint, happy path and failure path, via `TestClient`.
- **Retention**: prunes by age and by size, oldest-first.
- **Architecture**: the import contract test from section 6.

Fake time. Do not write tests that sleep. Inject a clock.

---

## 10. Build plan

Implement vertically, one slice at a time, in this order. Each slice ends
with a runnable demo and its acceptance criteria met. Do not begin a slice
before the previous one is demonstrable.

| #   | Slice                       | Done when                                                                                                                                                                                              |
| --- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0   | Skeleton and tooling        | `uv sync`, `uv run pytest`, `ruff`, `mypy` all pass on an empty-but-valid package. `uv run sentinel` prints a version banner.                                                                          |
| 1   | Configuration               | Example config loads and validates. A bad value exits with a readable message. Tests cover both.                                                                                                       |
| 2   | Database and event log      | Schema creates on first run. Events can be written and queried by time, type, severity.                                                                                                                |
| 3   | State machine               | Every transition table row passes. Illegal transitions raise. Zero I/O in the module.                                                                                                                  |
| 4   | Event bus and rule engine   | Publishing an event drives a transition, persists it, and returns the expected action list. Timers schedule and cancel.                                                                                |
| 5   | API and dashboard           | Fire tablet loads the dashboard. PIN arms and disarms. Status reflects real state. Recent events render. Lockout works.                                                                                |
| 6   | Audio                       | Announcements play through the real USB device and through a mock. Volume is settable. `AnnouncementFinished` fires.                                                                                   |
| 7   | Camera abstraction and mock | `MockCamera` replays a directory of stills. Snapshot endpoint serves JPEG. Dashboard shows the polling preview.                                                                                        |
| 8   | **End-to-end MVP on mocks** | Mock camera plus mock detector drives ARMED to ALERT to WARNING to ESCALATED to COOLDOWN, plays audio, records, logs everything, all visible on the dashboard. **This is the milestone that matters.** |
| 9   | Real camera                 | `RtspCamera` via OpenCV on the substream. Reconnect with backoff. `CameraOffline` fires on loss and clears on recovery. Clips record from the main stream.                                             |
| 10  | Real detection              | Motion gate plus ONNX YOLOv8n. Debouncer tuned. Inference time logged. Sustained operation without frame backlog.                                                                                      |
| 11  | Kiosk hardening             | systemd unit, retention job running, disk-low warning, tablet stays awake and auto-recovers after a Pi reboot.                                                                                         |

After slice 8 you have a working product. Slices 9 through 11 swap mocks for
reality and should require zero changes above the provider layer. If they
do require such changes, the abstraction in slices 6 through 8 was wrong,
and that is worth stopping to discuss.

---

## 11. Documentation

Write docs as you go, in the same commit as the code. A doc written at the
end is a doc nobody trusts.

Maintain in `docs/`:

- `architecture.md` - subsystem responsibilities and the import contract
- `event-flow.md` - traced path from a camera frame to a speaker playing
- `state-machine.md` - the table, rendered, with timer semantics
- `configuration.md` - every key, its type, default, and effect
- `deployment.md` - Pi setup, systemd, kiosk config, both Docker and host paths
- `hardware.md` - the bill of materials and the wiring
- `DECISIONS.md` - append-only log, one entry per significant choice

A `DECISIONS.md` entry is: date, decision, alternatives considered, why,
and what would cause a reversal. Append an entry whenever you make a call
this document did not make for you. **This file is the single highest-value
artifact for the engineer who inherits this repo in two years.**

Assume that engineer has no access to any conversation that produced this
code.

---

## 12. Conventions

- `ruff` for lint and format, default line length 88
- `mypy --strict` on `sentinel/`, no `Any` without a comment justifying it
- Structured logging via stdlib `logging`, JSON formatter in production,
  never `print`
- Conventional commit messages, one slice may span several commits
- Protocols (`typing.Protocol`) for provider interfaces, not ABCs
- Custom exceptions inherit from a single `SentinelError` base
- No bare `except`. Catch specific exceptions or let it crash loudly.
- Timestamps are timezone-aware UTC internally, localized only for display

---

## 13. Stop and ask

Do not decide these alone. Stop, state the tradeoff, and wait.

- Adding any dependency not listed in section 5
- Changing the state set, the transition table, or the event taxonomy
- Changing the frontend approach, adding any build step
- Any design that requires network access beyond the LAN
- Changing the auth model or the session mechanism
- Introducing a broker, queue service, or second process beyond the app
- Any change that makes a test require real hardware
- Discovering that a slice 9 to 11 provider swap needs changes above the
  provider layer
- Anything in section 3 starting to look necessary

When in doubt, build the smaller thing and ask.
