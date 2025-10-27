# NeoZen - A Modern Nmap GUI

![NeoZen Placeholder Logo](https://placehold.co/600x150/7e22ce/white?text=NeoZen)
*(Replace with an actual logo later)*

NeoZen is a modern, cross-platform interface for the powerful Nmap network scanner. Built with Python 3 using a layered architecture, it offers both a rich desktop application (PyQt6) and a browser-based web dashboard (Flask), providing a feature-rich, user-friendly alternative to the classic Zenmap.

**Key Highlights:**
- 🎨 Modern, intuitive interface with polished design
- 🌐 **Dual interface support** - Desktop GUI (PyQt6) and Web Dashboard (Browser-based)
- 🏗️ **Layered architecture** - Pure Python core, GUI-agnostic, framework adapters
- 📦 **Minimal dependencies** - Web dashboard runs without PyQt6 (~100MB smaller)
- 🔧 Visual Custom Scan Builder with intelligent option compatibility
- 📊 Real-time scan results with comprehensive host details
- 💾 Standalone executables - no Python installation required
- 🐳 **Two Docker containers** - Desktop (X11) and Web (browser-only, no X11)
- 🔍 Default OS and service version detection enabled
- 📝 Host documentation with persistent notes
- 💻 Cross-platform support (Linux, macOS, Windows)

**Status:** Version 0.2.0 - Stable with clean architecture, ready for production use.

## Features

### ✅ Completed Features

#### **Modern UI & Design**
* Built with Python 3 and PyQt6
* Modern, polished interface with custom styling
* Application icon for branding
* Resizable split views for optimal workspace

#### **Advanced Scan Configuration**
* Target input (IP, hostname, network range)
* **OS Detection Checkbox** - Enable/disable OS detection (-O flag) with one click (enabled by default)
* **Service Version Detection Checkbox** - Enable/disable service/version detection (-sV flag) with one click (enabled by default)
* **Visual Custom Scan Builder** - Interactive dialog for building custom scan commands with:
  * Scan techniques (TCP SYN, Connect, UDP, ACK, Window, Null, FIN, Xmas, Ping)
  * Port specifications (Fast, All Ports, Top 1-1000)
  * Timing templates (T0-T5)
  * Detection options (OS, Service Version, Scripts, Aggressive)
  * Other options (Verbose, Reason, Packet Trace, No DNS)
  * **Intelligent compatibility system** - incompatible options automatically greyed out
  * Real-time command preview
* Selection of common predefined scan types (Intense, Quick, Ping, etc.)
* Custom Nmap argument input with live command display
* **Profile Management** - Save and load custom scan configurations (target + arguments)
* Live Command Display - See the exact Nmap command that will be executed

#### **Scan Execution**
* Background thread execution - keeps UI responsive during scans
* Ability to stop running scans gracefully
* Progress bar for running scans
* **Privilege Warning** - Real-time status bar notifications for scans requiring admin/root privileges

#### **Results Display & Analysis**
* **Raw Output Tab** - Live, human-readable output from Nmap as the scan runs
* **Parsed Results Tab** - Sortable table view (Host, Proto, Port, State, Service, Product, Version)
* **Host Details Area** - Comprehensive information for selected hosts:
  * Hostname, IP Address, State
  * MAC Address and Vendor (if available)
  * OS Detection results (guesses and accuracy)
  * Detailed Port/Service list
  * NSE Script output (both host-level and port-level)
* **Host Notes Feature** - Add and save documentation notes for each scanned host

#### **File Operations**
* Save scan results to Nmap XML files
* **Raw Output Embedding** - Option to embed raw console output in XML files for complete preservation
* Open and display results from previously saved Nmap XML files
* **Notes Persistence** - Host notes saved alongside scan results
* Prompt to save unsaved results on application close
* Extract and display embedded raw output from saved files

#### **Distribution & Packaging** ✨
* **Standalone Executables** - Built automatically during installation
  * Linux/macOS: Single `neozen` executable
  * Windows: Single `neozen.exe` executable
  * No Python or dependencies required to run
* Cross-platform build system (PyInstaller)
* Automated installation scripts with integrated build process
* Make targets for easy building

#### **Containerization (Phase 8)** ✨
* **Minimal Docker Container** - Lightweight containerized version
  * Based on python:3.11-slim for small image size
  * Includes Nmap and all necessary dependencies
  * X11 forwarding support for GUI
  * Network host mode for full Nmap functionality
  * Persistent volumes for scan results and configuration
* **Easy Deployment** - Simple build and run scripts
  * docker-build.sh for building the container
  * docker-run.sh for running with X11 forwarding
  * docker-compose.yml for advanced orchestration
* **Isolated Environment** - Run NeoZen without installing Python or dependencies on host

#### **Web Dashboard (Phase 9)** ✨
* **Browser-Based Interface** - Access NeoZen from any modern web browser
  * Flask web server with REST API
  * Real-time updates via WebSocket (Socket.IO)
  * Modern, responsive HTML5/CSS3/JavaScript UI
  * **No X11 forwarding required** - browser-only access
* **Full Feature Parity** - All core features available via web interface
  * Scan configuration (target, profiles, arguments)
  * OS Detection and Service Version Detection checkboxes
  * Real-time scan output streaming
  * Parsed results table with comprehensive host details
  * Profile management (save/load custom configurations)
* **Dual Interface Support** - Choose the interface that fits your needs
  * Desktop GUI (PyQt6) for local use with rich UI
  * Web Dashboard for remote access and containerized deployments
* **Simple Deployment** - Dedicated web container
  * Dockerfile.web for minimal web-only deployment (~150MB vs ~250MB)
  * docker-build-web.sh and docker-run-web.sh scripts
  * Access via http://localhost:8080 or http://HOST_IP:8080

#### **Architecture Refactoring (v0.2.0)** ✨
* **Layered Architecture** - Separation of concerns with clean boundaries
  * **Core Layer** - Pure Python scanner with no GUI dependencies
    - `NmapScanner` class using `threading.Thread` (not QThread)
    - Callback-based communication (no framework-specific signals)
    - Reusable across any interface type
  * **Adapter Layer** - Framework-specific wrappers
    - `QtScannerAdapter` for PyQt6 desktop GUI
    - `WebScannerAdapter` for Flask web dashboard
    - Easy to add new adapters (CLI, API, mobile)
  * **UI Layer** - Desktop GUI and Web Dashboard implementations
* **Dependency Optimization** - Install only what you need
  * **Core**: python-nmap, psutil (no GUI frameworks!)
  * **Desktop**: `pip install -e ".[desktop]"` adds PyQt6
  * **Web**: `pip install -e ".[web]"` adds Flask (NO PyQt6!)
  * **Both**: `pip install -e ".[all]"` installs everything
* **Benefits Achieved**
  * Web container: ~100MB reduction (no PyQt6/Qt6 libraries)
  * Core scanner can be used standalone for CLI tools or APIs
  * Easy addition of new interfaces without modifying core
  * Better testability - core logic testable without GUI
  * Improved maintainability - changes isolated to appropriate layers

### 🚧 Planned Features

#### **Phase 6: Topology View**
* Graphical network map visualization
* Visual representation of discovered hosts
* Interactive network topology diagram

#### **Future Enhancements**
* Scan comparison functionality
* Scan history and management
* Export results to multiple formats (CSV, JSON, HTML)
* Advanced filtering and search in results
* Custom NSE script management
* Themes and user preferences
* Scheduled/automated scans

## Architecture

NeoZen follows a **layered architecture** that separates core business logic from UI frameworks:

### Layers

1. **Core Layer** (`neozen/core/`) - Pure Python, no GUI dependencies
   - `scanner_core.py` - Nmap execution with callbacks
   - `profiles.py` - Profile management
   - `models.py` - Data models

2. **Adapter Layer** (`neozen/adapters/`) - Framework-specific wrappers
   - `qt_scanner.py` - PyQt6 adapter for desktop GUI
   - `web_scanner.py` - Flask adapter for web dashboard

3. **UI Layer** - User interfaces
   - `neozen/ui/` - PyQt6 desktop application
   - `neozen/web/` - Flask web dashboard

### Benefits

This design allows:
- **Web interface without PyQt6** (~100MB smaller container)
- **Easy addition of new interfaces** (CLI, API, mobile)
- **Core logic testable** without GUI framework
- **Better maintainability** - changes to core don't affect UIs

For detailed architecture documentation, see [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md).

## Prerequisites

### Core Requirements
* **Nmap:** Must be installed separately and available in your system's PATH. Download from [nmap.org](https://nmap.org).
* **Python 3:** Version 3.7 or higher (only required for building from source).

### Interface-Specific Requirements

| Interface | Requirements | Notes |
|-----------|-------------|-------|
| **Desktop GUI** | PyQt6, X11/display server | For local desktop use |
| **Web Dashboard** | Flask, browser | No PyQt6, no X11 needed! |
| **Standalone Executables** | None (Nmap only) | Everything bundled |
| **Docker Containers** | Docker | Everything included |

## Quick Installation

NeoZen v0.2.0 offers flexible installation based on your needs!

### Choose Your Interface

**Desktop GUI Only:**
```bash
git clone <your-repository-url>
cd neozen
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or .\venv\Scripts\activate on Windows

pip install -e ".[desktop]"
python main.py
```

**Web Dashboard Only:**
```bash
git clone <your-repository-url>
cd neozen
python3 -m venv venv
source venv/bin/activate

pip install -e ".[web]"
python -m neozen.web.app
# Access at http://localhost:8080 or http://HOST_IP:8080 from any machine on the network
```

**Both Interfaces:**
```bash
git clone <your-repository-url>
cd neozen
python3 -m venv venv
source venv/bin/activate

pip install -e ".[all]"
```

### Automated Installation Scripts

NeoZen includes installation scripts that install **all interfaces**:

**Linux / macOS:**
```bash
./install.sh
```

The script will:
- Check for Python 3 and Nmap
- Attempt to install Nmap if missing (requires sudo)
- Create a virtual environment
- Install all dependencies (desktop + web)
- Build standalone executable

**Windows:**
```cmd
install.bat
```

The script will check for Python 3 and Nmap and guide you through installation if needed.

### Alternative: Using Make (Linux/macOS)

If you have `make` installed:

```bash
make install    # Install NeoZen
make run        # Run the application
```

### Manual Installation

If you prefer to install manually:

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd neozen
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv

    # Linux/macOS:
    source venv/bin/activate

    # Windows:
    .\venv\Scripts\activate
    ```

3.  **Install NeoZen:**
    ```bash
    pip install -e .
    ```

## Usage

### After Quick Installation

```bash
# Linux/macOS
source venv/bin/activate
neozen

# Or directly:
./venv/bin/neozen

# Windows
venv\Scripts\activate.bat
neozen
```

### After Manual Installation

```bash
# If virtual environment is activated:
neozen

# Or run directly:
python main.py
```

### Using the Application

1. **Enter a target** (IP address, hostname, or network range)
2. **Configure your scan:**
   - Enable/disable **OS Detection** and **Service Version Detection** checkboxes (both enabled by default)
   - Select a predefined scan profile, or
   - Click **"Build Custom Scan..."** to use the visual scan builder, or
   - Manually enter custom Nmap arguments
3. **Click "Scan"** to start
4. **View results** in real-time:
   - **Raw Output tab** - Live console output from Nmap
   - **Parsed Results tab** - Structured table view
5. **Select a host** to see detailed information and add notes
6. **Save results** via File > Save Scan Results (option to include raw output)

**Note:** Some scan types require administrator/root privileges. NeoZen will display a warning in the status bar when privileged scans are selected. The OS Detection feature (-O) requires elevated privileges.

## Building Standalone Executables

Standalone executables are automatically built during installation and placed in the project directory.

### Automatic Build During Installation

When you run the installation scripts (`install.sh` or `install.bat`), they will automatically:
1. Install NeoZen in a virtual environment
2. Build a standalone executable in the project directory
3. Give you both options to run the application

**Linux / macOS:**
```bash
./install.sh
# Creates: ./neozen
```

**Windows:**
```cmd
install.bat
REM Creates: neozen.exe
```

### Manual Build Only (Optional)

If you only want to build the executable without installation:

**Linux / macOS:**
```bash
./build.sh
```

**Windows:**
```cmd
build.bat
```

**Using Make (Linux/macOS):**
```bash
make build
```

### Running the Standalone Executable

**Linux / macOS:**
```bash
./neozen
```

**Windows:**
```cmd
neozen.exe
```

Or simply double-click the executable in your file explorer.

### Making it Globally Available

**Linux / macOS:**
```bash
sudo cp neozen /usr/local/bin/neozen
sudo chmod +x /usr/local/bin/neozen
```

Then you can run `neozen` from anywhere!

**Windows:**

Add the project directory to your PATH environment variable, then you can run `neozen` from any command prompt.

## Running in Docker Container

NeoZen offers **two Docker containers** optimized for different use cases:

### Container Comparison

| Container | Size | X11 Required? | PyQt6? | Use Case |
|-----------|------|---------------|--------|----------|
| **Desktop** | ~250MB | ✅ Yes | ✅ Yes | Local desktop GUI with X11 forwarding |
| **Web** | ~150MB | ❌ No | ❌ No | Remote access, browser-based, headless |

### Prerequisites for Docker

* **Docker:** Install Docker Engine from [docker.com](https://docs.docker.com/get-docker/)
* **X11 Server:** Only for desktop container (pre-installed on Linux, XQuartz for macOS, VcXsrv/Xming for Windows)

### Desktop Container (PyQt6 GUI with X11)

**Build:**
```bash
./docker-build.sh
```

**Run:**
```bash
xhost +local:docker  # Allow X11 access
./docker-run.sh
xhost -local:docker  # Cleanup (optional)
```

**Requirements:** X11 server, display forwarding setup
**Size:** ~250MB (includes PyQt6 and X11 libraries)

### Web Container (Browser-based, No X11) 🆕

**Build:**
```bash
./docker-build-web.sh
```

**Run:**
```bash
./docker-run-web.sh
```

**Access:**
- Local: http://localhost:8080
- Remote: http://HOST_IP:8080 (replace HOST_IP with your server's IP address)

**Requirements:** Just Docker and a web browser!
**Size:** ~150MB (no PyQt6, no X11 libraries)
**Advantages:** Simpler setup, remote access, no display server needed

### Using Docker Compose

Docker Compose supports both desktop GUI and web versions via profiles:

**Desktop GUI version (requires X11 forwarding):**
```bash
# Start NeoZen desktop GUI
docker-compose --profile desktop up

# Run in background
docker-compose --profile desktop up -d

# Stop the container
docker-compose --profile desktop down
```

**Web Dashboard version (browser-based):**
```bash
# Start NeoZen web dashboard
docker-compose --profile web up

# Run in background
docker-compose --profile web up -d

# Access at:
#  - Local: http://localhost:8080
#  - Remote: http://HOST_IP:8080 (from any machine on your network)

# Stop the container
docker-compose --profile web down
```

### Manual Docker Commands

**Build:**
```bash
docker build -t neozen:latest .
```

**Run (Linux/macOS):**
```bash
# Allow X11 forwarding
xhost +local:docker

# Run the container
docker run -it --rm \
    --name neozen \
    --network host \
    --cap-add=NET_ADMIN \
    --cap-add=NET_RAW \
    -e DISPLAY=${DISPLAY} \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v ${HOME}/.Xauthority:/home/neozen/.Xauthority:ro \
    neozen:latest

# Cleanup
xhost -local:docker
```

**Features of Docker Deployment:**
- ✅ **Two optimized containers** - Desktop (~250MB) and Web (~150MB)
- ✅ **Web container** - No X11, no PyQt6, browser-only access
- ✅ **Desktop container** - Full PyQt6 GUI with X11 forwarding
- ✅ Minimal base (python:3.11-slim)
- ✅ Network host mode for full Nmap capabilities
- ✅ Persistent volumes for scan results
- ✅ Non-root user execution for security
- ✅ Health checks included

## Running the Web Dashboard

NeoZen's browser-based web interface provides **the same Nmap scanning power** without GUI dependencies, making it perfect for remote access and containerized deployments.

### 🆕 What's New in v0.2.0

The web dashboard is now **completely independent** from PyQt6:
- ✅ **No PyQt6 dependency** - Web install is ~100MB smaller
- ✅ **No X11 required** - Runs on headless servers
- ✅ **Pure Python core** - Uses callback-based NmapScanner
- ✅ **Faster installation** - Only Flask and websocket libraries needed

### Quick Start with Web Interface

**Option 1: Docker (Recommended)**

```bash
./docker-build-web.sh
./docker-run-web.sh
```

**Option 2: Local Installation**

```bash
# Clone and setup
git clone <your-repository-url>
cd neozen
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or .\venv\Scripts\activate on Windows

# Install ONLY web dependencies (no PyQt6!)
pip install -e ".[web]"

# Start the web server
python -m neozen.web.app
```

**Access:**
- Local: http://localhost:8080
- Remote: http://HOST_IP:8080 (from any machine on your network)

#### Network Access Notes

The web dashboard uses `host` network mode in Docker, which means:
- ✅ The application binds to `0.0.0.0:8080` (all network interfaces)
- ✅ Accessible from any machine on your network via `http://HOST_IP:8080`
- ✅ No port mapping needed - uses host's network directly

**To find your host IP address:**
```bash
# Linux/macOS
hostname -I | awk '{print $1}'
# or
ip addr show | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr IPv4
```

**Firewall considerations:**
- Ensure port 8080 is open in your firewall
- Linux: `sudo ufw allow 8080/tcp`
- Windows: Allow port 8080 in Windows Defender Firewall
- Cloud/VPS: Configure security group to allow inbound TCP on port 8080

### Using the Web Interface

1. **Connection Status** - Check the connection indicator in the footer (green = connected)
2. **Configure Scan:**
   - Enter target (IP, hostname, or network range)
   - Select a saved profile or use Custom Scan
   - Enter custom Nmap arguments if needed
   - Enable/disable OS Detection and Service Detection checkboxes
3. **Start Scan** - Click "Start Scan" button
4. **View Results** - Switch between tabs:
   - **Raw Output** - Live console output from Nmap
   - **Parsed Results** - Structured table with host/port details
5. **Manage Profiles** - Save configurations for reuse

**Features of Web Dashboard (v0.2.0):**
- ✅ **Zero GUI dependencies** - No PyQt6, no X11, no display server
- ✅ **100MB smaller** - Only Flask and core dependencies
- ✅ **Real-time updates** - WebSocket-based output streaming
- ✅ **Full feature parity** - Same scanning capabilities as desktop
- ✅ **Profile management** - Save, load, and delete scan configurations
- ✅ **Modern responsive UI** - Works on desktop, tablet, mobile
- ✅ **Remote access ready** - Access from any device with browser
- ✅ **Headless server friendly** - Perfect for cloud/VPS deployments

### Web vs Desktop Interface

**Choose Desktop GUI (PyQt6) when:**
- Running locally on your workstation
- You prefer native desktop applications
- You want the richest UI experience with all PyQt6 features

**Choose Web Dashboard when:**
- Running in Docker containers
- Accessing NeoZen remotely
- Working on headless/remote servers
- You want browser-based access from any device
- You want to avoid X11 forwarding setup

## Development

### Install with Development Dependencies

```bash
# Using the installation script with dev tools
./install.sh
source venv/bin/activate
pip install -e ".[dev]"

# Or using make
make dev
```

### Running Tests

```bash
# Activate virtual environment first
source venv/bin/activate

# Run tests
pytest tests/

# Or using make
make test
```

### Code Quality

```bash
# Format code
make format

# Run linting
make lint
```

## License

*(Currently unlicensed. Choose an appropriate open-source license like MIT, GPLv2+, etc., and add a LICENSE file).*

## Contributing

*(Optional: Add guidelines here if you plan to accept contributions).*

---

*This README is a work in progress and will be updated as the project develops.*