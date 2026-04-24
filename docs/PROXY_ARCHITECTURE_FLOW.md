# Proxy Assignment - Complete Architecture Flow

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TEGUFOX GUI (Qt6)                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Sessions Page                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ Proxy: [▼]   │  │  [Test]      │  │  [Launch]    │    │ │
│  │  │ ✓ proxy_2    │  │              │  │              │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PROXY MANAGER                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ProxyManager.load("proxy_2")                              │ │
│  │  Returns: {                                                │ │
│  │    "host": "gw-resi-gb.coldproxy.com",                    │ │
│  │    "port": 30331,                                          │ │
│  │    "username": "netphinnwb_98165-...",                    │ │
│  │    "password": "3DS5eiErHbYed",                           │ │
│  │    "protocol": "http",                                     │ │
│  │    "status": "active"                                      │ │
│  │  }                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION WORKER (QThread)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Build proxy_config:                                       │ │
│  │  {                                                         │ │
│  │    "server": "http://gw-resi-gb.coldproxy.com:30331",    │ │
│  │    "username": "netphinnwb_98165-...",                    │ │
│  │    "password": "3DS5eiErHbYed"                            │ │
│  │  }                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TEGUFOX SESSION                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SessionConfig(                                            │ │
│  │    headless=False,                                         │ │
│  │    viewport_width=800,                                     │ │
│  │    viewport_height=600,                                    │ │
│  │    proxy=proxy_config  ← Stored in config                 │ │
│  │  )                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              _build_launch_options()                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  opts = {                                                  │ │
│  │    'executable_path': '/path/to/tegufox',                 │ │
│  │    'firefox_user_prefs': {...},                           │ │
│  │    'proxy': {                                              │ │
│  │      "server": "http://gw-resi-gb.coldproxy.com:30331",  │ │
│  │      "username": "netphinnwb_98165-...",                  │ │
│  │      "password": "3DS5eiErHbYed"                          │ │
│  │    }                                                       │ │
│  │  }                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  _start_tegufox()                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ⚠️  CRITICAL STEP: Extract proxy from dict                │ │
│  │                                                            │ │
│  │  proxy_config = launch_opts.pop('proxy', None)            │ │
│  │                                                            │ │
│  │  if proxy_config:                                          │ │
│  │    Camoufox(                                               │ │
│  │      headless=False,                                       │ │
│  │      i_know_what_im_doing=True,                           │ │
│  │      proxy=proxy_config,  ← Named parameter!              │ │
│  │      **launch_opts                                         │ │
│  │    )                                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAMOUFOX WRAPPER                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Camoufox.__init__(**launch_options)                       │ │
│  │    ↓                                                       │ │
│  │  Camoufox.__enter__()                                      │ │
│  │    ↓                                                       │ │
│  │  NewBrowser(playwright, **self.launch_options)             │ │
│  │    ↓                                                       │ │
│  │  from_options = launch_options(                            │ │
│  │    headless=False,                                         │ │
│  │    proxy=proxy_config,  ← Received as named param         │ │
│  │    **kwargs                                                │ │
│  │  )                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              launch_options() Helper (utils.py)                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  def launch_options(                                       │ │
│  │    headless: Optional[bool] = None,                        │ │
│  │    proxy: Optional[Dict[str, str]] = None,  ← Named param │ │
│  │    ...                                                     │ │
│  │  ) -> Dict[str, Any]:                                      │ │
│  │                                                            │ │
│  │    result = {                                              │ │
│  │      'headless': headless,                                 │ │
│  │      'firefox_user_prefs': {...},                         │ │
│  │      ...                                                   │ │
│  │    }                                                       │ │
│  │                                                            │ │
│  │    if proxy is not None:                                   │ │
│  │      result["proxy"] = proxy  ← Added to result           │ │
│  │                                                            │ │
│  │    return result                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PLAYWRIGHT / FIREFOX                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  playwright.firefox.launch(                                │ │
│  │    executable_path='/path/to/tegufox',                     │ │
│  │    firefox_user_prefs={...},                              │ │
│  │    proxy={                                                 │ │
│  │      "server": "http://gw-resi-gb.coldproxy.com:30331",  │ │
│  │      "username": "netphinnwb_98165-...",                  │ │
│  │      "password": "3DS5eiErHbYed"                          │ │
│  │    }                                                       │ │
│  │  )                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIREFOX BROWSER                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ✅ Browser launches with proxy configured                 │ │
│  │  ✅ All HTTP/HTTPS requests go through proxy               │ │
│  │  ✅ External IP = Proxy IP                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Critical Fix Explanation

### ❌ What Was Wrong

```python
# In _start_tegufox()
launch_opts = {
    'executable_path': '...',
    'firefox_user_prefs': {...},
    'proxy': proxy_config  # ← Proxy buried in dict
}

self._camoufox = Camoufox(
    headless=False,
    i_know_what_im_doing=True,
    **launch_opts  # ← Proxy unpacked as part of kwargs
)

# Result: launch_options() function never receives proxy as named parameter
# It's just another key in **kwargs, not the expected 'proxy' parameter
```

### ✅ What Is Correct

```python
# In _start_tegufox()
launch_opts = {
    'executable_path': '...',
    'firefox_user_prefs': {...},
    'proxy': proxy_config
}

# Extract proxy BEFORE passing to Camoufox
proxy_config = launch_opts.pop('proxy', None)

self._camoufox = Camoufox(
    headless=False,
    i_know_what_im_doing=True,
    proxy=proxy_config,  # ← Named parameter
    **launch_opts        # ← Rest of options
)

# Result: launch_options() receives proxy as named parameter
# Function properly validates and includes it in result dict
```

## Why This Matters

The `launch_options()` function signature is:

```python
def launch_options(
    headless: Optional[bool] = None,
    proxy: Optional[Dict[str, str]] = None,  # ← Named parameter
    executable_path: Optional[str] = None,
    ...
) -> Dict[str, Any]:
```

When you call:
- `launch_options(proxy=config)` → ✅ Works (named parameter)
- `launch_options(**{'proxy': config})` → ❌ Doesn't work (kwargs dict)

Python treats these differently:
- Named parameter: `proxy` is bound to the function parameter
- Kwargs dict: `proxy` is just another key in `**kwargs`

## Data Flow Summary

1. **GUI**: User selects proxy → proxy name string
2. **ProxyManager**: Load proxy data → dict with host/port/credentials
3. **SessionWorker**: Build proxy config → Playwright format
4. **SessionConfig**: Store proxy config → passed to TegufoxSession
5. **_build_launch_options()**: Add proxy to opts dict
6. **_start_tegufox()**: Extract proxy from dict → pass as named param
7. **Camoufox**: Forward proxy to launch_options() → named parameter
8. **launch_options()**: Validate and include in result
9. **Playwright**: Launch Firefox with proxy configured
10. **Firefox**: All requests go through proxy

## Key Takeaways

1. **Firefox requires proxy at launch level** (not context level)
2. **Credentials must be separate** from server URL
3. **Camoufox expects proxy as named parameter** (not in dict)
4. **Extract proxy before passing to Camoufox()** (use .pop())
5. **Test with httpbin.org** (fv.pro has proxy issues)

---

**Status**: ✅ Working  
**Last Updated**: April 23, 2026
