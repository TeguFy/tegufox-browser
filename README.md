<div align="center">
  <img src="tegufox-tool.png" alt="Tegufox Logo" width="300"/>
  
  # Tegufox Browser
  
  > Trình duyệt anti-detect thế hệ mới, tối ưu cho thương mại điện tử
</div>

[![License](https://img.shields.io/badge/license-MPL%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-planning-orange.svg)](ROADMAP.md)
[![Based on](https://img.shields.io/badge/based%20on-Camoufox-green.svg)](https://github.com/CloverLabsAI/camoufox)

---

## 🦊 Giới thiệu

**Tegufox** là một trình duyệt anti-detect được fork từ [Camoufox](https://github.com/CloverLabsAI/camoufox), được thiết kế đặc biệt để vượt qua các hệ thống chống gian lận trên các nền tảng thương mại điện tử như eBay, Amazon, và Etsy.

### Tại sao Tegufox?

Camoufox là một nền tảng tuyệt vời cho web scraping và automation, nhưng các nền tảng thương mại điện tử hiện đại yêu cầu nhiều hơn thế:

- ✅ **Fingerprint consistency** - Tính nhất quán tuyệt đối giữa OS, GPU, fonts, screen
- ✅ **Behavioral simulation** - Mô phỏng hành vi người dùng thật (Neuromotor Jitter)
- ✅ **E-commerce optimization** - Profiles tối ưu cho từng platform
- ✅ **Advanced bypass** - Vượt qua Cloudflare Turnstile, reCAPTCHA v3

---

## 🎯 Triết lý

> **"Fake Environment, Not Fake Browser"**

Thay vì cố gắng "lừa" hệ thống, Tegufox tạo ra một môi trường có độ tin cậy cao đến mức mọi phép đo lường từ phía hệ thống anti-fraud đều trả về kết quả tích cực.

---

## ✨ Tính năng (Planned)

### Kế thừa từ Camoufox:
- **C++ engine-level patches** - Không phải JS injection
- **Playwright integration** - Sandboxed page agent
- **WebRTC IP spoofing** - Protocol-level masking
- **Navigator spoofing** - Device, browser, locale
- **WebGL/Canvas spoofing** - Hardware fingerprinting
- **Font protection** - Metrics randomization

### Tegufox enhancements:
- 🎯 **Neuromotor Jitter** - Mouse movement theo Fitts' Law
- 🎯 **E-commerce profiles** - eBay, Amazon, Etsy optimized
- 🎯 **Fingerprint consistency engine** - Correlation validation
- 🎯 **Advanced TLS tuning** - JA3/JA4 per-platform
- 🎯 **Behavioral AI** - Typing rhythm, scroll patterns
- 🎯 **Cloud sync** - Profile management & team collaboration

---

## 🚀 Quick Start

> **⚠️ Project is in planning phase. Installation instructions coming soon.**

```bash
# Clone repository (when available)
git clone https://github.com/yourusername/tegufox.git
cd tegufox

# Build from source
./build.sh

# Run with Python API
pip install tegufox
```

```python
# Example usage (planned API)
from tegufox import Tegufox

# Launch with e-commerce optimized profile
with Tegufox(platform='ebay', geo='US') as browser:
    page = browser.new_page()
    page.goto("https://www.ebay.com")
    # Automation với fingerprint nhất quán + behavioral AI
```

---

## 📊 Roadmap

Xem chi tiết tại [ROADMAP.md](ROADMAP.md)

### Timeline:
- **Phase 0**: Research & Fork (2-3 tuần) - *Current*
- **Phase 1**: Setup & Optimization (3-4 tuần)
- **Phase 2**: Enhanced Fingerprinting (2 tháng)
- **Phase 3**: Behavioral Simulation (2-3 tháng)
- **Phase 4**: E-commerce Optimization (2 tháng)
- **Phase 5**: Ecosystem & API (1-2 tháng)

**Total**: 6-10 tháng đến production-ready

---

## 🎯 Use Cases

### ✅ Legitimate use cases:
- E-commerce automation tools
- Price monitoring & comparison
- Market research & analytics
- Multi-account management (với proper authorization)
- Testing anti-fraud systems (với permission)

### ⚠️ Disclaimer:
Tegufox là một công cụ. Người dùng chịu trách nhiệm đảm bảo tuân thủ Terms of Service của các platforms và luật pháp địa phương.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Tegufox Browser Core            │
│      (Firefox Gecko Engine + Patches)   │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────┐ │
│  │ Fingerprint  │  │ Behavioral AI   │ │
│  │ Consistency  │  │ (Neuromotor)    │ │
│  │ Engine       │  │                 │ │
│  └──────────────┘  └─────────────────┘ │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────┐ │
│  │ WebRTC       │  │ TLS/HTTP        │ │
│  │ IP Manager   │  │ Fingerprint     │ │
│  └──────────────┘  └─────────────────┘ │
├─────────────────────────────────────────┤
│       Playwright Integration            │
│         (Sandboxed Agent)               │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      Python API / REST API              │
│  (Profile Management, Automation)       │
└─────────────────────────────────────────┘
```

---

## 📚 Documentation

- [Roadmap](ROADMAP.md) - Development roadmap & phases
- [Idea](idea.md) - Original concept & architecture (Vietnamese)
- [Contributing](CONTRIBUTING.md) - How to contribute *(coming soon)*
- [API Reference](docs/API.md) - API documentation *(coming soon)*

---

## 🤝 Based On

Tegufox được fork từ và dựa trên:
- **[Camoufox](https://github.com/CloverLabsAI/camoufox)** by daijro & CloverLabsAI
- **[Firefox](https://www.mozilla.org/firefox/)** by Mozilla
- **[Playwright](https://playwright.dev/)** by Microsoft

Cảm ơn tất cả maintainers và contributors của các projects trên!

---

## 📄 License

MPL 2.0 (Mozilla Public License)

Tegufox là một fork của Camoufox, tuân theo MPL 2.0 license. Tất cả modifications được công khai theo yêu cầu của license.

---

## ⚠️ Legal Notice

Tegufox được phát triển cho mục đích nghiên cứu và testing. Việc sử dụng tool này để vi phạm Terms of Service của bất kỳ platform nào hoặc cho các hoạt động bất hợp pháp là **KHÔNG** được khuyến khích và nằm ngoài trách nhiệm của tác giả.

Người dùng chịu hoàn toàn trách nhiệm về cách sử dụng tool này.

---

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/tegufox/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/tegufox/discussions)

---

**Status**: 🟠 Planning Phase  
**Version**: 0.1.0-alpha  
**Last Updated**: 2026-04-13
