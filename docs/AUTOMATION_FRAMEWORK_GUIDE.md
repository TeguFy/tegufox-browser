# Tegufox Automation Framework v1.0 - User Guide

**Author:** Tegufox Browser Toolkit  
**Date:** April 14, 2026  
**Phase:** 1 - Week 3 Day 13  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Components](#core-components)
5. [API Reference](#api-reference)
6. [Multi-Account Workflows](#multi-account-workflows)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage](#advanced-usage)
10. [Examples](#examples)

---

## Overview

### What is Tegufox Automation Framework?

The Tegufox Automation Framework is a **production-grade automation toolkit** built on top of Camoufox browser with advanced anti-detection capabilities. It provides:

- **TegufoxSession**: High-level wrapper around Playwright with human-like behavior
- **ProfileRotator**: Multi-account session management with automatic rotation
- **SessionManager**: Persistent session state across browser restarts
- **Anti-detection features**: DNS leak prevention, HTTP/2 fingerprinting, human mouse movements
- **E-commerce ready**: Optimized for Amazon, eBay, Etsy, and other platforms

### Key Features

✅ **DNS Leak Prevention** - DoH/DoT integration (Cloudflare, Quad9, Mullvad)  
✅ **HTTP/2 Fingerprint Consistency** - TLS + HTTP/2 + User-Agent alignment  
✅ **Human-like Mouse Movements** - Bezier curves, Fitts's Law timing, tremor simulation  
✅ **Random Delays & Jitter** - Anti-bot timing randomization  
✅ **Session Persistence** - Save/restore cookies, storage, visited URLs  
✅ **Multi-account Rotation** - Round-robin, random, or weighted strategies  
✅ **Canvas Noise & WebGL Spoofing** - Integrated from Week 2 patches  
✅ **Screenshot on Error** - Automatic debugging screenshots  

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Tegufox Automation Framework                │
├─────────────────────────────────────────────────────────────┤
│  TegufoxSession  │  ProfileRotator  │  SessionManager       │
├─────────────────────────────────────────────────────────────┤
│  HumanMouse     │  SessionConfig   │  SessionState          │
├─────────────────────────────────────────────────────────────┤
│                   Camoufox (Playwright)                      │
├─────────────────────────────────────────────────────────────┤
│  DNS Prevention │  HTTP/2 Fingerprint │  Canvas/WebGL       │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.9+ (tested with Python 3.14.3)
- Camoufox 0.5.0+
- 4GB+ RAM
- macOS, Linux, or Windows

### Step 1: Install Camoufox

```bash
pip install camoufox
```

### Step 2: Clone Tegufox Browser Toolkit

```bash
git clone https://github.com/your-org/tegufox-browser.git
cd tegufox-browser
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python3 tegufox_automation.py
```

Expected output:
```
Tegufox Automation Framework v1.0
==================================================

Example 1: Basic session
✓ Basic session complete

Example 2: DNS leak test
DNS leak test: PASS
DNS servers: 1

Example 3: Profile rotation
✓ Rotation 1: chrome-120-windows
✓ Rotation 2: firefox-115-windows

==================================================
All examples complete!
```

---

## Quick Start

### Example 1: Basic Session

```python
from tegufox_automation import TegufoxSession

# Create session with Chrome 120 profile
with TegufoxSession(profile="chrome-120") as session:
    # Navigate to website
    session.goto("https://amazon.com")
    
    # Human-like click
    session.human_click("#nav-search-submit-button")
    
    # Human-like typing
    session.human_type("#twotabsearchtextbox", "laptop")
    
    # Random delay (1-3 seconds)
    session.wait_random(1, 3)
    
    # Screenshot
    session.screenshot("amazon-search.png")
```

### Example 2: Multi-Account Rotation

```python
from tegufox_automation import ProfileRotator

# Create rotator with 3 seller accounts
rotator = ProfileRotator([
    "amazon-seller-1",
    "amazon-seller-2",
    "amazon-seller-3"
], strategy="round-robin")

# Rotate through accounts
for session in rotator:
    with session:
        session.goto("https://sellercentral.amazon.com")
        session.human_click("#login-button")
        # ... perform seller tasks
```

### Example 3: Session Persistence

```python
from tegufox_automation import TegufoxSession, SessionManager

manager = SessionManager("sessions/")

# Day 1: Login and save session
with TegufoxSession("chrome-120") as session:
    session.goto("https://amazon.com")
    session.human_click("#nav-signin")
    # ... perform login
    manager.save(session, name="amazon-main")

# Day 2: Restore session (already logged in)
with TegufoxSession("chrome-120") as session:
    manager.restore(session, name="amazon-main")
    session.goto("https://amazon.com/orders")  # Already logged in!
```

---

## Core Components

### 1. TegufoxSession

**Primary automation interface** - wraps Camoufox/Playwright with anti-detection.

#### Constructor

```python
TegufoxSession(
    profile: Optional[str] = None,          # Profile name (e.g., "chrome-120")
    profile_path: Optional[str] = None,     # Path to profile JSON
    config: Optional[SessionConfig] = None, # SessionConfig object
    **kwargs                                # Additional config params
)
```

#### Key Methods

| Method | Description |
|--------|-------------|
| `goto(url)` | Navigate to URL with random delay |
| `human_click(selector)` | Click with human-like mouse movement |
| `human_type(selector, text)` | Type with human-like timing |
| `human_scroll(distance, direction)` | Scroll with human-like behavior |
| `wait_random(min, max)` | Random delay (anti-detection) |
| `wait_for_selector(selector)` | Wait for element to appear |
| `screenshot(path)` | Take screenshot |
| `evaluate(script)` | Execute JavaScript |
| `get_cookies()` | Get all cookies |
| `set_cookies(cookies)` | Set cookies |
| `validate_dns_leak()` | Validate DNS leak prevention |
| `validate_http2_fingerprint()` | Validate HTTP/2 fingerprint |

#### Usage Patterns

**Context Manager (Recommended)**
```python
with TegufoxSession(profile="chrome-120") as session:
    session.goto("https://example.com")
    # Browser automatically closes after block
```

**Manual Start/Stop**
```python
session = TegufoxSession(profile="chrome-120")
session.start()
session.goto("https://example.com")
session.stop()
```

### 2. SessionConfig

**Configuration object** for TegufoxSession behavior.

```python
from tegufox_automation import SessionConfig

config = SessionConfig(
    # Browser settings
    headless=False,              # Run in headless mode
    viewport_width=1920,         # Custom viewport width
    viewport_height=1080,        # Custom viewport height
    
    # Anti-detection
    enable_dns_leak_prevention=True,
    enable_human_mouse=True,
    enable_random_delays=True,
    enable_idle_jitter=True,
    
    # Timing (milliseconds)
    action_delay_min=100,
    action_delay_max=500,
    page_load_timeout=30000,
    navigation_timeout=30000,
    
    # Session persistence
    save_session_state=True,
    session_dir=Path("sessions/"),
    
    # Screenshots
    screenshot_on_error=True,
    screenshot_dir=Path("screenshots/errors/"),
)

session = TegufoxSession(profile="chrome-120", config=config)
```

### 3. ProfileRotator

**Multi-account session manager** with automatic rotation.

#### Constructor

```python
ProfileRotator(
    profiles: List[str],                    # List of profile names
    strategy: str = "round-robin",          # Rotation strategy
    session_config: Optional[SessionConfig] = None,
    **kwargs
)
```

#### Rotation Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `round-robin` | Sequential rotation | Fair distribution |
| `random` | Random selection | Unpredictable pattern |
| `weighted` | Least recently used first | Load balancing |

#### Example

```python
rotator = ProfileRotator(
    profiles=["seller-1", "seller-2", "seller-3"],
    strategy="weighted"
)

for session in rotator:
    with session:
        # Use session
        pass
```

### 4. SessionManager

**Persistent session state** across browser restarts.

#### Methods

```python
manager = SessionManager("sessions/")

# Save session state
manager.save(session, name="my-session")

# Restore session state
manager.restore(session, name="my-session")

# List all saved sessions
sessions = manager.list_sessions()

# Delete saved session
manager.delete("my-session")
```

#### Session State Contents

- Cookies
- Local storage
- Session storage
- Visited URLs
- Custom metadata

---

## API Reference

### TegufoxSession API

#### Navigation

```python
# Navigate to URL
session.goto(
    url: str,                           # Target URL
    wait_until: str = "domcontentloaded" # "load" | "domcontentloaded" | "networkidle"
)
```

#### Interactions

```python
# Human-like click
session.human_click(
    selector: str,      # CSS selector or XPath
    **kwargs           # Additional click options
)

# Human-like typing
session.human_type(
    selector: str,      # CSS selector for input
    text: str,         # Text to type
    delay_min: int = 50,   # Min delay between keys (ms)
    delay_max: int = 150,  # Max delay between keys (ms)
)

# Human-like scrolling
session.human_scroll(
    distance: int = 500,        # Scroll distance (pixels)
    direction: str = "down"     # "down" | "up" | "left" | "right"
)
```

#### Waiting

```python
# Random delay
session.wait_random(
    min_seconds: float = 1.0,
    max_seconds: float = 3.0
)

# Wait for selector
session.wait_for_selector(
    selector: str,              # CSS selector
    timeout: Optional[int] = None,  # Timeout (ms)
    state: str = "visible"      # "attached" | "detached" | "visible" | "hidden"
)
```

#### Utilities

```python
# Screenshot
session.screenshot(
    path: str,              # Output file path
    full_page: bool = False # Capture full page
)

# JavaScript evaluation
result = session.evaluate(
    script: str             # JavaScript code
)

# Cookies
cookies = session.get_cookies()
session.set_cookies(cookies: List[Dict])
```

#### Validation

```python
# DNS leak test
result = session.validate_dns_leak()
# Returns: {"is_leaking": bool, "dns_servers": [...], "status": "PASS|FAIL"}

# HTTP/2 fingerprint test
result = session.validate_http2_fingerprint()
# Returns: {"ja3_hash": str, "status": "PASS|FAIL"}
```

---

## Multi-Account Workflows

### Use Case 1: Amazon Seller Accounts

```python
from tegufox_automation import ProfileRotator, SessionManager

# Setup
rotator = ProfileRotator([
    "amazon-seller-us-1",
    "amazon-seller-us-2",
    "amazon-seller-uk-1"
], strategy="round-robin")

manager = SessionManager("sessions/amazon-sellers/")

# Daily workflow
for session in rotator:
    with session:
        profile_name = session.profile.get('name')
        
        # Restore previous session
        manager.restore(session, name=profile_name)
        
        # Navigate to Seller Central
        session.goto("https://sellercentral.amazon.com")
        
        # Check inventory
        session.human_click("#inventory-menu")
        session.wait_random(1, 2)
        
        # Update prices
        session.human_click("#pricing-menu")
        session.wait_random(1, 2)
        
        # Save session
        manager.save(session, name=profile_name)
```

### Use Case 2: eBay Listing Management

```python
from tegufox_automation import TegufoxSession

def update_ebay_listings(profile: str, listings: List[Dict]):
    with TegufoxSession(profile=profile) as session:
        session.goto("https://www.ebay.com/sh/lst/active")
        
        for listing in listings:
            # Find listing
            session.human_type("#search-listings", listing['title'])
            session.wait_random(1, 2)
            
            # Click edit
            session.human_click(f"[data-listing-id='{listing['id']}'] .edit-button")
            session.wait_random(2, 3)
            
            # Update price
            session.human_type("#price-input", str(listing['new_price']))
            session.wait_random(0.5, 1)
            
            # Save
            session.human_click("#save-button")
            session.wait_random(2, 4)

# Run for multiple accounts
for seller_profile in ["ebay-seller-1", "ebay-seller-2"]:
    update_ebay_listings(seller_profile, my_listings)
```

### Use Case 3: Etsy Shop Automation

```python
from tegufox_automation import TegufoxSession

def check_etsy_orders(profile: str):
    with TegufoxSession(profile=profile) as session:
        # Login
        session.goto("https://www.etsy.com/your/shops/me/orders")
        
        # Check for new orders
        new_orders = session.evaluate("""
            () => {
                const badges = document.querySelectorAll('.badge-new');
                return badges.length;
            }
        """)
        
        if new_orders > 0:
            print(f"📦 {new_orders} new orders!")
            
            # Process orders
            for i in range(new_orders):
                session.human_click(f".order-row:nth-child({i+1})")
                session.wait_random(2, 3)
                
                # Mark as shipped
                session.human_click("#mark-shipped-button")
                session.wait_random(1, 2)
        
        # Screenshot for records
        session.screenshot(f"etsy-orders-{profile}.png")

check_etsy_orders("etsy-shop-main")
```

---

## Best Practices

### 1. Profile Selection

**Match profile to use case:**

| Use Case | Recommended Profile | Reason |
|----------|-------------------|--------|
| Amazon US | `chrome-120` | Chrome dominates Amazon traffic |
| eBay | `chrome-120` or `firefox-115` | Both common |
| Etsy | `safari-17` (macOS) or `chrome-120` | Creative user base |
| Price monitoring | `firefox-115` | Privacy-focused |

**DoH provider alignment:**
- Chrome profiles → Cloudflare DoH (matches Chrome default)
- Firefox profiles → Quad9 DoH (privacy alignment)
- Safari profiles → Cloudflare DoH (matches Apple infrastructure)

### 2. Timing & Delays

**Always use random delays:**

```python
# ✅ Good
session.human_click("#button")
session.wait_random(1, 3)
session.human_type("#input", "text")

# ❌ Bad (bot-like)
session.human_click("#button")
session.human_type("#input", "text")
```

**Recommended delay ranges:**

| Action | Min | Max | Notes |
|--------|-----|-----|-------|
| After click | 0.5s | 1.5s | Button response time |
| After page load | 1.0s | 3.0s | Reading content |
| After typing | 0.3s | 0.8s | Thinking time |
| Between actions | 0.5s | 2.0s | Natural pauses |

### 3. Session Persistence

**Save sessions after login:**

```python
manager = SessionManager("sessions/")

# Login once
with TegufoxSession("chrome-120") as session:
    session.goto("https://amazon.com")
    # ... perform login
    manager.save(session, name="amazon-main")

# Reuse session (no login needed)
with TegufoxSession("chrome-120") as session:
    manager.restore(session, name="amazon-main")
    session.goto("https://amazon.com/orders")
```

### 4. Error Handling

**Always use try/except with screenshots:**

```python
config = SessionConfig(
    screenshot_on_error=True,
    screenshot_dir=Path("screenshots/errors/")
)

try:
    with TegufoxSession("chrome-120", config=config) as session:
        session.goto("https://example.com")
        session.human_click("#risky-button")
except Exception as e:
    print(f"Error: {e}")
    # Screenshot already saved in screenshots/errors/
```

### 5. Fingerprint Validation

**Validate fingerprints periodically:**

```python
with TegufoxSession("chrome-120") as session:
    # Validate DNS leak prevention
    dns_result = session.validate_dns_leak()
    assert dns_result['status'] == 'PASS', "DNS leak detected!"
    
    # Validate HTTP/2 fingerprint
    http2_result = session.validate_http2_fingerprint()
    print(f"JA3 hash: {http2_result.get('ja3_hash', 'unknown')}")
```

### 6. Multi-Account Best Practices

**Rotate profiles regularly:**

```python
# ✅ Good - weighted rotation (least recently used)
rotator = ProfileRotator(
    profiles=["seller-1", "seller-2", "seller-3"],
    strategy="weighted"
)

# ❌ Bad - always using same profile
session = TegufoxSession("seller-1")
```

**Use separate session directories:**

```python
# Per-account session storage
manager_us = SessionManager("sessions/amazon-us/")
manager_uk = SessionManager("sessions/amazon-uk/")
manager_ebay = SessionManager("sessions/ebay/")
```

---

## Troubleshooting

### Problem 1: "Camoufox not installed" Error

**Solution:**
```bash
pip install camoufox
# Or if using venv
source venv/bin/activate
pip install camoufox
```

### Problem 2: "Profile not found" Error

**Solution:**
```bash
# Check profile exists
ls profiles/
# Should show: chrome-120.json, firefox-115.json, safari-17.json

# Use correct profile name (without .json extension)
session = TegufoxSession(profile="chrome-120")  # ✅
session = TegufoxSession(profile="chrome-120.json")  # ❌
```

### Problem 3: DNS Leak Detected

**Solution:**

1. Check profile has `dns_config` enabled:
```python
with open("profiles/chrome-120.json") as f:
    profile = json.load(f)
    print(profile['dns_config']['enabled'])  # Should be True
```

2. Verify Firefox preferences applied:
```python
session = TegufoxSession("chrome-120")
session.start()
# Check network.trr.mode preference is set to 3
```

3. **Note:** Full DoH requires browser rebuild with `http2-fingerprint.patch`

### Problem 4: Slow Performance

**Solutions:**

1. Disable random delays for testing:
```python
config = SessionConfig(enable_random_delays=False)
```

2. Use headless mode:
```python
config = SessionConfig(headless=True)
```

3. Reduce page load timeout:
```python
config = SessionConfig(page_load_timeout=10000)
```

### Problem 5: Element Not Found

**Solution:**

Use `wait_for_selector` before clicking:
```python
# ✅ Good
session.wait_for_selector("#button", timeout=10000)
session.human_click("#button")

# ❌ Bad
session.human_click("#button")  # May fail if element not loaded
```

---

## Advanced Usage

### Custom Profile Creation

```python
import json

# Create custom profile
custom_profile = {
    "name": "my-custom-profile",
    "screen": {"width": 1920, "height": 1080},
    "navigator": {
        "userAgent": "Mozilla/5.0 ...",
        "platform": "Win32"
    },
    "dns_config": {
        "enabled": True,
        "provider": "cloudflare"
    },
    "firefox_preferences": {
        "network.trr.mode": 3,
        "network.trr.uri": "https://mozilla.cloudflare-dns.com/dns-query"
    }
}

# Save profile
with open("profiles/my-custom-profile.json", "w") as f:
    json.dump(custom_profile, f, indent=2)

# Use profile
session = TegufoxSession(profile="my-custom-profile")
```

### Custom Mouse Configuration

```python
from tegufox_mouse import MouseConfig

# Create custom mouse config
mouse_config = MouseConfig(
    strategy="bezier",           # Bezier curves
    overshoot_chance=0.8,        # 80% overshoot
    overshoot_max=15.0,          # Max 15px overshoot
    click_delay_min=100,         # 100ms before click
    click_delay_max=300,         # 300ms before click
    tremor_enabled=True,         # Enable tremor
    tremor_sigma=1.5,            # Stronger tremor
)

config = SessionConfig(mouse_config=mouse_config)
session = TegufoxSession("chrome-120", config=config)
```

### Accessing Raw Playwright Page

```python
with TegufoxSession("chrome-120") as session:
    # Access raw Playwright page
    page = session.page
    
    # Use any Playwright method
    page.locator("#button").click()
    page.fill("#input", "text")
    page.screenshot(path="screenshot.png")
```

### Custom JavaScript Injection

```python
with TegufoxSession("chrome-120") as session:
    session.goto("https://example.com")
    
    # Inject custom JavaScript
    session.evaluate("""
        () => {
            // Override navigator properties
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Custom analytics blocking
            window.ga = function() {};
            window.gtag = function() {};
        }
    """)
```

---

## Examples

### Complete Amazon Seller Workflow

```python
from tegufox_automation import TegufoxSession, SessionManager

def amazon_seller_workflow(profile: str):
    """Complete Amazon seller daily workflow"""
    
    manager = SessionManager("sessions/amazon/")
    
    with TegufoxSession(profile=profile) as session:
        # Restore previous session
        manager.restore(session, name=profile)
        
        # Navigate to Seller Central
        session.goto("https://sellercentral.amazon.com")
        session.wait_random(2, 4)
        
        # Check for new orders
        session.human_click("#orders-menu")
        session.wait_random(1, 2)
        
        new_orders = session.evaluate("""
            () => document.querySelectorAll('.new-order-badge').length
        """)
        
        print(f"📦 {new_orders} new orders")
        
        # Check inventory alerts
        session.human_click("#inventory-menu")
        session.wait_random(1, 2)
        
        low_stock = session.evaluate("""
            () => document.querySelectorAll('.low-stock-warning').length
        """)
        
        print(f"⚠️ {low_stock} low stock alerts")
        
        # Update prices (competitive pricing)
        session.human_click("#pricing-menu")
        session.wait_random(1, 2)
        
        # Screenshot for records
        session.screenshot(f"amazon-{profile}-{int(time.time())}.png")
        
        # Save session
        manager.save(session, name=profile)

# Run workflow
amazon_seller_workflow("amazon-seller-us-1")
```

### eBay Price Monitoring Bot

```python
from tegufox_automation import TegufoxSession
import time

def monitor_ebay_competitor_prices(search_term: str, max_pages: int = 3):
    """Monitor competitor prices on eBay"""
    
    results = []
    
    with TegufoxSession(profile="firefox-115") as session:
        # Search for product
        session.goto(f"https://www.ebay.com/sch/i.html?_nkw={search_term}")
        session.wait_random(2, 3)
        
        for page in range(max_pages):
            # Extract listings
            listings = session.evaluate("""
                () => {
                    const items = document.querySelectorAll('.s-item');
                    return Array.from(items).map(item => ({
                        title: item.querySelector('.s-item__title')?.innerText,
                        price: item.querySelector('.s-item__price')?.innerText,
                        shipping: item.querySelector('.s-item__shipping')?.innerText,
                        link: item.querySelector('.s-item__link')?.href
                    }));
                }
            """)
            
            results.extend(listings)
            
            # Next page
            if page < max_pages - 1:
                session.human_click(".pagination__next")
                session.wait_random(2, 4)
        
        # Save results
        import json
        with open(f"ebay-prices-{int(time.time())}.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"💰 Monitored {len(results)} listings")
        return results

# Run monitoring
monitor_ebay_competitor_prices("vintage camera", max_pages=3)
```

---

## Summary

The Tegufox Automation Framework provides **production-grade automation** with advanced anti-detection capabilities:

✅ **Easy to use** - Pythonic API, context managers  
✅ **Anti-detection** - DNS leak prevention, HTTP/2 fingerprinting, human behavior  
✅ **Multi-account** - ProfileRotator for seamless account management  
✅ **Persistent sessions** - Save/restore across browser restarts  
✅ **E-commerce ready** - Optimized for Amazon, eBay, Etsy  
✅ **Production tested** - 26+ automated tests  

**Get started in 5 minutes:**

```python
from tegufox_automation import TegufoxSession

with TegufoxSession(profile="chrome-120") as session:
    session.goto("https://amazon.com")
    session.human_click("#nav-search")
    session.human_type("#twotabsearchtextbox", "laptop")
    session.screenshot("amazon.png")
```

For support, open an issue at: https://github.com/your-org/tegufox-browser

---

**Document Version:** 1.0  
**Last Updated:** April 14, 2026  
**Total Lines:** 850+
