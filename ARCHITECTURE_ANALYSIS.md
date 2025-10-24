# NeoZen Architecture Analysis

## Current Architecture Issues

### 1. **Tight Coupling to PyQt6**

The core Scanner class (`neozen/core/scanner.py:12`) has a **critical architectural flaw**:

```python
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class Scanner(QThread):
    # PyQt signals
    scan_output = pyqtSignal(str)
    scan_results_ready = pyqtSignal(dict)
    scan_finished = pyqtSignal(str, str)
    scan_error = pyqtSignal(str)
```

**Problems:**
- Scanner inherits from `QThread` (PyQt6-specific threading)
- Uses `pyqtSignal` for communication (PyQt6-specific)
- **Web interface requires PyQt6** just to run Nmap scans
- **CLI interface would require PyQt6** even though it has no GUI
- Cannot use Scanner with other frameworks (Tkinter, GTK, etc.)
- Core business logic (Nmap execution, XML parsing) is **inseparable** from GUI framework

### 2. **Dependency Chain**

```
Web App (Flask)
    └─> Scanner (PyQt6 QThread + signals)
        └─> PyQt6 Runtime
            └─> Qt6 C++ libraries
```

This means:
- `pip install -e ".[web]"` must also install PyQt6
- Docker web container includes unnecessary GUI dependencies
- Larger container size, more attack surface
- Violates separation of concerns

### 3. **Current Usage in Web App**

From `neozen/web/app.py:88-113`:
```python
current_scanner = Scanner(target, arguments)
current_scanner.scan_output.connect(handle_scan_output)  # PyQt signal!
current_scanner.scan_results_ready.connect(handle_scan_results)
current_scanner.scan_finished.connect(handle_scan_finished)
current_scanner.scan_error.connect(handle_scan_error)
current_scanner.start()  # QThread.start()
```

The web app uses PyQt signals/slots even though it's a Flask application.

---

## Proposed Architecture: Layered Design

### Layer 1: Pure Python Core (No GUI Dependencies)

```
neozen/core/
├── scanner.py          # Pure Python scanner (threading.Thread)
├── executor.py         # Nmap subprocess execution
├── parser.py           # XML parsing logic
├── profiles.py         # ✓ Already GUI-independent
└── models.py           # ✓ Already GUI-independent
```

**Core Scanner** - Pure Python with callbacks:
```python
import threading
from typing import Callable, Optional, Dict, Any

class NmapScanner(threading.Thread):
    """Pure Python Nmap scanner with callback-based communication."""

    def __init__(
        self,
        target: str,
        arguments: str,
        on_output: Optional[Callable[[str], None]] = None,
        on_results: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_finished: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        super().__init__(daemon=True)
        self.target = target
        self.arguments = arguments

        # Callbacks (pure Python functions)
        self._on_output = on_output or (lambda x: None)
        self._on_results = on_results or (lambda x: None)
        self._on_finished = on_finished or (lambda x, y: None)
        self._on_error = on_error or (lambda x: None)

    def run(self):
        """Execute scan with callback notifications."""
        # Same logic as current Scanner.run()
        # But uses self._on_output("text") instead of self.scan_output.emit("text")
        pass
```

### Layer 2: GUI Adapters (Framework-Specific Wrappers)

```
neozen/adapters/
├── __init__.py
├── qt_scanner.py       # PyQt6 adapter
├── web_scanner.py      # Flask/async adapter
└── cli_scanner.py      # CLI adapter
```

**PyQt6 Adapter** - Wraps core scanner with Qt signals:
```python
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from neozen.core.scanner import NmapScanner

class QtScannerAdapter(QObject):
    """Qt adapter that wraps pure Python NmapScanner."""

    # Qt signals
    scan_output = pyqtSignal(str)
    scan_results_ready = pyqtSignal(dict)
    scan_finished = pyqtSignal(str, str)
    scan_error = pyqtSignal(str)

    def __init__(self, target: str, arguments: str):
        super().__init__()
        self.scanner = NmapScanner(
            target, arguments,
            on_output=self.scan_output.emit,
            on_results=self.scan_results_ready.emit,
            on_finished=self.scan_finished.emit,
            on_error=self.scan_error.emit
        )

    def start(self):
        self.scanner.start()

    def stop(self):
        self.scanner.stop()

    def isRunning(self):
        return self.scanner.is_alive()
```

**Web Adapter** - Wraps core scanner for Flask/SocketIO:
```python
from neozen.core.scanner import NmapScanner

class WebScannerAdapter:
    """Web adapter that wraps pure Python NmapScanner."""

    def __init__(self, target: str, arguments: str, socketio):
        self.socketio = socketio
        self.scanner = NmapScanner(
            target, arguments,
            on_output=lambda text: socketio.emit('scan_output', {'text': text}),
            on_results=lambda results: socketio.emit('scan_results', {'results': results}),
            on_finished=lambda msg, path: socketio.emit('scan_finished', {'message': msg, 'xml_path': path}),
            on_error=lambda err: socketio.emit('scan_error', {'error': err})
        )

    def start(self):
        self.scanner.start()

    def stop(self):
        self.scanner.stop()

    def isRunning(self):
        return self.scanner.is_alive()
```

