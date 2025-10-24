# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NeoZen is a modern, cross-platform GUI for Nmap built with Python 3 and PyQt6. It aims to replace the aging Zenmap with a more maintainable and feature-rich interface. The project uses subprocess-based Nmap execution for better control and live output streaming.

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
- PyQt6: GUI framework
- python-nmap: XML parsing library for Nmap output
- psutil: Process management for stopping scans and child processes

## Architecture

### Core Structure

The application follows a clean separation between UI and business logic:

- **main.py**: Entry point that creates QApplication and MainWindow
- **neozen/ui/main_window.py**: Main UI class (MainWindow) containing all GUI logic, profile management, and scan coordination
- **neozen/core/scanner.py**: Background thread (Scanner) that executes Nmap via subprocess, captures live output, and parses XML results
- **neozen/core/profiles.py**: Profile persistence layer (ProfileManager) with platform-specific config directory handling
- **neozen/core/models.py**: Placeholder for future data models (currently minimal)

### Threading Model

The Scanner class inherits from QThread and runs Nmap scans asynchronously:
- Uses subprocess.Popen for process control and live output capture
- Emits PyQt signals (scan_output, scan_results_ready, scan_finished, scan_error) to communicate with MainWindow
- Runs with `-oX` flag to save XML to a temporary file, which is parsed after completion
- Stop functionality uses psutil to properly terminate Nmap and all child processes

### Data Flow

1. User configures scan in MainWindow (target, profile, arguments)
2. MainWindow creates Scanner thread with target and arguments
3. Scanner builds command, starts subprocess, and streams output via scan_output signal
4. Scanner saves XML to temp file, parses it using python-nmap's analyse_nmap_xml_scan()
5. Scanner emits structured results dict via scan_results_ready signal
6. MainWindow populates results table and host details area
7. Temp XML file path is passed back for optional user save

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
- **Phases 1-5**: Core functionality complete (UI, scanning, results display, file operations, advanced features)
- **Phase 6**: Planned topology view (network map visualization)
- **Phase 7**: Planned packaging for distribution (executables for Windows/macOS/Linux)

## Code Style Notes

- Extensive comments explaining logic, especially in Scanner thread
- Uses f-strings for string formatting
- Type hints are minimal (Python 3.7+ compatible)
- Signal/slot pattern for UI communication
- Error handling with try/except blocks, errors displayed via QMessageBox

## External Dependencies

- **Nmap**: Must be installed separately and available in system PATH
- **Python 3.7+**: Required for Python features used
