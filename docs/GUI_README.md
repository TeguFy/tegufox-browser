# Tegufox GUI - Profile Manager

Modern PyQt6 desktop application for managing Tegufox browser profiles.

## Features

### ✅ Implemented

**Profile Creation:**
- Create single or bulk profiles (1-30 at once)
- Platform templates: eBay Seller, Amazon FBA, Etsy Shop, Generic
- Auto-generated random seeds for canvas/audio fingerprinting
- Configurable browser settings (screen resolution, GPU, user agent, etc.)

**Profile Management:**
- View all profiles in card-based layout
- Click profile cards to view detailed configuration
- Delete profiles with confirmation dialog
- Refresh profile list automatically after creation
- Search functionality (UI ready)

**User Interface:**
- Dark theme (Catppuccin-inspired colors)
- Sidebar navigation with multiple sections
- Responsive layout with scrollable areas
- Professional design matching modern anti-detect browsers

### 📋 Planned

- Edit existing profiles
- Export profiles for use with Camoufox
- Profile groups/folders
- Cloud sync integration
- Task automation UI
- Profile templates marketplace

## Usage

### Launch GUI

```bash
# Activate virtual environment
source venv/bin/activate

# Run GUI
python tegufox_gui.py
```

### Create Profiles

1. Click **"Create"** in the sidebar under PROFILES section
2. Fill in profile details:
   - **Name**: Unique identifier (e.g., `seller-001`)
   - **Platform**: Choose template (eBay, Amazon, Etsy, Generic)
   - **Bulk count**: Use slider to create multiple profiles at once
3. Click **"Create Profile"** button
4. Profiles are saved to the SQLite profile database

### View Profiles

1. Click **"Local"** in the sidebar to view all profiles
2. Click on any profile card to see detailed configuration
3. Use search box to filter profiles (coming soon)

### Delete Profiles

1. Click the 🗑️ icon on any profile card
2. Confirm deletion in the dialog
3. Profile record is permanently removed

## Architecture

### Technology Stack

- **Framework**: PyQt6 (Python 3.14.3)
- **UI Style**: Custom dark theme with Catppuccin colors
- **Data Format**: Database-backed profile records
- **Integration**: Uses `tegufox-config` CLI logic internally

### Project Structure

```
tegufox_gui.py          # Main GUI application
├── DarkPalette         # Color scheme constants
├── PLATFORM_TEMPLATES  # Profile templates (eBay, Amazon, etc.)
├── create_profile_data # Core profile creation logic
│
├── ProfileCard         # Individual profile card widget
├── CreateProfileWidget # Profile creation form
├── ProfilesListWidget  # Profiles list view
└── TegufoxProfileManager # Main window
```

### Data Flow

```
User Input (GUI)
    ↓
CreateProfileWidget.create_profile()
    ↓
create_profile_data() → Generates JSON
    ↓
ProfileDatabase (saved in SQLite)
    ↓
profile_created signal
    ↓
ProfilesListWidget.refresh_profiles()
    ↓
Load and display ProfileCard widgets
```

## Configuration

### Platform Templates

Each platform template includes:

**eBay Seller:**
- Windows 10, NVIDIA GPU
- 1920x1080, 8 cores
- Canvas noise: 0.02

**Amazon FBA:**
- macOS, Apple M1
- 1470x956, 10 cores  
- Canvas noise: 0.015

**Etsy Shop:**
- Windows 11, Generic GPU
- 2560x1440, 12 cores
- Canvas noise: 0.025

**Generic:**
- Windows 10 baseline
- Minimal configuration

### Profile Structure

Profiles are stored as structured records in SQLite and loaded through `ProfileManager`.

## Development

### Testing

```bash
# Test profile creation logic
python test_gui_integration.py

# Test actual GUI workflow
python tegufox_gui.py
# Then manually: Create → View → Delete
```

### Adding New Platform Templates

Edit `PLATFORM_TEMPLATES` in `tegufox_gui.py`:

```python
PLATFORM_TEMPLATES['new-platform'] = {
    'desc': 'Description here',
    'config': {
        'navigator:userAgent': '...',
        'navigator:platform': 'Win32',
        'screen:width': 1920,
        'screen:height': 1080,
        # ... more config keys
    }
}
```

### Customizing Theme

Edit `DarkPalette` class colors:

```python
class DarkPalette:
    BACKGROUND = "#1e1e2e"  # Main background
    ACCENT = "#89b4fa"      # Blue accent
    RED = "#f38ba8"         # Red accent
    # ... more colors
```

## Troubleshooting

**GUI doesn't launch:**
```bash
# Check PyQt6 installation
pip install PyQt6

# Verify Python version
python --version  # Should be 3.10+
```

**Profiles not showing:**
```bash
# Check database exists
ls -la tegufox_core/profiles.db

# Click "Refresh" button in GUI
```

**Font warning on macOS:**
```
# Warning about "SF Pro Display" is harmless
# You can change the font in main():
font = QFont("Arial", 12)  # Use system font
```

## Next Steps

See `ROADMAP.md` for the complete development plan. Current focus:

1. ✅ GUI skeleton and basic navigation
2. ✅ Profile creation integration
3. ✅ Profile viewing and deletion
4. 🔄 Profile editing
5. 📋 Build automation integration
6. 📋 Testing framework UI

## License

Part of Tegufox Browser project - see main README.md
