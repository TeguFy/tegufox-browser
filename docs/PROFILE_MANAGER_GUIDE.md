# Tegufox Profile Manager v1.0 - User Guide

**Author:** Tegufox Browser Toolkit  
**Date:** April 14, 2026  
**Phase:** 1 - Week 3 Day 14  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [CLI Commands](#cli-commands)
5. [Python API](#python-api)
6. [Profile Structure](#profile-structure)
7. [Validation System](#validation-system)
8. [Template System](#template-system)
9. [Best Practices](#best-practices)
10. [Examples](#examples)

---

## Overview

### What is Tegufox Profile Manager?

The Tegufox Profile Manager is a **comprehensive profile management system** for Tegufox browser profiles. It provides both CLI and Python API for creating, validating, and managing browser fingerprint profiles with anti-detection capabilities.

### Key Features

✅ **Profile CRUD Operations** - Create, read, update, delete profiles  
✅ **Validation System** - 3 levels (basic, standard, strict) with consistency checks  
✅ **Template Generator** - Browser-specific presets (Chrome, Firefox, Safari)  
✅ **Bulk Operations** - Clone, merge, import, export multiple profiles  
✅ **Search & Filter** - Find profiles by name, browser, description  
✅ **Integration** - Works with configure-dns.py, tegufox_automation.py  
✅ **Statistics** - Track validation scores, browser distribution  

### Components

```
┌─────────────────────────────────────────────────────────────┐
│              Tegufox Profile Manager v1.0                    │
├─────────────────────────────────────────────────────────────┤
│  CLI Tool (tegufox-profile)  │  Python API (profile_manager)│
├─────────────────────────────────────────────────────────────┤
│  Validation  │  Templates  │  Bulk Ops  │  Search           │
├─────────────────────────────────────────────────────────────┤
│                       Profile JSON Files                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.9+ (tested with Python 3.14.3)
- Tegufox Browser Toolkit

### Step 1: Ensure Profile Manager is Installed

```bash
cd /path/to/tegufox-browser
ls profile_manager.py tegufox-profile  # Should exist
```

### Step 2: Make CLI Tool Executable

```bash
chmod +x tegufox-profile
```

### Step 3: Test Installation

```bash
./tegufox-profile --help
```

Expected output:
```
usage: tegufox-profile [-h] [--profiles-dir PROFILES_DIR]
                       {list,show,validate,create,template,clone,merge,delete,export,import,search,stats}
                       ...

Tegufox Profile Manager - Manage browser profiles
```

---

## Quick Start

### Example 1: List All Profiles

```bash
./tegufox-profile list
```

Output:
```
Profiles (3):
  chrome-120                     Chrome 120 on Windows 11 - Complete TLS + HTTP/2
  firefox-115                    Firefox 115 ESR on Windows 11
  safari-17                      Safari 17 on macOS Sonoma
```

### Example 2: Show Profile Details

```bash
./tegufox-profile show chrome-120
```

Output:
```
Profile: chrome-120
============================================================
Name: chrome-120-windows
Description: Chrome 120 on Windows 11 - Complete TLS + HTTP/2
Created: 2026-04-13
Version: 1.0

Navigator:
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...
  Platform: Win32
  Vendor: Google Inc.

Screen:
  Size: 1920x1080

DNS:
  Enabled: True
  Provider: cloudflare

Fingerprints:
  JA3: 579ccef312d18482fc42e2b822ca2430
  JA4: t13d1516h2_8daaf6152771_e5627906d626
```

### Example 3: Validate Profile

```bash
./tegufox-profile validate chrome-120 --level standard
```

Output:
```
Profile: chrome-120
============================================================
Valid: ✓ YES
Score: 0.95 / 1.00
Level: standard

✓ Profile is valid!
```

### Example 4: Create from Template

```bash
./tegufox-profile template chrome-120 my-chrome-profile
```

Output:
```
✓ Created profile from template: chrome-120
  Name: my-chrome-profile
  Path: profiles/my-chrome-profile.json
  Validation score: 0.95
```

---

## CLI Commands

### 1. list - List All Profiles

```bash
./tegufox-profile list [OPTIONS]
```

**Options:**
- `--pattern PATTERN` - Glob pattern filter (e.g., "chrome-*")

**Examples:**
```bash
# List all profiles
./tegufox-profile list

# List only Chrome profiles
./tegufox-profile list --pattern "chrome-*"
```

### 2. show - Show Profile Details

```bash
./tegufox-profile show NAME [OPTIONS]
```

**Options:**
- `--json` - Output as JSON

**Examples:**
```bash
# Show profile details
./tegufox-profile show chrome-120

# Show as JSON
./tegufox-profile show chrome-120 --json
```

### 3. validate - Validate Profile

```bash
./tegufox-profile validate NAME [OPTIONS]
```

**Options:**
- `--level LEVEL` - Validation level: basic, standard, strict (default: standard)

**Examples:**
```bash
# Standard validation
./tegufox-profile validate chrome-120

# Strict validation
./tegufox-profile validate chrome-120 --level strict
```

**Validation Levels:**

| Level | Checks |
|-------|--------|
| **basic** | Required fields, structure |
| **standard** | + TLS/HTTP2 consistency, DoH alignment |
| **strict** | + Cross-layer validation, UA consistency |

### 4. create - Create New Profile

```bash
./tegufox-profile create NAME [OPTIONS]
```

**Options:**
- `--description DESC` - Profile description
- `--force` - Overwrite existing profile
- `--edit` - Open in editor after creation

**Examples:**
```bash
# Create new profile
./tegufox-profile create my-profile --description "My custom profile"

# Create and edit
./tegufox-profile create my-profile --edit
```

### 5. template - Create from Template

```bash
./tegufox-profile template BROWSER NAME [OPTIONS]
```

**Options:**
- `--os OS` - Operating system (windows/macos/linux)
- `--width WIDTH` - Screen width (default: 1920)
- `--height HEIGHT` - Screen height (default: 1080)
- `--doh-provider PROVIDER` - DoH provider (cloudflare/quad9/mullvad)
- `--force` - Overwrite existing profile

**Available Templates:**
- `chrome-120` - Chrome 120 (Windows 11)
- `firefox-115` - Firefox 115 ESR (Windows 11)
- `safari-17` - Safari 17 (macOS Sonoma)

**Examples:**
```bash
# Create Chrome profile
./tegufox-profile template chrome-120 my-chrome

# Create with custom settings
./tegufox-profile template firefox-115 my-firefox \
  --os linux \
  --width 2560 \
  --height 1440 \
  --doh-provider quad9
```

### 6. clone - Clone Profile

```bash
./tegufox-profile clone SOURCE DESTINATION [OPTIONS]
```

**Options:**
- `--force` - Overwrite existing destination

**Examples:**
```bash
# Clone profile
./tegufox-profile clone chrome-120 chrome-120-copy

# Clone and overwrite
./tegufox-profile clone chrome-120 my-chrome --force
```

### 7. merge - Merge Profiles

```bash
./tegufox-profile merge BASE OVERLAY NAME [OPTIONS]
```

**Options:**
- `--force` - Overwrite existing output profile

**Examples:**
```bash
# Merge two profiles (overlay overwrites base)
./tegufox-profile merge chrome-120 my-customizations merged-profile
```

### 8. delete - Delete Profile

```bash
./tegufox-profile delete NAME [OPTIONS]
```

**Options:**
- `-y, --yes` - Skip confirmation

**Examples:**
```bash
# Delete with confirmation
./tegufox-profile delete old-profile

# Delete without confirmation
./tegufox-profile delete old-profile -y
```

### 9. export - Export Profiles

```bash
./tegufox-profile export NAME [NAME...] -o OUTPUT_FILE
```

**Examples:**
```bash
# Export single profile
./tegufox-profile export chrome-120 -o backup.json

# Export multiple profiles
./tegufox-profile export chrome-120 firefox-115 safari-17 -o all-profiles.json
```

### 10. import - Import Profiles

```bash
./tegufox-profile import FILE [OPTIONS]
```

**Options:**
- `--force` - Overwrite existing profiles

**Examples:**
```bash
# Import profiles
./tegufox-profile import backup.json

# Import and overwrite
./tegufox-profile import backup.json --force
```

### 11. search - Search Profiles

```bash
./tegufox-profile search QUERY
```

**Examples:**
```bash
# Search by name
./tegufox-profile search chrome

# Search by description
./tegufox-profile search "Windows 11"
```

### 12. stats - Show Statistics

```bash
./tegufox-profile stats
```

Output:
```
Profile Statistics
============================================================
Total profiles: 15

Browser distribution:
  chrome       3
  firefox      2
  safari       1
  other        9

Validation:
  Valid:   6
  Invalid: 9
  Average score: 0.84
```

---

## Python API

### ProfileManager Class

```python
from profile_manager import ProfileManager, ValidationLevel

# Initialize
manager = ProfileManager("profiles/")

# Create profile
profile = manager.create(name="my-profile", description="Custom profile")

# Create from template
profile = manager.create_from_template(
    template="chrome-120",
    name="my-chrome"
)

# Save profile
manager.save(profile, "my-profile")

# Load profile
profile = manager.load("my-profile")

# Delete profile
manager.delete("my-profile")

# List profiles
profiles = manager.list()
profiles_filtered = manager.list("chrome-*")

# Check existence
exists = manager.exists("my-profile")
```

### Validation

```python
# Validate profile
result = manager.validate(profile, ValidationLevel.STANDARD)

print(f"Valid: {result.valid}")
print(f"Score: {result.score:.2f}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")
```

### Bulk Operations

```python
# Clone profile
cloned = manager.clone("source", "destination")

# Merge profiles
merged = manager.merge("base", "overlay", "output")

# Export multiple profiles
manager.export_bulk(["profile1", "profile2"], "export.json")

# Import profiles
imported = manager.import_bulk("export.json", overwrite=False)
```

### Template Generation

```python
# Generate template
profile = manager.generate_template(
    browser="chrome-120",
    os="windows",
    screen_width=2560,
    screen_height=1440,
    doh_provider="cloudflare"
)

manager.save(profile, "custom-chrome")
```

### Search & Statistics

```python
# Search profiles
results = manager.search("chrome")

# Filter by browser
chrome_profiles = manager.filter_by_browser("chrome")

# Get statistics
stats = manager.get_stats()
print(f"Total: {stats['total_profiles']}")
print(f"Browser counts: {stats['browser_counts']}")
print(f"Validation: {stats['validation']}")
```

---

## Profile Structure

### Complete Profile JSON

```json
{
  "name": "chrome-120-windows",
  "description": "Chrome 120 on Windows 11",
  "created": "2026-04-14",
  "version": "1.0",
  
  "screen": {
    "width": 1920,
    "height": 1080,
    "availWidth": 1920,
    "availHeight": 1040,
    "colorDepth": 24,
    "pixelDepth": 24
  },
  
  "navigator": {
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "platform": "Win32",
    "vendor": "Google Inc.",
    "hardwareConcurrency": 8,
    "deviceMemory": 8,
    "maxTouchPoints": 0,
    "language": "en-US",
    "languages": ["en-US", "en"]
  },
  
  "tls": {
    "version": "1.3",
    "cipher_suites": [...],
    "extensions": {...}
  },
  
  "http2": {
    "settings": {...},
    "window_update": 15663105,
    "pseudo_header_order": ["method", "authority", "scheme", "path"]
  },
  
  "webgl": {
    "vendor": "Google Inc. (Intel)",
    "renderer": "ANGLE...",
    "extensions": [...],
    "parameters": {...}
  },
  
  "canvas": {
    "noise": {
      "seed": "chrome-120-session-001",
      "intensity": 0.02,
      "magnitude": 2
    }
  },
  
  "dns_config": {
    "enabled": true,
    "provider": "cloudflare",
    "doh": {
      "uri": "https://mozilla.cloudflare-dns.com/dns-query",
      "bootstrap_address": "1.1.1.1",
      "mode": 3
    },
    "ipv6": {"enabled": false},
    "webrtc": {"enabled": false},
    "prefetch": {"dns_prefetch": false}
  },
  
  "firefox_preferences": {
    "network.trr.mode": 3,
    "network.trr.uri": "https://mozilla.cloudflare-dns.com/dns-query",
    ...
  },
  
  "fingerprints": {
    "ja3": "579ccef312d18482fc42e2b822ca2430",
    "ja4": "t13d1516h2_8daaf6152771_e5627906d626",
    "akamai_http2": "1:65536;2:0;3:1000;4:6291456..."
  }
}
```

### Required Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ Yes | Profile identifier |
| `navigator` | ✅ Yes | Navigator properties |
| `navigator.userAgent` | ✅ Yes | User-Agent string |
| `screen` | ⚠️ Recommended | Screen dimensions |
| `tls` | ⚠️ Recommended | TLS fingerprint |
| `http2` | ⚠️ Recommended | HTTP/2 settings |
| `dns_config` | ⚠️ Recommended | DNS leak prevention |

---

## Validation System

### Validation Levels

#### 1. Basic Validation

**Checks:**
- Required fields present (`name`, `navigator`)
- Navigator has `userAgent`
- Basic structure validity

**Use Case:** Quick structure check

```bash
./tegufox-profile validate my-profile --level basic
```

#### 2. Standard Validation (Default)

**Checks:**
- All basic checks
- TLS + HTTP/2 consistency
- DNS configuration validity
- DoH provider alignment with browser
- Fingerprint hashes present

**Use Case:** Production profile validation

```bash
./tegufox-profile validate my-profile --level standard
```

#### 3. Strict Validation

**Checks:**
- All standard checks
- HTTP/2 pseudo-header order matches browser
- User-Agent ↔ vendor consistency
- Cross-layer fingerprint consistency

**Use Case:** Maximum anti-detection assurance

```bash
./tegufox-profile validate my-profile --level strict
```

### Validation Scoring

Profiles receive a score from 0.0 to 1.0:

| Score | Quality | Recommendation |
|-------|---------|----------------|
| 0.95 - 1.00 | Excellent | Production-ready |
| 0.85 - 0.94 | Good | Minor fixes recommended |
| 0.70 - 0.84 | Fair | Multiple issues to fix |
| < 0.70 | Poor | Major rework needed |

### DoH Provider Alignment

**Chrome profiles** → Cloudflare DoH  
**Firefox profiles** → Quad9 DoH  
**Safari profiles** → Cloudflare DoH  

Mismatches trigger warnings in standard/strict validation.

---

## Template System

### Available Templates

#### Chrome 120

```bash
./tegufox-profile template chrome-120 my-chrome
```

**Fingerprint:**
- JA3: `579ccef312d18482fc42e2b822ca2430`
- Pseudo-header order: `m,a,s,p`
- DoH: Cloudflare
- Vendor: Google Inc.

#### Firefox 115

```bash
./tegufox-profile template firefox-115 my-firefox
```

**Fingerprint:**
- JA3: `de350869b8c85de67a350c8d186f11e6`
- Pseudo-header order: `m,p,a,s`
- DoH: Quad9
- Vendor: (empty)

#### Safari 17

```bash
./tegufox-profile template safari-17 my-safari
```

**Fingerprint:**
- JA3: `66818e4f5f48d10b27e4892c00347c3f`
- Pseudo-header order: `m,s,a,p`
- DoH: Cloudflare
- Vendor: Apple Computer, Inc.

### Custom Template Options

```bash
./tegufox-profile template chrome-120 custom-chrome \
  --os macos \
  --width 2560 \
  --height 1440 \
  --doh-provider mullvad
```

---

## Best Practices

### 1. Profile Naming Convention

**Good naming:**
```
chrome-120-amazon-seller-1
firefox-115-ebay-buyer
safari-17-etsy-shop-main
```

**Bad naming:**
```
profile1
test
abc123
```

### 2. Validation Before Use

Always validate profiles before using in automation:

```bash
./tegufox-profile validate my-profile --level standard
```

### 3. Regular Backups

```bash
# Backup all profiles
./tegufox-profile export $(./tegufox-profile list | awk '{print $1}') -o backup-$(date +%Y%m%d).json
```

### 4. Version Control

Keep profiles in git:

```bash
git add profiles/*.json
git commit -m "Update profiles"
```

### 5. Template Over Manual Creation

Always prefer templates over manual creation:

```bash
# ✅ Good
./tegufox-profile template chrome-120 my-profile

# ❌ Bad
./tegufox-profile create my-profile  # Missing fingerprints
```

---

## Examples

### Example 1: Create Amazon Seller Profile

```bash
# Create from Chrome template
./tegufox-profile template chrome-120 amazon-seller-us-1 \
  --description "Amazon Seller Central US Account 1" \
  --width 1920 \
  --height 1080

# Validate
./tegufox-profile validate amazon-seller-us-1 --level strict

# Use in automation
python3 -c "
from tegufox_automation import TegufoxSession
with TegufoxSession('amazon-seller-us-1') as session:
    session.goto('https://sellercentral.amazon.com')
"
```

### Example 2: Clone Profile for Multi-Account

```bash
# Clone base profile
./tegufox-profile clone chrome-120 ebay-seller-1
./tegufox-profile clone chrome-120 ebay-seller-2
./tegufox-profile clone chrome-120 ebay-seller-3

# Verify all profiles
for profile in ebay-seller-{1..3}; do
  ./tegufox-profile validate $profile
done
```

### Example 3: Merge Custom Settings

```bash
# Create base profile
./tegufox-profile template chrome-120 base-profile

# Create customizations profile (manual editing)
cat > profiles/my-custom.json <<EOF
{
  "name": "my-custom",
  "screen": {
    "width": 2560,
    "height": 1440
  },
  "dns_config": {
    "provider": "mullvad"
  }
}
EOF

# Merge
./tegufox-profile merge base-profile my-custom final-profile

# Validate merged profile
./tegufox-profile validate final-profile --level strict
```

### Example 4: Bulk Import/Export

```bash
# Export all Chrome profiles
./tegufox-profile export \
  $(./tegufox-profile search chrome | awk '{print $1}') \
  -o chrome-profiles-backup.json

# Import on another machine
./tegufox-profile import chrome-profiles-backup.json
```

### Example 5: Profile Validation Pipeline

```bash
#!/bin/bash
# validate-all.sh - Validate all profiles

for profile in $(./tegufox-profile list | awk '{print $1}'); do
  echo "Validating $profile..."
  ./tegufox-profile validate $profile --level standard || {
    echo "❌ $profile failed validation"
    exit 1
  }
done

echo "✓ All profiles validated successfully!"
```

---

## Troubleshooting

### Problem 1: Profile Not Found

**Error:**
```
Error: Profile not found: my-profile
```

**Solution:**
```bash
# List available profiles
./tegufox-profile list

# Check profile directory
ls profiles/
```

### Problem 2: Validation Fails

**Error:**
```
Valid: ✗ NO
Score: 0.75
Errors:
  ✗ User-Agent claims Chrome but vendor is 'Mozilla'
```

**Solution:**

Fix the inconsistency in the profile JSON:

```json
{
  "navigator": {
    "userAgent": "Mozilla/5.0... Chrome/120.0.0.0 ...",
    "vendor": "Google Inc."  // Changed from "Mozilla"
  }
}
```

### Problem 3: Template Not Found

**Error:**
```
Error: Unknown template: chrome-121
Available: chrome-120, firefox-115, safari-17
```

**Solution:**

Use an available template:

```bash
./tegufox-profile template chrome-120 my-profile
```

---

## Summary

The Tegufox Profile Manager provides **comprehensive profile management** for browser fingerprinting:

✅ **Easy CLI** - 12 commands for all operations  
✅ **Python API** - Full programmatic access  
✅ **Validation** - 3 levels, scoring system  
✅ **Templates** - Chrome, Firefox, Safari presets  
✅ **Bulk Ops** - Clone, merge, import, export  
✅ **Integration** - Works with automation framework  

**Get started in 30 seconds:**

```bash
# Create profile
./tegufox-profile template chrome-120 my-profile

# Validate
./tegufox-profile validate my-profile

# Use in automation
python3 -c "
from tegufox_automation import TegufoxSession
with TegufoxSession('my-profile') as session:
    session.goto('https://example.com')
"
```

For support, see: `docs/DAY_14_COMPLETION_REPORT.md`

---

**Document Version:** 1.0  
**Last Updated:** April 14, 2026  
**Total Lines:** 900+
