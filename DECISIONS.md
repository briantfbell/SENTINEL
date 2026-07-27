# Decision Log

Append-only. One entry per significant choice. Newest at the bottom.

Format: date, decision, alternatives considered, rationale, and what would
cause a reversal.

This file exists for the engineer who inherits this repository with no
access to the conversations that produced it. Write for that person.

---

## 0001 - Jinja2 plus HTMX instead of React

**Date:** project inception
**Decision:** Server-rendered Jinja2 templates with HTMX for partial updates.
No JavaScript build step, no bundler, HTMX vendored locally.

**Alternatives:** React SPA, Vue, plain server-rendered HTML with full page
reloads.

**Rationale:** The display is an Amazon Fire tablet running Silk, an aging
Chromium fork on weak hardware, unattended for months at a time. Server
rendering keeps one source of truth and eliminates client-side state that
can desynchronize during a long uptime. A build step would add a toolchain
to maintain on a Pi for no MVP benefit.

**Would reverse if:** the dashboard grows genuinely interactive surfaces
such as a drag-and-drop rule editor, or multiple simultaneous clients need
real-time bidirectional updates.

---

## 0002 - Snapshot polling for live preview

**Date:** project inception
**Decision:** The dashboard polls a JPEG snapshot endpoint on an interval.
The implementation sits behind a `StreamProvider` protocol.

**Alternatives:** MJPEG proxy, HLS, WebRTC via go2rtc.

**Rationale:** RTSP does not play natively in a browser, so something has to
transcode or proxy. MJPEG is CPU-expensive on a Pi and on the tablet. HLS
adds several seconds of latency, which is wrong for a live deterrence loop.
WebRTC is the correct long-term answer but adds a second service to run and
debug. Snapshot polling is the option that cannot break, and the interface
makes it swappable.

**Would reverse if:** the latency proves unacceptable in practice, at which
point go2rtc plus a WebRTC `StreamProvider` is the intended path.

---

## 0003 - ONNX Runtime instead of the ultralytics package

**Date:** project inception
**Decision:** YOLOv8n exported to ONNX, executed via `onnxruntime`. The
`ultralytics` package is not a runtime dependency.

**Alternatives:** ultralytics runtime, OpenCV DNN with MobileNet-SSD,
TensorFlow Lite, Google Coral.

**Rationale:** `ultralytics` is AGPL-licensed, which would impose copyleft
obligations if this repository is ever published. ONNX Runtime is
permissively licensed, has no opinion about the model, and keeps the door
open to swapping architectures. Coral remains available later behind the
same `Detector` protocol.

**Would reverse if:** the project stays permanently private and inference
performance on ONNX Runtime proves inadequate.

---

## 0004 - Motion gating before inference

**Date:** project inception
**Decision:** Frame differencing rejects still frames before any inference
runs. Inference is additionally rate-limited to a configured maximum FPS.

**Alternatives:** run the detector on every frame, run on a fixed interval
regardless of motion.

**Rationale:** A Pi 5 running a detector on every frame saturates a core and
builds a frame backlog. The overwhelming majority of frames from a fixed
camera contain no change at all, and rejecting them costs almost nothing.

**Would reverse if:** the hardware gains a dedicated accelerator making
per-frame inference cheap, or motion gating proves to miss slow approaches.

---

## 0005 - Detection hysteresis lives in the detection layer

**Date:** project inception
**Decision:** A `DetectionDebouncer` converts raw per-frame model output
into domain events using a consecutive-frame threshold, a confidence floor,
a minimum box size, and an absence timeout.

**Alternatives:** emit an event per positive frame and let the state machine
absorb the noise.

**Rationale:** Raw model output flaps frame to frame. Without hysteresis the
state machine thrashes between states every few seconds and the event log
becomes unusable as evidence. Placing this in the detection layer keeps the
state machine pure and the debouncer independently testable with no model.

**Would reverse if:** a detector emerges with output stable enough that the
debouncer becomes a no-op.

---

## 0006 - State machine and rule engine have separate authority

**Date:** project inception
**Decision:** The state machine is the only component permitted to change
system state and performs no I/O. The rule engine reads state and produces
declarative actions, never mutating state and never calling providers
directly.

**Alternatives:** a single component handling both, rules that mutate state.

**Rationale:** Two components able to change state means two sources of
truth and a class of bug that is extremely difficult to trace. The split
also makes both halves testable without mocks.

**Would reverse if:** never. This is foundational.

---

## 0007 - Server-side authentication with hashed PIN

**Date:** project inception
**Decision:** Argon2-hashed PIN in config, server-side verification,
opaque session tokens with TTL, server-side IP-keyed lockout, LAN-bound
listener.

**Alternatives:** client-side PIN check, no auth on the assumption the LAN
is trusted.

**Rationale:** The keypad is a UI affordance. Anyone on the Wi-Fi can reach
the API directly and disarm the system with a single request. This is cheap
to build correctly at the start and expensive to retrofit.

**Would reverse if:** never for the MVP shape. Would extend if user accounts
are ever added.

---

## 0008 - Docker for development, systemd for production

**Date:** project inception
**Decision:** Compose runs the app with mock providers only, no device
passthrough. Production runs on the Pi host under systemd via `uv sync`.

**Alternatives:** full containerization with ALSA and camera device
passthrough, no containers at all.

**Rationale:** Audio and camera passthrough into a container on a Pi is a
known time sink with little payoff for a single-host deployment. Keeping the
container path hardware-free means it runs on any laptop and in CI, which is
where its value actually is.

**Would reverse if:** the deployment target becomes multi-host or the
project needs reproducible hardware-attached builds.