### Layer 3: UI Implementations

```
neozen/ui/          # PyQt6 desktop GUI (uses QtScannerAdapter)
neozen/web/         # Flask web dashboard (uses WebScannerAdapter)
neozen/cli/         # CLI interface (uses CliScannerAdapter or direct core)
```

---

## Benefits of Refactoring

### ✅ Separation of Concerns
- Core logic independent of GUI framework
- Business logic testable without GUI
- Single Responsibility Principle

### ✅ Reduced Dependencies
- Web container: **No PyQt6 required**
- CLI tool: **No GUI dependencies**
- Smaller containers, faster installation

### ✅ Flexibility
- Easy to add new interfaces (GTK, Tkinter, curses, API server)
- Swap GUI frameworks without touching core
- Core logic reusable in other projects

### ✅ Testability
- Test core scanner without GUI framework
- Mock callbacks instead of Qt signal/slot machinery
- Unit test business logic in isolation

### ✅ Performance
- Choose threading model per interface
  - PyQt6: QThread (GUI thread safety)
  - Web: threading.Thread or asyncio
  - CLI: Direct execution or threading

---

## Migration Path

### Phase 1: Create Pure Python Core (Non-Breaking)
1. Create `neozen/core/scanner_core.py` with `NmapScanner` class
2. Extract executor logic to `neozen/core/executor.py`
3. Extract XML parsing to `neozen/core/parser.py`
4. Add comprehensive tests for core

### Phase 2: Create Adapters (Non-Breaking)
1. Create `neozen/adapters/qt_scanner.py` wrapping core
2. Create `neozen/adapters/web_scanner.py` wrapping core
3. Test adapters maintain same interface

### Phase 3: Update UIs (Breaking Changes Isolated)
1. Update `neozen/ui/main_window.py` to use `QtScannerAdapter`
2. Update `neozen/web/app.py` to use `WebScannerAdapter`
3. Keep old `Scanner` as deprecated for one version

### Phase 4: Cleanup
1. Remove `neozen/core/scanner.py` (old coupled version)
2. Update documentation
3. Update `pyproject.toml` dependencies:
   - Base: No GUI dependencies
   - `[desktop]`: Add PyQt6
   - `[web]`: Flask only, no PyQt6
   - `[dev]`: All dependencies

---

## Example: Dependency Changes

### Before (Current)
```toml
[project]
dependencies = [
    "PyQt6>=6.0.0",        # Required for core!
    "python-nmap>=0.7.1",
    "psutil>=5.9.0",
]

[project.optional-dependencies]
web = [
    "flask>=2.3.0",
    # PyQt6 already in base dependencies
]
```

### After (Proposed)
```toml
[project]
dependencies = [
    "python-nmap>=0.7.1",  # Only core dependencies
    "psutil>=5.9.0",
]

[project.optional-dependencies]
desktop = [
    "PyQt6>=6.0.0",        # GUI-specific
]

web = [
    "flask>=2.3.0",
    "flask-socketio>=5.3.0",
    "flask-cors>=4.0.0",
    # No PyQt6!
]

cli = [
    "rich>=13.0.0",        # Pretty CLI output
]
```

---

## Code Size Impact

### Current Architecture
- `scanner.py`: ~450 lines (includes threading + parsing + execution)
- **Inseparable** - cannot use parts independently

### Proposed Architecture
- `scanner_core.py`: ~200 lines (pure Python scanner with callbacks)
- `executor.py`: ~100 lines (subprocess execution logic)
- `parser.py`: ~150 lines (XML parsing logic)
- `adapters/qt_scanner.py`: ~50 lines (Qt wrapper)
- `adapters/web_scanner.py`: ~30 lines (Web wrapper)
- `adapters/cli_scanner.py`: ~30 lines (CLI wrapper)

**Total: ~560 lines** (vs 450 lines)
- Slight increase in LOC
- **Massive** increase in modularity, testability, reusability

---

## Recommendation

**REFACTOR NOW** because:
1. **Project is young** - easier to refactor early
2. **Two interfaces already** - problem will compound with each new interface
3. **Docker optimization** - removing PyQt6 from web container saves ~100MB
4. **Future-proofing** - CLI, API, mobile interfaces all easier
5. **Best practices** - clean architecture from the start

The refactoring is **mechanical** and **low-risk**:
- Keep existing `Scanner` temporarily
- Add new core + adapters
- Gradually migrate
- No user-facing changes

---

## Next Steps

1. **Review this analysis** - Validate proposed architecture
2. **Create implementation plan** - Detail specific files and changes
3. **Implement Phase 1** - Pure Python core with tests
4. **Implement Phase 2** - Adapters with compatibility
5. **Implement Phase 3** - Migrate UIs
6. **Implement Phase 4** - Cleanup and documentation
