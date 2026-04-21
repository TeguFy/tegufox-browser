# Tegufox Browser - Architecture

## 📁 Project Structure

```
tegufox-browser/
├── tegufox_core/              # Core business logic (pure Python, no UI/runtime deps)
│   ├── __init__.py
│   ├── consistency_engine.py  # Fingerprint consistency validation
│   ├── fingerprint_registry.py # SQLite-based fingerprint tracking
│   ├── profile_manager.py     # Profile CRUD operations
│   ├── profile_generator.py   # Profile template generation
│   ├── generator_v2.py        # Market-weighted profile sampling
│   └── webgl_database.py      # WebGL vendor/renderer database
│
├── tegufox_automation/        # Browser automation layer (Playwright/Camoufox)
│   ├── __init__.py
│   ├── session.py             # TegufoxSession, ProfileRotator, SessionManager
│   ├── mouse.py               # HumanMouse - realistic mouse movements
│   └── keyboard.py            # HumanKeyboard - human-like typing
│
├── tegufox_gui/               # PyQt6 graphical interface
│   ├── __init__.py
│   └── app.py                 # Profile manager GUI + automation runner
│
├── tegufox_cli/               # Command-line tools
│   ├── __init__.py            # Re-exports automation classes
│   └── api.py                 # FastAPI REST API server
│
├── tegufox-gui                # GUI entry point script
├── tegufox-cli                # CLI entry point script
│
├── profiles/                  # Profile storage (JSON files)
├── data/                      # SQLite databases
└── tests/                     # Test suite
```

## 🎯 Design Principles

### 1. **Separation of Concerns**

- **Core** = Pure business logic (no UI, no browser runtime)
- **Automation** = Browser control layer (can be used by GUI or CLI)
- **GUI** = User interface (manages profiles + runs automation)
- **CLI** = Command-line tools + API server

### 2. **Dependency Flow**

```
GUI ──────┐
          ├──> Automation ──> Core
CLI ──────┘
```

- GUI and CLI both depend on Automation
- Automation depends on Core
- Core has no dependencies on other layers

### 3. **Reusability**

The automation layer can be imported and used from:
- ✅ GUI (PyQt6 app can run automation scripts)
- ✅ CLI (command-line automation)
- ✅ Custom Python scripts
- ✅ Jupyter notebooks
- ✅ API endpoints

## 🚀 Usage Examples

### From GUI
```python
# GUI can import and use automation
from tegufox_automation import TegufoxSession, HumanMouse

# Run automation from GUI button click
def on_run_automation_clicked():
    with TegufoxSession(profile="my-profile") as session:
        session.goto("https://example.com")
        session.human_click("#button")
```

### From CLI
```bash
# Run CLI commands
./tegufox-cli profile create my-profile chrome-144 windows
./tegufox-cli fleet generate 10
./tegufox-cli api start --port 8420
```

### From Python Script
```python
from tegufox_core import ProfileManager, generate_fleet
from tegufox_automation import TegufoxSession

# Generate profiles
manager = ProfileManager("profiles")
fleet = generate_fleet(manager, count=5)

# Run automation
for profile in fleet:
    with TegufoxSession(profile=profile["name"]) as session:
        session.goto("https://example.com")
        session.human_type("#search", "query")
```

### From API
```bash
# Start API server
./tegufox-cli api start

# Use REST endpoints
curl http://localhost:8420/profiles
curl -X POST http://localhost:8420/fleet/generate?count=10
```

## 📦 Package Responsibilities

### `tegufox_core`
- Profile CRUD (create, read, update, delete)
- Consistency validation (TLS, HTTP/2, DNS, WebGL)
- Fingerprint generation (market-weighted sampling)
- Anti-correlation tracking (SQLite registry)
- **No dependencies on**: Playwright, Camoufox, PyQt6

### `tegufox_automation`
- Browser session management (Playwright/Camoufox wrapper)
- Human-like mouse movements (Bezier curves, Fitts's Law)
- Human-like keyboard typing (log-normal timing, typos)
- Profile rotation and session persistence
- **Dependencies**: Playwright, Camoufox, tegufox_core

### `tegufox_gui`
- PyQt6 profile manager interface
- Visual profile editor
- Fleet generation wizard
- **Automation runner** (can execute automation scripts)
- **Dependencies**: PyQt6, tegufox_core, tegufox_automation

### `tegufox_cli`
- Command-line profile management
- FastAPI REST API server
- Re-exports automation classes for convenience
- **Dependencies**: FastAPI, tegufox_core, tegufox_automation

## 🔧 Development

### Running the GUI
```bash
./tegufox-gui
# or
python tegufox-gui
```

### Running the CLI
```bash
./tegufox-cli profile list
./tegufox-cli api start --port 8420
```

### Importing in Code
```python
# Core functionality
from tegufox_core import ProfileManager, ConsistencyEngine, generate_fleet

# Automation
from tegufox_automation import TegufoxSession, HumanMouse, HumanKeyboard

# CLI (re-exports automation for convenience)
from tegufox_cli import TegufoxSession  # Same as tegufox_automation
```

## 🧪 Testing

```bash
# Test core logic
pytest tests/test_consistency_engine.py
pytest tests/test_profile_manager.py

# Test automation
pytest tests/test_automation_framework.py

# Test API
pytest tests/test_api.py
```

## 📝 Migration Notes

### Old Structure → New Structure

| Old Location | New Location |
|-------------|--------------|
| `consistency_engine.py` | `tegufox_core/consistency_engine.py` |
| `profile_manager.py` | `tegufox_core/profile_manager.py` |
| `tegufox_automation.py` | `tegufox_automation/session.py` |
| `tegufox_mouse.py` | `tegufox_automation/mouse.py` |
| `tegufox_keyboard.py` | `tegufox_automation/keyboard.py` |
| `tegufox_gui.py` | `tegufox_gui/app.py` |
| `tegufox_api.py` | `tegufox_cli/api.py` |

### Import Changes

```python
# OLD
from consistency_engine import ConsistencyEngine
from tegufox_automation import TegufoxSession
from tegufox_mouse import HumanMouse

# NEW
from tegufox_core.consistency_engine import ConsistencyEngine
from tegufox_automation import TegufoxSession, HumanMouse
```

## 🎨 Benefits of New Structure

1. **Clear separation** - Core logic is independent of UI/runtime
2. **Reusable automation** - Can be used from GUI, CLI, or custom scripts
3. **Testable** - Each layer can be tested independently
4. **Maintainable** - Changes to one layer don't affect others
5. **Scalable** - Easy to add new interfaces (web UI, mobile app, etc.)

## 🔮 Future Extensions

- **Web UI** - Add `tegufox_web/` for browser-based interface
- **Mobile** - Add `tegufox_mobile/` for mobile automation
- **Plugins** - Add `tegufox_plugins/` for custom automation scripts
- **Cloud** - Add `tegufox_cloud/` for distributed automation
