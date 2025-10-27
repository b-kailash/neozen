# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NeoZen is a modern, cross-platform interface for Nmap built with Python 3. It offers both a rich desktop GUI (PyQt6) and a browser-based web dashboard (Flask), providing flexibility for different use cases. The project uses a layered architecture with a pure Python core that is GUI-framework agnostic, allowing the same Nmap logic to power different interfaces.

## Development Commands

### Running the Application
```bash
# Ensure virtual environment is activated first
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Run the application
python main.py
```

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Install dependencies
python -m pip install -r requirements.txt
```

### Dependencies

**Core dependencies (always required):**
- python-nmap: XML parsing library for Nmap output
- psutil: Process management for stopping scans and child processes

**Optional dependencies (interface-specific):**
- PyQt6: Desktop GUI framework (`pip install -e ".[desktop]"`)
- Flask + Flask-SocketIO: Web dashboard (`pip install -e ".[web]"`)

**Installation:**
```bash
# Desktop GUI only
pip install -e ".[desktop]"

# Web dashboard only
pip install -e ".[web]"

# Both interfaces
pip install -e ".[all]"
```

## Architecture

NeoZen follows a **layered architecture** that separates core business logic from UI frameworks:

### Layer 1: Pure Python Core (GUI-agnostic)

**Location:** `neozen/core/`

- **scanner_core.py**: `NmapScanner` class - Pure Python threading.Thread implementation
  - Executes Nmap via subprocess
  - Captures live output
  - Parses XML results
  - Uses **callbacks** instead of framework-specific signals
  - No GUI dependencies - can be used standalone

- **profiles.py**: `ProfileManager` - Profile persistence with platform-specific paths
- **models.py**: Data models (currently minimal)

**Key Design:** The core scanner uses callback functions for communication:
```python
scanner = NmapScanner(
    target="192.168.1.1",
    arguments="-sV -T4",
    on_output=lambda text: print(text),
    on_results=lambda results: process(results),
    on_finished=lambda msg, path: cleanup(path),
    on_error=lambda err: handle_error(err)
)
scanner.start()
```

### Layer 2: GUI Adapters (Framework-specific)

**Location:** `neozen/adapters/`

Adapters wrap the core scanner for specific frameworks:

- **qt_scanner.py**: `QtScannerAdapter` - Wraps `NmapScanner` with PyQt6 signals
  - Translates callbacks → PyQt signals
  - Maintains backward compatibility with old `Scanner` API
  - Used by desktop GUI

- **web_scanner.py**: `WebScannerAdapter` - Wraps `NmapScanner` for Flask/SocketIO
  - Translates callbacks → SocketIO events
  - No PyQt6 dependency
  - Used by web dashboard

**Example Qt Adapter:**
```python
from neozen.adapters.qt_scanner import QtScannerAdapter

