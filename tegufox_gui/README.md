# Tegufox GUI - Refactored Structure

## Overview
The Tegufox GUI has been refactored from a monolithic 3712-line `app.py` into a modular, maintainable structure.

## New Structure

```
tegufox_gui/
├── __init__.py
├── app.py                      # Main application (203 lines, was 3712)
├── components/                 # Reusable UI components
│   ├── __init__.py
│   ├── profile_card.py        # ProfileCard widget
│   ├── sidebar_button.py      # SidebarButton widget
│   └── stat_card.py           # StatCard widget
├── pages/                      # Application pages
│   ├── __init__.py
│   ├── dashboard_page.py      # Dashboard/Home page
│   ├── profiles_page.py       # Profiles list page
│   ├── create_profile_page.py # Profile creation page
│   ├── sessions_page.py       # Sessions management page
│   └── settings_page.py       # Settings page
└── utils/                      # Utilities and configuration
    ├── __init__.py
    ├── styles.py              # DarkPalette theme colors
    └── config.py              # Platform templates and config logic
```

## Benefits

1. **Modularity**: Each component/page is in its own file
2. **Maintainability**: Easy to find and modify specific features
3. **Reusability**: Components can be imported and reused
4. **Testability**: Individual modules can be tested in isolation
5. **Readability**: Smaller files are easier to understand
6. **Scalability**: Easy to add new pages or components

## File Sizes

- **app.py**: 203 lines (94.5% reduction from 3712 lines)
- **components/**: ~150 lines total across 3 files
- **pages/**: ~2500 lines total across 5 files
- **utils/**: ~150 lines total across 2 files

## Usage

```python
# Import the main application
from tegufox_gui.app import TegufoxProfileManager, main

# Or import specific components
from tegufox_gui.components import ProfileCard, SidebarButton, StatCard
from tegufox_gui.pages import DashboardWidget, ProfilesListWidget
from tegufox_gui.utils import DarkPalette, PLATFORM_TEMPLATES
```

## Running the Application

```bash
# From project root
python3 tegufox_gui/app.py

# Or using the module
python3 -m tegufox_gui.app
```

## Migration Notes

- Original `app.py` backed up to `app.py.backup`
- All functionality preserved
- Import paths updated to use new module structure
- No breaking changes to external API
