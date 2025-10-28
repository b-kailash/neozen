# NeoZen - Modern Nmap GUI

**A modern, cross-platform interface for Nmap with dual desktop and web interfaces**

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/yourusername/neozen)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)

---

## What is NeoZen?

NeoZen provides an intuitive graphical interface for Nmap, the industry-standard network scanner. Choose between a rich desktop application or a browser-based web dashboard—both interfaces share the same powerful scanning engine.

### Why NeoZen?

- **🌐 Dual Interface** - Desktop GUI (PyQt6) or Web Dashboard (browser-based)
- **🚀 Easy Deployment** - Run with Docker in seconds
- **🎯 User-Friendly** - Visual scan builder, predefined profiles, real-time results
- **🏗️ Clean Architecture** - GUI-agnostic core, minimal dependencies
- **🔒 Privileged Scans** - Automatic sudo handling for OS detection and SYN scans
- **💻 Cross-Platform** - Linux, macOS, Windows support

---

## Quick Start (Recommended)

### Web Dashboard - Docker (Fastest) ⭐

**Get running in 30 seconds:**

```bash
git clone https://github.com/yourusername/neozen.git
cd neozen
docker-compose --profile web up -d
```

**Access:** http://localhost:8080 (login: admin/admin)

**📖 [Complete Web Setup Guide →](WEB_SETUP.md)**

---

### Desktop GUI - Python

```bash
git clone https://github.com/yourusername/neozen.git
cd neozen
pip install -e ".[desktop]"
python main.py
```

---

## Installation Options

| Method | Best For | Setup Time | Documentation |
|--------|----------|------------|---------------|
| **Docker Web** ⭐ | Servers, remote access, multi-user | 30 seconds | **[Web Setup Guide](WEB_SETUP.md)** |
| **Docker Desktop** | Containerized desktop | 1 minute | See below |
| **Python Web** | Development, customization | 2 minutes | **[Web Setup Guide](WEB_SETUP.md)** |
| **Python Desktop** | Local desktop use | 2 minutes | See below |

### Docker Desktop GUI

```bash
xhost +local:docker  # Allow X11 forwarding (Linux/macOS)
docker-compose --profile desktop up -d
```

### Python - Desktop GUI

```bash
git clone https://github.com/yourusername/neozen.git
cd neozen
python3 -m venv venv
source venv/bin/activate  # .\venv\Scripts\activate on Windows
pip install -e ".[desktop]"
python main.py
```

### Automated Scripts

**Linux/macOS:** `./install.sh` | **Windows:** `install.bat`

---

## Features

### Scan Configuration
- **Visual Scan Builder** - Interactive dialog with intelligent option compatibility
- **Predefined Scan Types** - Intense, Quick, Ping, TCP SYN, UDP, and more
- **Profile Management** - Save and reuse scan configurations
- **OS Detection** - Automatic OS fingerprinting (requires privileges)
- **Service Detection** - Identify services and versions
- **Custom Arguments** - Full Nmap command-line flexibility

### Scan Execution
- **Real-Time Output** - Live console output during scans
- **Progress Tracking** - Visual indication of scan progress
- **Parallel Scanning** - Scan multiple hosts simultaneously (up to 10 workers)
- **Stop/Resume** - Control scans with start/stop buttons
- **Automatic Sudo** - Handles privileged operations transparently

### Results & Analysis
- **Parsed Results** - Structured tables with host details
- **Port Information** - State, service, product, version
- **OS Detection Results** - Operating system identification
- **MAC Addresses** - Vendor identification
- **Export Options** - Save results as XML, JSON, or CSV
- **Host Notes** - Add persistent documentation to discovered hosts

### Interface Options

#### Desktop GUI (PyQt6)
- Native desktop application
- Split-panel layout
- Advanced scan builder dialog
- Profile manager
- Host notes with persistence

#### Web Dashboard (Flask)
- Browser-based interface
- **Multi-user support** with authentication
- **Per-user scan isolation** and history
- Real-time WebSocket updates
- Responsive design (works on mobile)
- Remote access ready
- No installation required (Docker)

### Multi-User Features (Web Dashboard)

The web dashboard supports multiple concurrent users with full data isolation:

- **User Authentication** - Secure login system with password hashing
- **Session Management** - Per-user scan sessions and results
- **Scan History** - Each user has their own scan history database
- **Device Notes** - Per-user notes for documented hosts
- **Concurrent Scanning** - Multiple users can run scans simultaneously
- **Data Isolation** - WebSocket rooms ensure users only see their own updates

**Default Credentials:**
- Username: `admin`
- Password: `admin`

⚠️ **Security Notice:** Change the default admin password immediately after first login. The web interface does not use HTTPS by default—consider using a reverse proxy (nginx, Caddy) with SSL/TLS for production deployments.

**Database:** The web interface uses SQLite (`neozen.db`) by default. For production deployments, configure `DATABASE_URL` environment variable to use PostgreSQL or MySQL.

---

## Usage

### Web Interface

1. **Start the server** (Docker or Python)
2. **Open browser** to http://localhost:8080
3. **Login** with credentials (default: admin/admin)
4. **Configure scan:**
   - Enter target (IP, hostname, or network range)
   - Select scan type from dropdown
   - Enable OS/Service detection if needed
   - Optional: Enable parallel scanning for network ranges
5. **Start scan** and view real-time output
6. **Switch to "Device List"** tab for structured data
7. **Click on a device** to view detailed port information
8. **Add notes** to devices for documentation (saved per-user)
9. **Export results** as XML, JSON, or CSV
10. **View scan history** via API: `GET /api/scans/history`

### Desktop GUI

1. **Launch application:** `python main.py`
2. **Configure target and scan options**
3. **Use Visual Scan Builder** for advanced configurations
4. **Save profiles** for frequently used scans
5. **View results** in real-time
6. **Add notes** to hosts for documentation

---

## Network Access

The web interface is accessible at:
- **Local machine:** http://localhost:8080
- **Same network:** http://SERVER_IP:8080
- **Internet:** Requires port forwarding and firewall configuration

**Quick firewall setup (allow port 8080):**
```bash
sudo ufw allow 8080/tcp  # Linux (UFW)
```

