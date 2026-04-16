# Tegufox — Development TODO

> Task tracking cho Tegufox deep browser fingerprint engine

**Last Updated**: 2026-04-16
**Current Phase**: Phase 3 — Consistency Engine (scaffold complete)

---

## ✅ Phase 0: Foundation & Research — COMPLETE

- [x] Clone & analyze Camoufox source
- [x] Document MaskConfig system (38 patches)
- [x] Setup dev environment (Python 3.14.3, Playwright, Camoufox 0.5.0)
- [x] Baseline fingerprint tests (CreepJS, BrowserLeaks)
- [x] Document patch system (docs/CAMOUFOX_PATCH_SYSTEM.md)

---

## Phase 1: Toolkit & Automation Framework — IN PROGRESS

### Week 1–2: Toolkit — ✅ Done
- [x] tegufox-patch / tegufox-generate-patch / tegufox-validate-patch CLI
- [x] tegufox-config — Config management CLI
- [x] HTTP/2 fingerprinting module
- [x] DNS leak prevention (scripts/configure-dns.py)

### Week 3: Automation Framework — ✅ Done
- [x] tegufox_automation.py — TegufoxSession, ProfileRotator, SessionManager
- [x] tegufox_mouse.py — Neuromotor Jitter (Fitts’ Law)
- [x] profile_manager.py — CRUD, 3-level validation, templates
- [x] tegufox-profile CLI — 12 commands
- [x] Tests: 20/20 passing

### Week 4: Testing & Finalization — PENDING
- [ ] Integration tests: end-to-end profile → session → automation
- [ ] Performance benchmarks (profile load < 50ms, validation < 100ms)
- [ ] Security audit (file permissions, no sensitive data in logs)
- [ ] Week 3 Completion Report

---

## Phase 2: Core C++ Engine Patches — ✅ CORE COMPLETE

8 Tegufox patches đã sinh + apply trên Firefox source (trên tag `camoufox-patched`).
Xem `patches/tegufox/series` cho thứ tự apply. Còn pending: end-to-end build verification + test suite C++ tự động.

- [x] 01 Canvas v2 — per-domain seed + ImageData noise (`CANVAS_V2_COMPLETE.md`)
- [x] 02 WebGL Enhanced — GPU matrix + extension list (`WEBGL_ENHANCED_COMPLETE.md`)
- [x] 03 Audio Context v2 — AudioBuffer + AnalyserNode noise (`AUDIO_CONTEXT_COMPLETE.md`, `AUDIO_V2_BYTE_FIX.md`)
- [x] 04 TLS JA3/JA4 — cipher order + extension list per browser (`TLS_JA3_JA4_COMPLETE.md`)
- [x] 05 WebRTC ICE v2 — ICE candidate interception (`WEBRTC_ICE_V2_COMPLETE.md`)
- [x] 06 Font Metrics v2 — measureText offset per domain
- [x] 07 HTTP/2 Settings — SETTINGS/WINDOW_UPDATE frames (`HTTP2_SETTINGS_COMPLETE.md`)
- [x] 08 Navigator v2 — hardwareConcurrency, deviceMemory, plugins (`NAVIGATOR_V2_COMPLETE.md`)

### Phase 2 Pending
- [x] Full build of Firefox with all 8 patches applied (XUL 239MB, all Tegufox symbols verified)
- [ ] C++ integration tests (Canvas determinism, WebGL consistency matrix) u2014 requires packaged .app
- [x] Benchmark: Python-side overhead < 1ms per operation (7/7 benchmarks pass)
- [ ] Battery API patch (deferred — low priority)
- [ ] Juggler/Automation isolation patch (deferred)
- [ ] DNS DoH built-in C++ patch (existing Python script works)
- [x] Consolidate *_COMPLETE.md into `docs/phase2/` subfolder

---

## Phase 3: Fingerprint Consistency Engine — ✅ COMPLETE

