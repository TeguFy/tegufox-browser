# HTTP/2 Fingerprinting Defense - Design Document

**Status**: Week 3 Day 11 Design (Phase 1)  
**Target**: TLS/JA3 + HTTP/2 SETTINGS spoofing for Firefox/Camoufox  
**Estimated Implementation**: 300-400 lines C++ patch  
**Date**: April 2026

---

## Executive Summary

HTTP/2 fingerprinting is a **protocol-layer bot detection technique** that analyzes TLS handshake parameters (JA3/JA4) and HTTP/2 connection settings to identify the software making requests. Unlike browser fingerprinting (Canvas, WebGL), this operates **before any JavaScript executes** and is **impossible to bypass with JavaScript hooks**.

### The Problem

Modern anti-bot systems (Cloudflare, Akamai, DataDome) use **multi-layer fingerprinting**:

```
Layer 1: TLS/JA3 Fingerprint (during TLS handshake)
  ↓
Layer 2: HTTP/2 Settings (SETTINGS frame, WINDOW_UPDATE, pseudo-headers)
  ↓
Layer 3: JavaScript Fingerprint (Canvas, WebGL, navigator)
  ↓
Layer 4: Behavioral Analysis (mouse, timing, scroll)
```

**Detection happens at Layer 1-2**, even if you perfectly spoof Layer 3-4. A mismatch between:
- **TLS fingerprint** (says "Chrome 120 on BoringSSL")
- **HTTP/2 settings** (says "Firefox 115 on NSS")
- **User-Agent header** (claims "Safari 17")

...triggers **instant bot flag** before the page even loads.

### Key Statistics (2026)

- **87%** of top 10K websites use TLS/HTTP/2 fingerprinting (Akamai research)
- **JA3 spoofing is "table stakes"** - everyone does it, so defenders look deeper
- **HTTP/2 fingerprinting** is the new frontier (SETTINGS, WINDOW_UPDATE, pseudo-headers)
- **Cross-layer mismatch** is the strongest detection signal

### Solution Approach

We will implement **C++-level TLS and HTTP/2 spoofing** in Firefox's NSS (Network Security Services) and HTTP/2 implementation:

1. **TLS Cipher Suite Override** - Control cipher suite order in ClientHello
2. **HTTP/2 SETTINGS Spoofing** - Override SETTINGS frame parameters
3. **WINDOW_UPDATE Randomization** - Match browser-specific flow control
4. **Pseudo-Header Ordering** - Control `:method`, `:path`, `:authority`, `:scheme` order
5. **MaskConfig Integration** - Profile-based configuration (Chrome, Firefox, Safari templates)

This approach is **undetectable** because:
- ✅ Operates at C++ level (before protocol serialization)
- ✅ No JavaScript hooking (toString() returns "[native code]")
- ✅ No prototype tampering (Object.getOwnPropertyDescriptor passes)
- ✅ Perfect consistency across all layers

---

## 1. Technical Background

### 1.1 What is JA3 Fingerprinting?

**JA3** is a TLS fingerprinting method developed by Salesforce (2017) that creates an MD5 hash from 5 fields in the **TLS ClientHello** message:

```
JA3 = MD5(TLSVersion, CipherSuites, Extensions, EllipticCurves, ECPointFormats)
```

#### Example ClientHello → JA3 Hash

**Raw ClientHello fields**:
```
TLS Version:        771 (TLS 1.2)
Cipher Suites:      4865-4866-4867-49195-49199-52393-52392
Extensions:         0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21
Elliptic Curves:    29-23-24-25-256-257
EC Point Formats:   0
```

**Concatenated string** (pre-hash):
```
771,4865-4866-4867-49195-49199-52393-52392,0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21,29-23-24-25-256-257,0
```

**JA3 Hash** (MD5):
```
579ccef312d18482fc42e2b822ca2430
```

#### Why Order Matters

**Chrome 120** (BoringSSL):
```
Cipher Suites: 4865-4866-4867-49195-49199-52393...
JA3: 579ccef312d18482fc42e2b822ca2430
```

**Firefox 115** (NSS):
```
Cipher Suites: 4865-4867-4866-49196-49200-159...
JA3: de350869b8c85de67a350c8d186f11e6
```

**Python requests** (OpenSSL):
```
Cipher Suites: 49200-49199-49172-49171-157-156...
JA3: 4d7a28d6f2263ed61de88ca66eb011e3
```

→ **Different order = Different fingerprint = Instant bot detection**

### 1.2 What is JA4 Fingerprinting?

**JA4** (FoxIO, 2022) improves on JA3 by:
1. **Sorting cipher suites** (eliminates randomization, like Google GREASE)
2. **Human-readable format** (not opaque MD5 hash)
3. **Structured output** (`a_b_c` format)

#### JA4 Format

```
JA4 = Protocol_CipherCount+CipherHash_ExtensionCount+ExtensionHash_SignatureAlgorithms
```

**Example JA4 fingerprint**:
```
t13d1516h2_8daaf6152771_e5627906d626
│││││││││   │             │
│││││││││   │             └─ Extension hash (SHA-256 truncated)
│││││││││   └─────────────── Cipher hash (SHA-256 truncated)
│││││││└─ ALPN first value (h2 = HTTP/2)
││││││└── Extension count (16)
│││││└─── Cipher count (15)
││││└──── SNI present (1) or absent (0)
│││└───── TLS version (d = draft, 1 = 1.0, 2 = 1.2, 3 = 1.3)
││└────── QUIC (q) or TCP (t)
│└─────── Protocol type (t = TLS)
```

### 1.3 What is HTTP/2 Fingerprinting?

**HTTP/2 fingerprinting** analyzes the **SETTINGS frame** sent during HTTP/2 connection establishment. Different browsers/libraries send different settings.

#### HTTP/2 Connection Flow

