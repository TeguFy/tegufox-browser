<div align="center">
  <img src="tegufox-tool.png" alt="Tegufox Logo" width="250"/>
  
  # Tegufox - Quick Start Guide
  
  > **Tổng kết dự án và hướng dẫn bắt đầu nhanh**
</div>

---

## 📋 Tổng quan dự án

**Tegufox** = Firefox-based anti-detect browser tối ưu cho e-commerce  
**Base**: Fork từ Camoufox  
**Timeline**: 6-10 tháng  
**Status**: Planning phase

### 🎯 Mục tiêu
Tạo trình duyệt vượt qua được:
- ✅ eBay anti-fraud (>85% survival)
- ✅ Amazon bot detection (>90% success)
- ✅ Etsy verification (6+ months shop longevity)
- ✅ Cloudflare Turnstile (>90% pass)

---

## 📁 Cấu trúc dự án hiện tại

```
tegufox-browser/
├── README.md          # Giới thiệu dự án
├── ROADMAP.md         # Lộ trình chi tiết 5 phases
├── TODO.md            # Task tracking theo tuần
├── idea.md            # Concept & architecture (tiếng Việt)
└── .atom8n/           # OpenCode metadata
```

---

## 🚀 Bắt đầu ngay (Phase 0)

### Step 1: Fork Camoufox
```bash
# Clone Camoufox
git clone https://github.com/CloverLabsAI/camoufox.git tegufox
cd tegufox

# Setup remotes
git remote rename origin upstream
git remote add origin https://github.com/YOUR_USERNAME/tegufox.git

# Create main branch for Tegufox
git checkout -b tegufox-main
```

### Step 2: Install dependencies

**macOS**:
```bash
# Install Homebrew dependencies
brew install python@3.11 rust node npm

# Install Firefox build tools
brew install mercurial autoconf@2.13

# Python dependencies
pip3 install playwright pytest
```

**Linux (Ubuntu/Debian)**:
```bash
# System dependencies
sudo apt update
sudo apt install python3.11 python3-pip rustc cargo nodejs npm
sudo apt install mercurial autoconf2.13 build-essential

# Python dependencies
pip3 install playwright pytest
```

**Windows**:
```powershell
# Install via Chocolatey
choco install python rust nodejs mercurial

# Python dependencies
pip install playwright pytest
```

### Step 3: Build Camoufox
```bash
# Install Camoufox Python package
pip install camoufox

# Or build from source
cd pythonlib
pip install -e .

# Fetch browser binary
python -c "from camoufox import Camoufox; Camoufox(headless=False).close()"
```

### Step 4: Test current capabilities
```python
# test_camoufox.py
from camoufox import Camoufox

with Camoufox(headless=False) as browser:
    page = browser.new_page()
    
    # Test 1: CreepJS
    page.goto("https://abrahamjuliot.github.io/creepjs/")
    page.wait_for_timeout(5000)
    print("CreepJS test loaded - check trust score")
    
    # Test 2: BrowserLeaks
    page.goto("https://browserleaks.com/")
    page.wait_for_timeout(3000)
    print("BrowserLeaks loaded")
    
    # Test 3: WebRTC leak
    page.goto("https://ipleak.net/")
    page.wait_for_timeout(5000)
    print("Check for WebRTC leaks")
    
    input("Press Enter to close...")
```

### Step 5: Test với e-commerce platforms
```python
# test_ecommerce.py
from camoufox import Camoufox

platforms = [
    ("eBay", "https://www.ebay.com"),
    ("Amazon", "https://www.amazon.com"),
    ("Etsy", "https://www.etsy.com"),
]

for name, url in platforms:
    print(f"\n Testing {name}...")
    with Camoufox(headless=False, geoip=True) as browser:
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)
        
        # Check for bot detection
        content = page.content()
        if "captcha" in content.lower():
            print(f"❌ {name}: CAPTCHA detected")
        elif "verify" in content.lower():
            print(f"⚠️ {name}: Verification required")
        else:
            print(f"✅ {name}: Loaded successfully")
        
        input(f"Check {name} manually. Press Enter to continue...")
```

---

## 📊 What to document (Phase 0)

### Week 1: Build & Environment
- [ ] Build success/failure
- [ ] Build time
- [ ] Dependencies issues
- [ ] Platform-specific problems

### Week 2: Testing Results
Create `docs/phase0-testing.md`:
```markdown
# Phase 0 Testing Results

## Fingerprint Tests
- CreepJS trust score: X%
- BrowserLeaks pass rate: X%
- WebRTC leaks: Yes/No
- Canvas fingerprint: Unique/Common
- WebGL fingerprint: Details...

## E-commerce Tests
- eBay: Success/CAPTCHA/Block
- Amazon: Success/Verification/Block
- Etsy: Success/Verification/Block

## Observations
- What works well
- What doesn't work
- Patterns observed
```

