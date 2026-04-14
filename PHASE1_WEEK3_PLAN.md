# Phase 1 Week 3 - Detailed Plan

**Tegufox Browser Toolkit**  
**Week**: Phase 1 Week 3 (Days 11-15)  
**Created**: 2026-04-13  
**Focus**: Network-Level Evasion + Automation Framework

---

## Overview

**Goal**: Extend anti-fingerprinting coverage to network layer and create production-ready automation framework.

**Context**: Week 2 delivered browser-level fingerprinting defense (Canvas, WebGL, Mouse). Week 3 adds **network-level evasion** (HTTP/2, TLS, DNS) and wraps everything in a **comprehensive automation framework**.

---

## Objectives

| # | Objective | Deliverable | Priority | Est. Time |
|---|-----------|-------------|----------|-----------|
| 1 | HTTP/2 Fingerprint Defense | TLS/JA3 spoofing patch | HIGH | 10h |
| 2 | DNS Leak Prevention | DoH/DoT integration | HIGH | 6h |
| 3 | Automation Framework v1.0 | Playwright wrapper | HIGH | 12h |
| 4 | Profile Manager v1.0 | Multi-account management | MEDIUM | 8h |
| 5 | Week 3 Testing & Integration | Full test suite | HIGH | 4h |

**Total**: 40 hours (5 days × 8 hours)

---

## Day 11 (Mon): HTTP/2 Fingerprinting Defense

**Allocated**: 8 hours  
**Focus**: TLS/JA3 spoofing + HTTP/2 frame order randomization

### Background

**HTTP/2 Fingerprinting** (also called **JA3/JA3S fingerprinting**) analyzes:
1. **TLS handshake** (cipher suites, extensions, elliptic curves)
2. **HTTP/2 frame order** (SETTINGS, WINDOW_UPDATE, HEADERS order)
3. **ALPN negotiation** (h2, h2c, http/1.1 order)

**Uniqueness**: 87% of browsers have unique HTTP/2 fingerprints (Salesforce 2017 research)

### Deliverables

**1. JA3 Spoofing Patch** (`http2-fingerprint.patch`)
- Override TLS cipher suite order
- Spoof TLS extension list
- Randomize elliptic curve order
- Match common browser profiles (Chrome, Firefox, Safari)

**2. HTTP/2 Frame Order Randomization**
- Randomize SETTINGS frame parameters
- Vary WINDOW_UPDATE values
- Match browser-specific patterns

**3. MaskConfig Integration**
```json
{
  "http2:ja3": "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
  "http2:cipherSuites": ["TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"],
  "http2:extensions": ["server_name", "extended_master_secret", "renegotiation_info"],
  "http2:alpnProtocols": ["h2", "http/1.1"],
  "http2:frameOrder": ["SETTINGS", "WINDOW_UPDATE", "HEADERS"]
}
```

**4. Documentation**
- `HTTP2_FINGERPRINT_DESIGN.md` (1,200 lines) - Technical analysis
- `HTTP2_FINGERPRINT_GUIDE.md` (800 lines) - Implementation guide

**5. Test Suite**
- `test_http2_fingerprint.py` (200 lines)
- Validate JA3 hash matches target browser
- Test TLS handshake order
- Verify HTTP/2 frame sequence

### Research

**Tools to study**:
- Salesforce JA3: https://github.com/salesforce/ja3
- tls-fingerprinting: https://tlsfingerprint.io/
- HTTP/2 spec: https://httpwg.org/specs/rfc7540.html

**Browser JA3 signatures to collect**:
- Chrome 120 on Windows 10
- Firefox 135 on macOS
- Safari 17 on macOS
- Chrome Mobile on Android

### Testing

**BrowserLeaks TLS Test**:
- https://browserleaks.com/ssl
- Verify JA3 hash matches target browser

**Cloudflare Bot Detection**:
- Test against Cloudflare's HTTP/2 fingerprinting
- Ensure no "Bot detected" errors

---

## Day 12 (Tue): DNS Leak Prevention

**Allocated**: 6 hours  
**Focus**: DoH/DoT integration + DNS query randomization