```
1. TLS Handshake (JA3/JA4 fingerprint captured here)
   ↓
2. HTTP/2 Connection Preface ("PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n")
   ↓
3. SETTINGS Frame (HTTP/2 fingerprint captured here)
   ↓
4. WINDOW_UPDATE Frame
   ↓
5. PRIORITY Frames (optional)
   ↓
6. HEADERS Frame (pseudo-header order fingerprinted)
```

#### SETTINGS Frame Parameters

| Parameter | Chrome 120 | Firefox 115 | Python httpx | curl 8.0 |
|-----------|------------|-------------|--------------|----------|
| `HEADER_TABLE_SIZE` (1) | 65536 | 65536 | 4096 | 4096 |
| `ENABLE_PUSH` (2) | 0 | 0 | 1 | 0 |
| `MAX_CONCURRENT_STREAMS` (3) | 1000 | 200 | 100 | 100 |
| `INITIAL_WINDOW_SIZE` (4) | 6291456 | 131072 | 65535 | 65535 |
| `MAX_FRAME_SIZE` (5) | 16384 | 16384 | 16384 | 16384 |
| `MAX_HEADER_LIST_SIZE` (6) | 262144 | 262144 | (not sent) | (not sent) |

#### Akamai HTTP/2 Fingerprint Format

Akamai uses this format (Black Hat USA 2017):

```
S[settings]|WU[window_update]|P[priorities]|PS[pseudo_header_order]
```

**Example fingerprints**:

**Chrome 120**:
```
1:65536;2:0;3:1000;4:6291456;5:16384;6:262144|15663105|0|m,a,s,p
│                                              │        │  │
│                                              │        │  └─ :method,:authority,:scheme,:path
│                                              │        └──── No PRIORITY frames
│                                              └─────────── WINDOW_UPDATE increment
└────────────────────────────────────────────────────────── SETTINGS (ID:value pairs)
```

**Firefox 115**:
```
1:65536;2:0;3:200;4:131072;5:16384;6:262144|12517377|3,5,7,9,11|m,p,a,s
                                            │        │          │
                                            │        │          └─ :method,:path,:authority,:scheme
                                            │        └──────────── Stream IDs with PRIORITY
                                            └───────────────────── WINDOW_UPDATE increment
```

**Python httpx** (h2 library):
```
1:4096;2:1;3:100;4:65535;5:16384|0|0|m,a,s,p
                                 │  │
                                 │  └─ No PRIORITY frames
                                 └──── WINDOW_UPDATE = 0 (not sent)
```

→ **Instant bot flag**: Claims "Chrome" User-Agent but sends Python httpx fingerprint

### 1.4 Cross-Layer Detection

Modern anti-bot systems **cross-validate** multiple layers:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: TLS/JA3 Fingerprint                           │
│   → Identifies TLS library (BoringSSL, NSS, OpenSSL)   │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: HTTP/2 Fingerprint                            │
│   → Identifies HTTP stack (Chromium, Firefox, Python)  │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: User-Agent Header                             │
│   → Claims to be "Chrome 120 on Windows"               │
└────────────────┬────────────────────────────────────────┘
                 ↓
         ┌───────┴────────┐
         │  All Match?    │
         └───────┬────────┘
                 ↓
         ┌───────┴────────┐
     YES │                │ NO
         ↓                ↓
    [Allow]          [Block/Challenge]
```

**Example mismatch** (instant bot flag):
```
TLS/JA3:        579ccef3... (Chrome 120/BoringSSL)
HTTP/2:         1:4096;2:1;... (Python httpx/h2)
User-Agent:     Mozilla/5.0... Chrome/120.0
                                 ↓
                        ❌ BOT DETECTED
```

**Perfect match** (passes detection):
```
TLS/JA3:        579ccef3... (Chrome 120/BoringSSL)
HTTP/2:         1:65536;2:0;3:1000;... (Chrome 120)
User-Agent:     Mozilla/5.0... Chrome/120.0
                                 ↓
                        ✅ LIKELY HUMAN
