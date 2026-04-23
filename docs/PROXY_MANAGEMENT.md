# Proxy Management Feature

## Overview

Tab quản lý proxy với đầy đủ tính năng CRUD, import bulk, và test proxy.

## Features

### 1. Import Proxies
- **Single import**: Thêm từng proxy qua form
- **Bulk import**: Import nhiều proxy cùng lúc
- **Supported formats**:
  - `ip:port:user:pass` (e.g., `192.168.1.1:8080:admin:secret`)
  - `user:pass@ip:port` (e.g., `admin:secret@192.168.1.1:8080`)
  - `ip:port` (no authentication, e.g., `192.168.1.1:8080`)

### 2. CRUD Operations
- **Create**: Thêm proxy mới với đầy đủ thông tin
- **Read**: Xem chi tiết proxy
- **Update**: Sửa thông tin proxy (host, port, username, password, protocol, notes)
- **Delete**: Xóa single hoặc multiple proxies

### 3. Test Proxy
- **Single test**: Click nút 🔍 trên từng proxy card
- **Bulk test**: Select multiple proxies → click "🔍 Test" button
- Fetch IP từ https://api.ipify.org
- Hiển thị:
  - ✓ Success: IP address + response time
  - ✗ Failed: Error message
- Auto-update status: `active` (green) / `failed` (red) / `inactive` (gray)

### 4. Search & Filter
- Search by name, host, or username
- Sort by: Name A→Z, Name Z→A, Date newest, Date oldest
- Select all / Deselect all
- **Bulk operations**:
  - Delete multiple selected proxies
  - Test multiple selected proxies

## Database Schema

```python
ProxyPool:
  - id (primary key)
  - name (unique, indexed)
  - host (IP address)
  - port (integer)
  - username (optional)
  - password (optional)
  - protocol (http/https/socks5)
  - status (active/inactive/failed)
  - last_checked (datetime)
  - last_ip (string - result from test)
  - created (datetime)
  - notes (text)
```

## Usage

### GUI
```bash
python tegufox-gui
```

Click "Proxies" 🔌 in sidebar to access proxy management.

### Programmatic API

```python
from tegufox_core.proxy_manager import ProxyManager

pm = ProxyManager()

# Create single proxy
proxy = pm.create(
    name="my_proxy",
    host="192.168.1.100",
    port=8080,
    username="admin",
    password="secret",
    protocol="http",
    notes="My test proxy"
)

# Bulk import
proxies = [
    "10.0.0.1:3128:user:pass",
    "user:pass@10.0.0.2:8888",
    "10.0.0.3:8080",
]
success_count, errors = pm.bulk_import(proxies)

# Test proxy
result = pm.test_proxy("my_proxy")
if result["success"]:
    print(f"IP: {result['ip']}")
    print(f"Response time: {result['response_time']}s")
else:
    print(f"Error: {result['error']}")

# Search
results = pm.search("10.0.0")

# Update
pm.update("my_proxy", status="active", notes="Working proxy")

# Delete
pm.delete("my_proxy")

# Delete multiple
pm.delete_multiple(["proxy_1", "proxy_2", "proxy_3"])
```

## Files Created

1. **Backend**:
   - `tegufox_core/proxy_manager.py` - ProxyManager class + database models
   - `tegufox_core/proxies.db` - SQLite database (auto-created)

2. **Frontend**:
   - `tegufox_gui/pages/proxies_page.py` - ProxiesWidget + ProxyCard components

3. **Tests**:
   - `tests/test_proxy_manager.py` - Comprehensive test suite
   - `tests/demo_proxy_manager.py` - Demo script
   - `tests/demo_test_selected_proxies.py` - Bulk test demo

## Testing

Run test suite:
```bash
python tests/test_proxy_manager.py
```

Run demos:
```bash
python tests/demo_proxy_manager.py
python tests/demo_test_selected_proxies.py
```

## Notes

- Proxy database is separate from profile database (`proxies.db` vs `profiles.db`)
- Test functionality requires `httpx` library (already in dependencies)
- Proxy testing uses https://api.ipify.org to fetch external IP
- Failed tests automatically update proxy status to "failed"
- Successful tests update status to "active" and store last IP