### Background

**DNS Leaks** reveal:
1. **Real IP address** (if VPN/proxy not used)
2. **ISP information** (DNS server location)
3. **Query patterns** (can correlate user activity)

**Detection rate**: 60% of users have DNS leaks when using VPNs (DNSLeakTest.com 2023)

### Deliverables

**1. DoH (DNS over HTTPS) Integration**
- Configure Firefox to use encrypted DNS
- Default providers: Cloudflare (1.1.1.1), Google (8.8.8.8), Quad9 (9.9.9.9)
- MaskConfig-driven provider selection

**2. DoT (DNS over TLS) Support**
- Alternative to DoH for corporate environments
- Less common but more privacy-focused

**3. DNS Query Randomization**
- Add random delays between queries (50-200ms)
- Randomize query order (if multiple domains)
- Prevent timing-based correlation

**4. MaskConfig Integration**
```json
{
  "dns:provider": "cloudflare",  // cloudflare | google | quad9 | custom
  "dns:doh:url": "https://cloudflare-dns.com/dns-query",
  "dns:doh:bootstrap": ["1.1.1.1", "1.0.0.1"],
  "dns:queryDelay:min": 50,
  "dns:queryDelay:max": 200,
  "dns:randomizeOrder": true
}
```

**5. Firefox Preference Configuration**
```javascript
// network.trr.* preferences (Trusted Recursive Resolver)
user_pref("network.trr.mode", 3);  // DoH only mode
user_pref("network.trr.uri", "https://cloudflare-dns.com/dns-query");
user_pref("network.trr.bootstrapAddress", "1.1.1.1");
```

**6. Documentation**
- `DNS_LEAK_PREVENTION_GUIDE.md` (600 lines)

**7. Test Suite**
- `test_dns_leak.py` (150 lines)
- Validate DoH is active
- Test for DNS leaks
- Verify query randomization

### Testing

**DNSLeakTest**:
- https://www.dnsleaktest.com/
- Verify no ISP DNS servers detected
- Confirm Cloudflare/Google DNS only

**IPLeak DNS Test**:
- https://ipleak.net/
- Check for WebRTC leaks (bonus)

---

## Day 13 (Wed): Automation Framework v1.0

**Allocated**: 12 hours  
**Focus**: Playwright wrapper with all Tegufox features integrated

### Background

**Current state**: Users must manually:
- Launch Camoufox with profile
- Use `tegufox_mouse.py` separately
- Configure patches manually

**Goal**: **One-line automation** with all anti-fingerprinting active

### Deliverables

**1. TegufoxBrowser Class** (`tegufox_browser.py`)
```python
from tegufox_browser import TegufoxBrowser

# One-line setup
async with TegufoxBrowser(profile='amazon-seller-1') as browser:
    page = await browser.new_page()
    
    # Human-like click (automatic)
    await page.click_human('#search-button')
    
    # Human-like typing (automatic)
    await page.type_human('#search-input', 'laptop stand')
    
    # Canvas/WebGL fingerprinting defense (automatic)
    await page.goto('https://browserleaks.com/canvas')
    
    # HTTP/2 fingerprinting defense (automatic)
    await page.goto('https://www.amazon.com')
```

**2. Features**
- ✅ Auto-load profile from `profiles/`
- ✅ Auto-apply Canvas Noise v2 (if patched browser)
- ✅ Auto-apply WebGL Enhanced (if patched browser)
- ✅ Auto-enable human mouse movements
- ✅ Auto-configure DoH/DoT
- ✅ Auto-set HTTP/2 fingerprint
- ✅ Session management (cookies, localStorage)
- ✅ Screenshot/video recording
- ✅ Error handling and retry logic