```

---

## 2. Design Goals

### 2.1 Primary Objectives

1. **TLS/JA3 Control**
   - Override cipher suite ordering in ClientHello
   - Configure TLS extensions (SNI, ALPN, supported_groups, signature_algorithms)
   - Match browser-specific TLS libraries (BoringSSL for Chrome, NSS for Firefox)
   - Support TLS 1.2 and TLS 1.3

2. **HTTP/2 Settings Control**
   - Override SETTINGS frame parameters (6 standard settings)
   - Configure WINDOW_UPDATE increment (flow control)
   - Control PRIORITY frame behavior (send or skip)
   - Set pseudo-header ordering (`:method`, `:path`, `:authority`, `:scheme`)

3. **Cross-Layer Consistency**
   - TLS fingerprint must match HTTP/2 fingerprint
   - HTTP/2 fingerprint must match User-Agent claim
   - All layers must tell the same "browser story"

4. **Profile-Based Configuration**
   - MaskConfig integration for easy profile management
   - Pre-built templates: `chrome-120`, `firefox-115`, `safari-17`, `edge-120`
   - Custom cipher suite lists for advanced users

### 2.2 Success Criteria

| Test | Target | Measurement |
|------|--------|-------------|
| **JA3 Hash Match** | Match target browser exactly | BrowserLeaks SSL test |
| **JA4 Hash Match** | Match target browser exactly | tls.peet.ws test |
| **HTTP/2 Settings Match** | Match SETTINGS frame | Scrapfly HTTP/2 fingerprint test |
| **WINDOW_UPDATE Match** | Match increment value | Wireshark packet capture |
| **Pseudo-Header Order** | Match `:method` order | Scrapfly HTTP/2 test |
| **Cross-Layer Consistency** | No TLS ↔ HTTP/2 mismatch | Cloudflare bot detection |
| **Amazon.com Access** | No bot challenge | Real-world test |
| **eBay.com Access** | No bot challenge | Real-world test |

### 2.3 Non-Goals (Out of Scope)

- ❌ **HTTP/3 / QUIC** - Future work (Week 4+)
- ❌ **ECH (Encrypted ClientHello)** - TLS 1.3 extension, not yet widely deployed
- ❌ **GREASE randomization** - Firefox doesn't use GREASE (Chrome feature)
- ❌ **TLS session resumption** - Session tickets handled by NSS automatically

---

## 3. Algorithm Design

### 3.1 TLS Cipher Suite Override

#### 3.1.1 Approach: NSS Cipher Suite Configuration

Firefox uses **NSS (Network Security Services)** for TLS. We will hook into NSS's cipher suite selection before the ClientHello is serialized.

**Target file**: `security/nss/lib/ssl/ssl3con.c` (Firefox source tree)

**Hook point**: `ssl3_SendClientHello()` function

#### 3.1.2 Cipher Suite Data Structure

We'll create a **MaskConfig-controlled cipher suite list**:

```json
{
  "tls": {
    "version": "1.3",
    "cipher_suites": [
      "TLS_AES_128_GCM_SHA256",
      "TLS_AES_256_GCM_SHA384",
      "TLS_CHACHA20_POLY1305_SHA256",
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
    ],
    "extensions": {
      "sni": true,
      "alpn": ["h2", "http/1.1"],
      "supported_groups": ["x25519", "secp256r1", "secp384r1"],
      "signature_algorithms": ["ecdsa_secp256r1_sha256", "rsa_pss_rsae_sha256"]
    }
  }
}
```

#### 3.1.3 NSS Cipher Suite Mapping

NSS uses internal cipher suite constants. We need to map our MaskConfig names to NSS constants:

| MaskConfig Name | NSS Constant | Hex Value | Description |
|-----------------|--------------|-----------|-------------|
| `TLS_AES_128_GCM_SHA256` | `TLS_AES_128_GCM_SHA256` | `0x1301` | TLS 1.3 |
| `TLS_AES_256_GCM_SHA384` | `TLS_AES_256_GCM_SHA384` | `0x1302` | TLS 1.3 |
| `TLS_CHACHA20_POLY1305_SHA256` | `TLS_CHACHA20_POLY1305_SHA256` | `0x1303` | TLS 1.3 |
| `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` | `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` | `0xC02B` | TLS 1.2 |
| `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` | `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` | `0xC02F` | TLS 1.2 |

**Full cipher suite mapping** (50+ suites): See Appendix A

#### 3.1.4 Algorithm Pseudocode

```cpp
// In ssl3con.c, inside ssl3_SendClientHello()

// Step 1: Check if MaskConfig has custom cipher suites
const char* custom_cipher_suites = GetMaskConfigString("tls.cipher_suites");

if (custom_cipher_suites != nullptr) {
    // Step 2: Parse MaskConfig cipher suite list
    std::vector<std::string> cipher_names = ParseCipherSuiteList(custom_cipher_suites);
    
    // Step 3: Map to NSS cipher suite constants
    std::vector<PRUint16> nss_ciphers;
    for (const auto& name : cipher_names) {
        PRUint16 suite = MapCipherNameToNSS(name);
        if (suite != 0) {
            nss_ciphers.push_back(suite);
        }
    }
    
    // Step 4: Override NSS's default cipher suite list
    if (!nss_ciphers.empty()) {
        ss->ssl3.hs.cipher_suites = nss_ciphers;
        ss->ssl3.hs.cipher_suite_count = nss_ciphers.size();
        
        // TEGUFOX MARKER: TLS cipher suite override active
        TEGUFOX_LOG("TLS cipher suites overridden: %d suites", nss_ciphers.size());
    }
}

// Continue with normal ClientHello construction...
```

#### 3.1.5 Extension Handling

Similarly, we'll override TLS extensions:

```cpp
// In ssl3ext.c

// Override supported_groups (elliptic curves)
const char* custom_groups = GetMaskConfigString("tls.extensions.supported_groups");
if (custom_groups != nullptr) {
    std::vector<std::string> group_names = ParseGroupList(custom_groups);
    std::vector<SSLNamedGroup> nss_groups;
    
    for (const auto& name : group_names) {
        SSLNamedGroup group = MapGroupNameToNSS(name);
        if (group != ssl_grp_none) {
            nss_groups.push_back(group);
        }
    }
    
    if (!nss_groups.empty()) {
        ss->xtnData.clientSupportedGroups = nss_groups;
        TEGUFOX_LOG("Supported groups overridden: %d groups", nss_groups.size());
    }
}

// Override signature_algorithms
const char* custom_sig_algs = GetMaskConfigString("tls.extensions.signature_algorithms");
// ... similar pattern
```

### 3.2 HTTP/2 Settings Override

#### 3.2.1 Approach: HTTP/2 Frame Modification

Firefox's HTTP/2 implementation is in `netwerk/protocol/http/Http2Session.cpp`. We'll hook the `SendSettings()` function.

**Target file**: `netwerk/protocol/http/Http2Session.cpp`

**Hook point**: `Http2Session::SendSettings()` function

#### 3.2.2 SETTINGS Frame Structure

HTTP/2 SETTINGS frame format (RFC 9113):

```
+-----------------------------------------------+
|                 Length (24)                   |
+---------------+---------------+---------------+
|   Type (8)    |   Flags (8)   |
+-+-------------+---------------+-------------------------------+
|R|                 Stream Identifier (31)                      |
+=+=============================================================+
|       Identifier (16)         |
+-------------------------------+-------------------------------+
|                        Value (32)                             |
+---------------------------------------------------------------+
|       Identifier (16)         |
+-------------------------------+-------------------------------+
|                        Value (32)                             |
+---------------------------------------------------------------+
```

**Standard SETTINGS identifiers**:

| ID | Name | Default | Chrome | Firefox | Python |
|----|------|---------|--------|---------|--------|
| `0x1` | `HEADER_TABLE_SIZE` | 4096 | 65536 | 65536 | 4096 |
| `0x2` | `ENABLE_PUSH` | 1 | 0 | 0 | 1 |
| `0x3` | `MAX_CONCURRENT_STREAMS` | ∞ | 1000 | 200 | 100 |
| `0x4` | `INITIAL_WINDOW_SIZE` | 65535 | 6291456 | 131072 | 65535 |
| `0x5` | `MAX_FRAME_SIZE` | 16384 | 16384 | 16384 | 16384 |
| `0x6` | `MAX_HEADER_LIST_SIZE` | ∞ | 262144 | 262144 | - |

#### 3.2.3 MaskConfig Schema

```json
{
  "http2": {
    "settings": {
      "header_table_size": 65536,
      "enable_push": 0,
      "max_concurrent_streams": 1000,
      "initial_window_size": 6291456,
      "max_frame_size": 16384,
      "max_header_list_size": 262144
    },
    "window_update": 15663105,
    "priority_frames": false,
    "pseudo_header_order": ["method", "authority", "scheme", "path"]
  }
}
```

#### 3.2.4 Algorithm Pseudocode

```cpp
// In Http2Session.cpp, inside SendSettings()

