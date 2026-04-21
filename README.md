<div align="center">
  <img src="tegufox-tool.png" alt="Tegufox Logo" width="300"/>
  
  # Tegufox Browser
  
  > Deep browser fingerprint engine — spoofing đa tầng từ Gecko C++ core
</div>

[![License](https://img.shields.io/badge/license-MPL%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-phase%201-yellow.svg)](ROADMAP.md)
[![Based on](https://img.shields.io/badge/based%20on-Camoufox-green.svg)](https://github.com/CloverLabsAI/camoufox)

---

## Giới thiệu

**Tegufox** là một deep browser fingerprint engine, fork từ [Camoufox](https://github.com/CloverLabsAI/camoufox) (Firefox Gecko), tập trung vào việc giả lập môi trường trình duyệt ở tất cả các tầng — từ giao thức mạng cấp thấp cho đến hành vi sinh trắc học.

Mục tiêu không phải là "giả lập trình duyệt" mà là **tạo ra một môi trường thực thi có độ tin cậy cao đến mức bất kỳ phép đo nào cũng trả về kết quả như một người dùng bình thường**.

### Tại sao Tegufox?

Camoufox giải quyết được vấn đề headless bypass rất tốt. Nhưng các hệ thống anti-fraud hiện đại kiểm tra nhiều hơn:

- Không chỉ "có phải bot không" — mà "môi trường này có nhất quán không?"
- Kiểm tra sự tương quan giữa OS, GPU, fonts, screen, TLS, hành vi
- Phân tích TLS JA3/JA4, HTTP/2 SETTINGS frames
- Đánh giá quang phổ hành vi: mouse, typing, scroll

Tegufox can thiệp vào từng tầng một cách nhất quán.

---

## Triết lý

> **"Fake Environment, Not Fake Browser"**

Thay vì cố gắng "lừa" hệ thống, Tegufox tạo ra một môi trường có sự nhất quán nội bộ tuyệt đối giữa tất cả các tầng — từ network protocol cho đến chuyển động của chuột.

---

## Kiến trúc Fingerprint Đa tầng

```
┌─────────────────────────────────────────────┐
│            Tegufox Engine                   │
├─────────────────────────────────────────────┤
│  Layer 7: Behavioral                        │
│  Mouse neuromotor • Typing rhythm           │
│  Scroll momentum • Form interaction         │
├─────────────────────────────────────────────┤
│  Layer 6: Hardware Fingerprint              │
│  WebGL/Canvas noise • Audio Context         │
│  Font metrics • Battery API                 │
├─────────────────────────────────────────────┤
│  Layer 5: Browser Environment               │
│  Navigator • Screen • Viewport              │
│  Headless masking • Automation hiding       │
├─────────────────────────────────────────────┤
│  Layer 4: Network Protocol                  │
│  TLS JA3/JA4 • HTTP/2 SETTINGS             │
│  Pseudo-header order • ALPN                 │
├─────────────────────────────────────────────┤
│  Layer 3: Network                           │
│  WebRTC ICE masking • DNS (DoH/DoT)         │
│  IP consistency • STUN leak prevention      │
└─────────────────────────────────────────────┘
               │ C++ Patches + MaskConfig
               ▼
┌─────────────────────────────────────────────┐
│     Camoufox → Firefox Gecko Engine         │
└─────────────────────────────────────────────┘
```

---

## Tính năng

### Kế thừa từ Camoufox:
- **C++ engine-level patches** — không JS injection
- **Playwright integration** — sandboxed page agent
- **WebRTC IP spoofing** — protocol-level masking
- **Navigator spoofing** — device, browser, locale
- **WebGL/Canvas spoofing** — hardware fingerprinting
- **Font protection** — metrics randomization

### Tegufox enhancements:
- **Fingerprint Consistency Engine** — cross-layer correlation validation (OS ↔ GPU ↔ Fonts ↔ Screen)
- **TLS/HTTP2 Alignment** — JA3/JA4 + HTTP/2 SETTINGS khiến bất kỳ browser nào
- **WebRTC ICE Manager** — can thiệp từ PeerConnectionImpl.cpp, self-destruct API
- **Neuromotor Mouse** — Fitts' Law, distance-aware trajectory, micro-tremor
- **Canvas Noise v2** — per-domain seed, chống hash correlation
- **WebGL Enhanced** — GPU vendor/renderer/extensions consistency
- **DNS Leak Prevention** — DoH/DoT integration
- **Automation Framework** — high-level Python API, profile rotation, session management

---

## Quick Start

```bash
git clone https://github.com/lugondev/tegufox-browser
cd tegufox-browser
python -m venv venv && source venv/bin/activate
pip install camoufox
```

```python
from tegufox_automation import TegufoxSession

with TegufoxSession(profile="chrome-120") as session:
    session.goto("https://creepjs.com")
    session.screenshot("fingerprint-test.png")
```

---

## Use Cases

Tegufox là một engine. Nó có thể được dùng cho bất kỳ kịch bản nào cần browser fingerprint không thể phân biệt với người dùng thật:

- Web automation & scraping
- Privacy & anonymous browsing
- Security research & bot detection testing
- Multi-account management
- Anti-fraud system testing
- E-commerce automation *(một ví dụ use case)*

---

## Roadmap

Xem chi tiết tại [ROADMAP.md](ROADMAP.md)

| Phase | Mô tả | Trạng thái |
|-------|---------|-------------|
| 0 | Foundation & Research | ✅ Complete |
| 1 | Toolkit & Automation Framework | 🔄 In Progress |
| 2 | Core C++ Engine Patches | Planned |
| 3 | Fingerprint Consistency Engine | Planned |
| 4 | Behavioral Layer | Planned |
| 5 | Ecosystem & API | Planned |

---

## Dựa trên

- **[Camoufox](https://github.com/CloverLabsAI/camoufox)** by daijro & CloverLabsAI
- **[Firefox](https://www.mozilla.org/firefox/)** by Mozilla
- **[Playwright](https://playwright.dev/)** by Microsoft

---

## License

MPL 2.0 (Mozilla Public License)

---

## Legal Notice

Tegufox được phát triển cho mục đích nghiên cứu, bảo mật và testing. Người dùng chịu hoàn toàn trách nhiệm về cách sử dụng tool này.

---

**Status**: Phase 1 — Week 3  
**Version**: 0.1.0-alpha  
**Last Updated**: 2026-04-14
