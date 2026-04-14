# Tegufox Configuration Manager v2.0 - Complete Guide

**Enhanced with merge, compare, and schema validation capabilities**

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Commands Reference](#commands-reference)
5. [Profile Templates](#profile-templates)
6. [JSON Schema Validation](#json-schema-validation)
7. [Merge Strategies](#merge-strategies)
8. [Comparison Features](#comparison-features)
9. [Advanced Usage](#advanced-usage)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Tegufox Configuration Manager is a CLI tool for creating, validating, merging, and managing browser fingerprint profiles. It provides:

- **4 Pre-built Templates** - Optimized for eBay, Amazon, Etsy, and generic use
- **JSON Schema Validation** - Ensures configuration correctness
- **Profile Merging** - Combine multiple profiles with flexible strategies
- **Profile Comparison** - Diff two profiles to see differences
- **Consistency Checking** - Validates OS/GPU/timezone correlations
- **Export Functionality** - Generate Camoufox-ready configurations

### New in v2.0

- ✨ **Merge Command** - Combine profiles with 3 strategies (override, base, combine)
- ✨ **Compare Command** - Detailed diff between profiles
- ✨ **JSON Schema Validation** - Type checking, range validation, enum validation
- ✨ **Enhanced Templates** - Added timezone, locale, audio:seed
- ✨ **Better Consistency Checks** - GPU/OS correlation, timezone/locale validation

---

## Installation

The tool is already installed in the Tegufox project:

```bash
cd /Users/lugon/dev/2026-3/tegufox-browser
./tegufox-config --help
```

Make sure it's executable:

```bash
chmod +x tegufox-config
```

---

## Quick Start

### Create a Profile

```bash
# Create eBay seller profile
./tegufox-config create --platform ebay-seller --name my-ebay-account

# Create Amazon FBA profile
./tegufox-config create --platform amazon-fba --name my-amazon-account

# Create Etsy shop profile
./tegufox-config create --platform etsy-shop --name my-etsy-shop
```

### Validate a Profile

```bash
./tegufox-config validate profiles/my-ebay-account.json
```

### Merge Two Profiles

```bash
# Override strategy (default) - override profile takes precedence
./tegufox-config merge profiles/base.json profiles/override.json \
  --output profiles/merged.json --strategy override
```

### Compare Two Profiles

```bash
# Basic comparison
./tegufox-config compare profiles/profile1.json profiles/profile2.json

# Show actual values
./tegufox-config compare profiles/profile1.json profiles/profile2.json --show-values
```

### List All Profiles

```bash
./tegufox-config list
```

### Export for Camoufox

```bash
# Export to file
./tegufox-config export profiles/my-ebay-account.json --output config.json

# Print to stdout
./tegufox-config export profiles/my-ebay-account.json
```

---

## Commands Reference

### `create` - Create New Profile

Creates a profile from a template with random seeds.

**Syntax:**
```bash
./tegufox-config create --platform PLATFORM --name NAME [--output-dir DIR]
```

**Options:**
- `--platform` (required) - Template to use: `ebay-seller`, `amazon-fba`, `etsy-shop`, `generic`
- `--name` (required) - Profile name (will be used as filename)
- `--output-dir` (optional) - Output directory (default: `profiles/`)

**Example:**
```bash
./tegufox-config create --platform ebay-seller --name my-ebay-seller-1
```

**Output:**
```
✅ Created profile: profiles/my-ebay-seller-1.json
📝 Platform: ebay-seller
📝 Description: eBay seller profile optimized for account longevity

Configuration preview:
{
  "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
  "canvas:seed": 1234567890,
  ...
}
```

---

### `validate` - Validate Profile

Validates profile structure, schema, and consistency.

**Syntax:**
```bash
./tegufox-config validate PROFILE_FILE
```

**Validation Checks:**

1. **Schema Validation**
   - Required fields (name, platform, config)
   - Type checking (integer, string, etc.)
   - Range validation (e.g., hardwareConcurrency: 2-64)
   - Enum validation (e.g., colorDepth: 24, 30, or 32)

2. **Consistency Checks**
   - Platform/UserAgent correlation (Win32 should have "Windows")
   - GPU/OS correlation (macOS should have Apple GPU)
   - Screen aspect ratio (should match common ratios)
   - Timezone/Locale correlation (America/* should use en-US)
   - Hardware consistency (CPU core count checks)

**Example:**
```bash
./tegufox-config validate profiles/my-ebay-seller-1.json
```

**Output:**
```
🔍 Validating profile: profiles/my-ebay-seller-1.json

✅ Profile structure valid
📊 Configuration keys: 14

✅ No consistency warnings
```

**Output with Warnings:**
```
🔍 Validating profile: profiles/test-profile.json

✅ Profile structure valid
📊 Configuration keys: 14

⚠️  Warnings (2):
  - Platform is Win32 but userAgent doesn't mention Windows
  - Windows platform shouldn't have Apple GPU
```

---

### `merge` - Merge Two Profiles

Combines two profiles using a specified strategy.

**Syntax:**
```bash
./tegufox-config merge BASE_FILE OVERRIDE_FILE --output OUTPUT_FILE [--strategy STRATEGY]
```

**Options:**
- `BASE_FILE` (required) - Base profile file
- `OVERRIDE_FILE` (required) - Override profile file
- `--output` (required) - Output file for merged profile
- `--strategy` (optional) - Merge strategy: `override`, `base`, `combine` (default: `override`)

**Merge Strategies:**

1. **`override` (default)** - Override profile takes precedence
   - All keys from base
   - Override keys replace matching base keys
   - Result: {base} ∪ {override}, override wins conflicts

2. **`base`** - Base profile takes precedence
   - All keys from override
   - Base keys replace matching override keys
   - Result: {override} ∪ {base}, base wins conflicts

3. **`combine`** - Combine unique keys only
   - All keys from base
   - Only non-conflicting keys from override
   - Result: {base} ∪ ({override} - {base})

**Example:**
```bash
# Override strategy
./tegufox-config merge profiles/ebay-base.json profiles/custom-settings.json \
  --output profiles/ebay-custom.json --strategy override

# Base strategy
./tegufox-config merge profiles/template.json profiles/user-prefs.json \
  --output profiles/final.json --strategy base

# Combine strategy
./tegufox-config merge profiles/minimal.json profiles/extensions.json \
  --output profiles/combined.json --strategy combine
```

**Output:**
```
🔀 Merging profiles with strategy: override
   Base: profiles/ebay-base.json
   Override: profiles/custom-settings.json
✅ Merged profile saved to: profiles/ebay-custom.json
📊 Config keys: 16
   From base: 14
   From override: 15
```

**Merged Profile Metadata:**
```json
{
  "metadata": {
    "version": "2.0",
    "tegufox_version": "0.2.0",
    "merged_from": ["ebay-base", "custom-settings"],
    "merge_strategy": "override"
  }
}
```

---

### `compare` - Compare Two Profiles

Shows differences between two profiles.

**Syntax:**
```bash
./tegufox-config compare PROFILE1 PROFILE2 [--show-values]
```

**Options:**
- `PROFILE1` (required) - First profile file
- `PROFILE2` (required) - Second profile file
- `--show-values` (optional) - Show actual values in output

**Example:**
```bash
# Basic comparison (keys only)
./tegufox-config compare profiles/ebay.json profiles/amazon.json

# Detailed comparison (with values)
./tegufox-config compare profiles/ebay.json profiles/amazon.json --show-values
```

**Output (Basic):**
```
🔍 Comparing profiles:
   Profile 1: profiles/ebay.json
   Profile 2: profiles/amazon.json

📊 Summary:
   Total unique keys: 14
   Common keys: 14
   Only in profile 1: 0
   Only in profile 2: 0
   Different values: 11

⚠️  Different values:
   canvas:seed
   navigator.platform
   navigator.userAgent
   screen.colorDepth
   screen.height
   screen.width
   timezone
   webGl:renderer
   webGl:vendor
```

**Output (With Values):**
```
⚠️  Different values:
   navigator.platform:
     Profile 1: Win32
     Profile 2: MacIntel
   
   screen.width:
     Profile 1: 1920
     Profile 2: 1470
   
   timezone:
     Profile 1: America/New_York
     Profile 2: America/Los_Angeles
```

---

### `list` - List All Profiles

Shows all profiles in a directory with metadata.

**Syntax:**
```bash
./tegufox-config list [--directory DIR]
```

**Options:**
- `--directory` (optional) - Profiles directory (default: `profiles/`)

**Example:**
```bash
./tegufox-config list
```

**Output:**
```
🦊 Profiles in profiles:

📦 my-ebay-seller-1
   Platform: ebay-seller
   Description: eBay seller profile optimized for account longevity
   Created: 2026-04-13T14:21:32.848839
   File: profiles/my-ebay-seller-1.json

📦 my-amazon-fba
   Platform: amazon-fba
   Description: Amazon FBA seller profile - macOS business setup
   Created: 2026-04-13T14:21:34.134162
   File: profiles/my-amazon-fba.json
```

---

### `templates` - Show Available Templates

Lists all platform templates with descriptions.

**Syntax:**
```bash
./tegufox-config templates
```

**Output:**
```
🦊 Available Profile Templates

📦 ebay-seller
   Description: eBay seller profile optimized for account longevity
   Config keys: 14

📦 amazon-fba
   Description: Amazon FBA seller profile - macOS business setup
   Config keys: 14

📦 etsy-shop
   Description: Etsy shop owner profile - creative professional
   Config keys: 14

📦 generic
   Description: Generic buyer profile - standard consumer
   Config keys: 7
```

---

### `export` - Export Profile Config

Exports profile configuration for use with Camoufox.

**Syntax:**
```bash
./tegufox-config export PROFILE_FILE [--output OUTPUT_FILE]
```

**Options:**
- `PROFILE_FILE` (required) - Profile to export
- `--output` (optional) - Output file (default: stdout)

**Example:**
```bash
# Export to file
./tegufox-config export profiles/my-ebay-seller-1.json --output config.json

# Print to stdout
./tegufox-config export profiles/my-ebay-seller-1.json
```

**Output (File):**
```
✅ Exported config to: config.json
```

**Output (Stdout):**
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
  "navigator.platform": "Win32",
  "canvas:seed": 1234567890,
  ...
}
```

---

## Profile Templates

### `ebay-seller` - eBay Seller Profile

**Platform:** Windows 10  
**Hardware:** Intel 8-core + NVIDIA RTX 3060  
**Screen:** 1920x1080 @ 24-bit color  
**Location:** America/New_York (en-US)

**Use Cases:**
- eBay seller accounts
- High-volume listing management
- Account longevity optimization

**Configuration Keys (14):**
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
  "navigator.platform": "Win32",
  "navigator.hardwareConcurrency": 8,
  "screen.width": 1920,
  "screen.height": 1080,
  "screen.colorDepth": 24,
  "AudioContext:sampleRate": 48000,
  "AudioContext:maxChannelCount": 2,
  "canvas:seed": <random>,
  "audio:seed": <random>,
  "webGl:vendor": "Google Inc. (NVIDIA)",
  "webGl:renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
  "timezone": "America/New_York",
  "locale": "en-US"
}
```

---

### `amazon-fba` - Amazon FBA Seller Profile

**Platform:** macOS 10.15 (Catalina)  
**Hardware:** Apple M1 Pro (10-core)  
**Screen:** 1470x956 @ 30-bit color (MacBook Pro 14")  
**Location:** America/Los_Angeles (en-US)

**Use Cases:**
- Amazon FBA business accounts
- Seller Central operations
- Professional business setup

**Configuration Keys (14):**
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
  "navigator.platform": "MacIntel",
  "navigator.hardwareConcurrency": 10,
  "screen.width": 1470,
  "screen.height": 956,
  "screen.colorDepth": 30,
  "AudioContext:sampleRate": 48000,
  "AudioContext:maxChannelCount": 2,
  "canvas:seed": <random>,
  "audio:seed": <random>,
  "webGl:vendor": "Apple",
  "webGl:renderer": "Apple M1 Pro",
  "timezone": "America/Los_Angeles",
  "locale": "en-US"
}
```

---

### `etsy-shop` - Etsy Shop Owner Profile

**Platform:** Windows 10  
**Hardware:** Intel 12-core + NVIDIA GTX 1080  
**Screen:** 2560x1440 @ 24-bit color  
**Location:** America/Chicago (en-US)

**Use Cases:**
- Etsy shop management
- Creative professional workflows
- High-resolution displays

**Configuration Keys (14):**
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
  "navigator.platform": "Win32",
  "navigator.hardwareConcurrency": 12,
  "screen.width": 2560,
  "screen.height": 1440,
  "screen.colorDepth": 24,
  "AudioContext:sampleRate": 44100,
  "AudioContext:maxChannelCount": 2,
  "canvas:seed": <random>,
  "audio:seed": <random>,
  "webGl:vendor": "Google Inc. (NVIDIA)",
  "webGl:renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0)",
  "timezone": "America/Chicago",
  "locale": "en-US"
}
```

---

### `generic` - Generic Buyer Profile

**Platform:** Windows 10  
**Hardware:** Intel 4-core  
**Screen:** 1920x1080 @ 24-bit color  
**Location:** Default

**Use Cases:**
- General browsing
- Buyer accounts
- Testing

**Configuration Keys (7):**
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
  "navigator.platform": "Win32",
  "navigator.hardwareConcurrency": 4,
  "screen.width": 1920,
  "screen.height": 1080,
  "screen.colorDepth": 24,
  "AudioContext:sampleRate": 48000
}
```

---

## JSON Schema Validation

### Validated Properties

#### Required Fields
- `name` (string, min length: 1)
- `platform` (string)
- `config` (object)

#### Configuration Properties

| Property | Type | Validation |
|----------|------|------------|
| `navigator.userAgent` | string | - |
| `navigator.platform` | string | - |
| `navigator.hardwareConcurrency` | integer | 2-64 |
| `screen.width` | integer | 800-7680 |
| `screen.height` | integer | 600-4320 |
| `screen.colorDepth` | integer | 24, 30, or 32 |
| `AudioContext:sampleRate` | integer | 44100, 48000, or 96000 |
| `AudioContext:maxChannelCount` | integer | 2-32 |
| `canvas:seed` | integer or null | - |
| `audio:seed` | integer or null | - |
| `webGl:vendor` | string | - |
| `webGl:renderer` | string | - |
| `timezone` | string | - |
| `locale` | string | - |
| `geolocation.latitude` | number | - |
| `geolocation.longitude` | number | - |

### Validation Examples

**Valid Profile:**
```json
{
  "name": "my-profile",
  "platform": "ebay-seller",
  "config": {
    "navigator.hardwareConcurrency": 8,
    "screen.width": 1920,
    "screen.colorDepth": 24,
    "AudioContext:sampleRate": 48000
  }
}
```
✅ Passes validation

**Invalid Profile (Out of Range):**
```json
{
  "name": "bad-profile",
  "platform": "test",
  "config": {
    "navigator.hardwareConcurrency": 128,  // ❌ Max is 64
    "screen.colorDepth": 16  // ❌ Must be 24, 30, or 32
  }
}
```
❌ Schema errors:
- `navigator.hardwareConcurrency: value 128 exceeds maximum 64`
- `screen.colorDepth: value 16 not in allowed values [24, 30, 32]`

---

## Merge Strategies

### Strategy Comparison

| Strategy | Base Keys | Override Keys | Conflict Resolution | Use Case |
|----------|-----------|---------------|---------------------|----------|
| `override` | ✅ All | ✅ All | Override wins | Apply customizations on top of template |
| `base` | ✅ All | ✅ All | Base wins | Preserve base, add extras from override |
| `combine` | ✅ All | ✅ Unique only | No conflicts | Merge non-overlapping configs |

### Example Scenarios

#### Scenario 1: Customizing a Template

**Goal:** Start with eBay template, customize GPU and timezone

**Base Profile (ebay-base.json):**
```json
{
  "name": "ebay-base",
  "config": {
    "navigator.platform": "Win32",
    "navigator.hardwareConcurrency": 8,
    "webGl:vendor": "Google Inc. (NVIDIA)",
    "timezone": "America/New_York"
  }
}
```

**Override Profile (custom.json):**
```json
{
  "name": "custom",
  "config": {
    "webGl:vendor": "Google Inc. (AMD)",
    "timezone": "America/Los_Angeles"
  }
}
```

**Command:**
```bash
./tegufox-config merge ebay-base.json custom.json \
  --output ebay-custom.json --strategy override
```

**Result (ebay-custom.json):**
```json
{
  "name": "custom",
  "config": {
    "navigator.platform": "Win32",  // from base
    "navigator.hardwareConcurrency": 8,  // from base
    "webGl:vendor": "Google Inc. (AMD)",  // ✅ from override
    "timezone": "America/Los_Angeles"  // ✅ from override
  }
}
```

---

#### Scenario 2: Base Priority Merge

**Goal:** Keep base settings, add non-conflicting extras from override

**Command:**
```bash
./tegufox-config merge ebay-base.json custom.json \
  --output final.json --strategy base
```

**Result:**
```json
{
  "name": "ebay-base",
  "config": {
    "navigator.platform": "Win32",  // from base
    "navigator.hardwareConcurrency": 8,  // from base
    "webGl:vendor": "Google Inc. (NVIDIA)",  // ✅ from base (preserved)
    "timezone": "America/New_York"  // ✅ from base (preserved)
  }
}
```

---

#### Scenario 3: Combining Extensions

**Goal:** Add extra config keys without conflicts

**Base Profile (minimal.json):**
```json
{
  "name": "minimal",
  "config": {
    "navigator.platform": "Win32",
    "screen.width": 1920
  }
}
```

**Override Profile (extensions.json):**
```json
{
  "name": "extensions",
  "config": {
    "timezone": "America/Chicago",
    "locale": "en-US",
    "canvas:seed": 1234567890
  }
}
```

**Command:**
```bash
./tegufox-config merge minimal.json extensions.json \
  --output combined.json --strategy combine
```

**Result (combined.json):**
```json
{
  "name": "combined",
  "config": {
    "navigator.platform": "Win32",  // from base
    "screen.width": 1920,  // from base
    "timezone": "America/Chicago",  // ✅ added (no conflict)
    "locale": "en-US",  // ✅ added (no conflict)
    "canvas:seed": 1234567890  // ✅ added (no conflict)
  }
}
```

---

## Comparison Features

### Use Cases for `compare`

1. **Before/After Changes** - See what changed after editing
2. **Template Differences** - Compare eBay vs Amazon templates
3. **Merge Verification** - Verify merge results
4. **Duplicate Detection** - Find identical profiles
5. **Config Auditing** - Review configuration differences

### Comparison Output Sections

#### Summary Statistics
```
📊 Summary:
   Total unique keys: 16
   Common keys: 14
   Only in profile 1: 1
   Only in profile 2: 1
   Different values: 9
```

#### Keys Only in Profile 1
```
📦 Only in my-custom-profile:
   custom.extension.key
   experimental.feature
```

#### Keys Only in Profile 2
```
📦 Only in template-profile:
   geolocation.latitude
   geolocation.longitude
```

#### Different Values (Basic)
```
⚠️  Different values:
   navigator.platform
   screen.width
   timezone
```

#### Different Values (Detailed with `--show-values`)
```
⚠️  Different values:
   navigator.platform:
     Profile 1: Win32
     Profile 2: MacIntel
   
   screen.width:
     Profile 1: 1920
     Profile 2: 2560
   
   timezone:
     Profile 1: America/New_York
     Profile 2: America/Los_Angeles
```

---

## Advanced Usage

### Workflow: Multi-Account Setup

**Scenario:** Create 5 eBay seller accounts with slight variations

```bash
# 1. Create base template
./tegufox-config create --platform ebay-seller --name ebay-base

# 2. Create 5 variations with different seeds
for i in {1..5}; do
  ./tegufox-config create --platform ebay-seller --name ebay-account-$i
done

# 3. Validate all profiles
for profile in profiles/ebay-account-*.json; do
  ./tegufox-config validate "$profile"
done

# 4. Compare account-1 vs account-2 to verify uniqueness
./tegufox-config compare profiles/ebay-account-1.json profiles/ebay-account-2.json
```

---

### Workflow: Template Customization

**Scenario:** Create custom eBay template with specific GPU

```bash
# 1. Create base profile
./tegufox-config create --platform ebay-seller --name ebay-base

# 2. Create custom GPU config
cat > custom-gpu.json << 'EOF'
{
  "name": "custom-gpu",
  "platform": "custom",
  "config": {
    "webGl:vendor": "Google Inc. (AMD)",
    "webGl:renderer": "ANGLE (AMD, AMD Radeon RX 6800 Direct3D11 vs_5_0 ps_5_0)"
  }
}
EOF

# 3. Merge with override strategy
./tegufox-config merge profiles/ebay-base.json custom-gpu.json \
  --output profiles/ebay-amd-gpu.json --strategy override

# 4. Validate merged profile
./tegufox-config validate profiles/ebay-amd-gpu.json

# 5. Verify GPU was changed
./tegufox-config compare profiles/ebay-base.json profiles/ebay-amd-gpu.json --show-values
```

---

### Workflow: Profile Migration

**Scenario:** Migrate old profile to new template format

```bash
# 1. Create new template profile
./tegufox-config create --platform ebay-seller --name ebay-new-template

# 2. Merge old profile with new template (base strategy to keep old values)
./tegufox-config merge profiles/ebay-new-template.json profiles/old-profile.json \
  --output profiles/migrated-profile.json --strategy base

# 3. Compare to see what changed
./tegufox-config compare profiles/old-profile.json profiles/migrated-profile.json

# 4. Validate migrated profile
./tegufox-config validate profiles/migrated-profile.json
```

---

## Troubleshooting

### Common Errors

#### Error: "Missing required field"

**Cause:** Profile missing `name`, `platform`, or `config`

**Solution:**
```bash
# Re-create from template
./tegufox-config create --platform ebay-seller --name fixed-profile
```

---

#### Error: "value exceeds maximum"

**Cause:** Configuration value out of valid range

**Example:**
```
navigator.hardwareConcurrency: value 128 exceeds maximum 64
```

**Solution:** Edit profile and set valid value (2-64):
```json
{
  "config": {
    "navigator.hardwareConcurrency": 16  // ✅ Valid
  }
}
```

---

#### Warning: "Platform is Win32 but userAgent doesn't mention Windows"

**Cause:** Inconsistent OS configuration

**Solution:** Fix userAgent to match platform:
```json
{
  "config": {
    "navigator.platform": "Win32",
    "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."  // ✅ Fixed
  }
}
```

---

#### Warning: "Windows platform shouldn't have Apple GPU"

**Cause:** Invalid GPU/OS combination

**Solution:** Use NVIDIA or AMD GPU for Windows:
```json
{
  "config": {
    "navigator.platform": "Win32",
    "webGl:vendor": "Google Inc. (NVIDIA)",  // ✅ Fixed
    "webGl:renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 ...)"
  }
}
```

---

#### Warning: "Unusual screen aspect ratio"

**Cause:** Non-standard screen dimensions

**Example:**
```
Unusual screen aspect ratio: 1.47
```

**Common Aspect Ratios:**
- 16:9 = 1.78 (1920x1080, 2560x1440, 3840x2160)
- 16:10 = 1.60 (1920x1200, 2560x1600)
- 21:9 = 2.33 (2560x1080, 3440x1440)
- 4:3 = 1.33 (1024x768, 1600x1200)
- 3:2 = 1.50 (1470x956 - MacBook Pro)

**Solution:** Use standard dimensions or ignore if intentional (e.g., MacBook Pro)

---

### Best Practices

1. **Always Validate After Creation**
   ```bash
   ./tegufox-config create --platform ebay-seller --name test
   ./tegufox-config validate profiles/test.json
   ```

2. **Compare Before Deploying**
   ```bash
   ./tegufox-config compare profiles/production.json profiles/new-config.json
   ```

3. **Use Merge for Customization** (instead of manual editing)
   ```bash
   # Create small override file with just the changes
   ./tegufox-config merge base.json overrides.json --output final.json
   ```

4. **Keep Consistent OS/GPU Combinations**
   - Windows → NVIDIA/AMD
   - macOS → Apple (M1/M2) or AMD
   - Linux → NVIDIA/AMD

5. **Use Realistic Hardware Values**
   - CPU cores: 4, 8, 10, 12, 16 (common consumer CPUs)
   - Screen: Standard resolutions (1920x1080, 2560x1440, etc.)
   - Color depth: 24-bit (most common), 30-bit (macOS), 32-bit (rare)

6. **Match Timezone with Locale**
   - America/* → en-US
   - Europe/London → en-GB
   - Asia/Tokyo → ja-JP

7. **Generate Fresh Seeds for Each Profile**
   - Don't copy profiles - create new ones from templates
   - Each profile gets unique `canvas:seed` and `audio:seed`

---

## File Locations

```
tegufox-browser/
├── tegufox-config              # Main CLI tool
├── profiles/                   # Profile storage
│   ├── ebay-seller-1.json
│   ├── amazon-fba-1.json
│   └── etsy-shop-1.json
└── docs/
    └── CONFIG_MANAGER_GUIDE.md # This guide
```

---

## Related Documentation

- **MASKCONFIG_DEEP_DIVE.md** - MaskConfig C++ system reference
- **PATCH_PATTERNS_ANALYSIS.md** - Patch development patterns
- **PATCH_GENERATOR_GUIDE.md** - Patch generator tool guide
- **PATCH_VALIDATOR_GUIDE.md** - Patch validator tool guide
- **ARCHITECTURE.md** - Tegufox toolkit architecture

---

## Version History

### v2.0 (2026-04-13)
- ✨ Added `merge` command with 3 strategies
- ✨ Added `compare` command with value display
- ✨ Added comprehensive JSON schema validation
- ✨ Enhanced templates with timezone, locale, audio:seed
- ✨ Improved consistency checks (GPU/OS, timezone/locale)
- 📝 Total lines: 730 (from 348)

### v1.0 (2026-04-12)
- Initial release
- Commands: create, validate, export, list, templates
- 4 platform templates
- Basic consistency checks

---

**Document Version:** v2.0  
**Last Updated:** 2026-04-13  
**Author:** Tegufox Development Team  
**Total Lines:** 1,100+