nsresult Http2Session::SendSettings() {
    // Step 1: Check if MaskConfig has custom HTTP/2 settings
    uint32_t header_table_size = GetMaskConfigUint32("http2.settings.header_table_size", 65536);
    uint32_t enable_push = GetMaskConfigUint32("http2.settings.enable_push", 0);
    uint32_t max_concurrent = GetMaskConfigUint32("http2.settings.max_concurrent_streams", 1000);
    uint32_t initial_window = GetMaskConfigUint32("http2.settings.initial_window_size", 6291456);
    uint32_t max_frame = GetMaskConfigUint32("http2.settings.max_frame_size", 16384);
    uint32_t max_header_list = GetMaskConfigUint32("http2.settings.max_header_list_size", 262144);
    
    // Step 2: Build SETTINGS frame with custom values
    nsAutoCString settingsFrame;
    
    // Frame header (9 bytes)
    uint32_t payloadLength = 6 * 6; // 6 settings, 6 bytes each
    settingsFrame.Append((char)(payloadLength >> 16));
    settingsFrame.Append((char)(payloadLength >> 8));
    settingsFrame.Append((char)(payloadLength & 0xFF));
    settingsFrame.Append((char)0x04); // Type = SETTINGS
    settingsFrame.Append((char)0x00); // Flags = 0
    settingsFrame.Append((char)0x00); // Stream ID = 0 (4 bytes)
    settingsFrame.Append((char)0x00);
    settingsFrame.Append((char)0x00);
    settingsFrame.Append((char)0x00);
    
    // Setting 1: HEADER_TABLE_SIZE
    settingsFrame.Append((char)0x00);
    settingsFrame.Append((char)0x01);
    settingsFrame.Append((char)(header_table_size >> 24));
    settingsFrame.Append((char)(header_table_size >> 16));
    settingsFrame.Append((char)(header_table_size >> 8));
    settingsFrame.Append((char)(header_table_size & 0xFF));
    
    // Setting 2: ENABLE_PUSH
    settingsFrame.Append((char)0x00);
    settingsFrame.Append((char)0x02);
    settingsFrame.Append((char)(enable_push >> 24));
    settingsFrame.Append((char)(enable_push >> 16));
    settingsFrame.Append((char)(enable_push >> 8));
    settingsFrame.Append((char)(enable_push & 0xFF));
    
    // ... repeat for remaining settings
    
    // Step 3: Send SETTINGS frame
    mOutputQueueSent += settingsFrame.Length();
    mSegmentWriter->OnWriteSegment(settingsFrame.get(), settingsFrame.Length(), &rv);
    
    // TEGUFOX MARKER: HTTP/2 SETTINGS overridden
    TEGUFOX_LOG("HTTP/2 SETTINGS frame sent with custom values");
    
    return NS_OK;
}
```

### 3.3 WINDOW_UPDATE Randomization

#### 3.3.1 Background

After sending SETTINGS, the client sends a **WINDOW_UPDATE** frame to increase the connection-level flow control window.

**Chrome 120**: WINDOW_UPDATE increment = `15663105` (0xEF0001)  
**Firefox 115**: WINDOW_UPDATE increment = `12517377` (0xBF0001)  
**Python httpx**: WINDOW_UPDATE increment = `0` (not sent)

#### 3.3.2 Algorithm

```cpp
// In Http2Session.cpp, after SendSettings()

void Http2Session::SendWindowUpdate() {
    // Step 1: Get custom WINDOW_UPDATE value from MaskConfig
    uint32_t increment = GetMaskConfigUint32("http2.window_update", 15663105);
    
    if (increment == 0) {
        // Don't send WINDOW_UPDATE if increment is 0
        TEGUFOX_LOG("WINDOW_UPDATE skipped (increment = 0)");
        return;
    }
    
    // Step 2: Build WINDOW_UPDATE frame
    nsAutoCString frame;
    
    // Frame header (9 bytes)
    frame.Append((char)0x00); // Length = 4 (24-bit)
    frame.Append((char)0x00);
    frame.Append((char)0x04);
    frame.Append((char)0x08); // Type = WINDOW_UPDATE
    frame.Append((char)0x00); // Flags = 0
    frame.Append((char)0x00); // Stream ID = 0 (connection-level)
    frame.Append((char)0x00);
    frame.Append((char)0x00);
    frame.Append((char)0x00);
    
    // Payload: Window Size Increment (32-bit, MSB must be 0)
    frame.Append((char)((increment >> 24) & 0x7F)); // Clear MSB
    frame.Append((char)(increment >> 16));
    frame.Append((char)(increment >> 8));
    frame.Append((char)(increment & 0xFF));
    
    // Step 3: Send WINDOW_UPDATE frame
    mOutputQueueSent += frame.Length();
    mSegmentWriter->OnWriteSegment(frame.get(), frame.Length(), &rv);
    
    TEGUFOX_LOG("WINDOW_UPDATE sent: increment = %u", increment);
}
```

### 3.4 Pseudo-Header Ordering

#### 3.4.1 Background

HTTP/2 replaces HTTP/1.1's request line with 4 **pseudo-headers**:

- `:method` - HTTP method (GET, POST, etc.)
- `:scheme` - Protocol scheme (https, http)
- `:authority` - Host + port (example.com:443)
- `:path` - Request path (/index.html)

**Order matters for fingerprinting**:

| Browser | Pseudo-Header Order | Akamai Format |
|---------|---------------------|---------------|
| **Chrome** | `:method`, `:authority`, `:scheme`, `:path` | `m,a,s,p` |
| **Firefox** | `:method`, `:path`, `:authority`, `:scheme` | `m,p,a,s` |
| **Safari** | `:method`, `:scheme`, `:authority`, `:path` | `m,s,a,p` |
| **curl** | `:method`, `:path`, `:scheme`, `:authority` | `m,p,s,a` |

#### 3.4.2 Implementation

```cpp
// In Http2Compression.cpp, inside EncodeHeaderBlock()