---

## 0009 - NVMe over SD card, RTC battery required

**Date:** project inception
**Decision:** Boot and record to an NVMe drive on the M.2 HAT+. Populate the
Pi 5 RTC battery connector.

**Alternatives:** SD card boot with recordings to USB storage, accept clock
drift.

**Rationale:** Continuous clip recording will exhaust an SD card's write
endurance. Separately, an offline system has no NTP, and a Pi without an RTC
battery comes back from a power loss with a meaningless clock, which
destroys the evidentiary value of the entire event log.

**Would reverse if:** the deployment gains reliable network time and
recording moves off the boot device.

---

## 0010 - Retention policy in the MVP

**Date:** project inception
**Decision:** Age-based and size-based pruning of recordings ships in the
MVP rather than being deferred.

**Alternatives:** defer retention until storage becomes a problem.

**Rationale:** A full disk takes down the database, the recorder, and the
dashboard simultaneously, and it does so silently at 3am several months
after deployment. This is a small amount of code that prevents a total
outage.

**Would reverse if:** never.

---

## 0011 - Added a `[state]` config section for escalation timer durations

**Date:** 2026-07-27
**Decision:** Added `grace_seconds` (default 10), `warning_seconds` (default
30), and `cooldown_seconds` (default 60) under a new `[state]` section,
consumed by the services-layer dispatcher when it executes `StartTimer`
actions.

**Alternatives:** hardcode the durations, fold them into `[detection]`
(where `absence_seconds` already lives), leave them undocumented until a
later slice forced the question.

**Rationale:** Building slice 4 (event bus and rule engine) surfaced a real
gap: the transition table's `GraceExpired`, `WarningExpired`, and
`CooldownExpired` timers are load-bearing but AGENTS.md section 8.1 never
gives them a config home, and section 8.1's hard rule is "no magic numbers
anywhere." `[detection]`'s `absence_seconds` is a different concept — how
long the *detector* waits before declaring absence, not how long the
*state machine* waits before escalating — so folding the two together
would conflate detection-layer and state-layer timing. A new section
matching the `sentinel/state` package name was the smallest change that
kept the values named, typed, and validated like everything else in
config.

**Would reverse if:** the escalation ladder gains enough independent
per-transition timers that a flat three-key section stops being legible,
at which point a structured `[state.timers]` table might replace it.

---

## 0012 - Audio: subprocess to `aplay`/`amixer`, not `sounddevice`

**Date:** 2026-07-27
**Decision:** `AplayAudioPlayer` shells out to `aplay` to play a WAV clip and
`amixer` to set volume beforehand, both via stdlib `subprocess`. No new
runtime dependency.

**Alternatives:** `sounddevice` (PortAudio bindings), which section 5 also
named as an option pending this decision.

**Rationale:** `sounddevice` needs `libportaudio2` installed on the host
and typically numpy for buffer handling, for a use case that's just "play
a pre-rendered WAV file at a given volume" — no synthesis, no streaming,
no low-latency requirement. `aplay` and `amixer` ship in `alsa-utils`,
which is present on Raspberry Pi OS by default and trivial to add anywhere
else. Zero new Python dependencies, and the real player is exercised only
by hand on real hardware anyway (rule 2: no hardware in the test suite),
so there's no test-authoring cost either way — the deciding factor was
footprint on the Pi image and the dev/CI Docker image, not testability.

**Also closes a config gap surfaced building this:** section 8.1 never
gave announcement clips a config home. Added `audio.warning_clip_path`,
`audio.escalated_clip_path` (defaulting to `sounds/warning.wav` and
`sounds/escalated.wav`, gitignored like `models/` and `data/`), and
`audio.mixer_control` (default `"Master"`, the ALSA mixer control
`amixer` targets) — same reasoning as decision 0011: config, not magic
numbers.

**Would reverse if:** a future slice needs real-time audio synthesis,
ducking, or multi-channel mixing that pre-rendered clips can't express.

---

## 0013 - Leaving a state early cancels its pending escalation timer

**Date:** 2026-07-27
**Decision:** The services-layer dispatcher calls `TimerService.cancel_all()`
whenever a notification causes an actual state change (`from_state !=
to_state`), before executing that transition's own actions. Self-loops
(e.g. `ALERT + PersonDetected -> ALERT`, "refresh presence, no re-entry
actions") do not cancel anything, since nothing left.

**Alternatives:** add an explicit `CancelTimers` action to every individual
transition-table row that can leave a state before its timer expires
(`ALERT + PersonGone`, `WARNING + PersonGone`, `COOLDOWN + PersonDetected`);
leave it as-is and accept the occasional orphaned-timer exception.

**Rationale:** Found by exercising slice 6's audio flow end-to-end for the
first time: `WARNING + PersonGone -> COOLDOWN` stops audio and starts a
cooldown timer, but the *warning* timer started on the way into WARNING
was still running. It fired `WarningExpired` into `COOLDOWN` a moment
later — not in the transition table, so `IllegalTransitionError`, in a
background task the test suite hadn't previously exercised. The same class
of bug exists for `ALERT + PersonGone` (orphaned grace timer) and
`COOLDOWN + PersonDetected` (orphaned cooldown timer). Patching each row
individually is exactly the "special case buried in the handler" section
7.2 warns against for the wildcard rows; the real invariant is that at
most one escalation timer is ever meaningful at a time, scoped to the
state that started it, so enforcing it centrally in the dispatcher is
smaller and can't be forgotten by a future rule added to the table.

**Would reverse if:** a future slice needs multiple concurrent, independent
timers that must survive a state change (nothing in the current ladder
does).
