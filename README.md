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

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd neozen_project
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    # Create venv (use python3 if python points to Python 2)
    python -m venv venv

    # Activate venv
    # Windows (cmd/powershell):
    .\venv\Scripts\activate
    # macOS/Linux (bash/zsh):
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    # Ensure pip is using the venv's Python
    python -m pip install -r requirements.txt
    ```

## Usage

1.  Make sure your virtual environment is activated.
2.  Run the main application script from the project root directory:
    ```bash
    python main.py
    ```
3.  Enter a target, select a scan profile or options, and click "Scan".

## License

*(Currently unlicensed. Choose an appropriate open-source license like MIT, GPLv2+, etc., and add a LICENSE file).*

## Contributing

*(Optional: Add guidelines here if you plan to accept contributions).*

---

*This README is a work in progress and will be updated as the project develops.*