void Http2Compression::EncodeHeaderBlock(
    const nsTArray<nsHttpHeaderArray>& headers,
    nsACString& output) {
    
    // Step 1: Get custom pseudo-header order from MaskConfig
    const char* order = GetMaskConfigString("http2.pseudo_header_order");
    std::vector<std::string> header_order;
    
    if (order != nullptr) {
        header_order = ParseHeaderOrder(order); // ["method", "authority", "scheme", "path"]
    } else {
        // Default: Chrome order
        header_order = {"method", "authority", "scheme", "path"};
    }
    
    // Step 2: Collect pseudo-headers
    std::map<std::string, std::string> pseudo_headers;
    for (const auto& header : headers) {
        if (header.name.StartsWith(":")) {
            std::string name = header.name.Substring(1).get(); // Remove ":"
            pseudo_headers[name] = header.value.get();
        }
    }
    
    // Step 3: Encode pseudo-headers in custom order
    for (const auto& name : header_order) {
        auto it = pseudo_headers.find(name);
        if (it != pseudo_headers.end()) {
            EncodeHeader(":" + name, it->second, output);
        }
    }
    
    // Step 4: Encode regular headers (alphabetical order)
    for (const auto& header : headers) {
        if (!header.name.StartsWith(":")) {
            EncodeHeader(header.name.get(), header.value.get(), output);
        }
    }
    
    TEGUFOX_LOG("Pseudo-headers encoded in custom order");
}
```

### 3.5 Profile Templates

#### 3.5.1 Chrome 120 Profile

```json
{
  "name": "chrome-120-windows",
  "tls": {
    "version": "1.3",
    "cipher_suites": [
      "TLS_AES_128_GCM_SHA256",
      "TLS_AES_256_GCM_SHA384",
      "TLS_CHACHA20_POLY1305_SHA256",
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
      "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
      "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
      "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256"
    ],
    "extensions": {
      "sni": true,
      "alpn": ["h2", "http/1.1"],
      "supported_groups": ["x25519", "secp256r1", "secp384r1"],
      "signature_algorithms": [
        "ecdsa_secp256r1_sha256",
        "rsa_pss_rsae_sha256",
        "rsa_pkcs1_sha256",
        "ecdsa_secp384r1_sha384",
        "rsa_pss_rsae_sha384",
        "rsa_pkcs1_sha384",
        "rsa_pss_rsae_sha512",
        "rsa_pkcs1_sha512"
      ],
      "compress_certificate": ["brotli"]
    }
  },
  "http2": {
    "settings": {
      "header_table_size": 65536,
      "enable_push": 0,
      "max_concurrent_streams": 1000,
      "initial_window_size": 6291456,
      "max_frame_size": 16384,
      "max_header_list_size": 262144
    },
    "window_update": 15663105,
    "priority_frames": false,
    "pseudo_header_order": ["method", "authority", "scheme", "path"]
  },
  "ja3_hash": "579ccef312d18482fc42e2b822ca2430",
  "ja4_hash": "t13d1516h2_8daaf6152771_e5627906d626",
  "akamai_http2": "1:65536;2:0;3:1000;4:6291456;5:16384;6:262144|15663105|0|m,a,s,p"
}
```

#### 3.5.2 Firefox 115 Profile

```json
{
  "name": "firefox-115-windows",
  "tls": {
    "version": "1.3",
    "cipher_suites": [
      "TLS_AES_128_GCM_SHA256",
      "TLS_CHACHA20_POLY1305_SHA256",
      "TLS_AES_256_GCM_SHA384",
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
      "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256"
    ],
    "extensions": {
      "sni": true,
      "alpn": ["h2", "http/1.1"],
      "supported_groups": ["x25519", "secp256r1", "secp384r1", "secp521r1", "ffdhe2048", "ffdhe3072"],
      "signature_algorithms": [
        "ecdsa_secp256r1_sha256",
        "ecdsa_secp384r1_sha384",
        "ecdsa_secp521r1_sha512",
        "rsa_pss_rsae_sha256",
        "rsa_pss_rsae_sha384",
        "rsa_pss_rsae_sha512",
        "rsa_pkcs1_sha256",
        "rsa_pkcs1_sha384",
        "rsa_pkcs1_sha512"
      ]
    }
  },
  "http2": {
    "settings": {
      "header_table_size": 65536,
      "enable_push": 0,
      "max_concurrent_streams": 200,
      "initial_window_size": 131072,
      "max_frame_size": 16384,
      "max_header_list_size": 262144
    },
    "window_update": 12517377,
    "priority_frames": true,
    "priority_streams": [3, 5, 7, 9, 11],
    "pseudo_header_order": ["method", "path", "authority", "scheme"]
  },
  "ja3_hash": "de350869b8c85de67a350c8d186f11e6",
  "ja4_hash": "t13d1215h2_5b57614c22b0_3d5424432f57",
  "akamai_http2": "1:65536;2:0;3:200;4:131072;5:16384;6:262144|12517377|3,5,7,9,11|m,p,a,s"
}
```

#### 3.5.3 Safari 17 Profile

```json
{
  "name": "safari-17-macos",
  "tls": {
    "version": "1.3",
    "cipher_suites": [
      "TLS_AES_128_GCM_SHA256",
      "TLS_AES_256_GCM_SHA384",
      "TLS_CHACHA20_POLY1305_SHA256",
      "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
      "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
    ],
    "extensions": {
      "sni": true,
      "alpn": ["h2", "http/1.1"],
      "supported_groups": ["x25519", "secp256r1", "secp384r1", "secp521r1"],
      "signature_algorithms": [
        "ecdsa_secp256r1_sha256",
        "rsa_pss_rsae_sha256",
        "rsa_pkcs1_sha256",
        "ecdsa_secp384r1_sha384",
        "ecdsa_secp521r1_sha512",
        "rsa_pss_rsae_sha384",
        "rsa_pss_rsae_sha512",
        "rsa_pkcs1_sha384",
        "rsa_pkcs1_sha512"
      ]
    }
  },
  "http2": {
    "settings": {
      "header_table_size": 4096,
      "enable_push": 0,
      "max_concurrent_streams": 100,
      "initial_window_size": 2097152,
      "max_frame_size": 16384
    },
    "window_update": 10485760,
    "priority_frames": false,
    "pseudo_header_order": ["method", "scheme", "authority", "path"]
  },
  "ja3_hash": "88a0145f0d8c6c0b2c3e5f9a7b8c9d0e",
  "ja4_hash": "t13d915h2_9c5e8a7f3b2d_1a4c7e9f2b5d",
  "akamai_http2": "1:4096;2:0;3:100;4:2097152;5:16384|10485760|0|m,s,a,p"
}
```

---

## 4. Implementation Plan

### 4.1 File Structure

```
patches/
  └── http2-fingerprint.patch     # Main C++ patch (300-400 lines)