### Engine
- [x] `consistency_engine.py` — Rule ABC, RuleResult, ConsistencyReport, ConsistencyEngine
- [x] PlatformUARule — UA ↔ navigator.platform
- [x] LanguageLocaleRule — navigator.language coherence
- [x] ScreenDPRViewportRule — width/height/DPR/taskbar plausibility
- [x] TLSCipherOrderRule — UA ↔ cipher prefix per browser family
- [x] GPUWebGLRule — regex patterns per platform (Win32/MacIntel/Linux)
- [x] OSFontListRule — OS_REQUIRED_FONTS dict (windows/macos/linux)
- [x] HTTP2PseudoHeaderRule u2014 UA u2194 HTTP/2 pseudo-header order per browser
- [x] LocaleTimezoneRule u2014 navigator.language region u2194 profile.timezone

### Anti-correlation
- [x] `fingerprint_registry.py` — SQLite schema, record / find_collisions / export_json
- [x] CLI: `tegufox-profile collisions <name>`
- [x] Hook registry.record() into `tegufox_automation.TegufoxSession.goto()`

### Generator v2
- [x] `generator_v2.py` — sample_browser_os, generate_fleet, screen pool per OS
- [x] MARKET_DISTRIBUTIONS — 7 entries (Chrome/Firefox/Safari × Win/Mac/Linux)
- [x] `tegufox-profile template --weighted` flag wired to generator_v2

### Tests
- [x] `tests/test_consistency_engine.py` — 32 tests, all 6 rules implemented
- [x] `tests/test_fingerprint_registry.py` — 10 tests for record/collision/export roundtrip
- [x] `tests/test_consistency_integration.py` u2014 6 tests across all profiles

---

## Phase 4: Behavioral Layer

### Mouse Movement v2
- [x] Bezier paths + Fitts’ Law + tremor + overshoot (`tegufox_mouse.py`)
- [x] Statistical validation (velocity bell curve, tremor Gaussian, overshoot)
- [ ] C++ event-level integration (requires packaged binary)
- [ ] Visual trajectory plots for QA

### Keyboard
- [x] `tegufox_keyboard.py` — HumanKeyboard class
- [x] Inter-keystroke interval: log-normal distribution
- [x] Per-bigram timing model (50+ bigrams)
- [x] Typo + correction simulation (adjacent key bias + backspace)
- [x] WPM envelope: 40–80 WPM with warmup + fatigue

### Scroll
- [x] Ease-out-cubic physics in `tegufox_mouse.scroll()`
- [x] Platform-specific step sizes (win=100, mac=40, linux=53)
- [x] Random micro-pause simulation (8% per tick)

### Bot Detection Validation
- [x] 16 statistical validation tests (mouse + keyboard + scroll)
- [ ] Cloudflare Turnstile pass rate > 90% (requires live testing)
- [ ] reCAPTCHA v3 score > 0.7 (requires live testing)

---

## Phase 5: Ecosystem & API

- [x] REST API: Profile CRUD, consistency scoring, fleet generation (13 endpoints)
- [x] Browser control: /sessions/* (launch, goto, type, click, scroll, screenshot, evaluate, close)
- [x] OpenAPI documentation (auto-generated at /docs)
- [ ] Plugin system: loadable spoofing modules
- [ ] Python SDK (pip installable)
- [ ] Node.js / TypeScript SDK
- [ ] Example projects

---

## Milestones

- [x] M0: Foundation complete
- [x] M1: Toolkit + Automation Framework
- [x] M2a: 8 C++ patches written and applied (end-to-end build still pending)
- [ ] M2b: Full build verified on BrowserLeaks/CreepJS
- [x] M3: Consistency engine — 8 rules + anti-correlation + generator v2
- [ ] M4: Full behavioral layer (Phase 4)
- [ ] M5: Production API release (Phase 5)

---

**Overall Progress**: M1/M5 complete, M2 ~80% (patches written, build verification pending), M3 complete
**Next immediate**: Phase 2 full build verification → Phase 4 behavioral layer