**📖 For production deployment, SSL, reverse proxy, and security configuration, see [Web Setup Guide](WEB_SETUP.md#production-deployment)**

---

## Architecture

NeoZen uses a **layered architecture** that separates core logic from UI frameworks:

```
┌─────────────────────────────────────────────────┐
│           UI Layer (PyQt6 / Flask)              │
│  ┌──────────────────┐  ┌────────────────────┐  │
│  │ Desktop GUI      │  │  Web Dashboard     │  │
│  │  (main_window.py)│  │  (app.py)          │  │
│  └──────────────────┘  └────────────────────┘  │
├─────────────────────────────────────────────────┤
│          Adapter Layer (Framework-Specific)     │
│  ┌──────────────────┐  ┌────────────────────┐  │
│  │ QtScannerAdapter │  │  Direct Callbacks  │  │
│  │  (qt_scanner.py) │  │  (no adapter)      │  │
│  └──────────────────┘  └────────────────────┘  │
├─────────────────────────────────────────────────┤
│        Core Layer (Pure Python, GUI-agnostic)   │
│  ┌──────────────────────────────────────────┐  │
│  │ NmapScanner / ParallelNmapScanner        │  │
│  │ (scanner_core.py - threading.Thread)     │  │
│  │ • Callback-based communication           │  │
│  │ • No GUI dependencies                    │  │
│  │ • Reusable across interfaces             │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Benefits:**
- Core scanner works without any GUI framework
- Web interface doesn't need PyQt6 (~100MB savings)
- Easy to add new interfaces (CLI, API, mobile)
- Better testability and maintainability

For detailed architecture documentation, see [CLAUDE.md](CLAUDE.md).

---

## Requirements

### Core Requirements
- **Nmap** - Must be installed and in system PATH ([download here](https://nmap.org))
- **Python 3.7+** - Only for non-Docker installations

### Docker Requirements
- **Docker** - For containerized deployment
- **Web browser** - For web interface

### Interface-Specific Requirements

| Interface | Requirements | Installation |
|-----------|-------------|--------------|
| **Web Dashboard** | Flask, python-nmap, psutil | `pip install -e ".[web]"` |
| **Desktop GUI** | PyQt6, python-nmap, psutil | `pip install -e ".[desktop]"` |
| **Both** | All of the above | `pip install -e ".[all]"` |
| **Docker** | None (everything included) | - |

---

## Privileged Scans

Some Nmap features require root/administrator privileges:
- **OS Detection** (-O)
- **SYN Scans** (-sS)
- **UDP Scans** (-sU)

### How NeoZen Handles This

**Docker (Web Interface):**
- ✅ Automatically configured with passwordless sudo for nmap
- ✅ Runs as non-root user with sudo privileges for nmap only
- ✅ No manual configuration needed

**Desktop GUI / Python:**
- On Linux/macOS: Run with sudo or configure sudoers
- On Windows: Run as Administrator

### Manual Sudo Configuration (Linux/macOS)

If not using Docker, configure passwordless sudo for nmap:

```bash
# Create sudoers file
echo "$USER ALL=(root) NOPASSWD: /usr/bin/nmap" | sudo tee /etc/sudoers.d/nmap-neozen
sudo chmod 0440 /etc/sudoers.d/nmap-neozen
```

---

## Development

### Project Structure
```
neozen/
├── neozen/
│   ├── core/              # Pure Python scanner (GUI-agnostic)
│   │   ├── scanner_core.py    # NmapScanner, ParallelNmapScanner
│   │   ├── profiles.py        # Profile management
│   │   └── models.py          # Data models
│   ├── adapters/          # Framework-specific adapters
│   │   ├── qt_scanner.py      # PyQt6 adapter
│   │   └── web_scanner.py     # Flask adapter (unused - uses core directly)
│   ├── ui/                # Desktop GUI (PyQt6)
│   │   ├── main_window.py     # Main application window
│   │   └── styles.py          # UI styling
│   └── web/               # Web Dashboard (Flask)
│       ├── app.py             # Flask application
│       ├── templates/         # HTML templates
│       └── static/            # CSS, JavaScript
├── main.py                # Desktop GUI entry point
├── Dockerfile             # Desktop container
├── Dockerfile.web         # Web container
├── docker-compose.yml     # Multi-container configuration
└── README.md              # This file
```

### Running from Source

```bash
# Clone repository
git clone https://github.com/yourusername/neozen.git
cd neozen

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[all]"

# Run desktop GUI
python main.py

# Or run web dashboard
python -m neozen.web.app
```

### Building Executables

```bash
# Linux/macOS
./build.sh

# Windows
build.bat
```

Executables will be created in the `dist/` directory.

---

## Troubleshooting

### Docker: Permission Denied Errors
If you see "Permission denied" for nmap operations:
```bash
# Rebuild with latest image
docker-compose --profile web build --no-cache
docker-compose --profile web up -d
```

### Docker: Cannot Resolve Host Warning
This is harmless but can be fixed by rebuilding with the latest Dockerfile.

### Web Interface: Connection Refused
Check firewall settings:
```bash
# Linux
sudo ufw status
sudo ufw allow 8080/tcp

# Check if port is listening
sudo ss -tlnp | grep 8080
```

### Desktop GUI: No Display
Ensure X11 forwarding is configured:
```bash
# Linux/macOS
xhost +local:docker
```

### Scans Failing: OS Detection Errors
OS detection requires privileges. Use Docker (automatic) or configure sudo manually.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Nmap** - The incredible network scanner by Gordon Lyon ([nmap.org](https://nmap.org))
- **PyQt6** - Python bindings for Qt6
- **Flask** - Micro web framework
- **python-nmap** - Python library for parsing Nmap XML output

---

## Roadmap

- [ ] Network topology visualization
- [ ] Comparison of scan results over time
- [ ] Integration with vulnerability databases
- [ ] API server mode
- [ ] Mobile-optimized interface
- [ ] Scan scheduling and automation
- [ ] Multi-user support with authentication

---

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/neozen/issues)
- **Documentation:** See [CLAUDE.md](CLAUDE.md) for architecture details
- **Nmap Help:** [Nmap Documentation](https://nmap.org/docs.html)

---

**Made with ❤️ for the security and network administration community**