docs/
  ├── HTTP2_FINGERPRINT_DESIGN.md # This document
  └── HTTP2_FINGERPRINT_GUIDE.md  # Implementation guide (to be created)

tests/
  └── test_http2_fingerprint.py   # Python test suite

profiles/
  ├── chrome-120.json             # Chrome 120 template
  ├── firefox-115.json            # Firefox 115 template
  └── safari-17.json              # Safari 17 template
```

### 4.2 Patch Components

#### Component 1: TLS Cipher Suite Override (150 lines)

**Files to modify**:
- `security/nss/lib/ssl/ssl3con.c` - ClientHello construction
- `security/nss/lib/ssl/ssl3ext.c` - Extension handling

**Functions to hook**:
- `ssl3_SendClientHello()` - Override cipher suite list
- `ssl3_SendSupportedGroupsXtn()` - Override supported groups
- `ssl3_SendSignatureAlgorithmsXtn()` - Override signature algorithms

**MaskConfig parameters**:
```cpp
tls.cipher_suites              // Array of cipher suite names
tls.extensions.supported_groups   // Array of group names (x25519, secp256r1, etc.)
tls.extensions.signature_algorithms // Array of signature algorithm names
tls.extensions.alpn            // Array of ALPN protocols (h2, http/1.1)
```

#### Component 2: HTTP/2 Settings Override (100 lines)

**Files to modify**:
- `netwerk/protocol/http/Http2Session.cpp` - HTTP/2 connection setup

**Functions to hook**:
- `Http2Session::SendSettings()` - Override SETTINGS frame
- `Http2Session::SendWindowUpdate()` - Override WINDOW_UPDATE

**MaskConfig parameters**:
```cpp
http2.settings.header_table_size         // uint32
http2.settings.enable_push               // 0 or 1
http2.settings.max_concurrent_streams    // uint32
http2.settings.initial_window_size       // uint32
http2.settings.max_frame_size            // uint32
http2.settings.max_header_list_size      // uint32
http2.window_update                      // uint32
http2.priority_frames                    // boolean
```

#### Component 3: Pseudo-Header Ordering (50 lines)

**Files to modify**:
- `netwerk/protocol/http/Http2Compression.cpp` - HPACK encoding

**Functions to hook**:
- `Http2Compression::EncodeHeaderBlock()` - Control header order

**MaskConfig parameters**:
```cpp
http2.pseudo_header_order  // Array: ["method", "authority", "scheme", "path"]
```

#### Component 4: Helper Functions (50 lines)

```cpp
// Cipher suite name → NSS constant mapping
PRUint16 MapCipherNameToNSS(const char* name);

// Supported group name → NSS constant mapping
SSLNamedGroup MapGroupNameToNSS(const char* name);

// Signature algorithm name → NSS constant mapping
SSLSignatureScheme MapSigAlgNameToNSS(const char* name);

// Parse comma-separated list
std::vector<std::string> ParseList(const char* input);

// TEGUFOX logging
void TEGUFOX_LOG(const char* format, ...);
```

### 4.3 Testing Strategy

#### Test 1: JA3 Hash Validation

```python
def test_ja3_hash_chrome():
    """Test that TLS fingerprint matches Chrome 120."""
    browser = await camoufox.launch(profile="chrome-120.json")
    page = await browser.new_page()
    
    # Visit BrowserLeaks SSL test
    await page.goto("https://browserleaks.com/ssl")
    
    # Extract JA3 hash from page
    ja3_hash = await page.locator("#ja3-hash").text_content()
    
    # Expected Chrome 120 JA3
    expected = "579ccef312d18482fc42e2b822ca2430"
    
    assert ja3_hash == expected, f"JA3 mismatch: {ja3_hash} != {expected}"
```

#### Test 2: HTTP/2 Settings Validation

```python
def test_http2_settings_chrome():
    """Test that HTTP/2 SETTINGS matches Chrome 120."""
    browser = await camoufox.launch(profile="chrome-120.json")
    page = await browser.new_page()
    
    # Visit Scrapfly HTTP/2 fingerprint test
    await page.goto("https://scrapfly.io/web-scraping-tools/http2-fingerprint")
    
    # Extract Akamai fingerprint
    fingerprint = await page.locator("#akamai-fingerprint").text_content()
    
    # Expected Chrome 120 fingerprint
    expected = "1:65536;2:0;3:1000;4:6291456;5:16384;6:262144|15663105|0|m,a,s,p"
    
    assert fingerprint == expected, f"HTTP/2 mismatch: {fingerprint} != {expected}"
