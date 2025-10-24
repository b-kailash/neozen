# NeoZen - A Modern Nmap GUI

![NeoZen Placeholder Logo](https://placehold.co/600x150/7e22ce/white?text=NeoZen)
*(Replace with an actual logo later)*

NeoZen is a modern, cross-platform graphical user interface (GUI) for the powerful Nmap network scanner. Built with Python 3, it offers both a rich desktop application (PyQt6) and a browser-based web dashboard (Flask), providing a feature-rich, user-friendly alternative to the classic Zenmap.

**Key Highlights:**
- 🎨 Modern, intuitive interface with polished design
- 🌐 Dual interface support - Desktop GUI (PyQt6) and Web Dashboard (Browser-based)
- 🔧 Visual Custom Scan Builder with intelligent option compatibility
- 📊 Real-time scan results with comprehensive host details
- 💾 Standalone executables - no Python installation required
- 🐳 Minimal Docker containers - isolated and portable deployment
- 🔍 Default OS and service version detection enabled
- 📝 Host documentation with persistent notes
- 💻 Cross-platform support (Linux, macOS, Windows)

**Status:** Active development - Core features complete, advanced features in progress.

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
  * No X11 forwarding required
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
  * Dockerfile.web for minimal web-only deployment
  * docker-build-web.sh and docker-run-web.sh scripts
  * Access via http://localhost:8080

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

* **Nmap:** Must be installed separately and available in your system's PATH. Download from [nmap.org](https://nmap.org).
* **Python 3:** Version 3.7 or higher (only required for building from source; standalone executables and Docker containers include everything needed).

## Quick Installation

NeoZen now includes automated installation scripts that handle everything for you!

### Linux / macOS

```bash
# Clone the repository
git clone <your-repository-url>
cd neozen

# Run the installation script
./install.sh
```

The script will:
- Check for Python 3 and Nmap
- Attempt to install Nmap if missing (requires sudo)
- Create a virtual environment
- Install all dependencies

### Windows

```cmd
REM Clone the repository
git clone <your-repository-url>
cd neozen

REM Run the installation script
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

NeoZen can run in a minimal Docker container, providing an isolated environment without installing Python or dependencies on your host system.

### Prerequisites for Docker

* **Docker:** Install Docker Engine from [docker.com](https://docs.docker.com/get-docker/)
* **X11 Server:** Required for GUI display (pre-installed on Linux, XQuartz for macOS, VcXsrv/Xming for Windows)

### Quick Start with Docker

**Build the container:**
```bash
./docker-build.sh
```

**Run the container:**
```bash
./docker-run.sh
```

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

# Access at http://localhost:8080

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
- ✅ Minimal image size (python:3.11-slim base)
- ✅ X11 forwarding for GUI
- ✅ Network host mode for full Nmap capabilities
- ✅ Persistent volumes for scan results
- ✅ Non-root user execution for security
- ✅ Health checks included

## Running the Web Dashboard

NeoZen includes a browser-based web interface, perfect for remote access and containerized deployments without X11 forwarding complexity.

### Quick Start with Web Interface

**Build the web container:**
```bash
./docker-build-web.sh
```

**Run the web server:**
```bash
./docker-run-web.sh
```

**Access the interface:**

Open your browser and navigate to:
```
http://localhost:8080
```

### Running Web Interface Locally (Without Docker)

You can also run the web interface directly on your host:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Install web dependencies
pip install -e ".[web]"

# Start the web server
python -m neozen.web.app
```

Then access at `http://localhost:8080`

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

**Features of Web Dashboard:**
- ✅ Real-time scan output streaming via WebSockets
- ✅ Full scan control (start, stop, configure)
- ✅ Profile management (save, load, delete)
- ✅ Modern responsive design
- ✅ No desktop dependencies or X11 required
- ✅ Perfect for remote access and headless servers
- ✅ Access from any device with a web browser

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