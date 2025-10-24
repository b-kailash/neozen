# NeoZen Refactoring Plan - Decouple Core from GUI

## Executive Summary

**Problem:** The core Nmap scanning logic is tightly coupled to PyQt6, making it impossible to use without GUI dependencies.

**Solution:** Implement a layered architecture with pure Python core and framework-specific adapters.

**Impact:**
- Web container: Remove PyQt6 (~100MB smaller)
- Enable CLI interface without GUI dependencies
- Future interfaces (API server, mobile) become trivial
- Improved testability and maintainability

---

## Implementation Phases

### Phase 1: Create Pure Python Core (Estimated: 4-6 hours)

**Goal:** Extract scanning logic into GUI-independent module.

**Files to Create:**

#### 1.1 `neozen/core/scanner_core.py`
```python
"""Pure Python Nmap scanner with callback-based communication."""

import threading
import subprocess
import psutil
import os
import shlex
import sys
import tempfile
import platform
from typing import Callable, Optional, Dict, Any

class NmapScanner(threading.Thread):
    """
    Pure Python Nmap scanner that uses callbacks instead of Qt signals.

    This class is GUI-framework agnostic and can be used with any interface.
    """

    def __init__(
        self,
        target: str,
        arguments: str,
        on_output: Optional[Callable[[str], None]] = None,
        on_results: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_finished: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize scanner with callbacks.

        Args:
            target: Target host(s)/network(s)
            arguments: Nmap command-line arguments
            on_output: Callback for live output (str) -> None
            on_results: Callback for parsed results (dict) -> None
            on_finished: Callback for completion (message, xml_path) -> None
            on_error: Callback for errors (error_msg) -> None
        """
        super().__init__(daemon=True)
        self.target = target
        self.base_arguments = arguments
        self._is_running = True
        self.nmap_process = None
        self.temp_xml_file_path = None

        # Store callbacks
        self._on_output = on_output or (lambda x: None)
        self._on_results = on_results or (lambda x: None)
        self._on_finished = on_finished or (lambda x, y: None)
        self._on_error = on_error or (lambda x: None)

    # Copy all methods from current Scanner:
    # - _cleanup_temp_file()
    # - _build_command()
    # - run()
    # - stop()

    # Replace all signal emissions:
    # self.scan_output.emit(text) -> self._on_output(text)
    # self.scan_results_ready.emit(results) -> self._on_results(results)
    # self.scan_finished.emit(msg, path) -> self._on_finished(msg, path)
    # self.scan_error.emit(error) -> self._on_error(error)
```

#### 1.2 `neozen/core/executor.py`
```python
"""Nmap subprocess execution logic."""

import subprocess
import shlex
import platform
from typing import List, Optional

class NmapExecutor:
    """Handles Nmap command building and subprocess execution."""

    @staticmethod
    def build_command(target: str, arguments: str, xml_output_path: str) -> Optional[List[str]]:
        """Build Nmap command with arguments."""
        # Extract command building logic from Scanner._build_command()
        pass

    @staticmethod
    def execute(command: List[str]) -> subprocess.Popen:
        """Execute Nmap command and return process handle."""
        # Extract process creation from Scanner.run()
        pass
```

#### 1.3 `neozen/core/parser.py`
```python
"""Nmap XML parsing logic."""

import nmap
from typing import Dict, Any

class NmapParser:
    """Parses Nmap XML output into structured data."""

    @staticmethod
    def parse_xml(xml_content: str) -> Dict[str, Any]:
        """
        Parse Nmap XML content.

        Args:
            xml_content: XML string from Nmap output

        Returns:
            Dictionary with structured host/port/service data
        """
        # Extract parsing logic from Scanner.run()
        pass
```

#### 1.4 `tests/test_scanner_core.py`
```python
"""Unit tests for pure Python scanner core."""

import unittest
from neozen.core.scanner_core import NmapScanner

class TestNmapScanner(unittest.TestCase):

    def test_scanner_creation(self):
        """Test scanner can be created without GUI dependencies."""
        scanner = NmapScanner(
            target="127.0.0.1",
            arguments="-sn",
            on_output=lambda x: None
        )
        self.assertIsNotNone(scanner)

    def test_callbacks_are_called(self):
        """Test that callbacks are invoked during scan."""
        outputs = []
        scanner = NmapScanner(
            target="127.0.0.1",
            arguments="-sn",
            on_output=lambda x: outputs.append(x)
        )
        # Run scan and verify callbacks
        pass
```

---

### Phase 2: Create GUI Adapters (Estimated: 2-3 hours)

**Goal:** Create thin wrappers that maintain existing interface.

**Files to Create:**

#### 2.1 `neozen/adapters/__init__.py`
```python
"""GUI framework adapters for NmapScanner core."""

from .qt_scanner import QtScannerAdapter
from .web_scanner import WebScannerAdapter

__all__ = ['QtScannerAdapter', 'WebScannerAdapter']
```