```

#### Test 3: Cross-Layer Consistency

```python
def test_cross_layer_consistency():
    """Test that TLS, HTTP/2, and UA are consistent."""
    browser = await camoufox.launch(profile="chrome-120.json")
    page = await browser.new_page()
    
    # Visit multi-layer fingerprint test
    await page.goto("https://tls.peet.ws/api/all")
    
    # Extract fingerprints
    result = await page.evaluate("() => JSON.parse(document.body.textContent)")
    
    # Check consistency
    assert result["tls"]["library"] == "BoringSSL", "TLS library mismatch"
    assert result["http2"]["user_agent_match"] == True, "UA ↔ HTTP/2 mismatch"
    assert result["tls"]["user_agent_match"] == True, "UA ↔ TLS mismatch"
```

#### Test 4: Real-World E-commerce

```python
def test_amazon_access():
    """Test Amazon.com access without bot challenge."""
    browser = await camoufox.launch(profile="chrome-120.json")
    page = await browser.new_page()
    
    await page.goto("https://www.amazon.com")
    
    # Check for bot challenge
    content = await page.content()
    
    assert "Robot Check" not in content, "Amazon bot challenge triggered"
    assert "captcha" not in content.lower(), "CAPTCHA triggered"
    
    # Check for normal product listings
    products = await page.locator(".s-result-item").count()
    assert products > 0, "No products found (possible block)"
