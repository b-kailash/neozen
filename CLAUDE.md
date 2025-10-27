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
- Executing command list: ['sudo', 'nmap', '-T4', '-A', '-v', '192.168.1.0/24', '-oX', '/tmp/tmp47vxz6n1.xml']
Joined command: sudo nmap -T4 -A -v 192.168.1.0/24 -oX /tmp/tmp47vxz6n1.xml
------------------------------
sudo: unable to resolve host neozen-web: Name or service not known
Starting Nmap 7.95 ( https://nmap.org ) at 2025-10-27 15:50 UTC
NSE: Loaded 157 scripts for scanning.
NSE: Script Pre-scanning.
Initiating NSE at 15:50
Completed NSE at 15:50, 0.00s elapsed
Initiating NSE at 15:50
Completed NSE at 15:50, 0.00s elapsed
Initiating NSE at 15:50
Completed NSE at 15:50, 0.00s elapsed
Initiating ARP Ping Scan at 15:50
Scanning 255 hosts [1 port/host]
Completed ARP Ping Scan at 15:50, 1.90s elapsed (255 total hosts)
Initiating Parallel DNS resolution of 25 hosts. at 15:50
Completed Parallel DNS resolution of 25 hosts. at 15:50, 0.00s elapsed
Nmap scan report for 192.168.1.0 [host down]
Nmap scan report for 192.168.1.2 [host down]
Nmap scan report for 192.168.1.3 [host down]
Nmap scan report for 192.168.1.6 [host down]
Nmap scan report for 192.168.1.7 [host down]
Nmap scan report for 192.168.1.8 [host down]
Nmap scan report for 192.168.1.9 [host down]
Nmap scan report for 192.168.1.11 [host down]
Nmap scan report for 192.168.1.12 [host down]
Nmap scan report for 192.168.1.13 [host down]
Nmap scan report for 192.168.1.14 [host down]
Nmap scan report for 192.168.1.15 [host down]
Nmap scan report for 192.168.1.16 [host down]
Nmap scan report for 192.168.1.17 [host down]
Nmap scan report for 192.168.1.18 [host down]
Nmap scan report for 192.168.1.19 [host down]
Nmap scan report for 192.168.1.21 [host down]
Nmap scan report for 192.168.1.22 [host down]
Nmap scan report for 192.168.1.23 [host down]
Nmap scan report for 192.168.1.24 [host down]
Nmap scan report for 192.168.1.26 [host down]
Nmap scan report for 192.168.1.27 [host down]
Nmap scan report for 192.168.1.28 [host down]
Nmap scan report for 192.168.1.29 [host down]
Nmap scan report for 192.168.1.30 [host down]
Nmap scan report for 192.168.1.31 [host down]
Nmap scan report for 192.168.1.32 [host down]
Nmap scan report for 192.168.1.33 [host down]
Nmap scan report for 192.168.1.34 [host down]
Nmap scan report for 192.168.1.35 [host down]
Nmap scan report for 192.168.1.36 [host down]
Nmap scan report for 192.168.1.37 [host down]
Nmap scan report for 192.168.1.38 [host down]
Nmap scan report for 192.168.1.39 [host down]
Nmap scan report for 192.168.1.40 [host down]
Nmap scan report for 192.168.1.41 [host down]
Nmap scan report for 192.168.1.42 [host down]
Nmap scan report for 192.168.1.43 [host down]
Nmap scan report for 192.168.1.44 [host down]
Nmap scan report for 192.168.1.45 [host down]
Nmap scan report for 192.168.1.46 [host down]
Nmap scan report for 192.168.1.47 [host down]
Nmap scan report for 192.168.1.48 [host down]
Nmap scan report for 192.168.1.49 [host down]
Nmap scan report for 192.168.1.50 [host down]
Nmap scan report for 192.168.1.51 [host down]
Nmap scan report for 192.168.1.52 [host down]
Nmap scan report for 192.168.1.53 [host down]
Nmap scan report for 192.168.1.54 [host down]
Nmap scan report for 192.168.1.55 [host down]
Nmap scan report for 192.168.1.56 [host down]
Nmap scan report for 192.168.1.57 [host down]
Nmap scan report for 192.168.1.58 [host down]
Nmap scan report for 192.168.1.59 [host down]
Nmap scan report for 192.168.1.60 [host down]
Nmap scan report for 192.168.1.61 [host down]
Nmap scan report for 192.168.1.62 [host down]
Nmap scan report for 192.168.1.63 [host down]
Nmap scan report for 192.168.1.64 [host down]
Nmap scan report for 192.168.1.65 [host down]
Nmap scan report for 192.168.1.66 [host down]
Nmap scan report for 192.168.1.67 [host down]
Nmap scan report for 192.168.1.68 [host down]
Nmap scan report for 192.168.1.69 [host down]
Nmap scan report for 192.168.1.70 [host down]
Nmap scan report for 192.168.1.71 [host down]
Nmap scan report for 192.168.1.72 [host down]
Nmap scan report for 192.168.1.73 [host down]
Nmap scan report for 192.168.1.74 [host down]
Nmap scan report for 192.168.1.75 [host down]
Nmap scan report for 192.168.1.76 [host down]
Nmap scan report for 192.168.1.77 [host down]
Nmap scan report for 192.168.1.78 [host down]
Nmap scan report for 192.168.1.79 [host down]
Nmap scan report for 192.168.1.80 [host down]
Nmap scan report for 192.168.1.81 [host down]
Nmap scan report for 192.168.1.82 [host down]
Nmap scan report for 192.168.1.83 [host down]
Nmap scan report for 192.168.1.85 [host down]
Nmap scan report for 192.168.1.86 [host down]
Nmap scan report for 192.168.1.87 [host down]
Nmap scan report for 192.168.1.88 [host down]
Nmap scan report for 192.168.1.89 [host down]
Nmap scan report for 192.168.1.90 [host down]
Nmap scan report for 192.168.1.91 [host down]
Nmap scan report for 192.168.1.92 [host down]
Nmap scan report for 192.168.1.93 [host down]
Nmap scan report for 192.168.1.94 [host down]
Nmap scan report for 192.168.1.95 [host down]
Nmap scan report for 192.168.1.96 [host down]
Nmap scan report for 192.168.1.97 [host down]
Nmap scan report for 192.168.1.98 [host down]
Nmap scan report for 192.168.1.99 [host down]
Nmap scan report for 192.168.1.101 [host down]
Nmap scan report for 192.168.1.102 [host down]
Nmap scan report for 192.168.1.103 [host down]
Nmap scan report for 192.168.1.104 [host down]
Nmap scan report for 192.168.1.105 [host down]
Nmap scan report for 192.168.1.106 [host down]
Nmap scan report for 192.168.1.107 [host down]
Nmap scan report for 192.168.1.108 [host down]
Nmap scan report for 192.168.1.109 [host down]
Nmap scan report for 192.168.1.110 [host down]
Nmap scan report for 192.168.1.111 [host down]
Nmap scan report for 192.168.1.112 [host down]
Nmap scan report for 192.168.1.113 [host down]
Nmap scan report for 192.168.1.114 [host down]
Nmap scan report for 192.168.1.115 [host down]
Nmap scan report for 192.168.1.116 [host down]
Nmap scan report for 192.168.1.117 [host down]
Nmap scan report for 192.168.1.118 [host down]
Nmap scan report for 192.168.1.119 [host down]
Nmap scan report for 192.168.1.120 [host down]
Nmap scan report for 192.168.1.121 [host down]
Nmap scan report for 192.168.1.122 [host down]
Nmap scan report for 192.168.1.123 [host down]
Nmap scan report for 192.168.1.124 [host down]
Nmap scan report for 192.168.1.125 [host down]
Nmap scan report for 192.168.1.126 [host down]
Nmap scan report for 192.168.1.127 [host down]
Nmap scan report for 192.168.1.128 [host down]
Nmap scan report for 192.168.1.129 [host down]
Nmap scan report for 192.168.1.130 [host down]
Nmap scan report for 192.168.1.131 [host down]
Nmap scan report for 192.168.1.132 [host down]
Nmap scan report for 192.168.1.133 [host down]
Nmap scan report for 192.168.1.134 [host down]
Nmap scan report for 192.168.1.135 [host down]
Nmap scan report for 192.168.1.136 [host down]
Nmap scan report for 192.168.1.137 [host down]
Nmap scan report for 192.168.1.138 [host down]
Nmap scan report for 192.168.1.139 [host down]
Nmap scan report for 192.168.1.140 [host down]
Nmap scan report for 192.168.1.141 [host down]
Nmap scan report for 192.168.1.142 [host down]
Nmap scan report for 192.168.1.143 [host down]
Nmap scan report for 192.168.1.144 [host down]
Nmap scan report for 192.168.1.145 [host down]
Nmap scan report for 192.168.1.146 [host down]
Nmap scan report for 192.168.1.147 [host down]
Nmap scan report for 192.168.1.148 [host down]
Nmap scan report for 192.168.1.149 [host down]
Nmap scan report for 192.168.1.150 [host down]
Nmap scan report for 192.168.1.151 [host down]
Nmap scan report for 192.168.1.152 [host down]
Nmap scan report for 192.168.1.153 [host down]
Nmap scan report for 192.168.1.154 [host down]
Nmap scan report for 192.168.1.155 [host down]
Nmap scan report for 192.168.1.156 [host down]
Nmap scan report for 192.168.1.157 [host down]
Nmap scan report for 192.168.1.158 [host down]
Nmap scan report for 192.168.1.159 [host down]
Nmap scan report for 192.168.1.160 [host down]
Nmap scan report for 192.168.1.161 [host down]
Nmap scan report for 192.168.1.162 [host down]
Nmap scan report for 192.168.1.163 [host down]
Nmap scan report for 192.168.1.164 [host down]
Nmap scan report for 192.168.1.165 [host down]
Nmap scan report for 192.168.1.166 [host down]
Nmap scan report for 192.168.1.168 [host down]
Nmap scan report for 192.168.1.169 [host down]
Nmap scan report for 192.168.1.170 [host down]
Nmap scan report for 192.168.1.171 [host down]
Nmap scan report for 192.168.1.172 [host down]
Nmap scan report for 192.168.1.175 [host down]
Nmap scan report for 192.168.1.177 [host down]
Nmap scan report for 192.168.1.178 [host down]
Nmap scan report for 192.168.1.179 [host down]
Nmap scan report for 192.168.1.180 [host down]
Nmap scan report for 192.168.1.181 [host down]
Nmap scan report for 192.168.1.182 [host down]
Nmap scan report for 192.168.1.183 [host down]
Nmap scan report for 192.168.1.184 [host down]
Nmap scan report for 192.168.1.185 [host down]
Nmap scan report for 192.168.1.186 [host down]
Nmap scan report for 192.168.1.188 [host down]
Nmap scan report for 192.168.1.189 [host down]
Nmap scan report for 192.168.1.191 [host down]
Nmap scan report for 192.168.1.192 [host down]
Nmap scan report for 192.168.1.193 [host down]
Nmap scan report for 192.168.1.195 [host down]
Nmap scan report for 192.168.1.197 [host down]
Nmap scan report for 192.168.1.199 [host down]
Nmap scan report for 192.168.1.200 [host down]
Nmap scan report for 192.168.1.202 [host down]
Nmap scan report for 192.168.1.203 [host down]
Nmap scan report for 192.168.1.204 [host down]
Nmap scan report for 192.168.1.205 [host down]
Nmap scan report for 192.168.1.206 [host down]
Nmap scan report for 192.168.1.207 [host down]
Nmap scan report for 192.168.1.208 [host down]
Nmap scan report for 192.168.1.209 [host down]
Nmap scan report for 192.168.1.210 [host down]
Nmap scan report for 192.168.1.211 [host down]
Nmap scan report for 192.168.1.212 [host down]
Nmap scan report for 192.168.1.213 [host down]
Nmap scan report for 192.168.1.214 [host down]
Nmap scan report for 192.168.1.215 [host down]
Nmap scan report for 192.168.1.216 [host down]
Nmap scan report for 192.168.1.217 [host down]
Nmap scan report for 192.168.1.218 [host down]
Nmap scan report for 192.168.1.219 [host down]
Nmap scan report for 192.168.1.220 [host down]
Nmap scan report for 192.168.1.223 [host down]
Nmap scan report for 192.168.1.224 [host down]
Nmap scan report for 192.168.1.226 [host down]
Nmap scan report for 192.168.1.227 [host down]
Nmap scan report for 192.168.1.228 [host down]
Nmap scan report for 192.168.1.229 [host down]
Nmap scan report for 192.168.1.230 [host down]
Nmap scan report for 192.168.1.231 [host down]
Nmap scan report for 192.168.1.232 [host down]
Nmap scan report for 192.168.1.233 [host down]
Nmap scan report for 192.168.1.234 [host down]
Nmap scan report for 192.168.1.236 [host down]
Nmap scan report for 192.168.1.237 [host down]
Nmap scan report for 192.168.1.238 [host down]
Nmap scan report for 192.168.1.239 [host down]
Nmap scan report for 192.168.1.240 [host down]
Nmap scan report for 192.168.1.241 [host down]
Nmap scan report for 192.168.1.242 [host down]
Nmap scan report for 192.168.1.246 [host down]
Nmap scan report for 192.168.1.248 [host down]
Nmap scan report for 192.168.1.249 [host down]
Nmap scan report for 192.168.1.250 [host down]
Nmap scan report for 192.168.1.251 [host down]
Nmap scan report for 192.168.1.252 [host down]
Nmap scan report for 192.168.1.253 [host down]
Nmap scan report for 192.168.1.254 [host down]
Nmap scan report for 192.168.1.255 [host down]
Initiating SYN Stealth Scan at 15:50
Scanning 25 hosts [1000 ports/host]
Discovered open port 80/tcp on 192.168.1.5
Discovered open port 80/tcp on 192.168.1.10
Discovered open port 80/tcp on 192.168.1.4
Discovered open port 80/tcp on 192.168.1.190
Discovered open port 80/tcp on 192.168.1.1
Discovered open port 80/tcp on 192.168.1.100
Discovered open port 80/tcp on 192.168.1.84
Discovered open port 443/tcp on 192.168.1.100
Discovered open port 22/tcp on 192.168.1.221
Discovered open port 22/tcp on 192.168.1.25
Discovered open port 22/tcp on 192.168.1.190
Discovered open port 22/tcp on 192.168.1.5
Discovered open port 443/tcp on 192.168.1.10
Discovered open port 22/tcp on 192.168.1.243
Discovered open port 443/tcp on 192.168.1.1
Discovered open port 22/tcp on 192.168.1.4
Discovered open port 22/tcp on 192.168.1.100
Discovered open port 22/tcp on 192.168.1.20
Discovered open port 22/tcp on 192.168.1.10
Discovered open port 135/tcp on 192.168.1.222
Discovered open port 135/tcp on 192.168.1.201
Discovered open port 8080/tcp on 192.168.1.174
Discovered open port 8080/tcp on 192.168.1.243
Discovered open port 445/tcp on 192.168.1.100
Discovered open port 139/tcp on 192.168.1.100
Discovered open port 111/tcp on 192.168.1.187
Discovered open port 53/tcp on 192.168.1.5
Discovered open port 111/tcp on 192.168.1.20
Discovered open port 111/tcp on 192.168.1.25
Discovered open port 3389/tcp on 192.168.1.221
Discovered open port 111/tcp on 192.168.1.100
Discovered open port 53/tcp on 192.168.1.100
Discovered open port 135/tcp on 192.168.1.167
Discovered open port 445/tcp on 192.168.1.167
Discovered open port 139/tcp on 192.168.1.167
Discovered open port 8009/tcp on 192.168.1.176
Discovered open port 8009/tcp on 192.168.1.84
Discovered open port 8000/tcp on 192.168.1.190
Discovered open port 8180/tcp on 192.168.1.225
Discovered open port 5357/tcp on 192.168.1.100
Discovered open port 8002/tcp on 192.168.1.174
Discovered open port 5001/tcp on 192.168.1.100
Discovered open port 9080/tcp on 192.168.1.176
Discovered open port 9080/tcp on 192.168.1.84
Discovered open port 5510/tcp on 192.168.1.100
Discovered open port 445/tcp on 192.168.1.201
Discovered open port 445/tcp on 192.168.1.222
Discovered open port 139/tcp on 192.168.1.222
Discovered open port 139/tcp on 192.168.1.201
Discovered open port 3389/tcp on 192.168.1.222
Discovered open port 445/tcp on 192.168.1.1
Discovered open port 81/tcp on 192.168.1.10
Discovered open port 8443/tcp on 192.168.1.84
Discovered open port 4045/tcp on 192.168.1.100
Discovered open port 53/tcp on 192.168.1.1
Increasing send delay for 192.168.1.194 from 0 to 5 due to 17 out of 42 dropped probes since last increase.
Discovered open port 5000/tcp on 192.168.1.100
Discovered open port 3128/tcp on 192.168.1.25
Discovered open port 3128/tcp on 192.168.1.20
Discovered open port 5555/tcp on 192.168.1.176
Increasing send delay for 192.168.1.194 from 5 to 10 due to 11 out of 18 dropped probes since last increase.
Discovered open port 8001/tcp on 192.168.1.174
Discovered open port 3261/tcp on 192.168.1.100
Discovered open port 8008/tcp on 192.168.1.84
Discovered open port 9000/tcp on 192.168.1.84
Discovered open port 7000/tcp on 192.168.1.174
Discovered open port 7000/tcp on 192.168.1.84
Completed SYN Stealth Scan against 192.168.1.198 in 16.99s (24 hosts left)
Completed SYN Stealth Scan against 192.168.1.190 in 17.02s (23 hosts left)
Completed SYN Stealth Scan against 192.168.1.174 in 17.33s (22 hosts left)
Completed SYN Stealth Scan against 192.168.1.4 in 17.51s (21 hosts left)
Completed SYN Stealth Scan against 192.168.1.84 in 18.87s (20 hosts left)
Completed SYN Stealth Scan against 192.168.1.196 in 19.32s (19 hosts left)
Completed SYN Stealth Scan against 192.168.1.5 in 19.36s (18 hosts left)
Completed SYN Stealth Scan against 192.168.1.176 in 19.54s (17 hosts left)
Completed SYN Stealth Scan against 192.168.1.25 in 21.30s (16 hosts left)
Discovered open port 2049/tcp on 192.168.1.100
Completed SYN Stealth Scan against 192.168.1.243 in 24.17s (15 hosts left)
Completed SYN Stealth Scan against 192.168.1.100 in 25.97s (14 hosts left)
Completed SYN Stealth Scan against 192.168.1.10 in 27.20s (13 hosts left)
Completed SYN Stealth Scan against 192.168.1.20 in 27.21s (12 hosts left)
Completed SYN Stealth Scan against 192.168.1.221 in 27.72s (11 hosts left)
Completed SYN Stealth Scan against 192.168.1.225 in 27.72s (10 hosts left)
Completed SYN Stealth Scan against 192.168.1.244 in 35.07s (9 hosts left)
Discovered open port 2179/tcp on 192.168.1.222
Increasing send delay for 192.168.1.187 from 0 to 5 due to max_successful_tryno increase to 5
Discovered open port 49152/tcp on 192.168.1.1
Completed SYN Stealth Scan against 192.168.1.187 in 60.06s (8 hosts left)
Completed SYN Stealth Scan against 192.168.1.201 in 76.62s (7 hosts left)
Completed SYN Stealth Scan against 192.168.1.173 in 78.08s (6 hosts left)
Completed SYN Stealth Scan against 192.168.1.247 in 80.41s (5 hosts left)
Completed SYN Stealth Scan against 192.168.1.245 in 81.02s (4 hosts left)
Completed SYN Stealth Scan against 192.168.1.222 in 83.61s (3 hosts left)
Completed SYN Stealth Scan against 192.168.1.167 in 84.53s (2 hosts left)
Completed SYN Stealth Scan against 192.168.1.1 in 84.74s (1 host left)
Completed SYN Stealth Scan at 15:51, 87.93s elapsed (25000 total ports)
Initiating Service scan at 15:51
Scanning 68 services on 25 hosts
Completed Service scan at 15:54, 165.88s elapsed (68 services on 25 hosts)
Initiating OS detection (try #1) against 25 hosts
Retrying OS detection (try #2) against 11 hosts
Retrying OS detection (try #3) against 80:6d:71:6e:76:22 (192.168.1.176)
WARNING: OS didn't match until try #3
NSE: Script scanning 25 hosts.
Initiating NSE at 15:54
Completed NSE at 15:55, 57.19s elapsed
Initiating NSE at 15:55
Completed NSE at 15:55, 2.67s elapsed
Initiating NSE at 15:55
Completed NSE at 15:55, 0.00s elapsed
Nmap scan report for BKAILASH-HOME.Home (192.168.1.1)
Host is up (0.00061s latency).
Not shown: 991 filtered tcp ports (no-response)
PORT      STATE  SERVICE       VERSION
53/tcp    open   domain        (unknown banner: UNKNOWN)
| fingerprint-strings:
|   DNSVersionBindReqTCP:
|     version
|     bind
|_    UNKNOWN
| dns-nsid:
|_  bind.version: UNKNOWN
80/tcp    open   http          HTTP Server
|_http-title: Did not follow redirect to https://bkailash-home.home/
| http-methods:
|_  Supported Methods: GET POST
| fingerprint-strings:
|   FourOhFourRequest:
|     HTTP/1.0 301 Moved Permanently
|     Location: https:///nice%20ports%2C/Trinity.txt.bak
|     Content-Length: 0
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:53 GMT
|     Server: HTTP Server
|   GenericLines:
|     HTTP/1.0 400 Bad Request
|     Content-Type: text/html
|     Content-Length: 345
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:53 GMT
|     Server: HTTP Server
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>400 Bad Request</title>
|     </head>
|     <body>
|     <h1>400 Bad Request</h1>
|     </body>
|     </html>
|   GetRequest:
|     HTTP/1.0 301 Moved Permanently
|     Location: https:///
|     Content-Length: 0
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:47 GMT
|     Server: HTTP Server
|   HTTPOptions:
|     HTTP/1.0 405 Method Not Allowed
|     Content-Type: text/html
|     Content-Length: 359
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:47 GMT
|     Server: HTTP Server
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>405 Method Not Allowed</title>
|     </head>
|     <body>
|     <h1>405 Method Not Allowed</h1>
|     </body>
|     </html>
|   RTSPRequest:
|     HTTP/1.0 400 Bad Request
|     Content-Type: text/html
|     Content-Length: 345
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:47 GMT
|     Server: HTTP Server
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>400 Bad Request</title>
|     </head>
|     <body>
|     <h1>400 Bad Request</h1>
|     </body>
|_    </html>
|_http-server-header: HTTP Server
135/tcp   closed msrpc
139/tcp   closed netbios-ssn
443/tcp   open   ssl/https     HTTP Server
|_http-server-header: HTTP Server
|_http-title: Gateways
|_ssl-date: TLS randomness does not represent time
| fingerprint-strings:
|   GetRequest:
|     HTTP/1.0 200 OK
|     Content-Type: text/html
|     ETag: "1494724295"
|     Last-Modified: Wed, 22 Jan 2025 21:13:59 GMT
|     Content-Length: 3250
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:54 GMT
|     Server: HTTP Server
|     <!DOCTYPE html><html lang="en"><head>
|     <meta charset="utf-8">
|     <meta http-equiv="X-UA-Compatible" content="IE=edge">
|     <title>Gateways</title>
|     <base href="/" id="baseHref">
|     <script type="text/javascript">
|     initialRegex = /^(.*/gui/?)/i;
|     usethis = window.location.pathname;
|     baseHref = initialRegex.exec(usethis);
|     (baseHref) {
|     usethis = baseHref[1];
|     else {
|     usethis = '/';
|     document.getElementById('baseHref').href = usethis || '/';
|     </script>
|     <script src="js/jquery.min.js"></script>
|   HTTPOptions:
|     HTTP/1.0 405 Method Not Allowed
|     Content-Type: text/html
|     Content-Length: 359
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:59 GMT
|     Server: HTTP Server
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>405 Method Not Allowed</title>
|     </head>
|     <body>
|     <h1>405 Method Not Allowed</h1>
|     </body>
|_    </html>
| http-methods:
|_  Supported Methods: GET POST
| ssl-cert: Subject: commonName=self-signedKey/organizationName=Sagemcom Ca/stateOrProvinceName=Ile-de-France/countryName=FR
| Issuer: commonName=self-signedKey/organizationName=Sagemcom Ca/stateOrProvinceName=Ile-de-France/countryName=FR
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha256WithRSAEncryption
| Not valid before: 2020-11-10T15:41:26
| Not valid after:  2030-11-08T15:41:26
| MD5:   ecb5:0b55:b2c2:a398:b5c2:ba56:893d:25bf
|_SHA-1: f3f6:8796:648e:e25a:a87b:bcb2:96a5:591a:e435:7676
445/tcp   open   microsoft-ds?
| fingerprint-strings:
|   Kerberos:
|     krbtgt
|   SMBProgNeg:
|     SMB@
|     NETWORK PROGRAM 1.0
|_    MICR
9000/tcp  closed cslistener
9090/tcp  closed zeus-admin
49152/tcp open   upnp          Portable SDK for UPnP 1.14.17 (Linux 4.19.294-5.04L.04; UPnP 1.0)
4 services unrecognized despite returning data. If you know the service/version, please submit the following fingerprints at https://nmap.org/cgi-bin/submit.cgi?new-service :
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port53-TCP:V=7.95%I=7%D=10/27%Time=68FF9519%P=x86_64-pc-linux-gnu%r(DNS
SF:VersionBindReqTCP,34,"\x002\0\x06\x85\x80\0\x01\0\x01\0\0\0\0\x07versio
SF:n\x04bind\0\0\x10\0\x03\xc0\x0c\0\x10\0\x03\0\0\0\0\0\x08\x07UNKNOWN");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port80-TCP:V=7.95%I=7%D=10/27%Time=68FF9514%P=x86_64-pc-linux-gnu%r(Get
SF:Request,97,"HTTP/1\.0\x20301\x20Moved\x20Permanently\r\nLocation:\x20ht
SF:tps:///\r\nContent-Length:\x200\r\nConnection:\x20close\r\nDate:\x20Mon
SF:,\x2027\x20Oct\x202025\x2015:51:47\x20GMT\r\nServer:\x20HTTP\x20Server\
SF:r\n\r\n")%r(HTTPOptions,205,"HTTP/1\.0\x20405\x20Method\x20Not\x20Allow
SF:ed\r\nContent-Type:\x20text/html\r\nContent-Length:\x20359\r\nConnectio
SF:n:\x20close\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:47\x20GMT\r\
SF:nServer:\x20HTTP\x20Server\r\n\r\n<\?xml\x20version=\"1\.0\"\x20encodin
SF:g=\"iso-8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD\x20XH
SF:TML\x201\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x20\x20
SF:\"http://www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n<html\
SF:x20xmlns=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x20lang=
SF:\"en\">\n\x20<head>\n\x20\x20<title>405\x20Method\x20Not\x20Allowed</ti
SF:tle>\n\x20</head>\n\x20<body>\n\x20\x20<h1>405\x20Method\x20Not\x20Allo
SF:wed</h1>\n\x20</body>\n</html>\n")%r(RTSPRequest,1F0,"HTTP/1\.0\x20400\
SF:x20Bad\x20Request\r\nContent-Type:\x20text/html\r\nContent-Length:\x203
SF:45\r\nConnection:\x20close\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:
SF:51:47\x20GMT\r\nServer:\x20HTTP\x20Server\r\n\r\n<\?xml\x20version=\"1\
SF:.0\"\x20encoding=\"iso-8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-/
SF:/W3C//DTD\x20XHTML\x201\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\
SF:x20\x20\x20\x20\"http://www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\
SF:.dtd\">\n<html\x20xmlns=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=
SF:\"en\"\x20lang=\"en\">\n\x20<head>\n\x20\x20<title>400\x20Bad\x20Reques
SF:t</title>\n\x20</head>\n\x20<body>\n\x20\x20<h1>400\x20Bad\x20Request</
SF:h1>\n\x20</body>\n</html>\n")%r(FourOhFourRequest,B6,"HTTP/1\.0\x20301\
SF:x20Moved\x20Permanently\r\nLocation:\x20https:///nice%20ports%2C/Trinit
SF:y\.txt\.bak\r\nContent-Length:\x200\r\nConnection:\x20close\r\nDate:\x2
SF:0Mon,\x2027\x20Oct\x202025\x2015:51:53\x20GMT\r\nServer:\x20HTTP\x20Ser
SF:ver\r\n\r\n")%r(GenericLines,1F0,"HTTP/1\.0\x20400\x20Bad\x20Request\r\
SF:nContent-Type:\x20text/html\r\nContent-Length:\x20345\r\nConnection:\x2
SF:0close\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:53\x20GMT\r\nServ
SF:er:\x20HTTP\x20Server\r\n\r\n<\?xml\x20version=\"1\.0\"\x20encoding=\"i
SF:so-8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD\x20XHTML\x
SF:201\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x20\x20\"htt
SF:p://www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n<html\x20xm
SF:lns=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x20lang=\"en\
SF:">\n\x20<head>\n\x20\x20<title>400\x20Bad\x20Request</title>\n\x20</hea
SF:d>\n\x20<body>\n\x20\x20<h1>400\x20Bad\x20Request</h1>\n\x20</body>\n</
SF:html>\n");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port443-TCP:V=7.95%T=SSL%I=7%D=10/27%Time=68FF951F%P=x86_64-pc-linux-gn
SF:u%r(GetRequest,D83,"HTTP/1\.0\x20200\x20OK\r\nContent-Type:\x20text/htm
SF:l\r\nETag:\x20\"1494724295\"\r\nLast-Modified:\x20Wed,\x2022\x20Jan\x20
SF:2025\x2021:13:59\x20GMT\r\nContent-Length:\x203250\r\nConnection:\x20cl
SF:ose\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:54\x20GMT\r\nServer:
SF:\x20HTTP\x20Server\r\n\r\n<!DOCTYPE\x20html><html\x20lang=\"en\"><head>
SF:\n\x20\x20\x20\x20\x20\x20\x20\x20<meta\x20charset=\"utf-8\">\n\x20\x20
SF:\x20\x20\x20\x20\x20\x20<meta\x20http-equiv=\"X-UA-Compatible\"\x20cont
SF:ent=\"IE=edge\">\n\x20\x20\x20\x20\x20\x20\x20\x20<title>Gateways</titl
SF:e>\n\x20\x20\x20\x20\x20\x20\x20\x20<base\x20href=\"/\"\x20id=\"baseHre
SF:f\">\n\x20\x20\x20\x20\x20\x20\x20\x20<script\x20type=\"text/javascript
SF:\">\n\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20var\x20initialRege
SF:x\x20=\x20/\^\(\.\*\\/gui\\/\?\)/i;\n\x20\x20\x20\x20\x20\x20\x20\x20\x
SF:20\x20\x20\x20var\x20usethis\x20=\x20window\.location\.pathname;\n\x20\
SF:x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20var\x20baseHref\x20=\x20init
SF:ialRegex\.exec\(usethis\);\n\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x2
SF:0\x20if\x20\(baseHref\)\x20{\n\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\
SF:x20\x20\x20\x20\x20\x20usethis\x20=\x20baseHref\[1\];\n\x20\x20\x20\x20
SF:\x20\x20\x20\x20\x20\x20\x20\x20}\x20else\x20{\n\x20\x20\x20\x20\x20\x2
SF:0\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20usethis\x20=\x20'/';\n\x20\x20
SF:\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20}\n\x20\x20\x20\x20\x20\x20\x20
SF:\x20\x20\x20\x20\x20document\.getElementById\('baseHref'\)\.href\x20=\x
SF:20usethis\x20\|\|\x20'/';\n\x20\x20\x20\x20\x20\x20\x20\x20</script>\n\
SF:n\x20\x20\x20\x20\x20\x20\x20\x20<script\x20src=\"js/jquery\.min\.js\">
SF:</script>\n\n\x20\x20\x20\x20\x20\x20\x20\x20\n\n\x20\x20\x20\x20\x20\x
SF:20\x20\x20<me")%r(HTTPOptions,205,"HTTP/1\.0\x20405\x20Method\x20Not\x2
SF:0Allowed\r\nContent-Type:\x20text/html\r\nContent-Length:\x20359\r\nCon
SF:nection:\x20close\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:59\x20
SF:GMT\r\nServer:\x20HTTP\x20Server\r\n\r\n<\?xml\x20version=\"1\.0\"\x20e
SF:ncoding=\"iso-8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD
SF:\x20XHTML\x201\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x
SF:20\x20\"http://www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n
SF:<html\x20xmlns=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x2
SF:0lang=\"en\">\n\x20<head>\n\x20\x20<title>405\x20Method\x20Not\x20Allow
SF:ed</title>\n\x20</head>\n\x20<body>\n\x20\x20<h1>405\x20Method\x20Not\x
SF:20Allowed</h1>\n\x20</body>\n</html>\n");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port445-TCP:V=7.95%I=7%D=10/27%Time=68FF9519%P=x86_64-pc-linux-gnu%r(SM
SF:BProgNeg,44,"\0\0\0@\xffSMB@\x0b\0\0\xc0\0\0\0\0\0\x01\0\x01\0\0\0\0\0\
SF:0\0\0\0@\x06\0\0\x01\0\0\x81\0\x02PC\x20NETWORK\x20PROGRAM\x201\.0\0\x0
SF:2MICR")%r(Kerberos,4D,"\0\0\0Ij\x81n0@\0\0\0\x03\x02\0\xc0\x03\x02\0\0\
SF:x01\0\0\0\0\0\0\0\x05\0P\x80\0\x10\xa2\x04\x1b\x02NM\xa3\x170\x15\xa0\x
SF:03\x02\x01\0\xa1\x0e0\x0c\x1b\x06krbtgt\x1b\x02NM\xa5\x11\x18\t\0\0\0\0
SF:\0\0\0\0");
MAC Address: BC:D5:ED:A4:6F:73 (Unknown)
Device type: WAP|general purpose|broadband router|specialized
Running (JUST GUESSING): Linux 2.6.X|2.4.X|5.X|3.X (96%), Asus embedded (91%), Philips embedded (87%)
OS CPE: cpe:/o:linux:linux_kernel:2.6.22 cpe:/o:linux:linux_kernel:2.4 cpe:/o:linux:linux_kernel:5.3 cpe:/o:linux:linux_kernel:2.6 cpe:/o:linux:linux_kernel:2.4.18 cpe:/h:asus:rt-ac66u cpe:/h:asus:rt-n16 cpe:/o:linux:linux_kernel:3.3
Aggressive OS guesses: OpenWrt Kamikaze 7.09 (Linux 2.6.22) (96%), OpenWrt 0.9 - 7.09 (Linux 2.4.30 - 2.4.34) (94%), OpenWrt White Russian 0.9 (Linux 2.4.30) (94%), Linux 5.3 (92%), Linux 2.6.9 - 2.6.21 (91%), Linux 2.4.18 (91%), Asus RT-AC66U router (Linux 2.6) (91%), Asus RT-N16 WAP (Linux 2.6) (90%), Asus RT-N66U WAP (Linux 2.6) (90%), Tomato 1.28 (Linux 2.6.22) (90%)
No exact OS matches for host (test conditions non-ideal).
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=263 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel:4.19.294-5.04l.04

Host script results:
| smb2-security-mode:
|   3:1:1:
|_    Message signing enabled but not required
|_clock-skew: -1s
| smb2-time:
|   date: 2025-10-27T15:54:39
|_  start_date: N/A

TRACEROUTE
HOP RTT     ADDRESS
1   0.61 ms BKAILASH-HOME.Home (192.168.1.1)

Nmap scan report for 44:a5:6e:a2:9a:15 (192.168.1.4)
Host is up (0.00038s latency).
Not shown: 998 closed tcp ports (reset)
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 9.6 (protocol 2.0)
80/tcp open  http
| fingerprint-strings:
|   GetRequest:
|     HTTP/1.0 200 OK
|     Content-Type: text/html
|     Last-Modified: Fri, 14 Mar 2025 18:48:54 GMT
|     Content-Length: 733
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:49 GMT
|     <html>
|     <head>
|     <script type="text/javascript" src="js/fileLoad_v2.js"></script>
|     <script type="text/javascript">
|     function gotoLogin()
|     document.cookie = "testcookie";
|     cookieEnabled = (document.cookie.indexOf("testcookie") != -1) ? true : false;
|     (cookieEnabled == false)
|     alert("Browser does not accept cookies. Please configure your browser to accept cookies in order to access the Web Interface.");
|     else
|     document.cookie = "testcookie; expires=Thu, 01 Jan 1970 00:00:00 GMT";
|     fileVer = (new Date().getTime());
|     "login.html?aj4="+fileVer;
|     '&bj4=' + md5(url.split('?')[1]);
|     window.location.href=url;
|     </script>
|     </head>
|     <body onload="gotoLogin();">
|     </body>
|     </html>
|   HTTPOptions:
|     HTTP/1.0 200 OK
|     Allow: OPTIONS, GET, HEAD, POST
|     Content-Length: 0
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:49 GMT
|   RTSPRequest:
|     HTTP/1.0 400 Bad Request
|     Content-Type: text/html
|     Content-Length: 345
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:49 GMT
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>400 Bad Request</title>
|     </head>
|     <body>
|     <h1>400 Bad Request</h1>
|     </body>
|_    </html>
|_http-title: 400 Bad Request
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port80-TCP:V=7.95%I=7%D=10/27%Time=68FF9514%P=x86_64-pc-linux-gnu%r(Get
SF:Request,384,"HTTP/1\.0\x20200\x20OK\r\nContent-Type:\x20text/html\r\nLa
SF:st-Modified:\x20Fri,\x2014\x20Mar\x202025\x2018:48:54\x20GMT\r\nContent
SF:-Length:\x20733\r\nConnection:\x20close\r\nDate:\x20Mon,\x2027\x20Oct\x
SF:202025\x2015:51:49\x20GMT\r\n\r\n<html>\n<head>\n<script\x20type=\"text
SF:/javascript\"\x20src=\"js/fileLoad_v2\.js\"></script>\n<script\x20type=
SF:\"text/javascript\">\nfunction\x20gotoLogin\(\)\n{\n\x20\x20document\.c
SF:ookie\x20=\x20\"testcookie\";\n\x20\x20cookieEnabled\x20=\x20\(document
SF:\.cookie\.indexOf\(\"testcookie\"\)\x20!=\x20-1\)\x20\?\x20true\x20:\x2
SF:0false;\n\x20\x20if\x20\(cookieEnabled\x20==\x20false\)\n\x20\x20{\n\x2
SF:0\x20\x20\x20alert\(\"Browser\x20does\x20not\x20accept\x20cookies\.\x20
SF:Please\x20configure\x20your\x20browser\x20to\x20accept\x20cookies\x20in
SF:\x20order\x20to\x20access\x20the\x20Web\x20Interface\.\"\);\n\x20\x20}\
SF:n\x20\x20else\n\x20\x20{\n\x20\x20\x20\x20\x20\x20document\.cookie\x20=
SF:\x20\"testcookie;\x20expires=Thu,\x2001\x20Jan\x201970\x2000:00:00\x20G
SF:MT\";\n\x20\x20}\n\n\x20\x20var\x20fileVer\x20=\x20\(new\x20Date\(\)\.g
SF:etTime\(\)\);\n\x20\x20var\x20url\x20=\x20\"login\.html\?aj4=\"\+fileVe
SF:r;\n\x20\x20url\x20=\x20url\x20\+\x20'&bj4='\x20\+\x20md5\(url\.split\(
SF:'\?'\)\[1\]\);\n\x20\x20window\.location\.href=url;\n}\n</script>\n</he
SF:ad>\n<body\x20onload=\"gotoLogin\(\);\">\n</body>\n</html>\n\n")%r(HTTP
SF:Options,7F,"HTTP/1\.0\x20200\x20OK\r\nAllow:\x20OPTIONS,\x20GET,\x20HEA
SF:D,\x20POST\r\nContent-Length:\x200\r\nConnection:\x20close\r\nDate:\x20
SF:Mon,\x2027\x20Oct\x202025\x2015:51:49\x20GMT\r\n\r\n")%r(RTSPRequest,1D
SF:B,"HTTP/1\.0\x20400\x20Bad\x20Request\r\nContent-Type:\x20text/html\r\n
SF:Content-Length:\x20345\r\nConnection:\x20close\r\nDate:\x20Mon,\x2027\x
SF:20Oct\x202025\x2015:51:49\x20GMT\r\n\r\n<\?xml\x20version=\"1\.0\"\x20e
SF:ncoding=\"iso-8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD
SF:\x20XHTML\x201\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x
SF:20\x20\"http://www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n
SF:<html\x20xmlns=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x2
SF:0lang=\"en\">\n\x20<head>\n\x20\x20<title>400\x20Bad\x20Request</title>
SF:\n\x20</head>\n\x20<body>\n\x20\x20<h1>400\x20Bad\x20Request</h1>\n\x20
SF:</body>\n</html>\n");
MAC Address: 44:A5:6E:A2:9A:15 (Netgear)
Device type: switch
Running: Netgear embedded, Linux 3.X
OS CPE: cpe:/o:linux:linux_kernel:3.18.24
OS details: Netgear GS108Tv3, GS110Tv3, or GS308T switch (Linux 3.18.24)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=261 (Good luck!)
IP ID Sequence Generation: All zeros

TRACEROUTE
HOP RTT     ADDRESS
1   0.38 ms 44:a5:6e:a2:9a:15 (192.168.1.4)

Nmap scan report for bc:24:11:ff:01:b2 (192.168.1.5)
Host is up (0.00033s latency).
Not shown: 997 closed tcp ports (reset)
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 9.2p1 Debian 2+deb12u6 (protocol 2.0)
| ssh-hostkey:
|   256 a8:a7:2d:d4:85:a9:f7:37:25:30:ce:a6:a2:7b:76:8f (ECDSA)
|_  256 1a:70:6d:bd:db:c4:11:ce:c7:4b:bd:6e:c3:a2:53:ee (ED25519)
53/tcp open  domain  dnsmasq 2.90+1 (pi-hole)
| dns-nsid:
|_  bind.version: dnsmasq-pi-hole-v2.90+1
80/tcp open  http    lighttpd 1.4.69
|_http-title: 400 Bad Request
|_http-server-header: lighttpd/1.4.69
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
MAC Address: BC:24:11:FF:01:B2 (Proxmox Server Solutions GmbH)
Device type: general purpose|router
Running: Linux 4.X|5.X, MikroTik RouterOS 7.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5 cpe:/o:mikrotik:routeros:7 cpe:/o:linux:linux_kernel:5.6.3
OS details: Linux 4.15 - 5.19, OpenWrt 21.02 (Linux 5.4), MikroTik RouterOS 7.2 - 7.5 (Linux 5.6.3)
Uptime guess: 3.462 days (since Fri Oct 24 04:50:12 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=258 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT     ADDRESS
1   0.33 ms bc:24:11:ff:01:b2 (192.168.1.5)

Nmap scan report for bc:24:11:ce:a4:2f (192.168.1.10)
Host is up (0.00033s latency).
Not shown: 996 closed tcp ports (reset)
PORT    STATE SERVICE   VERSION
22/tcp  open  ssh       OpenSSH 9.2p1 Debian 2+deb12u6 (protocol 2.0)
| ssh-hostkey:
|   256 55:71:c7:ee:53:50:d6:4a:93:18:74:26:f4:41:93:d6 (ECDSA)
|_  256 29:1d:a0:89:44:54:6f:ea:34:73:1d:66:27:fe:95:19 (ED25519)
80/tcp  open  http      OpenResty web app server
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-title: Did not follow redirect to http://192.168.1.10:81
|_http-server-header: openresty
81/tcp  open  http      OpenResty web app server
| http-methods:
|_  Supported Methods: GET HEAD
|_http-server-header: openresty
|_http-favicon: Unknown favicon MD5: 66D6CD2CA92C743089679129FDD51443
|_http-title: Nginx Proxy Manager
443/tcp open  ssl/https openresty
|_http-server-header: openresty
|_http-title: 400 The plain HTTP request was sent to HTTPS port
MAC Address: BC:24:11:CE:A4:2F (Proxmox Server Solutions GmbH)
Device type: general purpose
Running: Linux 4.X|5.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5
OS details: Linux 4.15 - 5.19, OpenWrt 21.02 (Linux 5.4)
Uptime guess: 29.129 days (since Sun Sep 28 12:49:26 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=253 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT     ADDRESS
1   0.33 ms bc:24:11:ce:a4:2f (192.168.1.10)

Nmap scan report for 38:22:e2:1e:51:64 (192.168.1.20)
Host is up (0.000024s latency).
Not shown: 997 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 9.2p1 Debian 2+deb12u7 (protocol 2.0)
| ssh-hostkey:
|   256 da:19:61:e2:35:9f:10:34:6c:c5:d9:11:9d:69:5b:83 (ECDSA)
|_  256 6e:4a:e5:a6:fa:73:2e:40:d0:ff:e2:7e:6c:11:37:5f (ED25519)
111/tcp  open  rpcbind 2-4 (RPC #100000)
| rpcinfo:
|   program version    port/proto  service
|   100000  2,3,4        111/tcp   rpcbind
|   100000  2,3,4        111/udp   rpcbind
|   100000  3,4          111/tcp6  rpcbind
|_  100000  3,4          111/udp6  rpcbind
3128/tcp open  http    Proxmox Virtual Environment REST API 3.0
|_http-title: Site doesn't have a title.
|_http-server-header: pve-api-daemon/3.0
MAC Address: 38:22:E2:1E:51:64 (HP)
Device type: general purpose
Running: Linux 4.X|5.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5
OS details: Linux 4.15 - 5.19
Uptime guess: 30.006 days (since Sat Sep 27 15:47:05 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=258 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT     ADDRESS
1   0.02 ms 38:22:e2:1e:51:64 (192.168.1.20)

Nmap scan report for dc:fe:07:e1:32:41 (192.168.1.25)
Host is up (0.00027s latency).
Not shown: 997 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 9.2p1 Debian 2+deb12u7 (protocol 2.0)
| ssh-hostkey:
|   256 8b:fd:2c:0a:fe:24:d5:ed:60:17:71:c3:10:bc:16:8b (ECDSA)
|_  256 23:6e:66:d1:59:cb:51:be:8c:6d:32:49:28:da:f4:d8 (ED25519)
111/tcp  open  rpcbind 2-4 (RPC #100000)
| rpcinfo:
|   program version    port/proto  service
|   100000  2,3,4        111/tcp   rpcbind
|   100000  2,3,4        111/udp   rpcbind
|   100000  3,4          111/tcp6  rpcbind
|_  100000  3,4          111/udp6  rpcbind
3128/tcp open  http    Proxmox Virtual Environment REST API 3.0
|_http-server-header: pve-api-daemon/3.0
|_http-title: Site doesn't have a title.
MAC Address: DC:FE:07:E1:32:41 (Pegatron)
Device type: general purpose|router
Running: Linux 4.X|5.X, MikroTik RouterOS 7.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5 cpe:/o:mikrotik:routeros:7 cpe:/o:linux:linux_kernel:5.6.3
OS details: Linux 4.15 - 5.19, OpenWrt 21.02 (Linux 5.4), MikroTik RouterOS 7.2 - 7.5 (Linux 5.6.3)
Uptime guess: 45.668 days (since Thu Sep 11 23:53:04 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=261 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT     ADDRESS
1   0.27 ms dc:fe:07:e1:32:41 (192.168.1.25)

Nmap scan report for f8:4e:17:51:be:55 (192.168.1.84)
Host is up (0.00094s latency).
Not shown: 993 closed tcp ports (reset)
PORT     STATE SERVICE         VERSION
80/tcp   open  http            nginx
| http-methods:
|_  Supported Methods: GET HEAD POST
|_http-title: 404 Not Found
7000/tcp open  rtsp            AirTunes rtspd 377.40.00
|_rtsp-methods: ERROR: Script execution failed (use -d to debug)
|_irc-info: Unable to open connection
8008/tcp open  http?
|_http-title: Site doesn't have a title.
8009/tcp open  ssl/ajp13?
|_ssl-date: TLS randomness does not represent time
|_ajp-methods: Failed to get a valid response for the OPTION request
| ssl-cert: Subject: commonName=d0ea8bec-a9e6-2de1-c89e-b0a0c7791163
| Issuer: commonName=d0ea8bec-a9e6-2de1-c89e-b0a0c7791163
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha256WithRSAEncryption
| Not valid before: 2025-10-26T16:32:04
| Not valid after:  2025-10-28T16:32:04
| MD5:   350f:eacb:73e0:8a22:a8c4:d97c:2fc6:327f
|_SHA-1: 9b1c:80fb:9aee:c09a:73ec:8eb6:f664:d410:bb12:46cb
8443/tcp open  ssl/https-alt?
|_http-title: Site doesn't have a title.
| ssl-cert: Subject: commonName=-8550923144965050090/organizationName=Google Inc/stateOrProvinceName=Washington/countryName=US
| Issuer: commonName=Sony TV BRAVIA_VH2 Mediatek MT5835 Cast ICA/organizationName=Google Inc/stateOrProvinceName=Washington/countryName=US
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha256WithRSAEncryption
| Not valid before: 2022-01-15T16:11:35
| Not valid after:  2042-01-15T16:11:35
| MD5:   a65e:f6b3:5d15:4955:d7b5:1030:c1a3:ae62
|_SHA-1: abeb:3ec8:da1e:e8c0:42b8:148a:a007:dc37:5029:b7b0
9000/tcp open  ssl/cslistener?
9080/tcp open  glrpc?
| fingerprint-strings:
|   GetRequest:
|     HTTP/1.0 200 OK
|     Date: Mon, 27 Oct 2025 15:51:45 GMT
|     Server: NRDP/2025.1.7.0
|     Connection: close
|     Cache-Control: no-cache
|     Content-Length: 9
|_    status=ok
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port9080-TCP:V=7.95%I=7%D=10/27%Time=68FF9514%P=x86_64-pc-linux-gnu%r(G
SF:etRequest,99,"HTTP/1\.0\x20200\x20OK\r\nDate:\x20Mon,\x2027\x20Oct\x202
SF:025\x2015:51:45\x20GMT\r\nServer:\x20NRDP/2025\.1\.7\.0\r\nConnection:\
SF:x20close\r\nCache-Control:\x20no-cache\r\nContent-Length:\x209\r\n\r\ns
SF:tatus=ok");
MAC Address: F8:4E:17:51:BE:55 (Sony)
Device type: phone
Running: Google Android 10.X, Linux 4.X
OS CPE: cpe:/o:google:android:10 cpe:/o:linux:linux_kernel:4
OS details: Android 9 - 10 (Linux 4.9 - 4.14)
Uptime guess: 6.908 days (since Mon Oct 20 18:07:33 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=255 (Good luck!)
IP ID Sequence Generation: All zeros

TRACEROUTE
HOP RTT     ADDRESS
1   0.94 ms f8:4e:17:51:be:55 (192.168.1.84)

Nmap scan report for 00:11:32:d0:d9:6f (192.168.1.100)
Host is up (0.00057s latency).
Not shown: 986 closed tcp ports (reset)
PORT     STATE SERVICE       VERSION
22/tcp   open  ssh           OpenSSH 8.2 (protocol 2.0)
| ssh-hostkey:
|   2048 c5:d8:df:a8:f1:84:82:53:2f:46:8d:23:28:f0:e4:87 (RSA)
|   256 0b:c5:87:6c:66:d5:0c:df:f9:af:e5:bf:af:09:e9:a4 (ECDSA)
|_  256 c7:83:5b:26:9d:32:f5:59:20:bb:b1:2b:ee:37:4a:60 (ED25519)
53/tcp   open  domain        (unknown banner: DNSServer)
| fingerprint-strings:
|   DNSVersionBindReqTCP:
|     version
|     bind
|_    DNSServer
| dns-nsid:
|_  bind.version: DNSServer
80/tcp   open  http          nginx
| http-methods:
|_  Supported Methods: GET HEAD
|_http-title: Home Network
111/tcp  open  rpcbind       2-4 (RPC #100000)
| rpcinfo:
|   program version    port/proto  service
|   100003  2,3         2049/udp   nfs
|   100003  2,3         2049/udp6  nfs
|   100003  2,3,4       2049/tcp   nfs
|_  100003  2,3,4       2049/tcp6  nfs
139/tcp  open  netbios-ssn   Samba smbd 4
443/tcp  open  ssl/http      nginx
| ssl-cert: Subject: commonName=bkailash.synology.me
| Subject Alternative Name: DNS:*.bkailash.synology.me, DNS:bkailash.synology.me
| Issuer: commonName=E8/organizationName=Let's Encrypt/countryName=US
| Public Key type: ec
| Public Key bits: 256
| Signature Algorithm: ecdsa-with-SHA384
| Not valid before: 2025-10-06T15:44:00
| Not valid after:  2026-01-04T15:43:59
| MD5:   9e1a:630a:f5fc:acca:8b5d:d67a:1341:7057
|_SHA-1: 2718:11f4:8ebd:1e67:b0ad:6f00:5b92:df53:649a:a3c9
|_ssl-date: TLS randomness does not represent time
|_http-title: Home Network
| http-methods:
|_  Supported Methods: GET HEAD
445/tcp  open  netbios-ssn   Samba smbd 4
2049/tcp open  nfs           2-4 (RPC #100003)
3261/tcp open  iscsi         Synology DSM Snapshot Replication iSCSI LUN
4045/tcp open  nlockmgr      1-4 (RPC #100021)
5000/tcp open  http          nginx
| http-robots.txt: 1 disallowed entry
|_/
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-title: Site doesn't have a title.
5001/tcp open  ssl/http      nginx
|_ssl-date: TLS randomness does not represent time
| http-robots.txt: 1 disallowed entry
|_/
|_http-title: bkailashNAS&nbsp;-&nbsp;Synology&nbsp;NAS
| ssl-cert: Subject: commonName=bkailash.synology.me
| Subject Alternative Name: DNS:*.bkailash.synology.me, DNS:bkailash.synology.me
| Issuer: commonName=E8/organizationName=Let's Encrypt/countryName=US
| Public Key type: ec
| Public Key bits: 256
| Signature Algorithm: ecdsa-with-SHA384
| Not valid before: 2025-10-06T15:44:00
| Not valid after:  2026-01-04T15:43:59
| MD5:   9e1a:630a:f5fc:acca:8b5d:d67a:1341:7057
|_SHA-1: 2718:11f4:8ebd:1e67:b0ad:6f00:5b92:df53:649a:a3c9
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
5357/tcp open  http          nginx
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-title: 502 Bad Gateway
5510/tcp open  secureidprop?
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port53-TCP:V=7.95%I=7%D=10/27%Time=68FF9519%P=x86_64-pc-linux-gnu%r(DNS
SF:VersionBindReqTCP,36,"\x004\0\x06\x85\0\0\x01\0\x01\0\0\0\0\x07version\
SF:x04bind\0\0\x10\0\x03\xc0\x0c\0\x10\0\x03\0\0\0\0\0\n\tDNSServer");
MAC Address: 00:11:32:D0:D9:70 (Synology Incorporated)
Device type: general purpose
Running: Linux 3.X|4.X
OS CPE: cpe:/o:linux:linux_kernel:3 cpe:/o:linux:linux_kernel:4
OS details: Linux 3.2 - 4.14
Uptime guess: 2.090 days (since Sat Oct 25 13:45:35 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=262 (Good luck!)
IP ID Sequence Generation: All zeros

Host script results:
| smb2-time:
|   date: 2025-10-27T15:54:58
|_  start_date: N/A
| nbstat: NetBIOS name: BKAILASHNAS, NetBIOS user: <unknown>, NetBIOS MAC: <unknown> (unknown)
| Names:
|   BKAILASHNAS<00>      Flags: <unique><active>
|   BKAILASHNAS<03>      Flags: <unique><active>
|   BKAILASHNAS<20>      Flags: <unique><active>
|   BKAILASHHOME<00>     Flags: <group><active>
|_  BKAILASHHOME<1e>     Flags: <group><active>
| smb2-security-mode:
|   3:1:1:
|_    Message signing enabled but not required

TRACEROUTE
HOP RTT     ADDRESS
1   0.57 ms 00:11:32:d0:d9:6f (192.168.1.100)

Nmap scan report for Priya-Laptop (192.168.1.167)
Host is up (0.0077s latency).
Not shown: 997 filtered tcp ports (no-response)
PORT    STATE SERVICE       VERSION
135/tcp open  msrpc         Microsoft Windows RPC
139/tcp open  netbios-ssn   Microsoft Windows netbios-ssn
445/tcp open  microsoft-ds?
MAC Address: 9C:B6:D0:91:57:DB (Rivet Networks)
Warning: OSScan results may be unreliable because we could not find at least 1 open and 1 closed port
Device type: general purpose|phone
Running (JUST GUESSING): Microsoft Windows 11|2022|10|2008|Phone (96%)
OS CPE: cpe:/o:microsoft:windows_11 cpe:/o:microsoft:windows_server_2022 cpe:/o:microsoft:windows_10 cpe:/o:microsoft:windows_server_2008::sp1 cpe:/o:microsoft:windows
Aggressive OS guesses: Microsoft Windows 11 21H2 (96%), Microsoft Windows Server 2022 (90%), Microsoft Windows 10 (90%), Microsoft Windows 10 1607 (89%), Microsoft Windows Server 2008 SP1 (87%), Microsoft Windows Phone 7.5 or 8.0 (86%), Microsoft Windows 10 1511 - 1607 (86%)
No exact OS matches for host (test conditions non-ideal).
Uptime guess: 0.809 days (since Sun Oct 26 20:30:42 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=261 (Good luck!)
IP ID Sequence Generation: Incremental
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
| smb2-security-mode:
|   3:1:1:
|_    Message signing enabled but not required
| smb2-time:
|   date: 2025-10-27T15:55:00
|_  start_date: N/A

TRACEROUTE
HOP RTT     ADDRESS
1   7.73 ms Priya-Laptop (192.168.1.167)

Nmap scan report for myHivehub (192.168.1.173)
Host is up (0.0012s latency).
All 1000 scanned ports on myHivehub (192.168.1.173) are in ignored states.
Not shown: 917 filtered tcp ports (no-response), 83 filtered tcp ports (port-unreach)
MAC Address: 00:1C:2B:17:E0:D5 (Alertme.com Limited)
Too many fingerprints match this host to give specific OS details
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   1.16 ms myHivehub (192.168.1.173)

Nmap scan report for Samsung (192.168.1.174)
Host is up (0.019s latency).
Not shown: 996 closed tcp ports (reset)
PORT     STATE SERVICE             VERSION
7000/tcp open  rtsp                AirTunes rtspd 377.40.00
|_rtsp-methods: ERROR: Script execution failed (use -d to debug)
|_irc-info: Unable to open connection
8001/tcp open  vcom-tunnel?
| fingerprint-strings:
|   DNSStatusRequestTCP, DNSVersionBindReqTCP, Help, RPCCheck, SSLSessionReq:
|     HTTP/1.0 403 Forbidden
|     content-type: text/html
|     content-length: 173
|     <html><head><meta charset=utf-8 http-equiv="Content-Language" content="en"/><link rel="stylesheet" type="text/css" href="/error.css"/></head><body><h1>403</h1></body></html>
|   FourOhFourRequest:
|     HTTP/1.0 404 Not Found
|     content-type: application/json; charset=utf-8
|     content-length: 29
|     <html><body>404</body></html>
|   GetRequest:
|     HTTP/1.0 401 Unauthorized
|     content-length: 29
|     <html><body>401</body></html>
|   HTTPOptions, RTSPRequest:
|     HTTP/1.0 200 OK
|     content-type: application/json; charset=utf-8
|     access-control-allow-headers: content-type
|_    content-length: 3
8002/tcp open  ssl/teradataordbms?
| ssl-cert: Subject: commonName=SmartViewSDK/organizationName=SmartViewSDK/countryName=KR
| Subject Alternative Name: IP Address:127.0.0.1
| Issuer: commonName=SmartViewSDK Root Ceritificate Authority/organizationName=SmartViewSDK/countryName=KR
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha256WithRSAEncryption
| Not valid before: 2016-09-21T08:36:31
| Not valid after:  2036-09-21T08:36:31
| MD5:   63a6:649e:c484:50bc:61e5:de02:1702:1064
|_SHA-1: 2d48:b837:dabe:a9e6:7588:ecd8:b809:3529:5656:d10c
| tls-alpn:
|_  http/1.1
|_ssl-date: TLS randomness does not represent time
| fingerprint-strings:
|   DNSStatusRequestTCP, DNSVersionBindReqTCP, Help, RPCCheck, SSLSessionReq:
|     HTTP/1.0 403 Forbidden
|     content-type: text/html
|     content-length: 173
|     <html><head><meta charset=utf-8 http-equiv="Content-Language" content="en"/><link rel="stylesheet" type="text/css" href="/error.css"/></head><body><h1>403</h1></body></html>
|   GetRequest:
|     HTTP/1.0 401 Unauthorized
|     content-length: 29
|     <html><body>401</body></html>
|   HTTPOptions, RTSPRequest:
|     HTTP/1.0 200 OK
|     content-type: application/json; charset=utf-8
|     access-control-allow-headers: content-type
|_    content-length: 3
8080/tcp open  http-proxy          WebServer
|_http-title: 403 Forbidden
|_http-server-header: WebServer
| fingerprint-strings:
|   FourOhFourRequest:
|     HTTP/1.0 404 Not Found
|     Content-Type: text/html
|     Access-Control-Allow-Origin: *
|     Access-Control-Allow-Headers: Content-Type
|     Content-Length: 341
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:53 GMT
|     Server: WebServer
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>404 Not Found</title>
|     </head>
|     <body>
|     <h1>404 Not Found</h1>
|     </body>
|     </html>
|   GetRequest:
|     HTTP/1.0 403 Forbidden
|     Content-Type: text/html
|     Access-Control-Allow-Origin: *
|     Access-Control-Allow-Headers: Content-Type
|     Content-Length: 341
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:53 GMT
|     Server: WebServer
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>403 Forbidden</title>
|     </head>
|     <body>
|     <h1>403 Forbidden</h1>
|     </body>
|     </html>
|   HTTPOptions:
|     HTTP/1.0 200 OK
|     Allow: OPTIONS, GET, HEAD, POST
|     Access-Control-Allow-Origin: *
|     Access-Control-Allow-Headers: Content-Type
|     Content-Length: 0
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:53 GMT
|     Server: WebServer
|   RTSPRequest:
|     HTTP/1.0 400 Bad Request
|     Content-Type: text/html
|     Content-Length: 345
|     Connection: close
|     Date: Mon, 27 Oct 2025 15:51:53 GMT
|     Server: WebServer
|     <?xml version="1.0" encoding="iso-8859-1"?>
|     <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
|     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
|     <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
|     <head>
|     <title>400 Bad Request</title>
|     </head>
|     <body>
|     <h1>400 Bad Request</h1>
|     </body>
|_    </html>
| http-methods:
|_  Supported Methods: OPTIONS GET HEAD POST
3 services unrecognized despite returning data. If you know the service/version, please submit the following fingerprints at https://nmap.org/cgi-bin/submit.cgi?new-service :
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port8001-TCP:V=7.95%I=7%D=10/27%Time=68FF951B%P=x86_64-pc-linux-gnu%r(G
SF:etRequest,4E,"HTTP/1\.0\x20401\x20Unauthorized\r\ncontent-length:\x2029
SF:\r\n\r\n<html><body>401</body></html>")%r(FourOhFourRequest,7A,"HTTP/1\
SF:.0\x20404\x20Not\x20Found\r\ncontent-type:\x20application/json;\x20char
SF:set=utf-8\r\ncontent-length:\x2029\r\n\r\n<html><body>404</body></html>
SF:")%r(HTTPOptions,84,"HTTP/1\.0\x20200\x20OK\r\ncontent-type:\x20applica
SF:tion/json;\x20charset=utf-8\r\naccess-control-allow-headers:\x20content
SF:-type\r\ncontent-length:\x203\r\n\r\n200")%r(RTSPRequest,84,"HTTP/1\.0\
SF:x20200\x20OK\r\ncontent-type:\x20application/json;\x20charset=utf-8\r\n
SF:access-control-allow-headers:\x20content-type\r\ncontent-length:\x203\r
SF:\n\r\n200")%r(RPCCheck,F5,"HTTP/1\.0\x20403\x20Forbidden\r\ncontent-typ
SF:e:\x20text/html\r\ncontent-length:\x20173\r\n\r\n<html><head><meta\x20c
SF:harset=utf-8\x20http-equiv=\"Content-Language\"\x20content=\"en\"/><lin
SF:k\x20rel=\"stylesheet\"\x20type=\"text/css\"\x20href=\"/error\.css\"/><
SF:/head><body><h1>403</h1></body></html>")%r(DNSVersionBindReqTCP,F5,"HTT
SF:P/1\.0\x20403\x20Forbidden\r\ncontent-type:\x20text/html\r\ncontent-len
SF:gth:\x20173\r\n\r\n<html><head><meta\x20charset=utf-8\x20http-equiv=\"C
SF:ontent-Language\"\x20content=\"en\"/><link\x20rel=\"stylesheet\"\x20typ
SF:e=\"text/css\"\x20href=\"/error\.css\"/></head><body><h1>403</h1></body
SF:></html>")%r(DNSStatusRequestTCP,F5,"HTTP/1\.0\x20403\x20Forbidden\r\nc
SF:ontent-type:\x20text/html\r\ncontent-length:\x20173\r\n\r\n<html><head>
SF:<meta\x20charset=utf-8\x20http-equiv=\"Content-Language\"\x20content=\"
SF:en\"/><link\x20rel=\"stylesheet\"\x20type=\"text/css\"\x20href=\"/error
SF:\.css\"/></head><body><h1>403</h1></body></html>")%r(Help,F5,"HTTP/1\.0
SF:\x20403\x20Forbidden\r\ncontent-type:\x20text/html\r\ncontent-length:\x
SF:20173\r\n\r\n<html><head><meta\x20charset=utf-8\x20http-equiv=\"Content
SF:-Language\"\x20content=\"en\"/><link\x20rel=\"stylesheet\"\x20type=\"te
SF:xt/css\"\x20href=\"/error\.css\"/></head><body><h1>403</h1></body></htm
SF:l>")%r(SSLSessionReq,F5,"HTTP/1\.0\x20403\x20Forbidden\r\ncontent-type:
SF:\x20text/html\r\ncontent-length:\x20173\r\n\r\n<html><head><meta\x20cha
SF:rset=utf-8\x20http-equiv=\"Content-Language\"\x20content=\"en\"/><link\
SF:x20rel=\"stylesheet\"\x20type=\"text/css\"\x20href=\"/error\.css\"/></h
SF:ead><body><h1>403</h1></body></html>");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port8002-TCP:V=7.95%T=SSL%I=7%D=10/27%Time=68FF952A%P=x86_64-pc-linux-g
SF:nu%r(GetRequest,4E,"HTTP/1\.0\x20401\x20Unauthorized\r\ncontent-length:
SF:\x2029\r\n\r\n<html><body>401</body></html>")%r(HTTPOptions,84,"HTTP/1\
SF:.0\x20200\x20OK\r\ncontent-type:\x20application/json;\x20charset=utf-8\
SF:r\naccess-control-allow-headers:\x20content-type\r\ncontent-length:\x20
SF:3\r\n\r\n200")%r(RTSPRequest,84,"HTTP/1\.0\x20200\x20OK\r\ncontent-type
SF::\x20application/json;\x20charset=utf-8\r\naccess-control-allow-headers
SF::\x20content-type\r\ncontent-length:\x203\r\n\r\n200")%r(RPCCheck,F5,"H
SF:TTP/1\.0\x20403\x20Forbidden\r\ncontent-type:\x20text/html\r\ncontent-l
SF:ength:\x20173\r\n\r\n<html><head><meta\x20charset=utf-8\x20http-equiv=\
SF:"Content-Language\"\x20content=\"en\"/><link\x20rel=\"stylesheet\"\x20t
SF:ype=\"text/css\"\x20href=\"/error\.css\"/></head><body><h1>403</h1></bo
SF:dy></html>")%r(DNSVersionBindReqTCP,F5,"HTTP/1\.0\x20403\x20Forbidden\r
SF:\ncontent-type:\x20text/html\r\ncontent-length:\x20173\r\n\r\n<html><he
SF:ad><meta\x20charset=utf-8\x20http-equiv=\"Content-Language\"\x20content
SF:=\"en\"/><link\x20rel=\"stylesheet\"\x20type=\"text/css\"\x20href=\"/er
SF:ror\.css\"/></head><body><h1>403</h1></body></html>")%r(DNSStatusReques
SF:tTCP,F5,"HTTP/1\.0\x20403\x20Forbidden\r\ncontent-type:\x20text/html\r\
SF:ncontent-length:\x20173\r\n\r\n<html><head><meta\x20charset=utf-8\x20ht
SF:tp-equiv=\"Content-Language\"\x20content=\"en\"/><link\x20rel=\"stylesh
SF:eet\"\x20type=\"text/css\"\x20href=\"/error\.css\"/></head><body><h1>40
SF:3</h1></body></html>")%r(Help,F5,"HTTP/1\.0\x20403\x20Forbidden\r\ncont
SF:ent-type:\x20text/html\r\ncontent-length:\x20173\r\n\r\n<html><head><me
SF:ta\x20charset=utf-8\x20http-equiv=\"Content-Language\"\x20content=\"en\
SF:"/><link\x20rel=\"stylesheet\"\x20type=\"text/css\"\x20href=\"/error\.c
SF:ss\"/></head><body><h1>403</h1></body></html>")%r(SSLSessionReq,F5,"HTT
SF:P/1\.0\x20403\x20Forbidden\r\ncontent-type:\x20text/html\r\ncontent-len
SF:gth:\x20173\r\n\r\n<html><head><meta\x20charset=utf-8\x20http-equiv=\"C
SF:ontent-Language\"\x20content=\"en\"/><link\x20rel=\"stylesheet\"\x20typ
SF:e=\"text/css\"\x20href=\"/error\.css\"/></head><body><h1>403</h1></body
SF:></html>");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port8080-TCP:V=7.95%I=7%D=10/27%Time=68FF951A%P=x86_64-pc-linux-gnu%r(G
SF:etRequest,234,"HTTP/1\.0\x20403\x20Forbidden\r\nContent-Type:\x20text/h
SF:tml\r\nAccess-Control-Allow-Origin:\x20\*\r\nAccess-Control-Allow-Heade
SF:rs:\x20Content-Type\r\nContent-Length:\x20341\r\nConnection:\x20close\r
SF:\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:53\x20GMT\r\nServer:\x20W
SF:ebServer\r\n\r\n<\?xml\x20version=\"1\.0\"\x20encoding=\"iso-8859-1\"\?
SF:>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD\x20XHTML\x201\.0\x20Tra
SF:nsitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x20\x20\"http://www\.w3\.
SF:org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n<html\x20xmlns=\"http://
SF:www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x20lang=\"en\">\n\x20<head
SF:>\n\x20\x20<title>403\x20Forbidden</title>\n\x20</head>\n\x20<body>\n\x
SF:20\x20<h1>403\x20Forbidden</h1>\n\x20</body>\n</html>\n")%r(HTTPOptions
SF:,DE,"HTTP/1\.0\x20200\x20OK\r\nAllow:\x20OPTIONS,\x20GET,\x20HEAD,\x20P
SF:OST\r\nAccess-Control-Allow-Origin:\x20\*\r\nAccess-Control-Allow-Heade
SF:rs:\x20Content-Type\r\nContent-Length:\x200\r\nConnection:\x20close\r\n
SF:Date:\x20Mon,\x2027\x20Oct\x202025\x2015:51:53\x20GMT\r\nServer:\x20Web
SF:Server\r\n\r\n")%r(RTSPRequest,1EE,"HTTP/1\.0\x20400\x20Bad\x20Request\
SF:r\nContent-Type:\x20text/html\r\nContent-Length:\x20345\r\nConnection:\
SF:x20close\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:53\x20GMT\r\nSe
SF:rver:\x20WebServer\r\n\r\n<\?xml\x20version=\"1\.0\"\x20encoding=\"iso-
SF:8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD\x20XHTML\x201
SF:\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x20\x20\"http:/
SF:/www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n<html\x20xmlns
SF:=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x20lang=\"en\">\
SF:n\x20<head>\n\x20\x20<title>400\x20Bad\x20Request</title>\n\x20</head>\
SF:n\x20<body>\n\x20\x20<h1>400\x20Bad\x20Request</h1>\n\x20</body>\n</htm
SF:l>\n")%r(FourOhFourRequest,234,"HTTP/1\.0\x20404\x20Not\x20Found\r\nCon
SF:tent-Type:\x20text/html\r\nAccess-Control-Allow-Origin:\x20\*\r\nAccess
SF:-Control-Allow-Headers:\x20Content-Type\r\nContent-Length:\x20341\r\nCo
SF:nnection:\x20close\r\nDate:\x20Mon,\x2027\x20Oct\x202025\x2015:51:53\x2
SF:0GMT\r\nServer:\x20WebServer\r\n\r\n<\?xml\x20version=\"1\.0\"\x20encod
SF:ing=\"iso-8859-1\"\?>\n<!DOCTYPE\x20html\x20PUBLIC\x20\"-//W3C//DTD\x20
SF:XHTML\x201\.0\x20Transitional//EN\"\n\x20\x20\x20\x20\x20\x20\x20\x20\x
SF:20\"http://www\.w3\.org/TR/xhtml1/DTD/xhtml1-transitional\.dtd\">\n<htm
SF:l\x20xmlns=\"http://www\.w3\.org/1999/xhtml\"\x20xml:lang=\"en\"\x20lan
SF:g=\"en\">\n\x20<head>\n\x20\x20<title>404\x20Not\x20Found</title>\n\x20
SF:</head>\n\x20<body>\n\x20\x20<h1>404\x20Not\x20Found</h1>\n\x20</body>\
SF:n</html>\n");
MAC Address: 04:B9:E3:55:EF:AE (Samsung Electronics)
Device type: general purpose|router
Running: Linux 4.X|5.X, MikroTik RouterOS 7.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5 cpe:/o:mikrotik:routeros:7 cpe:/o:linux:linux_kernel:5.6.3
OS details: Linux 4.15 - 5.19, OpenWrt 21.02 (Linux 5.4), MikroTik RouterOS 7.2 - 7.5 (Linux 5.6.3)
Uptime guess: 15.868 days (since Sat Oct 11 19:05:18 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=260 (Good luck!)
IP ID Sequence Generation: All zeros

TRACEROUTE
HOP RTT      ADDRESS
1   18.76 ms Samsung (192.168.1.174)

Nmap scan report for 80:6d:71:6e:76:22 (192.168.1.176)
Host is up (0.010s latency).
Not shown: 997 closed tcp ports (reset)
PORT     STATE SERVICE    VERSION
5555/tcp open  adb        Android Debug Bridge (token auth required)
8009/tcp open  tcpwrapped
|_ajp-methods: Failed to get a valid response for the OPTION request
9080/tcp open  glrpc?
| fingerprint-strings:
|   FourOhFourRequest:
|     HTTP/1.0 200 OK
|     Date: Mon, 27 Oct 2025 15:52:43 GMT
|     Server: NRDP/2025.1.7.0
|     Connection: close
|     Cache-Control: no-cache
|     Content-Length: 9
|     status=ok
|   GetRequest:
|     HTTP/1.0 200 OK
|     Date: Mon, 27 Oct 2025 15:51:57 GMT
|     Server: NRDP/2025.1.7.0
|     Connection: close
|     Cache-Control: no-cache
|     Content-Length: 9
|_    status=ok
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port9080-TCP:V=7.95%I=7%D=10/27%Time=68FF951E%P=x86_64-pc-linux-gnu%r(G
SF:etRequest,99,"HTTP/1\.0\x20200\x20OK\r\nDate:\x20Mon,\x2027\x20Oct\x202
SF:025\x2015:51:57\x20GMT\r\nServer:\x20NRDP/2025\.1\.7\.0\r\nConnection:\
SF:x20close\r\nCache-Control:\x20no-cache\r\nContent-Length:\x209\r\n\r\ns
SF:tatus=ok")%r(FourOhFourRequest,99,"HTTP/1\.0\x20200\x20OK\r\nDate:\x20M
SF:on,\x2027\x20Oct\x202025\x2015:52:43\x20GMT\r\nServer:\x20NRDP/2025\.1\
SF:.7\.0\r\nConnection:\x20close\r\nCache-Control:\x20no-cache\r\nContent-
SF:Length:\x209\r\n\r\nstatus=ok");
MAC Address: 80:6D:71:6E:76:22 (Amazon Technologies)
Device type: general purpose
Running: Google Android 10.X, Linux 4.X
OS CPE: cpe:/o:google:android:10 cpe:/o:linux:linux_kernel:4.14
OS details: Android 10 - 11 (Linux 4.14)
Uptime guess: 30.771 days (since Fri Sep 26 21:25:50 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=251 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Android; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT      ADDRESS
1   10.09 ms 80:6d:71:6e:76:22 (192.168.1.176)

Nmap scan report for 02:87:d3:5d:f2:0f (192.168.1.187)
Host is up (0.00061s latency).
Not shown: 999 closed tcp ports (reset)
PORT    STATE SERVICE VERSION
111/tcp open  rpcbind 2-4 (RPC #100000)
| rpcinfo:
|   program version    port/proto  service
|   100000  2,3,4        111/tcp   rpcbind
|   100000  2,3,4        111/udp   rpcbind
|   100000  3,4          111/tcp6  rpcbind
|_  100000  3,4          111/udp6  rpcbind
MAC Address: 90:A8:22:5B:3A:8F (Amazon Technologies)
Device type: general purpose|router
Running: Linux 4.X|5.X|6.X, MikroTik RouterOS 7.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5 cpe:/o:linux:linux_kernel:6.0 cpe:/o:mikrotik:routeros:7 cpe:/o:linux:linux_kernel:5.6.3
OS details: Linux 4.15 - 5.19, Linux 5.4 - 5.10, OpenWrt 21.02 (Linux 5.4), Linux 6.0, MikroTik RouterOS 7.2 - 7.5 (Linux 5.6.3)
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   0.61 ms 02:87:d3:5d:f2:0f (192.168.1.187)

Nmap scan report for 192.168.1.190
Host is up (0.00027s latency).
Not shown: 997 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 9.2p1 Debian 2+deb12u7 (protocol 2.0)
| ssh-hostkey:
|   256 3f:56:70:93:c6:ac:37:26:f1:0a:62:c5:cc:3c:84:05 (ECDSA)
|_  256 9b:25:6f:0a:b7:71:4e:ab:d3:00:9a:81:6b:d7:b9:23 (ED25519)
80/tcp   open  http    Apache httpd 2.4.65 ((Debian))
|_http-server-header: Apache/2.4.65 (Debian)
| http-methods:
|_  Supported Methods: HEAD GET POST OPTIONS
|_http-title: Apache2 Debian Default Page: It works
8000/tcp open  http    Uvicorn
|_http-server-header: uvicorn
| http-title:                 Paperless-ngx sign in
|_Requested resource was /accounts/login/?next=/
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-favicon: Unknown favicon MD5: 32A136901323F2B2EB12D529E10BF064
|_http-trane-info: Problem with XML parsing of /evox/about
MAC Address: BC:24:11:71:EE:36 (Proxmox Server Solutions GmbH)
Device type: general purpose
Running: Linux 4.X|5.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5
OS details: Linux 4.15 - 5.19
Uptime guess: 16.274 days (since Sat Oct 11 09:21:38 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=251 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT     ADDRESS
1   0.27 ms 192.168.1.190

Nmap scan report for 5a:8e:ef:81:fc:a8 (192.168.1.194)
Host is up (0.037s latency).
Not shown: 998 closed tcp ports (reset)
PORT     STATE    SERVICE VERSION
7/tcp    filtered echo
9080/tcp filtered glrpc
MAC Address: 5A:8E:EF:81:FC:A8 (Unknown)
Warning: OSScan results may be unreliable because we could not find at least 1 open and 1 closed port
Aggressive OS guesses: Barracuda 340 load balancer (97%), Aruba IAP-93 WAP (96%), Aruba Instant WAP (96%), Linux 2.6.32 (96%), Linksys RV042 router (96%), Linux 2.6.18 - 2.6.24 (96%), Linux 2.6.35 (96%), Nokia N900 mobile phone (Linux 2.6.28) (96%), OpenWrt (Linux 2.6.32) (96%), Linux 5.11 (96%)
No exact OS matches for host (test conditions non-ideal).
Network Distance: 1 hop

TRACEROUTE
HOP RTT      ADDRESS
1   37.18 ms 5a:8e:ef:81:fc:a8 (192.168.1.194)

Nmap scan report for Pixel-10-Pro (192.168.1.196)
Host is up (0.0060s latency).
All 1000 scanned ports on Pixel-10-Pro (192.168.1.196) are in ignored states.
Not shown: 1000 closed tcp ports (reset)
MAC Address: 3A:91:FE:D3:3B:3A (Unknown)
Too many fingerprints match this host to give specific OS details
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   5.98 ms Pixel-10-Pro (192.168.1.196)

Nmap scan report for Pixel-9-Pro (192.168.1.198)
Host is up (0.0097s latency).
All 1000 scanned ports on Pixel-9-Pro (192.168.1.198) are in ignored states.
Not shown: 1000 closed tcp ports (reset)
MAC Address: FE:51:2F:46:A7:DE (Unknown)
Too many fingerprints match this host to give specific OS details
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   9.72 ms Pixel-9-Pro (192.168.1.198)

Nmap scan report for PriYaShamitaBala (192.168.1.201)
Host is up (0.00068s latency).
Not shown: 997 filtered tcp ports (no-response)
PORT    STATE SERVICE       VERSION
135/tcp open  msrpc         Microsoft Windows RPC
139/tcp open  netbios-ssn   Microsoft Windows netbios-ssn
445/tcp open  microsoft-ds?
MAC Address: 68:F7:28:D8:74:0C (LCFC(HeFei) Electronics Technology)
Warning: OSScan results may be unreliable because we could not find at least 1 open and 1 closed port
Device type: general purpose|phone|specialized
Running (JUST GUESSING): Microsoft Windows 11|10|2022|2008|Phone|7 (96%)
OS CPE: cpe:/o:microsoft:windows_11 cpe:/o:microsoft:windows_10 cpe:/o:microsoft:windows_server_2022 cpe:/o:microsoft:windows_server_2008::sp1 cpe:/o:microsoft:windows cpe:/o:microsoft:windows_7
Aggressive OS guesses: Microsoft Windows 11 21H2 (96%), Microsoft Windows 10 (91%), Microsoft Windows 10 1607 (91%), Microsoft Windows Server 2022 (90%), Microsoft Windows Server 2008 SP1 (88%), Microsoft Windows Phone 7.5 or 8.0 (88%), Microsoft Windows Embedded Standard 7 (87%), Microsoft Windows 10 1511 - 1607 (86%)
No exact OS matches for host (test conditions non-ideal).
Uptime guess: 3.430 days (since Fri Oct 24 05:36:25 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=248 (Good luck!)
IP ID Sequence Generation: Incremental
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
| smb2-time:
|   date: 2025-10-27T15:54:59
|_  start_date: N/A
| nbstat: NetBIOS name: PRIYASHAMITABAL, NetBIOS user: <unknown>, NetBIOS MAC: 68:f7:28:d8:74:0c (LCFC(HeFei) Electronics Technology)
| Names:
|   PRIYASHAMITABAL<20>  Flags: <unique><active>
|   PRIYASHAMITABAL<00>  Flags: <unique><active>
|_  BKAILASHHOME<00>     Flags: <group><active>
| smb2-security-mode:
|   3:1:1:
|_    Message signing enabled and required

TRACEROUTE
HOP RTT     ADDRESS
1   0.68 ms PriYaShamitaBala (192.168.1.201)

Nmap scan report for Debian-WA (192.168.1.221)
Host is up (0.00023s latency).
Not shown: 998 closed tcp ports (reset)
PORT     STATE SERVICE       VERSION
22/tcp   open  ssh           OpenSSH 10.0p2 Debian 7 (protocol 2.0)
3389/tcp open  ms-wbt-server Microsoft Terminal Service
MAC Address: BC:24:11:7D:B9:EC (Proxmox Server Solutions GmbH)
Device type: general purpose|router
Running: Linux 4.X|5.X, MikroTik RouterOS 7.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5 cpe:/o:mikrotik:routeros:7 cpe:/o:linux:linux_kernel:5.6.3
OS details: Linux 4.15 - 5.19, OpenWrt 21.02 (Linux 5.4), MikroTik RouterOS 7.2 - 7.5 (Linux 5.6.3)
Uptime guess: 48.684 days (since Mon Sep  8 23:31:22 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=257 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OSs: Linux, Windows; CPE: cpe:/o:linux:linux_kernel, cpe:/o:microsoft:windows

TRACEROUTE
HOP RTT     ADDRESS
1   0.23 ms Debian-WA (192.168.1.221)

Nmap scan report for c8:5a:cf:ad:ec:dd (192.168.1.222)
Host is up (0.00070s latency).
Not shown: 995 filtered tcp ports (no-response)
PORT     STATE SERVICE       VERSION
135/tcp  open  msrpc         Microsoft Windows RPC
139/tcp  open  netbios-ssn   Microsoft Windows netbios-ssn
445/tcp  open  microsoft-ds?
2179/tcp open  vmrdp?
3389/tcp open  ms-wbt-server
|_ssl-date: TLS randomness does not represent time
| ssl-cert: Subject: commonName=HP-Mini-for-AI
| Issuer: commonName=HP-Mini-for-AI
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha256WithRSAEncryption
| Not valid before: 2025-09-25T09:59:35
| Not valid after:  2026-03-27T09:59:35
| MD5:   d54d:bb41:3bcb:328b:97f6:8fc8:6799:042c
|_SHA-1: 7f42:51a9:a4c1:ac72:f96d:6dff:299d:0eb4:c4a5:8c6f
| rdp-ntlm-info:
|   Target_Name: HP-MINI-FOR-AI
|   NetBIOS_Domain_Name: HP-MINI-FOR-AI
|   NetBIOS_Computer_Name: HP-MINI-FOR-AI
|   DNS_Domain_Name: HP-Mini-for-AI
|   DNS_Computer_Name: HP-Mini-for-AI
|   Product_Version: 10.0.26100
|_  System_Time: 2025-10-27T15:54:42+00:00
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port3389-TCP:V=7.95%I=7%D=10/27%Time=68FF9529%P=x86_64-pc-linux-gnu%r(T
SF:erminalServerCookie,13,"\x03\0\0\x13\x0e\xd0\0\0\x124\0\x02/\x08\0\x02\
SF:0\0\0");
MAC Address: C8:5A:CF:AD:EC:DD (HP)
Warning: OSScan results may be unreliable because we could not find at least 1 open and 1 closed port
Device type: general purpose|phone|specialized
Running (JUST GUESSING): Microsoft Windows 11|10|2022|2008|Phone|7 (96%)
OS CPE: cpe:/o:microsoft:windows_11 cpe:/o:microsoft:windows_10 cpe:/o:microsoft:windows_server_2022 cpe:/o:microsoft:windows_server_2008::sp1 cpe:/o:microsoft:windows cpe:/o:microsoft:windows_7
Aggressive OS guesses: Microsoft Windows 11 21H2 (96%), Microsoft Windows 10 (91%), Microsoft Windows 10 1607 (91%), Microsoft Windows Server 2022 (90%), Microsoft Windows Server 2008 SP1 (88%), Microsoft Windows Phone 7.5 or 8.0 (88%), Microsoft Windows Embedded Standard 7 (87%), Microsoft Windows 10 1511 - 1607 (86%)
No exact OS matches for host (test conditions non-ideal).
Uptime guess: 2.069 days (since Sat Oct 25 14:16:14 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=264 (Good luck!)
IP ID Sequence Generation: Incremental
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
| nbstat: NetBIOS name: HP-MINI-FOR-AI, NetBIOS user: <unknown>, NetBIOS MAC: c8:5a:cf:ad:ec:dd (HP)
| Names:
|   HP-MINI-FOR-AI<20>   Flags: <unique><active>
|   WORKGROUP<00>        Flags: <group><active>
|_  HP-MINI-FOR-AI<00>   Flags: <unique><active>
| smb2-security-mode:
|   3:1:1:
|_    Message signing enabled and required
| smb2-time:
|   date: 2025-10-27T15:55:00
|_  start_date: N/A

TRACEROUTE
HOP RTT     ADDRESS
1   0.70 ms c8:5a:cf:ad:ec:dd (192.168.1.222)

Nmap scan report for bkailashmac5020 (192.168.1.225)
Host is up (0.00096s latency).
Not shown: 999 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
8180/tcp open  http    McAfee Agent Common Services httpd
| http-methods:
|_  Supported Methods: HEAD POST OPTIONS
MAC Address: 3C:E1:A1:B7:3E:A8 (Universal Global Scientific Industrial)
Device type: general purpose
Running: Apple macOS 11.X|12.X|13.X
OS CPE: cpe:/o:apple:mac_os_x:11 cpe:/o:apple:mac_os_x:12 cpe:/o:apple:mac_os_x:13
OS details: Apple macOS 11 (Big Sur) - 13 (Ventura) or iOS 16 (Darwin 20.6.0 - 22.4.0)
Uptime guess: 0.001 days (since Mon Oct 27 15:54:28 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=254 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

TRACEROUTE
HOP RTT     ADDRESS
1   0.96 ms bkailashmac5020 (192.168.1.225)

Nmap scan report for MyRoute (192.168.1.243)
Host is up (0.00036s latency).
Not shown: 998 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 9.2p1 Debian 2+deb12u6 (protocol 2.0)
| ssh-hostkey:
|   256 a2:b5:d2:33:8f:34:1d:e4:7d:bf:37:11:7e:31:6e:38 (ECDSA)
|_  256 81:52:95:a6:d9:3e:bd:5b:20:8d:58:7b:05:c5:cd:bd (ED25519)
8080/tcp open  http    Node.js Express framework
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-title: scanservjs
|_http-open-proxy: Proxy might be redirecting requests
MAC Address: BC:24:11:8E:9B:52 (Proxmox Server Solutions GmbH)
Device type: general purpose|router
Running: Linux 4.X|5.X, MikroTik RouterOS 7.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5 cpe:/o:mikrotik:routeros:7 cpe:/o:linux:linux_kernel:5.6.3
OS details: Linux 4.15 - 5.19, OpenWrt 21.02 (Linux 5.4), MikroTik RouterOS 7.2 - 7.5 (Linux 5.6.3)
Uptime guess: 19.517 days (since Wed Oct  8 03:31:45 2025)
Network Distance: 1 hop
TCP Sequence Prediction: Difficulty=261 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE
HOP RTT     ADDRESS
1   0.36 ms MyRoute (192.168.1.243)

Nmap scan report for GW-B072BF27A0B5 (192.168.1.244)
Host is up (0.00025s latency).
All 1000 scanned ports on GW-B072BF27A0B5 (192.168.1.244) are in ignored states.
Not shown: 1000 closed tcp ports (reset)
MAC Address: B0:72:BF:27:A0:B5 (Murata Manufacturing)
Warning: OSScan results may be unreliable because we could not find at least 1 open and 1 closed port
Device type: specialized
Running: Honeywell embedded, IKEA embedded
OS CPE: cpe:/h:ikea:tradfri
OS details: Honeywell T5+ or T6 Thermostat, IKEA Tradfri Zigbee gateway
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   0.25 ms GW-B072BF27A0B5 (192.168.1.244)

Nmap scan report for Security_System (192.168.1.245)
Host is up (0.0062s latency).
All 1000 scanned ports on Security_System (192.168.1.245) are in ignored states.
Not shown: 1000 filtered tcp ports (no-response)
MAC Address: 00:1F:08:09:76:24 (Risco)
Too many fingerprints match this host to give specific OS details
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   6.17 ms Security_System (192.168.1.245)

Nmap scan report for MEDLAP19 (192.168.1.247)
Host is up (0.0019s latency).
All 1000 scanned ports on MEDLAP19 (192.168.1.247) are in ignored states.
Not shown: 1000 filtered tcp ports (no-response)
MAC Address: C0:25:A5:76:3C:22 (Dell)
Too many fingerprints match this host to give specific OS details
Network Distance: 1 hop

TRACEROUTE
HOP RTT     ADDRESS
1   1.92 ms MEDLAP19 (192.168.1.247)

Initiating SYN Stealth Scan at 15:55
Scanning CT235.bkailashhome (192.168.1.235) [1000 ports]
Discovered open port 22/tcp on 192.168.1.235
Discovered open port 8080/tcp on 192.168.1.235
Completed SYN Stealth Scan at 15:55, 0.03s elapsed (1000 total ports)
Initiating Service scan at 15:55
Scanning 2 services on CT235.bkailashhome (192.168.1.235)
Completed Service scan at 15:55, 6.01s elapsed (2 services on 1 host)
Initiating OS detection (try #1) against CT235.bkailashhome (192.168.1.235)
NSE: Script scanning 192.168.1.235.
Initiating NSE at 15:55
Completed NSE at 15:55, 0.26s elapsed
Initiating NSE at 15:55
Completed NSE at 15:55, 0.01s elapsed
Initiating NSE at 15:55
Completed NSE at 15:55, 0.00s elapsed
Nmap scan report for CT235.bkailashhome (192.168.1.235)
Host is up (0.000034s latency).
Not shown: 998 closed tcp ports (reset)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 9.2p1 Debian 2+deb12u7 (protocol 2.0)
| ssh-hostkey:
|   256 02:4e:94:0e:57:31:9d:45:8d:7f:4c:c4:48:32:bb:6a (ECDSA)
|_  256 08:d2:cc:54:ba:0e:8a:12:94:02:79:cc:5f:71:a1:ab (ED25519)
8080/tcp open  http    Werkzeug httpd 3.1.3 (Python 3.11.14)
| http-methods:
|_  Supported Methods: GET OPTIONS HEAD
|_http-server-header: Werkzeug/3.1.3 Python/3.11.14
|_http-title: NeoZen - Modern Nmap GUI (Web)
Device type: general purpose
Running: Linux 2.6.X|5.X
OS CPE: cpe:/o:linux:linux_kernel:2.6.32 cpe:/o:linux:linux_kernel:5 cpe:/o:linux:linux_kernel:6
OS details: Linux 2.6.32, Linux 5.0 - 6.2
Uptime guess: 15.408 days (since Sun Oct 12 06:08:31 2025)
Network Distance: 0 hops
TCP Sequence Prediction: Difficulty=257 (Good luck!)
IP ID Sequence Generation: All zeros
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

NSE: Script Post-scanning.
Initiating NSE at 15:55
Completed NSE at 15:55, 0.00s elapsed
Initiating NSE at 15:55
Completed NSE at 15:55, 0.00s elapsed
Initiating NSE at 15:55
Completed NSE at 15:55, 0.00s elapsed
Post-scan script results:
| clock-skew:
|   0s:
|     192.168.1.222 (c8:5a:cf:ad:ec:dd)
|     192.168.1.100 (00:11:32:d0:d9:6f)
|     192.168.1.201 (PriYaShamitaBala)
|_    192.168.1.167 (Priya-Laptop)
Read data files from: /usr/bin/../share/nmap
OS and Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 256 IP addresses (26 hosts up) scanned in 334.21 seconds
           Raw packets sent: 36028 (1.622MB) | Rcvd: 20898 (866.281KB)
------------------------------
Nmap process finished successfully. Reading & parsing results file...
[Error] Failed to read temporary XML file /tmp/tmp47vxz6n1.xml: [Errno 13] Permission denied: '/tmp/tmp47vxz6n1.xml'
 the scan ran but ended with an error. the Parsed Results tab was not populated. option for the user to select runtime arguments from a dialog not availabla