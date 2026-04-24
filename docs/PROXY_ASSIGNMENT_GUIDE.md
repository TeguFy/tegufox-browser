# Proxy Assignment Feature - Implementation Guide

## Overview
Added proxy assignment functionality to the Sessions page, allowing users to select a proxy from their proxy pool when launching browser sessions.

## Features Implemented

### 1. UI Components
- **Proxy Dropdown**: Shows all available proxies with status indicators
  - ✓ = Active (tested and working)
  - ✗ = Failed (last test failed)
  - ? = Unknown (not tested yet)
- **Test Button**: Allows testing proxy before launching session
- **Status Display**: Shows proxy name in session row when active

### 2. Proxy Selection
- Dropdown displays: `✓ proxy_name (host:port)`
- "None" option for sessions without proxy
- Stores proxy name as item data for easy retrieval

### 3. Proxy Testing
- Click "Test" button to verify proxy connection
- Tests by fetching external IP via https://api.ipify.org
- Updates proxy status in database
- Shows result dialog with IP and response time

### 4. Session Integration
- Proxy config passed through: SessionWorker → SessionConfig → TegufoxSession → Playwright
- Format: `{"server": "http://user:pass@host:port", "username": "...", "password": "..."}`
- Logs proxy status and connection details

## Usage

### In GUI
1. Open Sessions page
2. Select a profile
3. Select a proxy from dropdown (or "None")
4. (Optional) Click "Test" to verify proxy works
5. Click "Launch Session"
6. Browser will route all traffic through selected proxy

### Programmatically
```python
from tegufox_automation import TegufoxSession, SessionConfig
from tegufox_core.proxy_manager import ProxyManager

# Load proxy
pm = ProxyManager()
proxy_data = pm.load("proxy_1")

# Build config (IMPORTANT: server should NOT include credentials)
proxy_config = {
    "server": f"{proxy_data['protocol']}://{proxy_data['host']}:{proxy_data['port']}",
    "username": proxy_data.get("username"),
    "password": proxy_data.get("password"),
}

# Create session
config = SessionConfig(proxy=proxy_config)
with TegufoxSession(profile="chrome-120", config=config) as session:
    session.goto("https://example.com")
```

## Troubleshooting

### 502 Bad Gateway Error
**Cause**: Proxy server is down, blocked, or unreachable

**Solutions**:
1. Test the proxy using the "Test" button
2. Check proxy status (✓/✗ indicator)
3. Try a different proxy
4. Verify proxy credentials are correct
5. Check if proxy requires authentication

### Connection Timeout
**Cause**: Proxy server not responding

**Solutions**:
1. Increase timeout in SessionConfig
2. Test proxy connectivity
3. Check firewall/network settings
4. Try a different proxy

### Authentication Failed
**Cause**: Invalid username/password

**Solutions**:
1. Verify credentials in proxy manager
2. Update proxy with correct credentials
3. Test proxy to verify authentication

### Proxy Works in Test but Fails in Session
**Cause**: Different timeout or connection settings

**Solutions**:
1. Check browser logs for detailed error
2. Verify proxy supports HTTPS/WebSocket
3. Try with headless=False to see browser error
4. Check if proxy has rate limiting

## Testing

### Test Script
Run the included test script:
```bash
python3 test_proxy_session.py [proxy_name]
```

This will:
1. List available proxies
2. Test proxy connection
3. Launch browser with proxy
4. Navigate to IP check site
5. Display external IP

### Manual Testing
1. Add proxies to proxy manager
2. Test each proxy using "Test" button
3. Launch session with active proxy
4. Navigate to https://api.ipify.org
5. Verify IP matches proxy IP

## Files Modified

### tegufox_gui/pages/sessions_page.py
- Added proxy dropdown UI
- Added proxy test button
- Added `_reload_proxies()` method
- Added `_test_proxy()` method
- Updated `SessionWorker.__init__()` to accept proxy
- Updated `SessionWorker.run()` to load and configure proxy
- Updated `_launch_session()` to pass proxy
- Updated `_add_session_row()` to display proxy info

### tegufox_automation/session.py
- Added `proxy` field to `SessionConfig`
- Updated `_build_context_options()` to include proxy

## Database Schema

Proxies are stored in `tegufox_core/proxies.db`:
```sql
CREATE TABLE proxy_pool (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT,
    password TEXT,
    protocol TEXT DEFAULT 'http',
    status TEXT DEFAULT 'inactive',
    last_checked DATETIME,
    last_ip TEXT,
    created DATETIME,
    notes TEXT
);
```

## API Reference

### ProxyManager Methods
- `list()` - Get all proxy names
- `load(name)` - Load proxy by name
- `test_proxy(name, timeout)` - Test proxy connection
- `create(...)` - Create new proxy
- `update(name, **kwargs)` - Update proxy
- `delete(name)` - Delete proxy

### format_proxy_url(proxy_dict)
Converts proxy dict to URL format:
```python
format_proxy_url({
    "host": "1.2.3.4",
    "port": 8080,
    "username": "user",
    "password": "pass",
    "protocol": "http"
})
# Returns: "http://user:pass@1.2.3.4:8080"
```

## Best Practices

1. **Always test proxies** before using in production
2. **Monitor proxy status** - failed proxies are marked with ✗
3. **Rotate proxies** to avoid rate limiting
4. **Use active proxies** (✓) for better reliability
5. **Handle errors gracefully** - have fallback proxies ready

## Future Enhancements

Potential improvements:
- [ ] Automatic proxy rotation per session
- [ ] Proxy pool health monitoring
- [ ] Proxy performance metrics (speed, uptime)
- [ ] Bulk proxy testing
- [ ] Proxy groups/tags for organization
- [ ] Geographic proxy selection
- [ ] Automatic failover to backup proxy