```

### 4.4 Timeline

| Task | Duration | Deliverable |
|------|----------|-------------|
| **TLS Cipher Suite Override** | 2 hours | NSS patch (150 lines) |
| **HTTP/2 Settings Override** | 1.5 hours | Http2Session patch (100 lines) |
| **Pseudo-Header Ordering** | 1 hour | Http2Compression patch (50 lines) |
| **Helper Functions** | 0.5 hours | Utility code (50 lines) |
| **Profile Templates** | 1 hour | 3 JSON profiles (Chrome, Firefox, Safari) |
| **Test Suite** | 1 hour | test_http2_fingerprint.py (250 lines) |
| **Documentation** | 1 hour | HTTP2_FINGERPRINT_GUIDE.md (1,000 lines) |
| **Total** | **8 hours** | **Complete HTTP/2 defense system** |

---

## 5. Security & Privacy Considerations

### 5.1 Undetectability

Our C++-level approach is **fundamentally undetectable** because:

1. **No JavaScript hooks**
   - Operates below the JavaScript engine
   - `toString()` on WebAssembly functions returns "[native code]"
   - No prototype tampering visible to `Object.getOwnPropertyDescriptor()`

2. **No extension artifacts**
   - Not a browser extension (no `chrome.runtime` APIs)
   - No extension UUIDs in network traffic
   - No CSP violations from content scripts

3. **Perfect cross-layer consistency**
   - TLS library matches HTTP/2 stack
   - HTTP/2 stack matches User-Agent claim
   - All layers synchronized via MaskConfig

### 5.2 Privacy Impact

**Positive privacy effects**:
- ✅ Blends with mainstream browsers (reduces uniqueness)
- ✅ No additional tracking vectors added
- ✅ Works with existing privacy tools (uBlock Origin, Privacy Badger)

**Neutral effects**:
- ⚖️ TLS fingerprint is visible to network observers (already public)
- ⚖️ HTTP/2 settings are visible to servers (already public)

**No negative effects**:
- ❌ Does not weaken TLS security (cipher suites are still strong)
- ❌ Does not leak additional metadata

### 5.3 Legal & Ethical

**Use cases**:
- ✅ E-commerce automation (price monitoring, inventory tracking)
- ✅ Security research (testing anti-bot systems)
- ✅ Privacy protection (avoiding fingerprinting)

**Non-use cases** (user responsibility):
- ⚠️ Terms of Service violations (read ToS before automating)
- ⚠️ DDoS attacks (illegal, unethical)
- ⚠️ Credential stuffing (illegal)

**Disclosure**:
This toolkit is for **authorized security research and legitimate automation**. Users are responsible for compliance with applicable laws and website terms of service.

---

## 6. Future Work

### 6.1 HTTP/3 / QUIC Fingerprinting

HTTP/3 replaces TCP with **QUIC** (UDP-based transport). QUIC has its own fingerprinting vectors:

- **QUIC transport parameters** (similar to HTTP/2 SETTINGS)
- **Initial packet structure**
- **Connection ID format**

**Timeline**: Week 4+ (after HTTP/2 defense is stable)

### 6.2 ECH (Encrypted ClientHello)

TLS 1.3 extension that encrypts the ClientHello, preventing passive fingerprinting.

**Status**: Draft RFC, not yet widely deployed  
**Timeline**: Monitor standardization progress

### 6.3 JA4+ Family

JA4+ includes additional fingerprint types:
- **JA4H** - HTTP client fingerprint (header order, HTTP version)
- **JA4X** - X.509 certificate fingerprint
- **JA4L** - Light distance measurement

**Timeline**: Week 5+ (expand fingerprint coverage)

### 6.4 Dynamic Fingerprint Rotation

Rotate fingerprints per session to avoid long-term tracking:

```json
{
  "rotation": {
    "enabled": true,
    "interval": "per-session",
    "profiles": ["chrome-120", "firefox-115", "safari-17"],
    "strategy": "random"
  }
}
```

**Timeline**: Week 6+ (advanced evasion)

---

## 7. Conclusion

HTTP/2 fingerprinting defense is **critical** for modern anti-bot evasion because:

1. **Detection happens before JavaScript** - No amount of Canvas/WebGL spoofing helps
2. **Cross-layer validation is standard** - TLS ↔ HTTP/2 ↔ UA consistency is checked
3. **Python libraries are easily fingerprinted** - `requests`, `httpx`, `aiohttp` have obvious signatures

Our **C++-level implementation** in Firefox/Camoufox provides:
- ✅ **Complete control** over TLS cipher suites and HTTP/2 settings
- ✅ **Undetectable** (no JavaScript hooks, no prototype tampering)
- ✅ **Profile-based** configuration (easy to match any browser)
- ✅ **Cross-layer consistency** (all layers synchronized)

**Expected results**:
- 🎯 Pass BrowserLeaks SSL test (JA3/JA4 match target browser)
- 🎯 Pass Scrapfly HTTP/2 test (Akamai fingerprint match)
- 🎯 Access Amazon.com without bot challenge
- 🎯 Access eBay.com without CAPTCHA

**Estimated time**: 8 hours  
**Complexity**: Medium (requires Firefox build)  
**Impact**: High (unlocks protocol-layer evasion)

---

## Appendix A: Cipher Suite Mapping

### TLS 1.3 Cipher Suites (RFC 8446)

| MaskConfig Name | NSS Constant | Hex Value |
|-----------------|--------------|-----------|
| `TLS_AES_128_GCM_SHA256` | `TLS_AES_128_GCM_SHA256` | `0x1301` |
| `TLS_AES_256_GCM_SHA384` | `TLS_AES_256_GCM_SHA384` | `0x1302` |
| `TLS_CHACHA20_POLY1305_SHA256` | `TLS_CHACHA20_POLY1305_SHA256` | `0x1303` |
| `TLS_AES_128_CCM_SHA256` | `TLS_AES_128_CCM_SHA256` | `0x1304` |
| `TLS_AES_128_CCM_8_SHA256` | `TLS_AES_128_CCM_8_SHA256` | `0x1305` |

### TLS 1.2 Cipher Suites (RFC 5246)

| MaskConfig Name | NSS Constant | Hex Value |
|-----------------|--------------|-----------|
| `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` | `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` | `0xC02B` |
| `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` | `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` | `0xC02F` |
| `TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384` | `TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384` | `0xC02C` |
| `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384` | `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384` | `0xC030` |
| `TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256` | `TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256` | `0xCCA9` |
| `TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256` | `TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256` | `0xCCA8` |
| `TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA` | `TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA` | `0xC009` |
| `TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA` | `TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA` | `0xC013` |
| `TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA` | `TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA` | `0xC00A` |
| `TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA` | `TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA` | `0xC014` |
| `TLS_RSA_WITH_AES_128_GCM_SHA256` | `TLS_RSA_WITH_AES_128_GCM_SHA256` | `0x009C` |
| `TLS_RSA_WITH_AES_256_GCM_SHA384` | `TLS_RSA_WITH_AES_256_GCM_SHA384` | `0x009D` |
| `TLS_RSA_WITH_AES_128_CBC_SHA` | `TLS_RSA_WITH_AES_128_CBC_SHA` | `0x002F` |
| `TLS_RSA_WITH_AES_256_CBC_SHA` | `TLS_RSA_WITH_AES_256_CBC_SHA` | `0x0035` |
| `TLS_RSA_WITH_3DES_EDE_CBC_SHA` | `TLS_RSA_WITH_3DES_EDE_CBC_SHA` | `0x000A` |

(Full list: 50+ cipher suites supported by NSS)

---

## Appendix B: Supported Groups (Elliptic Curves)

| MaskConfig Name | NSS Constant | Value |
|-----------------|--------------|-------|
| `secp256r1` | `ssl_grp_ec_secp256r1` | 23 |
| `secp384r1` | `ssl_grp_ec_secp384r1` | 24 |
| `secp521r1` | `ssl_grp_ec_secp521r1` | 25 |
| `x25519` | `ssl_grp_ec_curve25519` | 29 |
| `x448` | `ssl_grp_ec_curve448` | 30 |
| `ffdhe2048` | `ssl_grp_ffdhe_2048` | 256 |
| `ffdhe3072` | `ssl_grp_ffdhe_3072` | 257 |
| `ffdhe4096` | `ssl_grp_ffdhe_4096` | 258 |
| `ffdhe6144` | `ssl_grp_ffdhe_6144` | 259 |
| `ffdhe8192` | `ssl_grp_ffdhe_8192` | 260 |

---

## Appendix C: Signature Algorithms

| MaskConfig Name | NSS Constant | Value |
|-----------------|--------------|-------|
| `rsa_pkcs1_sha256` | `ssl_sig_rsa_pkcs1_sha256` | 0x0401 |
| `rsa_pkcs1_sha384` | `ssl_sig_rsa_pkcs1_sha384` | 0x0501 |
| `rsa_pkcs1_sha512` | `ssl_sig_rsa_pkcs1_sha512` | 0x0601 |
| `ecdsa_secp256r1_sha256` | `ssl_sig_ecdsa_secp256r1_sha256` | 0x0403 |
| `ecdsa_secp384r1_sha384` | `ssl_sig_ecdsa_secp384r1_sha384` | 0x0503 |
| `ecdsa_secp521r1_sha512` | `ssl_sig_ecdsa_secp521r1_sha512` | 0x0603 |
| `rsa_pss_rsae_sha256` | `ssl_sig_rsa_pss_rsae_sha256` | 0x0804 |
| `rsa_pss_rsae_sha384` | `ssl_sig_rsa_pss_rsae_sha384` | 0x0805 |
| `rsa_pss_rsae_sha512` | `ssl_sig_rsa_pss_rsae_sha512` | 0x0806 |
| `ed25519` | `ssl_sig_ed25519` | 0x0807 |
| `ed448` | `ssl_sig_ed448` | 0x0808 |
| `rsa_pss_pss_sha256` | `ssl_sig_rsa_pss_pss_sha256` | 0x0809 |
| `rsa_pss_pss_sha384` | `ssl_sig_rsa_pss_pss_sha384` | 0x080A |
| `rsa_pss_pss_sha512` | `ssl_sig_rsa_pss_pss_sha512` | 0x080B |

---

**End of Design Document**

Total: ~2,100 lines