### Week 3: Gap Analysis
Create `docs/gap-analysis.md`:
```markdown
# Gap Analysis: Camoufox vs Tegufox Requirements

## Already Implemented ✅
1. Feature X - Location: `path/to/code.cpp`
2. Feature Y - Location: `path/to/code.py`

## Missing Features ❌
1. Neuromotor Jitter
   - Priority: High
   - Effort: 2-3 weeks
   - Dependencies: None

2. E-commerce profiles
   - Priority: High
   - Effort: 1 month
   - Dependencies: Fingerprint consistency

## Enhancement Opportunities 🔧
1. WebRTC masking
   - Current: Basic
   - Needed: Advanced with STUN blocking
   - Effort: 1 week
```

---

## 🎯 Success Criteria (Phase 0)

Sau 3 tuần, bạn cần có:
- [x] Camoufox build thành công
- [x] Chạy được basic tests
- [x] Document test results
- [x] Gap analysis hoàn chỉnh
- [x] Updated roadmap (nếu cần)

---

## 📚 Resources để học

### Firefox Development:
- Firefox Source Docs: https://firefox-source-docs.mozilla.org/
- Gecko Architecture: https://wiki.mozilla.org/Gecko
- Building Firefox: https://developer.mozilla.org/en-US/docs/Mozilla/Developer_guide/Build_Instructions

### Anti-detection:
- CreepJS: https://github.com/abrahamjuliot/creepjs
- BrowserLeaks: https://browserleaks.com/
- Fingerprint.com blog: https://fingerprint.com/blog/

### Behavioral Modeling:
- Fitts' Law: https://en.wikipedia.org/wiki/Fitts%27s_law
- Mouse Dynamics: Papers on human-computer interaction

### E-commerce Anti-fraud:
- eBay Seller Protection: https://www.ebay.com/help/policies/
- Amazon Account Health: https://sellercentral.amazon.com/

---

## 🛠️ Recommended Tools

### Development:
- **IDE**: VS Code với C++ extension
- **Debugger**: Firefox Developer Tools, gdb/lldb
- **Profiler**: Firefox Profiler, Valgrind

### Testing:
- **Fingerprint**: CreepJS, BrowserLeaks, AmIUnique
- **WebRTC**: ipleak.net, browserleaks.com/webrtc
- **TLS**: ja3er.com, tls.peet.ws

### Analysis:
- **Network**: Wireshark, mitmproxy
- **Reverse Engineering**: Ghidra, IDA Pro (for analyzing anti-fraud JS)

---

## ⚠️ Common Pitfalls

### 1. Build issues
- **Problem**: Firefox build fails
- **Solution**: Check `mach bootstrap`, install all dependencies

### 2. Patch conflicts
- **Problem**: Camoufox updates break our patches
- **Solution**: Pin Firefox version, selective merge

### 3. Detection still happens
- **Problem**: E-commerce platforms still detect
- **Solution**: Analyze traffic, check consistency, iterate

---

## 🤝 Getting Help

### Camoufox Community:
- GitHub: https://github.com/CloverLabsAI/camoufox
- Issues: https://github.com/CloverLabsAI/camoufox/issues

### Firefox Development:
- Matrix Chat: https://chat.mozilla.org/
- Developer Forum: https://discourse.mozilla.org/

---

## 📈 Next Milestones

After Phase 0, you'll move to:

**Phase 1** (Week 4-7): Setup & Optimization
- Rename to Tegufox
- Setup CI/CD
- Enhance profile management

**Phase 2** (Week 8-15): Enhanced Fingerprinting
- WebRTC improvements
- Fingerprint consistency engine
- E-commerce presets

**MVP Target**: Week 27 (6 months)

---

## 📝 Weekly Checklist

Copy this for each week:

```markdown
## Week X Checklist

### Planned:
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

### Completed:
- [x] Task A
- [x] Task B

### Blockers:
- Issue 1: Description
- Issue 2: Description

### Next Week:
- Focus area
- Key deliverables
```

---

## 🎬 Action Items (Today)

1. **Fork Camoufox** ← START HERE
2. **Install dependencies**
3. **Build successfully**
4. **Run first test**
5. **Document results**

---

**Good luck! 🦊**

Remember: This is a marathon, not a sprint. Focus on:
- ✅ Thorough documentation
- ✅ Test everything
- ✅ Learn as you go
- ✅ Don't rush patches

**Estimated time commitment**: 20-30 hours/week for 6-10 months

---

**Questions?** Review:
- [README.md](README.md) - Overview
- [ROADMAP.md](ROADMAP.md) - Detailed phases
- [TODO.md](TODO.md) - Week-by-week tasks
- [idea.md](idea.md) - Technical deep dive