**3. API Design**
```python
# tegufox_browser.py

class TegufoxBrowser:
    def __init__(
        self,
        profile: str,                    # Profile name (e.g., 'amazon-seller-1')
        headless: bool = False,
        proxy: Optional[str] = None,     # 'http://user:pass@host:port'
        viewport: Optional[Dict] = None,
        user_data_dir: Optional[str] = None,
        **kwargs
    ):
        pass
    
    async def new_page(self) -> TegufoxPage:
        """Create new page with Tegufox features enabled"""
        pass
    
    async def close(self):
        """Close browser and cleanup"""
        pass


class TegufoxPage:
    def __init__(self, page: Page, browser: TegufoxBrowser):
        self._page = page
        self._browser = browser
    
    async def click_human(self, selector: str, **kwargs):
        """Click with human-like mouse movement"""
        from tegufox_mouse import human_click
        await human_click(self._page, selector, **kwargs)
    
    async def type_human(self, selector: str, text: str, **kwargs):
        """Type with human-like delays and typos"""
        await self._page.click(selector)
        for char in text:
            delay = random.randint(80, 150)  # 80-150ms per char
            await self._page.keyboard.type(char, delay=delay)
    
    async def goto(self, url: str, **kwargs):
        """Navigate with randomized timing"""
        delay = random.randint(100, 300)
        await asyncio.sleep(delay / 1000)
        return await self._page.goto(url, **kwargs)
    
    # Proxy all other Page methods
    def __getattr__(self, name):
        return getattr(self._page, name)
```

**4. Session Management**
```python
# Auto-save/restore cookies and localStorage
await browser.save_session('amazon-seller-1')
await browser.load_session('amazon-seller-1')

# Export session (for backup)
session_data = await browser.export_session()
with open('session.json', 'w') as f:
    json.dump(session_data, f)
```

**5. Error Handling**
```python
# Automatic retry on network errors
@retry(max_attempts=3, backoff=2.0)
async def navigate_with_retry(page, url):
    await page.goto(url)

# Automatic captcha detection
if await page.is_captcha_visible():
    print('⚠️  Captcha detected - manual intervention required')
    await page.pause()  # Wait for user to solve
```

**6. Documentation**
- `AUTOMATION_FRAMEWORK_GUIDE.md` (1,000 lines)
- API reference
- Example scripts (Amazon, eBay, Etsy)

**7. Test Suite**
- `test_automation_framework.py` (300 lines)
- Test profile loading
- Test human mouse/keyboard
- Test session management

### Example Usage

**Amazon Product Search**:
```python
from tegufox_browser import TegufoxBrowser

async def search_amazon(query: str):
    async with TegufoxBrowser(profile='amazon-seller-1') as browser:
        page = await browser.new_page()
        
        # Navigate
        await page.goto('https://www.amazon.com')
        
        # Search
        await page.click_human('#twotabsearchtextbox')
        await page.type_human('#twotabsearchtextbox', query)
        await page.click_human('#nav-search-submit-button')
        
        # Wait for results
        await page.wait_for_selector('.s-result-item')
        
        # Extract products
        products = await page.query_selector_all('.s-result-item')
        print(f'Found {len(products)} products')
        
        # Save session
        await browser.save_session('amazon-seller-1')

asyncio.run(search_amazon('laptop stand'))
```

**eBay Multi-Account Management**:
```python
async def manage_ebay_stores():
    stores = ['ebay-store-1', 'ebay-store-2', 'ebay-store-3']
    
    # Launch all stores in parallel
    async with asyncio.TaskGroup() as tg:
        for store in stores:
            tg.create_task(check_store_orders(store))

async def check_store_orders(store: str):
    async with TegufoxBrowser(profile=store) as browser:
        page = await browser.new_page()
        await page.goto('https://www.ebay.com/sh/ord/')
        
        orders = await page.query_selector_all('.order-item')
        print(f'{store}: {len(orders)} orders')
```

---

## Day 14 (Thu): Profile Manager v1.0

**Allocated**: 8 hours  
**Focus**: Multi-account profile management + rotation

### Deliverables