#### 2.2 `neozen/adapters/qt_scanner.py`
```python
"""PyQt6 adapter for NmapScanner."""

from PyQt6.QtCore import QObject, pyqtSignal
from neozen.core.scanner_core import NmapScanner

class QtScannerAdapter(QObject):
    """
    Qt adapter that wraps pure Python NmapScanner.

    Maintains identical interface to old Scanner class for backward compatibility.
    """

    # Qt signals (same as old Scanner)
    scan_output = pyqtSignal(str)
    scan_results_ready = pyqtSignal(dict)
    scan_finished = pyqtSignal(str, str)
    scan_error = pyqtSignal(str)

    def __init__(self, target: str, arguments: str):
        super().__init__()
        # Create core scanner with Qt signal callbacks
        self.scanner = NmapScanner(
            target=target,
            arguments=arguments,
            on_output=self.scan_output.emit,
            on_results=self.scan_results_ready.emit,
            on_finished=self.scan_finished.emit,
            on_error=self.scan_error.emit
        )

    def start(self):
        """Start the scan thread."""
        self.scanner.start()

    def stop(self):
        """Stop the running scan."""
        self.scanner.stop()

    def isRunning(self) -> bool:
        """Check if scan is running."""
        return self.scanner.is_alive()

    def wait(self, msecs: int = -1) -> bool:
        """Wait for thread to finish (Qt compatibility)."""
        timeout = None if msecs == -1 else msecs / 1000.0
        self.scanner.join(timeout=timeout)
        return not self.scanner.is_alive()
```

#### 2.3 `neozen/adapters/web_scanner.py`
```python
"""Flask/SocketIO adapter for NmapScanner."""

from neozen.core.scanner_core import NmapScanner

class WebScannerAdapter:
    """
    Web adapter that wraps pure Python NmapScanner.

    Emits SocketIO events for web interface.
    """

    def __init__(self, target: str, arguments: str, socketio):
        """
        Initialize web scanner.

        Args:
            target: Scan target
            arguments: Nmap arguments
            socketio: Flask-SocketIO instance for emitting events
        """
        self.socketio = socketio
        self.scanner = NmapScanner(
            target=target,
            arguments=arguments,
            on_output=lambda text: socketio.emit('scan_output', {'text': text}),
            on_results=lambda results: socketio.emit('scan_results', {'results': results}),
            on_finished=lambda msg, path: socketio.emit('scan_finished', {
                'message': msg,
                'xml_path': path
            }),
            on_error=lambda err: socketio.emit('scan_error', {'error': err})
        )

    def start(self):
        """Start the scan thread."""
        self.scanner.start()

    def stop(self):
        """Stop the running scan."""
        self.scanner.stop()

    def isRunning(self) -> bool:
        """Check if scan is running."""
        return self.scanner.is_alive()
```

---

### Phase 3: Update UI Implementations (Estimated: 1-2 hours)

**Goal:** Migrate UIs to use new adapters.

#### 3.1 Update `neozen/ui/main_window.py`
```python
# Old import
# from neozen.core.scanner import Scanner

# New import
from neozen.adapters.qt_scanner import QtScannerAdapter as Scanner

# Rest of code unchanged!
# The adapter maintains the same interface
```

#### 3.2 Update `neozen/web/app.py`
```python
# Old import
# from neozen.core.scanner import Scanner

# New import
from neozen.adapters.web_scanner import WebScannerAdapter

# Update usage (lines 88-120)
def start_scan():
    global current_scanner, scan_output, scan_results

    data = request.json
    target = data.get('target')
    arguments = data.get('arguments', '')

    if not target:
        return jsonify({'error': 'Target is required'}), 400

    with scan_lock:
        if current_scanner and current_scanner.isRunning():
            return jsonify({'error': 'A scan is already running'}), 409

        # Clear previous scan data
        scan_output = []
        scan_results = {}

        # Create scanner with web adapter (no more PyQt signals!)
        current_scanner = WebScannerAdapter(target, arguments, socketio)

        # No need to connect signals - adapter handles it internally

        # Start scan
        current_scanner.start()

        # Notify clients
        socketio.emit('scan_started', {'target': target, 'arguments': arguments})

        return jsonify({'success': True, 'message': 'Scan started'})
```

---

### Phase 4: Update Dependencies (Estimated: 1 hour)

#### 4.1 Update `pyproject.toml`
```toml
[project]
name = "neozen"
version = "0.2.0"  # Bump version
dependencies = [
    # Core dependencies only - NO GUI!
    "python-nmap>=0.7.1",
    "psutil>=5.9.0",
]

[project.optional-dependencies]
desktop = [
    "PyQt6>=6.0.0",  # Only needed for desktop GUI
]

web = [
    "flask>=2.3.0",
    "flask-socketio>=5.3.0",
    "flask-cors>=4.0.0",
    "python-socketio>=5.9.0",
    # No PyQt6 dependency!
]

cli = [
    "rich>=13.0.0",  # For pretty CLI output (future)
]

dev = [
    "pytest>=7.0.0",
    "pytest-qt>=4.0.0",  # Still needed for Qt tests
    "black>=22.0.0",
    "ruff>=0.1.0",
]

build = [
    "pyinstaller>=5.0.0",
]

# All optional dependencies
all = [
    "PyQt6>=6.0.0",
    "flask>=2.3.0",
    "flask-socketio>=5.3.0",
    "flask-cors>=4.0.0",
    "python-socketio>=5.9.0",
    "rich>=13.0.0",
]
```