scanner = QtScannerAdapter(target, arguments)
scanner.scan_output.connect(self.handle_output)  # Qt signal!
scanner.start()
```

### Layer 3: UI Implementations

**Desktop GUI:** `neozen/ui/`
- Uses `QtScannerAdapter`
- PyQt6-based rich desktop application
- Entry point: `main.py`

**Web Dashboard:** `neozen/web/`
- Uses `NmapScanner` directly with custom callbacks
- Flask + SocketIO for real-time updates
- Browser-based interface
- Entry point: `neozen/web/app.py`
- Binds to `0.0.0.0:8080` for network access (configurable in `run_server()`)
- Accessible via localhost or host IP address
- Docker uses `network_mode: host` for direct host network access

### Threading Model

- **Core**: Uses Python's `threading.Thread` for portability
- **Qt Adapter**: Wraps thread with QObject for signal emission
- **Web**: Direct threading with SocketIO event emission
- Process control via subprocess.Popen
- Cleanup via psutil (terminates Nmap and child processes)

### Architecture Benefits

This layered design provides significant advantages:

1. **Separation of Concerns**: Core scanning logic is independent of UI framework
2. **Reduced Dependencies**:
   - Web container: No PyQt6 (~100MB smaller)
   - CLI tool: No GUI dependencies
3. **Flexibility**: Easy to add new interfaces (CLI, API server, mobile)
4. **Testability**: Core logic can be tested without GUI framework
5. **Reusability**: Same scanner core powers all interfaces
6. **Maintainability**: Changes to core don't affect adapters, and vice versa

### Data Flow

**Desktop GUI:**
1. User configures scan in MainWindow (target, profile, arguments)
2. MainWindow creates `QtScannerAdapter` with target and arguments
3. MainWindow connects Qt signals to handler methods
4. Adapter creates `NmapScanner` with callbacks that emit Qt signals
5. Scanner executes Nmap, streams output via callbacks → Qt signals
6. Scanner parses XML results, emits via callbacks → Qt signals
7. MainWindow receives signals and updates UI

**Web Dashboard:**
1. User submits scan via browser
2. Flask endpoint creates `NmapScanner` with custom callbacks
3. Callbacks update global state AND emit SocketIO events
4. Browser receives real-time updates via WebSocket
5. REST API endpoints provide scan status and results

### Results Data Structure

The parsed results dictionary uses this schema:
```python
{
  'host_ip': {
    'hostname': str,
    'state': str,  # 'up', 'down', 'unknown'
    'mac': str,
    'vendor': str,
    'osmatch': [{'name': str, 'accuracy': str, 'osclasses': [...]}],
    'protocols': {
      'tcp'|'udp'|'ip'|'sctp': {
        port_int: {
          'state': str, 'name': str, 'product': str, 'version': str,
          'extrainfo': str, 'cpe': str,
          'script': [{'id': str, 'output': str}]  # NSE port scripts
        }
      }
    },
    'hostscript': [{'id': str, 'output': str}]  # NSE host scripts
  }
}
```

### Profile Management

Profiles are stored in platform-specific locations:
- **Linux**: `~/.config/NeoZen/scan_profiles.json` (XDG_CONFIG_HOME)
- **macOS**: `~/Library/Application Support/NeoZen/scan_profiles.json`
- **Windows**: `%APPDATA%\NeoZen\scan_profiles.json`

Profile format: `{"profile_name": {"target": str, "arguments": str}}`

### Temporary File Handling

Scanner creates temp XML files using tempfile.NamedTemporaryFile with delete=False. Cleanup responsibilities:
- Scanner cleans up its own temp file if stopped before completion
- MainWindow stores `last_scan_xml_path` on successful completion
- MainWindow cleans up previous temp file when starting new scan or on app exit
- User can save temp file to permanent location via File > Save

## Important Implementation Details

### Privilege Detection
MainWindow checks for privileged flags (`-sS`, `-sU`, `-O`, `-A`) and displays a warning in the status bar using `_check_and_warn_privileged_scan()`. This does not prevent execution but alerts users they may need sudo/admin.

### Argument Handling
- Uses `shlex.split()` on Unix/Linux for proper quote handling
- Uses simple `str.split()` on Windows
- Command display uses `shlex.quote()` for safe shell representation
- Scan type combo boxes store Nmap arguments as UserRole data

### Process Termination
The Scanner.stop() method uses psutil to:
1. Find the Nmap parent process and all children (recursive)
2. Terminate children first, then parent
3. Wait up to 2 seconds for graceful termination
4. Kill any remaining processes forcefully
5. Clean up the temp XML file

### UI State Management
`_set_ui_scan_state(scanning: bool)` centralizes enabling/disabling of UI elements during scans. Key behaviors:
- Scan button disabled while scanning
- Stop button enabled only while scanning
- Save action enabled only when last_scan_xml_path exists and no scan is running
- Profile/scan type controls disabled during scan

### Close Event Handling
MainWindow.closeEvent() handles:
1. Prompting to stop running scans
2. Prompting to save unsaved results (with Save/Don't Save/Cancel options)
3. Cleaning up temp files before exit

## Development Phases

The project follows a phased development approach (see README):
- **Phases 1-7**: Core functionality complete (UI, scanning, results display, file operations, advanced features, packaging)
- **Phase 8**: Containerization complete (Docker support for desktop and web)
- **Phase 9**: Web Dashboard complete (browser-based interface)
- **Phase 10** (Refactoring): Architecture refactored to decouple core from GUI frameworks
- **Phase 6**: Still planned - topology view (network map visualization)

## Refactoring (v0.2.0)

In version 0.2.0, the architecture was refactored to separate concerns:

**Before:** Core scanner inherited from `QThread` and used PyQt signals, tightly coupling it to PyQt6.

**After:** Layered architecture with:
- Pure Python core (`NmapScanner`) using callbacks
- Framework-specific adapters (`QtScannerAdapter`, `WebScannerAdapter`)
- UI implementations using appropriate adapters

**Benefits:**
- Web interface no longer requires PyQt6 (~100MB reduction in dependencies)
- Core scanner can be used standalone or in CLI tools
- Easy to add new interfaces without modifying core
- Better testability and maintainability

**Migration:** Existing code using `Scanner` was updated to use `QtScannerAdapter`, which maintains API compatibility.

## Code Style Notes

- Extensive comments explaining logic, especially in scanner core
- Uses f-strings for string formatting
- Type hints are minimal (Python 3.7+ compatible)
- Callback pattern for core, signal/slot for Qt adapter
- Error handling with try/except blocks

## External Dependencies

- **Nmap**: Must be installed separately and available in system PATH
- **Python 3.7+**: Required for Python features used