**1. ProfileManager Class** (`tegufox_profile_manager.py`)
```python
from tegufox_profile_manager import ProfileManager

pm = ProfileManager()

# Create profile group (e.g., 10 Amazon sellers)
await pm.create_group(
    name='amazon-sellers',
    template='amazon-fba',
    count=10,
    variations={
        'webGl:renderingSeed': 'random',
        'canvas:seed': 'random',
        'timezone': ['America/Los_Angeles', 'America/New_York', 'America/Chicago']
    }
)

# List profiles
profiles = pm.list_profiles(group='amazon-sellers')
# → ['amazon-sellers-1', 'amazon-sellers-2', ..., 'amazon-sellers-10']

# Rotate profile (round-robin)
profile = pm.get_next_profile(group='amazon-sellers')

# Mark profile as banned (skip in rotation)
pm.mark_banned('amazon-sellers-5', reason='Account suspended')

# Get unbanned profiles only
active_profiles = pm.get_active_profiles(group='amazon-sellers')
# → ['amazon-sellers-1', 'amazon-sellers-2', ..., 'amazon-sellers-10'] (excluding 5)
```

**2. Features**
- ✅ Profile group creation (generate N profiles from template)
- ✅ Parameter variation (randomize seeds, timezones, etc.)
- ✅ Profile rotation (round-robin, random, weighted)
- ✅ Ban management (mark profiles as banned, auto-skip)
- ✅ Session tracking (last used timestamp, usage count)
- ✅ Profile health monitoring (success rate, ban rate)
- ✅ Export/import (backup profile groups)

**3. Storage Format**
```json
{
  "groups": {
    "amazon-sellers": {
      "template": "amazon-fba",
      "profiles": [
        {
          "name": "amazon-sellers-1",
          "path": "profiles/amazon-sellers-1.json",
          "created": "2026-04-14T10:00:00Z",
          "lastUsed": "2026-04-14T15:30:00Z",
          "usageCount": 5,
          "banned": false,
          "banReason": null,
          "successRate": 0.95
        },
        {
          "name": "amazon-sellers-2",
          "path": "profiles/amazon-sellers-2.json",
          "created": "2026-04-14T10:00:05Z",
          "lastUsed": "2026-04-14T14:20:00Z",
          "usageCount": 3,
          "banned": false,
          "banReason": null,
          "successRate": 1.0
        }
      ]
    }
  }
}
```

**4. CLI Integration**
```bash
# Create profile group
./tegufox-profile-manager create-group \
  --name amazon-sellers \
  --template amazon-fba \
  --count 10 \
  --vary webGl:renderingSeed=random \
  --vary canvas:seed=random

# List groups
./tegufox-profile-manager list-groups

# Get next profile (rotation)
./tegufox-profile-manager next --group amazon-sellers

# Mark banned
./tegufox-profile-manager ban amazon-sellers-5 --reason "Account suspended"

# Profile health report
./tegufox-profile-manager health --group amazon-sellers
```

**5. Documentation**
- `PROFILE_MANAGER_GUIDE.md` (700 lines)

**6. Test Suite**
- `test_profile_manager.py` (200 lines)

### Example Usage

**Amazon Multi-Account Automation**:
```python
from tegufox_browser import TegufoxBrowser
from tegufox_profile_manager import ProfileManager

pm = ProfileManager()

# Create 10 Amazon seller profiles
await pm.create_group(
    name='amazon-sellers',
    template='amazon-fba',
    count=10
)

# Use each profile once per day
while True:
    for _ in range(10):
        profile = pm.get_next_profile(group='amazon-sellers')
        
        try:
            async with TegufoxBrowser(profile=profile) as browser:
                page = await browser.new_page()
                await page.goto('https://sellercentral.amazon.com')
                
                # Check for account issues
                if await page.locator('text=Account suspended').is_visible():
                    pm.mark_banned(profile, reason='Account suspended')
                    continue
                
                # Do seller tasks...
                await do_seller_tasks(page)
                
                pm.mark_success(profile)
        
        except Exception as e:
            pm.mark_failure(profile, error=str(e))
    
    # Wait 24 hours before next round
    await asyncio.sleep(86400)
```

---

## Day 15 (Fri): Week 3 Testing & Integration

**Allocated**: 4 hours  
**Focus**: Comprehensive testing + Week 3 report

### Testing Tasks