#### 4.2 Update `Dockerfile.web`
```dockerfile
# Before: Had to install PyQt6 dependencies
# After: Only core + web dependencies

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    curl \
    && rm -rf /var/lib/apt/lists/*
    # No X11, Qt, or display libraries needed!

# Install only web dependencies
RUN pip install --no-cache-dir -e ".[web]"
# This will NOT install PyQt6 anymore!
```

---

### Phase 5: Cleanup & Documentation (Estimated: 2 hours)

#### 5.1 Deprecate old Scanner
```python
# neozen/core/scanner.py (keep temporarily)
import warnings
from neozen.adapters.qt_scanner import QtScannerAdapter

class Scanner(QtScannerAdapter):
    """
    DEPRECATED: Use QtScannerAdapter directly.

    This class will be removed in version 0.3.0.
    """
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Scanner is deprecated, use QtScannerAdapter instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
```

#### 5.2 Update README.md
```markdown
## Architecture

NeoZen follows a layered architecture:

- **Core Layer** (`neozen/core/`) - Pure Python, no GUI dependencies
  - `scanner_core.py` - Nmap execution with callbacks
  - `parser.py` - XML parsing logic
  - `executor.py` - Subprocess management
  - `profiles.py` - Profile management

- **Adapter Layer** (`neozen/adapters/`) - Framework-specific wrappers
  - `qt_scanner.py` - PyQt6 adapter for desktop GUI
  - `web_scanner.py` - Flask adapter for web dashboard

- **UI Layer** - User interfaces
  - `neozen/ui/` - PyQt6 desktop application
  - `neozen/web/` - Flask web dashboard

This design allows the same Nmap logic to power different interfaces.
```

#### 5.3 Update CLAUDE.md
```markdown
## Architecture (Updated)

The application uses a layered architecture:

### Core (Pure Python)
- **scanner_core.py**: NmapScanner with callback-based communication
- **No GUI dependencies** - can be used standalone

### Adapters (Framework-Specific)
- **qt_scanner.py**: Wraps NmapScanner with Qt signals for PyQt6
- **web_scanner.py**: Wraps NmapScanner for Flask/SocketIO

### Benefits
- Web interface: No PyQt6 required (~100MB smaller container)
- Easy to add new interfaces (CLI, API, mobile)
- Core logic testable without GUI
```

---

## Testing Strategy

### Unit Tests
- `tests/test_scanner_core.py` - Core scanner without GUI
- `tests/test_parser.py` - XML parsing
- `tests/test_executor.py` - Command building

### Integration Tests
- `tests/test_qt_adapter.py` - Qt adapter with PyQt6
- `tests/test_web_adapter.py` - Web adapter with Flask

### End-to-End Tests
- Desktop GUI: Existing PyQt tests
- Web interface: Existing Flask tests

---

## Rollout Plan

### Step 1: Create feature branch
```bash
git checkout -b refactor/decouple-scanner-from-gui
```

### Step 2: Implement phases sequentially
- Commit after each phase
- Test thoroughly before moving to next phase
- Keep old Scanner working during transition

### Step 3: Merge when stable
```bash
# After all phases complete and tested
git checkout Main
git merge refactor/decouple-scanner-from-gui
git push origin Main
```

### Step 4: Deprecation period
- Keep old `Scanner` class for 1 version (0.2.0)
- Remove in 0.3.0

---

## Risk Mitigation

### Backward Compatibility
- Adapters maintain identical interface
- Old code continues working
- Deprecation warnings guide migration

### Testing
- Comprehensive unit tests for core
- Integration tests for adapters
- Manual testing of both UIs

### Rollback Plan
- Feature branch allows easy rollback
- Old Scanner class kept during transition
- Can revert if issues found

---

## Timeline

**Estimated Total: 10-14 hours of development**

- Phase 1: 4-6 hours (core refactoring)
- Phase 2: 2-3 hours (adapters)
- Phase 3: 1-2 hours (UI updates)
- Phase 4: 1 hour (dependencies)
- Phase 5: 2 hours (documentation)

**Recommendation:** Allocate 2-3 days for implementation + testing.

---

## Success Criteria

✅ Web container runs without PyQt6
✅ Desktop GUI works identically
✅ All existing tests pass
✅ New core tests achieve >80% coverage
✅ Docker web image reduced by >80MB
✅ Documentation updated
✅ Clean git history with meaningful commits

---

## Questions for Review

1. **Approve architecture?** Layered design with pure core + adapters?
2. **Timeline acceptable?** 2-3 days for implementation?
3. **Breaking changes OK?** Internal only, APIs unchanged?
4. **Start immediately?** Or wait for next milestone?
