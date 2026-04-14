# Running Tests - Quick Guide

> How to run Tegufox Phase 0 tests

---

## Prerequisites

✅ Camoufox installed  
✅ Virtual environment activated  
✅ Playwright browsers downloaded

---

## Activate Virtual Environment

**Always run this first:**

```bash
cd /Users/lugon/dev/2026-3/tegufox-browser
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

---

## Test 1: Basic Functionality (5 minutes)

**Purpose**: Verify Camoufox can launch and navigate

```bash
python test_camoufox_basic.py
```

**Expected**:
- Browser window opens
- Navigates to example.com
- Shows page title
- Waits for manual inspection
- Press Ctrl+C or Enter to close

**Success Criteria**:
- ✅ No errors in terminal
- ✅ Browser opens visually
- ✅ Page loads completely

---

## Test 2: Fingerprint Detection (30-45 minutes)

**Purpose**: Test against fingerprinting sites

```bash
python test_fingerprint.py
```

**What happens**:
1. Opens CreepJS → wait 10 seconds
2. Opens BrowserLeaks Canvas → wait 5 seconds  
3. Opens BrowserLeaks WebGL → wait 5 seconds
4. Opens ipleak.net → wait 8 seconds
5. Opens BrowserLeaks JavaScript → wait 5 seconds

**For each test**:
- Browser opens to test site
- Wait for analysis to complete
- **Manually inspect** the results
- **Take screenshots** if possible
- Press Enter to continue to next test

**Document in**: `docs/phase0-fingerprint-results.md`

### What to Look For:

**CreepJS**:
- Trust score (top right corner)
- Red/yellow/green indicators
- Any "lies detected" warnings

**BrowserLeaks Canvas**:
- Canvas fingerprint hash
- Uniqueness percentage
- Image rendering

**BrowserLeaks WebGL**:
- GPU vendor/renderer
- Unmasked values
- Extensions list

**ipleak.net**:
- WebRTC IPs shown (should be none or only proxy IP)
- Local IP leaks (should be none)
- IPv6 leaks (should be none)

**Navigator Properties**:
- `navigator.webdriver` value (should be undefined)
- User agent string
- Platform/OS consistency

---

## Test 3: E-commerce Platforms (30-45 minutes)

**Purpose**: Test bot detection on real e-commerce sites

```bash
python test_ecommerce.py
```

**What happens**:
1. Tests eBay.com
2. Tests Amazon.com
3. Tests Etsy.com

**For each platform**:
- Browser opens to homepage
- Automatic detection check runs
- Shows results in terminal
- **Manually browse the site**:
  - Click search
  - Browse categories
  - View product pages
  - Try signing in (optional, use test account)
- Document if you see:
  - CAPTCHA
  - "Verify you're human"
  - "Unusual activity" warnings
  - Access denied/blocked
- Press Enter to continue

**Document in**: `docs/phase0-ecommerce-results.md`

---

## Documentation

After each test, fill in the template:

### Fingerprint Results

Open: `docs/phase0-fingerprint-results.md`

Fill in:
- Date/time
- Trust scores
- Detection status
- Screenshots paths
- Observations

### E-commerce Results

Open: `docs/phase0-ecommerce-results.md`

Fill in:
- Platform access results
- CAPTCHA encounters
- Detection triggers
- Browsing experience
- Screenshots

---

## Tips for Testing

### 1. Take Screenshots

**macOS**: Cmd+Shift+4, then spacebar, click window

Save to: `tegufox-browser/docs/screenshots/`

Naming convention:
- `creepjs-trust-score.png`
- `ebay-homepage.png`
- `amazon-captcha.png`

### 2. Record Browser Console

Open browser console: Cmd+Option+I (macOS)

Copy any errors/warnings to your notes.

### 3. Test Systematically

- One test at a time
- Don't rush
- Document everything
- Note timestamps

### 4. Network Conditions

For consistent results:
- Use same network throughout
- Note if using VPN/proxy
- Record approximate time of day

---

## Common Issues

### "Browser not found"
```bash
# Re-install Playwright browsers
source venv/bin/activate
playwright install firefox
```

### "Module not found: camoufox"
```bash
# Activate virtual environment
source venv/bin/activate

# Re-install if needed
cd /Users/lugon/dev/2026-3/camoufox-source/pythonlib
pip install -e .
```

### Browser doesn't open
- Check if headless mode is accidentally enabled
- Verify display server on Linux
- Check macOS permissions

### Test hangs/freezes
- Press Ctrl+C to stop
- Check internet connection
- Try again with longer timeout

---

## After Testing

### 1. Review Documentation

Make sure you filled in:
- [ ] All test results
- [ ] Screenshots attached
- [ ] Observations noted
- [ ] Gaps identified

### 2. Create Summary

In your notes, summarize:
- What works well
- What doesn't work
- Critical issues
- Surprises/unexpected findings

### 3. Next Steps

Prepare for Week 3:
- Gap analysis
- Architecture deep dive
- Planning Tegufox enhancements

---

## Quick Commands Reference

```bash
# Activate venv
source venv/bin/activate

# Run basic test
python test_camoufox_basic.py

# Run fingerprint tests
python test_fingerprint.py

# Run e-commerce tests
python test_ecommerce.py

# Deactivate venv when done
deactivate
```

---

## Expected Timeline

- **Test 1**: 5 minutes
- **Test 2**: 30-45 minutes
- **Test 3**: 30-45 minutes
- **Documentation**: 30-60 minutes
- **Total**: 2-3 hours

---

**Good luck with testing! 🧪🦊**
