# NeoZen - A Modern Nmap GUI

![NeoZen Placeholder Logo](https://placehold.co/600x150/7e22ce/white?text=NeoZen)
*(Replace with an actual logo later)*

NeoZen is a modern, cross-platform graphical user interface (GUI) for the powerful Nmap network scanner. Built using Python 3 and the PyQt6 framework, it provides a feature-rich, user-friendly alternative to the classic Zenmap.

**Key Highlights:**
- 🎨 Modern, intuitive interface with polished design
- 🔧 Visual Custom Scan Builder with intelligent option compatibility
- 📊 Real-time scan results with comprehensive host details
- 💾 Standalone executables - no Python installation required
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

## Prerequisites

* **Python 3:** Version 3.7 or higher recommended.
* **Nmap:** Must be installed separately and available in your system's PATH. Download from [nmap.org](https://nmap.org).

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