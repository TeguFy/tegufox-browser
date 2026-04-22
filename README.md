<div align="center">
  
# 🦊 Tegufox Browser

**Deep Browser Fingerprint Engine — Multi-Layer Spoofing from Gecko C++ Core**

[![License](https://img.shields.io/badge/license-MPL%202.0-blue.svg)](LICENSE)
[![Based on](https://img.shields.io/badge/based%20on-Camoufox-green.svg)](https://github.com/CloverLabsAI/camoufox)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

[English](#english) | [Tiếng Việt](#tiếng-việt)

</div>

---

## English

### 🎯 Overview

**Tegufox** is a deep browser fingerprint engine forked from [Camoufox](https://github.com/CloverLabsAI/camoufox) (Firefox Gecko), focused on simulating browser environments at all layers — from low-level network protocols to biometric behavior.

The goal is not to "fake a browser" but to **create an execution environment so trustworthy that any measurement returns results indistinguishable from a real user**.

### 🤔 Why Tegufox?

Camoufox solves headless bypass very well. But modern anti-fraud systems check much more:

- Not just "is this a bot?" — but "is this environment consistent?"
- Cross-correlation between OS, GPU, fonts, screen, TLS, behavior
- TLS JA3/JA4, HTTP/2 SETTINGS frames analysis
- Behavioral spectrum evaluation: mouse, typing, scroll

**Tegufox intervenes at every layer with absolute consistency.**

---

### 🏗️ Multi-Layer Fingerprint Architecture

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

### ✨ Features

#### Inherited from Camoufox:
- **C++ engine-level patches** — no JS injection
- **Playwright integration** — sandboxed page agent
- **WebRTC IP spoofing** — protocol-level masking
- **Navigator spoofing** — device, browser, locale
- **WebGL/Canvas spoofing** — hardware fingerprinting
- **Font protection** — metrics randomization

#### Tegufox Enhancements:
- **Fingerprint Consistency Engine** — cross-layer correlation validation (OS ↔ GPU ↔ Fonts ↔ Screen)
- **TLS/HTTP2 Alignment** — JA3/JA4 + HTTP/2 SETTINGS matching any browser
- **WebRTC ICE Manager** — intervention from PeerConnectionImpl.cpp, self-destruct API
- **Neuromotor Mouse** — Fitts' Law, distance-aware trajectory, micro-tremor
- **Canvas Noise v2** — per-domain seed, anti-hash correlation
- **WebGL Enhanced** — GPU vendor/renderer/extensions consistency
- **DNS Leak Prevention** — DoH/DoT integration
- **Profile Database** — SQLite-based profile management with templates
- **GUI & CLI Tools** — User-friendly interface and command-line tools
- **REST API** — Session control and automation endpoints

---

### 🚀 Quick Start

#### Installation

```bash
# Clone repository with submodules
git clone --recurse-submodules https://github.com/lugondev/tegufox-browser
cd tegufox-browser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Basic Usage

**CLI:**
```bash
# Launch GUI
./tegufox-gui

# Launch browser with CLI
./tegufox-cli launch --profile chrome-120

# List available profiles
./tegufox-cli profile list

# Create new profile
./tegufox-cli profile create --name my-profile --browser chrome
```

**Python API:**
```python
from tegufox_automation import TegufoxSession

# Launch with profile
with TegufoxSession(profile="chrome-120") as session:
    session.goto("https://creepjs.com")
    session.screenshot("fingerprint-test.png")
    
# Human-like interactions
with TegufoxSession(profile="firefox-115") as session:
    session.goto("https://example.com")
    session.human_click("#login-button")
    session.human_type("#username", "user@example.com")
    session.wait_human(1, 3)  # Random delay 1-3 seconds
```

**REST API:**
```bash
# Start API server
./tegufox-cli api --port 8080

# Create session via HTTP
curl -X POST http://localhost:8080/session/create \
  -H "Content-Type: application/json" \
  -d '{"profile": "chrome-120"}'

# Navigate
curl -X POST http://localhost:8080/session/{id}/goto \
  -d '{"url": "https://example.com"}'
```

---

### 📁 Project Structure

```
tegufox-browser/
├── tegufox_core/              # Core engine
│   ├── database.py            # Profile database
│   ├── profile_manager.py     # Profile CRUD
│   ├── consistency_engine.py  # Cross-layer validation
│   ├── generator_v2.py        # Profile generator
│   ├── webgl_dataset.py       # WebGL vendor/renderer dataset (data only)
│   └── webgl_database.py      # WebGL selection + normalization logic
├── tegufox_cli/               # Command-line interface
│   └── api.py                 # REST API server
├── tegufox_gui/               # Graphical interface
│   └── app.py                 # Tkinter GUI
├── tegufox_automation/        # Automation framework
│   ├── keyboard.py            # Natural typing
│   ├── mouse.py               # Neuromotor mouse
│   └── session.py             # Session management
├── patches/tegufox/           # C++ patches
│   ├── 01-canvas-v2.patch
│   ├── 02-webgl-enhanced.patch
│   ├── 03-audio-context-v2.patch
│   └── 09-branding.patch
├── scripts/                   # Utility scripts
│   ├── tegufox-build.sh       # Build automation
│   └── refresh_webgl_dataset.py # Semi-automatic WebGL dataset refresh
├── tests/                     # Test suite
├── docs/                      # Documentation
└── camoufox-source/           # Camoufox submodule
```

---

### 🎯 Use Cases

Tegufox is an engine. It can be used for any scenario requiring browser fingerprints indistinguishable from real users:

- **Web Automation & Scraping** — Bypass anti-bot detection
- **Privacy & Anonymous Browsing** — Protect your digital identity
- **Security Research** — Test bot detection systems
- **Multi-Account Management** — Manage multiple accounts safely
- **Anti-Fraud Testing** — Validate fraud detection systems
- **E-commerce Automation** — Automate shopping workflows

---

### 📚 Documentation

- [Architecture Design](docs/ARCHITECTURE.md)
- [DNS Leak Prevention](docs/DNS_LEAK_PREVENTION_GUIDE.md)
- [GUI Guide](docs/GUI_README.md)
- [Camoufox Patch System](docs/CAMOUFOX_PATCH_SYSTEM.md)
- [Mouse Movement](docs/MOUSE_MOVEMENT_V2_GUIDE.md)

---

### 🎮 WebGL Dataset Maintenance

The WebGL dataset is maintained separately from generation logic:

- Dataset file: `tegufox_core/webgl_dataset.py`
- Selection/normalization logic: `tegufox_core/webgl_database.py`
- Refresh script: `scripts/refresh_webgl_dataset.py`

Refresh workflow:

```bash
# Preview candidates from public sources (dry-run)
make webgl-refresh

# Apply merged candidates into tegufox_core/webgl_dataset.py
make webgl-refresh-apply
```

Direct script usage:

```bash
# Dry-run
python3 scripts/refresh_webgl_dataset.py

# Apply changes
python3 scripts/refresh_webgl_dataset.py --apply

# Optional: export extracted candidates for review
python3 scripts/refresh_webgl_dataset.py --output-candidates /tmp/webgl_candidates.json
```

---

### 🗺️ Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation & Research | ✅ Complete |
| **Phase 1** | Toolkit & Automation Framework | ✅ Complete |
| **Phase 2** | Core C++ Engine Patches | ✅ Complete |
| **Phase 3** | Fingerprint Consistency Engine | ✅ Complete |
| **Phase 4** | Behavioral Layer | ✅ Complete |
| **Phase 5** | Ecosystem & API | ✅ Complete |

**Current Status**: All phases complete. Production-ready browser fingerprint engine with:
- 9 C++ patches (Canvas, WebGL, Audio, TLS, WebRTC, Fonts, HTTP/2, Navigator, Branding)
- SQLite profile database with consistency validation
- GUI + CLI + REST API
- Human-like behavioral automation (mouse, keyboard, scroll)

---

### 🙏 Credits

Built on top of:
- **[Camoufox](https://github.com/CloverLabsAI/camoufox)** by daijro & CloverLabsAI
- **[Firefox](https://www.mozilla.org/firefox/)** by Mozilla
- **[Playwright](https://playwright.dev/)** by Microsoft

---

### 📄 License

MPL 2.0 (Mozilla Public License)

---

### ⚖️ Legal Notice

Tegufox is developed for research, security, and testing purposes. Users are solely responsible for how they use this tool. The developers assume no liability for misuse.

---

### 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

---

## Tiếng Việt

### 🎯 Tổng quan

**Tegufox** là một deep browser fingerprint engine, fork từ [Camoufox](https://github.com/CloverLabsAI/camoufox) (Firefox Gecko), tập trung vào việc giả lập môi trường trình duyệt ở tất cả các tầng — từ giao thức mạng cấp thấp cho đến hành vi sinh trắc học.

Mục tiêu không phải là "giả lập trình duyệt" mà là **tạo ra một môi trường thực thi có độ tin cậy cao đến mức bất kỳ phép đo nào cũng trả về kết quả như một người dùng bình thường**.

### 🤔 Tại sao Tegufox?

Camoufox giải quyết được vấn đề headless bypass rất tốt. Nhưng các hệ thống anti-fraud hiện đại kiểm tra nhiều hơn:

- Không chỉ "có phải bot không" — mà "môi trường này có nhất quán không?"
- Kiểm tra sự tương quan giữa OS, GPU, fonts, screen, TLS, hành vi
- Phân tích TLS JA3/JA4, HTTP/2 SETTINGS frames
- Đánh giá quang phổ hành vi: mouse, typing, scroll

**Tegufox can thiệp vào từng tầng một cách nhất quán.**

---

### 🏗️ Kiến trúc Fingerprint Đa tầng

```
┌─────────────────────────────────────────────┐
│            Tegufox Engine                   │
├─────────────────────────────────────────────┤
│  Tầng 7: Hành vi                            │
│  Chuyển động chuột • Nhịp gõ phím           │
│  Động lượng cuộn • Tương tác form           │
├─────────────────────────────────────────────┤
│  Tầng 6: Dấu vân tay phần cứng              │
│  WebGL/Canvas noise • Audio Context         │
│  Font metrics • Battery API                 │
├─────────────────────────────────────────────┤
│  Tầng 5: Môi trường trình duyệt             │
│  Navigator • Screen • Viewport              │
│  Che giấu headless • Ẩn automation          │
├─────────────────────────────────────────────┤
│  Tầng 4: Giao thức mạng                     │
│  TLS JA3/JA4 • HTTP/2 SETTINGS             │
│  Thứ tự pseudo-header • ALPN                │
├─────────────────────────────────────────────┤
│  Tầng 3: Mạng                               │
│  WebRTC ICE masking • DNS (DoH/DoT)         │
│  Nhất quán IP • Ngăn STUN leak              │
└─────────────────────────────────────────────┘
               │ C++ Patches + MaskConfig
               ▼
┌─────────────────────────────────────────────┐
│     Camoufox → Firefox Gecko Engine         │
└─────────────────────────────────────────────┘
```

---

### ✨ Tính năng

#### Kế thừa từ Camoufox:
- **C++ engine-level patches** — không JS injection
- **Playwright integration** — sandboxed page agent
- **WebRTC IP spoofing** — protocol-level masking
- **Navigator spoofing** — device, browser, locale
- **WebGL/Canvas spoofing** — hardware fingerprinting
- **Font protection** — metrics randomization

#### Cải tiến của Tegufox:
- **Fingerprint Consistency Engine** — kiểm tra tương quan đa tầng (OS ↔ GPU ↔ Fonts ↔ Screen)
- **TLS/HTTP2 Alignment** — JA3/JA4 + HTTP/2 SETTINGS khớp với bất kỳ trình duyệt nào
- **WebRTC ICE Manager** — can thiệp từ PeerConnectionImpl.cpp, self-destruct API
- **Neuromotor Mouse** — Fitts' Law, quỹ đạo nhận biết khoảng cách, rung nhỏ
- **Canvas Noise v2** — seed theo domain, chống tương quan hash
- **WebGL Enhanced** — nhất quán GPU vendor/renderer/extensions
- **DNS Leak Prevention** — tích hợp DoH/DoT
- **Profile Database** — quản lý profile dựa trên SQLite với templates
- **GUI & CLI Tools** — giao diện người dùng và công cụ dòng lệnh
- **REST API** — điểm cuối điều khiển session và automation

---

### 🚀 Bắt đầu nhanh

#### Cài đặt

```bash
# Clone repository với submodules
git clone --recurse-submodules https://github.com/lugondev/tegufox-browser
cd tegufox-browser

# Tạo môi trường ảo
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt
```

#### Sử dụng cơ bản

**CLI:**
```bash
# Khởi chạy GUI
./tegufox-gui

# Khởi chạy trình duyệt với CLI
./tegufox-cli launch --profile chrome-120

# Liệt kê profiles có sẵn
./tegufox-cli profile list

# Tạo profile mới
./tegufox-cli profile create --name my-profile --browser chrome
```

**Python API:**
```python
from tegufox_automation import TegufoxSession

# Khởi chạy với profile
with TegufoxSession(profile="chrome-120") as session:
    session.goto("https://creepjs.com")
    session.screenshot("fingerprint-test.png")
    
# Tương tác giống người
with TegufoxSession(profile="firefox-115") as session:
    session.goto("https://example.com")
    session.human_click("#login-button")
    session.human_type("#username", "user@example.com")
    session.wait_human(1, 3)  # Delay ngẫu nhiên 1-3 giây
```

**REST API:**
```bash
# Khởi động API server
./tegufox-cli api --port 8080

# Tạo session qua HTTP
curl -X POST http://localhost:8080/session/create \
  -H "Content-Type: application/json" \
  -d '{"profile": "chrome-120"}'

# Điều hướng
curl -X POST http://localhost:8080/session/{id}/goto \
  -d '{"url": "https://example.com"}'
```

---

### 📁 Cấu trúc dự án

```
tegufox-browser/
├── tegufox_core/              # Engine cốt lõi
│   ├── database.py            # Database profile
│   ├── profile_manager.py     # CRUD profile
│   ├── consistency_engine.py  # Kiểm tra đa tầng
│   └── generator_v2.py        # Tạo profile
├── tegufox_cli/               # Giao diện dòng lệnh
│   └── api.py                 # REST API server
├── tegufox_gui/               # Giao diện đồ họa
│   └── app.py                 # Tkinter GUI
├── tegufox_automation/        # Framework automation
│   ├── keyboard.py            # Gõ phím tự nhiên
│   ├── mouse.py               # Chuột neuromotor
│   └── session.py             # Quản lý session
├── patches/tegufox/           # C++ patches
│   ├── 01-canvas-v2.patch
│   ├── 02-webgl-enhanced.patch
│   ├── 03-audio-context-v2.patch
│   └── 09-branding.patch
├── scripts/                   # Scripts tiện ích
│   └── tegufox-build.sh       # Tự động build
├── tests/                     # Bộ test
├── docs/                      # Tài liệu
└── camoufox-source/           # Camoufox submodule
```

---

### 🎯 Trường hợp sử dụng

Tegufox là một engine. Nó có thể được dùng cho bất kỳ kịch bản nào cần browser fingerprint không thể phân biệt với người dùng thật:

- **Web Automation & Scraping** — Vượt qua phát hiện anti-bot
- **Privacy & Anonymous Browsing** — Bảo vệ danh tính số
- **Security Research** — Kiểm tra hệ thống phát hiện bot
- **Multi-Account Management** — Quản lý nhiều tài khoản an toàn
- **Anti-Fraud Testing** — Xác thực hệ thống phát hiện gian lận
- **E-commerce Automation** — Tự động hóa quy trình mua sắm

---

### 📚 Tài liệu

- [Thiết kế kiến trúc](docs/ARCHITECTURE.md)
- [Ngăn chặn DNS Leak](docs/DNS_LEAK_PREVENTION_GUIDE.md)
- [Hướng dẫn GUI](docs/GUI_README.md)
- [Hệ thống Patch Camoufox](docs/CAMOUFOX_PATCH_SYSTEM.md)
- [Mouse Movement](docs/MOUSE_MOVEMENT_V2_GUIDE.md)

---

### 🗺️ Lộ trình

| Giai đoạn | Mô tả | Trạng thái |
|-----------|-------|------------|
| **Phase 0** | Nền tảng & Nghiên cứu | ✅ Hoàn thành |
| **Phase 1** | Toolkit & Framework Automation | ✅ Hoàn thành |
| **Phase 2** | C++ Engine Patches cốt lõi | 🔄 Đang thực hiện |
| **Phase 3** | Fingerprint Consistency Engine | 📋 Đã lên kế hoạch |
| **Phase 4** | Tầng hành vi | 📋 Đã lên kế hoạch |
| **Phase 5** | Hệ sinh thái & API | 📋 Đã lên kế hoạch |

---

### 🙏 Ghi công

Xây dựng dựa trên:
- **[Camoufox](https://github.com/CloverLabsAI/camoufox)** bởi daijro & CloverLabsAI
- **[Firefox](https://www.mozilla.org/firefox/)** bởi Mozilla
- **[Playwright](https://playwright.dev/)** bởi Microsoft

---

### 📄 Giấy phép

MPL 2.0 (Mozilla Public License)

---

### ⚖️ Thông báo pháp lý

Tegufox được phát triển cho mục đích nghiên cứu, bảo mật và testing. Người dùng chịu hoàn toàn trách nhiệm về cách sử dụng tool này. Các nhà phát triển không chịu trách nhiệm về việc sử dụng sai mục đích.

---

### 🤝 Đóng góp

Chúng tôi hoan nghênh đóng góp! Vui lòng đọc hướng dẫn đóng góp và gửi pull requests.

---

<div align="center">

**Version**: 1.0.0  
**Last Updated**: 2026-04-22  
**Status**: Production Ready

Made with ❤️ for privacy and security research

</div>
