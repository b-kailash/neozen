# NeoZen - A Modern Nmap GUI

![NeoZen Placeholder Logo](https://placehold.co/600x150/7e22ce/white?text=NeoZen)
*(Replace with an actual logo later)*

NeoZen aims to be a modern, cross-platform graphical user interface (GUI) for the powerful Nmap network scanner. It is built using Python 3 and the PyQt6 framework, providing a user-friendly alternative to the classic (but aging) Zenmap.

This project is currently under development.

## Features (Implemented & Planned)

**Current Features (as of Phase 5 completion):**

* **Modern UI:** Built with Python 3 and PyQt6.
* **Scan Configuration:**
    * Target input (IP, hostname, network range).
    * Selection of common predefined scan types (Intense, Quick, Ping, etc.).
    * Custom Nmap argument input.
    * Profile Management: Save and load custom scan configurations (target + arguments).
    * Live Command Display: See the exact Nmap command that will be executed.
* **Scan Execution:**
    * Runs Nmap scans in a background thread to keep the UI responsive.
    * Ability to stop running scans.
    * Progress bar for running scans.
    * Privilege Warning: Notifies the user in the status bar if selected options likely require admin/root privileges.
* **Results Display:**
    * **Raw Output Tab:** Shows the live, human-readable output from Nmap as the scan runs.
    * **Parsed Results Tab:** Displays scan results in a sortable table (Host, Proto, Port, State, Service, Product, Version).
    * **Host Details Area:** (Always visible below tabs) Displays detailed information for the host selected in the Parsed Results table, including:
        * Hostname, IP Address, State
        * MAC Address and Vendor (if available)
        * OS Detection results (guesses and accuracy)
        * Detailed Port/Service list
        * NSE Script output (both host-level and port-level)
* **File Operations:**
    * Save completed scan results to an Nmap XML file.
    * Open and display results from previously saved Nmap XML files.
    * Prompt to save unsaved results on application close.

**Planned Features:**

* **Phase 6:** Topology View (Graphical network map).
* **Phase 7:** Packaging & Distribution (Standalone executables for Windows, macOS, Linux).
* More detailed scan configuration options (UI controls for specific flags).
* Scan comparison functionality.
* Advanced UI polish (icons, themes, user preferences).

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

1. Enter a target (IP address, hostname, or network range)
2. Select a scan profile or customize Nmap arguments
3. Click "Scan" to start
4. View results in real-time in the Raw Output tab
5. Explore parsed results in the Parsed Results tab
6. Save results via File > Save Scan Results

**Note:** Some scan types require administrator/root privileges. NeoZen will warn you in the status bar when privileged scans are selected.

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