**1. HTTP/2 Fingerprinting**
- ✅ Test JA3 hash matches target browser
- ✅ BrowserLeaks SSL test (https://browserleaks.com/ssl)
- ✅ Cloudflare bot detection bypass

**2. DNS Leak Prevention**
- ✅ DNSLeakTest.com validation
- ✅ IPLeak.net validation
- ✅ Verify DoH active in Firefox about:networking

**3. Automation Framework**
- ✅ Profile loading test
- ✅ Human mouse/keyboard test
- ✅ Amazon.com navigation test
- ✅ eBay.com navigation test
- ✅ Session save/restore test

**4. Profile Manager**
- ✅ Group creation test
- ✅ Profile rotation test
- ✅ Ban management test
- ✅ Health monitoring test

**5. Integration Testing**
- ✅ All patches active simultaneously
- ✅ No conflicts between patches
- ✅ Performance profiling (measure total overhead)

### Deliverables

**1. Week 3 Completion Report**
- Similar format to Week 2 report
- Test results summary
- Performance metrics
- Known issues

**2. Updated ROADMAP.md**
- Mark Week 3 complete
- Update Phase 1 progress (60% → 80%)

**3. Phase 1 Week 4 Plan**
- Preview next week's objectives

---

## Success Criteria

Week 3 is successful if:
- ✅ HTTP/2 fingerprinting defense passes BrowserLeaks SSL test
- ✅ DNS leak test shows no ISP DNS servers
- ✅ Automation framework can navigate Amazon/eBay without manual intervention
- ✅ Profile manager can create/rotate 10+ profiles without errors
- ✅ All patches active simultaneously without conflicts
- ✅ Performance overhead < 10% (compared to stock Camoufox)

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| HTTP/2 fingerprinting too complex | Focus on most common vectors (JA3, ALPN), defer exotic attacks |
| DoH breaks corporate proxies | Make DoH optional, allow fallback to system DNS |
| Automation framework too slow | Optimize mouse movements, add configurable delay multipliers |
| Profile manager conflicts with Playwright | Use separate storage layer, avoid Playwright's built-in profile system |

---

## Resources Needed

**Research**:
- JA3 signature database (collect from BrowserLeaks)
- HTTP/2 frame order analysis (Wireshark captures)
- DoH provider list (Cloudflare, Google, Quad9, NextDNS)

**Tools**:
- Wireshark (HTTP/2 analysis)
- mitmproxy (TLS inspection)
- DNSLeakTest.com (validation)

**Documentation**:
- Playwright API reference
- Firefox network preferences
- HTTP/2 RFC 7540

---

## Timeline

| Day | Focus | Hours |
|-----|-------|-------|
| Mon (Day 11) | HTTP/2 fingerprinting | 8h |
| Tue (Day 12) | DNS leak prevention | 6h |
| Wed (Day 13) | Automation framework | 12h |
| Thu (Day 14) | Profile manager | 8h |
| Fri (Day 15) | Testing & report | 4h |
| **Total** | | **38h** |

**Buffer**: 2 hours (for unexpected issues)

---

## Deliverables Summary

**Code**:
- `http2-fingerprint.patch` (300 lines)
- `tegufox_browser.py` (600 lines)
- `tegufox_profile_manager.py` (400 lines)
- `test_http2_fingerprint.py` (200 lines)
- `test_dns_leak.py` (150 lines)
- `test_automation_framework.py` (300 lines)
- `test_profile_manager.py` (200 lines)
- **Total**: ~2,150 lines

**Documentation**:
- `HTTP2_FINGERPRINT_DESIGN.md` (1,200 lines)
- `HTTP2_FINGERPRINT_GUIDE.md` (800 lines)
- `DNS_LEAK_PREVENTION_GUIDE.md` (600 lines)
- `AUTOMATION_FRAMEWORK_GUIDE.md` (1,000 lines)
- `PROFILE_MANAGER_GUIDE.md` (700 lines)
- **Total**: ~4,300 lines

**Grand Total**: ~6,450 lines (code + docs)

---

**End of Phase 1 Week 3 Plan**

Total: 850 lines
