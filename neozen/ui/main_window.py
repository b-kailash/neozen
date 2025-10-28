import sys
import json
import os
import nmap
import shutil
from pathlib import Path
import shlex # Import shlex for safer argument splitting/joining
from datetime import datetime
import csv

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QFileDialog,
    QAbstractItemView, QSplitter, QSpinBox # Added QSplitter and QSpinBox
)
from PyQt6.QtGui import QAction, QFont, QIcon # Added QFont and QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from neozen.adapters.qt_scanner import QtScannerAdapter as Scanner, QtParallelScannerAdapter
from neozen.core.profiles import ProfileManager
from neozen.resources import get_icon_path

# --- Custom Scan Builder Dialog ---
class CustomScanDialog(QDialog):
    """
    Dialog for building custom scan types by selecting various Nmap options.
    Handles option incompatibilities by disabling conflicting options.
    """
    def __init__(self, parent=None):
        """Initializes the custom scan builder dialog."""
        super().__init__(parent)
        self.setWindowTitle("Custom Scan Builder")
        self.setMinimumWidth(600)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create scroll area for options
        scroll = QWidget()
        scroll_layout = QVBoxLayout(scroll)

        # --- Scan Techniques (Mutually Exclusive) ---
        scan_tech_group = QWidget()
        scan_tech_layout = QVBoxLayout(scan_tech_group)
        scan_tech_layout.addWidget(QLabel("<b>Scan Technique:</b>"))

        self.scan_technique_group = []
        scan_techniques = [
            ("sS", "TCP SYN Scan (-sS)", "Stealth scan, requires privileges"),
            ("sT", "TCP Connect Scan (-sT)", "Full TCP connection, no privileges needed"),
            ("sU", "UDP Scan (-sU)", "Scan UDP ports, requires privileges"),
            ("sA", "TCP ACK Scan (-sA)", "Map firewall rulesets, requires privileges"),
            ("sW", "TCP Window Scan (-sW)", "Differentiate open/closed ports, requires privileges"),
            ("sN", "TCP Null Scan (-sN)", "No flags set, requires privileges"),
            ("sF", "TCP FIN Scan (-sF)", "FIN flag only, requires privileges"),
            ("sX", "TCP Xmas Scan (-sX)", "FIN, PSH, URG flags, requires privileges"),
            ("sn", "Ping Scan (-sn)", "Host discovery only, no port scan"),
        ]

        for key, label, tooltip in scan_techniques:
            cb = QCheckBox(label)
            cb.setToolTip(tooltip)
            cb.setProperty("option_key", key)
            cb.stateChanged.connect(self._on_scan_technique_changed)
            self.scan_technique_group.append(cb)
            scan_tech_layout.addWidget(cb)

        scroll_layout.addWidget(scan_tech_group)

        # --- Port Specification ---
        port_group = QWidget()
        port_layout = QVBoxLayout(port_group)
        port_layout.addWidget(QLabel("<b>Port Specification:</b>"))

        self.port_fast_cb = QCheckBox("Fast Scan (-F)")
        self.port_fast_cb.setToolTip("Scan fewer ports than default (top 100)")
        self.port_fast_cb.stateChanged.connect(self._on_option_changed)

        self.port_all_cb = QCheckBox("All Ports (-p-)")
        self.port_all_cb.setToolTip("Scan all 65535 ports")
        self.port_all_cb.stateChanged.connect(self._on_option_changed)

        self.port_top_cb = QCheckBox("Top Ports (-p 1-1000)")
        self.port_top_cb.setToolTip("Scan ports 1-1000")
        self.port_top_cb.stateChanged.connect(self._on_option_changed)

        port_layout.addWidget(self.port_fast_cb)
        port_layout.addWidget(self.port_all_cb)
        port_layout.addWidget(self.port_top_cb)

        scroll_layout.addWidget(port_group)

        # --- Timing Template (Mutually Exclusive) ---
        timing_group = QWidget()
        timing_layout = QVBoxLayout(timing_group)
        timing_layout.addWidget(QLabel("<b>Timing Template:</b>"))

        self.timing_group = []
        timings = [
            ("T0", "Paranoid (-T0)", "Very slow, for IDS evasion"),
            ("T1", "Sneaky (-T1)", "Slow, for IDS evasion"),
            ("T2", "Polite (-T2)", "Slower, less bandwidth"),
            ("T3", "Normal (-T3)", "Default timing"),
            ("T4", "Aggressive (-T4)", "Faster, assumes fast network"),
            ("T5", "Insane (-T5)", "Very fast, may sacrifice accuracy"),
        ]

        for key, label, tooltip in timings:
            cb = QCheckBox(label)
            cb.setToolTip(tooltip)
            cb.setProperty("option_key", key)
            cb.stateChanged.connect(self._on_timing_changed)
            self.timing_group.append(cb)
            timing_layout.addWidget(cb)

        scroll_layout.addWidget(timing_group)

        # --- Detection Options ---
        detection_group = QWidget()
        detection_layout = QVBoxLayout(detection_group)
        detection_layout.addWidget(QLabel("<b>Detection & Enumeration:</b>"))

        self.detect_os_cb = QCheckBox("OS Detection (-O)")
        self.detect_os_cb.setToolTip("Enable OS detection (requires privileges)")

        self.detect_version_cb = QCheckBox("Version Detection (-sV)")
        self.detect_version_cb.setToolTip("Probe open ports to determine service/version")

        self.detect_scripts_cb = QCheckBox("Default Scripts (-sC)")
        self.detect_scripts_cb.setToolTip("Run default NSE scripts")

        self.detect_aggressive_cb = QCheckBox("Aggressive Scan (-A)")
        self.detect_aggressive_cb.setToolTip("Enable OS detection, version detection, script scanning, and traceroute")
        self.detect_aggressive_cb.stateChanged.connect(self._on_aggressive_changed)

        detection_layout.addWidget(self.detect_os_cb)
        detection_layout.addWidget(self.detect_version_cb)
        detection_layout.addWidget(self.detect_scripts_cb)
        detection_layout.addWidget(self.detect_aggressive_cb)

        scroll_layout.addWidget(detection_group)

        # --- Other Options ---
        other_group = QWidget()
        other_layout = QVBoxLayout(other_group)
        other_layout.addWidget(QLabel("<b>Other Options:</b>"))

        self.verbose_cb = QCheckBox("Verbose Output (-v)")
        self.verbose_cb.setToolTip("Increase verbosity level")

        self.verbose2_cb = QCheckBox("Very Verbose (-vv)")
        self.verbose2_cb.setToolTip("Increase verbosity level even more")
        self.verbose2_cb.stateChanged.connect(self._on_option_changed)

        self.reason_cb = QCheckBox("Show Reason (--reason)")
        self.reason_cb.setToolTip("Display reason for port state")

        self.packet_trace_cb = QCheckBox("Packet Trace (--packet-trace)")
        self.packet_trace_cb.setToolTip("Show all packets sent and received")

        self.no_dns_cb = QCheckBox("No DNS Resolution (-n)")
        self.no_dns_cb.setToolTip("Never do DNS resolution")

        # Parallel scanning option
        self.parallel_scan_cb = QCheckBox("Enable Parallel Scanning")
        self.parallel_scan_cb.setToolTip("Discover live hosts first, then scan them in parallel for faster results")
        self.parallel_scan_cb.stateChanged.connect(self._on_parallel_scan_changed)

        # Max workers spinbox (only enabled when parallel scanning is enabled)
        workers_layout = QHBoxLayout()
        workers_label = QLabel("Max Workers:")
        workers_label.setToolTip("Number of parallel scanner threads (1-10)")
        self.max_workers_spinbox = QSpinBox()
        self.max_workers_spinbox.setRange(1, 10)
        self.max_workers_spinbox.setValue(5)
        self.max_workers_spinbox.setEnabled(False)  # Disabled by default
        self.max_workers_spinbox.setToolTip("Number of parallel scanner threads")
        workers_layout.addWidget(workers_label)
        workers_layout.addWidget(self.max_workers_spinbox)
        workers_layout.addStretch()

        other_layout.addWidget(self.verbose_cb)
        other_layout.addWidget(self.verbose2_cb)
        other_layout.addWidget(self.reason_cb)
        other_layout.addWidget(self.packet_trace_cb)
        other_layout.addWidget(self.no_dns_cb)
        other_layout.addWidget(self.parallel_scan_cb)
        other_layout.addLayout(workers_layout)

        scroll_layout.addWidget(other_group)

        # Add scroll area
        main_layout.addWidget(scroll)

        # --- Command Preview ---
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("<b>Command Preview:</b>"))
        self.command_preview = QLineEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setFont(QFont("Monospace"))
        preview_layout.addWidget(self.command_preview)
        main_layout.addLayout(preview_layout)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # Initial update
        self._update_command_preview()

    def _on_scan_technique_changed(self):
        """Handle scan technique selection (mutually exclusive within group)."""
        sender = self.sender()
        if sender.isChecked():
            # Uncheck all other scan techniques
            for cb in self.scan_technique_group:
                if cb != sender:
                    cb.setChecked(False)

        # Check for ping scan compatibility
        self._check_ping_scan_compatibility()
        self._update_command_preview()

    def _on_timing_changed(self):
        """Handle timing template selection (mutually exclusive)."""
        sender = self.sender()
        if sender.isChecked():
            # Uncheck all other timing templates
            for cb in self.timing_group:
                if cb != sender:
                    cb.setChecked(False)

        self._update_command_preview()

    def _on_aggressive_changed(self):
        """Handle aggressive scan option (disables individual detection options)."""
        is_aggressive = self.detect_aggressive_cb.isChecked()

        # Disable individual detection options when -A is selected
        self.detect_os_cb.setEnabled(not is_aggressive)
        self.detect_version_cb.setEnabled(not is_aggressive)
        self.detect_scripts_cb.setEnabled(not is_aggressive)

        if is_aggressive:
            # Uncheck the individual options
            self.detect_os_cb.setChecked(False)
            self.detect_version_cb.setChecked(False)
            self.detect_scripts_cb.setChecked(False)

        self._update_command_preview()

    def _on_parallel_scan_changed(self):
        """Handle parallel scanning option (enables/disables max workers spinbox)."""
        is_parallel = self.parallel_scan_cb.isChecked()
        self.max_workers_spinbox.setEnabled(is_parallel)

    def _on_option_changed(self):
        """Handle general option changes."""
        # Port specification mutual exclusivity
        sender = self.sender()
        if sender == self.port_fast_cb and self.port_fast_cb.isChecked():
            self.port_all_cb.setChecked(False)
            self.port_top_cb.setChecked(False)
        elif sender == self.port_all_cb and self.port_all_cb.isChecked():
            self.port_fast_cb.setChecked(False)
            self.port_top_cb.setChecked(False)
        elif sender == self.port_top_cb and self.port_top_cb.isChecked():
            self.port_fast_cb.setChecked(False)
            self.port_all_cb.setChecked(False)

        # Verbose mutual exclusivity
        if sender == self.verbose2_cb and self.verbose2_cb.isChecked():
            self.verbose_cb.setChecked(False)

        self._check_ping_scan_compatibility()
        self._update_command_preview()

    def _check_ping_scan_compatibility(self):
        """Disable port-related options when ping scan (-sn) is selected."""
        ping_scan_selected = False
        for cb in self.scan_technique_group:
            if cb.property("option_key") == "sn" and cb.isChecked():
                ping_scan_selected = True
                break

        # Disable port options when ping scan is selected
        self.port_fast_cb.setEnabled(not ping_scan_selected)
        self.port_all_cb.setEnabled(not ping_scan_selected)
        self.port_top_cb.setEnabled(not ping_scan_selected)

        if ping_scan_selected:
            self.port_fast_cb.setChecked(False)
            self.port_all_cb.setChecked(False)
            self.port_top_cb.setChecked(False)

    def _update_command_preview(self):
        """Update the command preview based on selected options."""
        args = []

        # Scan techniques
        for cb in self.scan_technique_group:
            if cb.isChecked():
                args.append(f"-{cb.property('option_key')}")

        # Port specification
        if self.port_fast_cb.isChecked():
            args.append("-F")
        elif self.port_all_cb.isChecked():
            args.append("-p-")
        elif self.port_top_cb.isChecked():
            args.append("-p 1-1000")

        # Timing
        for cb in self.timing_group:
            if cb.isChecked():
                args.append(f"-{cb.property('option_key')}")

        # Detection
        if self.detect_aggressive_cb.isChecked():
            args.append("-A")
        else:
            if self.detect_os_cb.isChecked():
                args.append("-O")
            if self.detect_version_cb.isChecked():
                args.append("-sV")
            if self.detect_scripts_cb.isChecked():
                args.append("-sC")

        # Other options
        if self.verbose2_cb.isChecked():
            args.append("-vv")
        elif self.verbose_cb.isChecked():
            args.append("-v")

        if self.reason_cb.isChecked():
            args.append("--reason")
        if self.packet_trace_cb.isChecked():
            args.append("--packet-trace")
        if self.no_dns_cb.isChecked():
            args.append("-n")

        # Update preview
        command = "nmap " + " ".join(args) + " <target>"
        self.command_preview.setText(command)

    def get_arguments(self):
        """
        Returns the constructed Nmap arguments string.

        Returns:
            str: Nmap arguments
        """
        args = []

        # Scan techniques
        for cb in self.scan_technique_group:
            if cb.isChecked():
                args.append(f"-{cb.property('option_key')}")

        # Port specification
        if self.port_fast_cb.isChecked():
            args.append("-F")
        elif self.port_all_cb.isChecked():
            args.append("-p-")
        elif self.port_top_cb.isChecked():
            args.append("-p 1-1000")

        # Timing
        for cb in self.timing_group:
            if cb.isChecked():
                args.append(f"-{cb.property('option_key')}")

        # Detection
        if self.detect_aggressive_cb.isChecked():
            args.append("-A")
        else:
            if self.detect_os_cb.isChecked():
                args.append("-O")
            if self.detect_version_cb.isChecked():
                args.append("-sV")
            if self.detect_scripts_cb.isChecked():
                args.append("-sC")

        # Other options
        if self.verbose2_cb.isChecked():
            args.append("-vv")
        elif self.verbose_cb.isChecked():
            args.append("-v")

        if self.reason_cb.isChecked():
            args.append("--reason")
        if self.packet_trace_cb.isChecked():
            args.append("--packet-trace")
        if self.no_dns_cb.isChecked():
            args.append("-n")

        return " ".join(args)


# --- Save Scan Results Dialog ---
class SaveScanDialog(QDialog):
    """
    Dialog for saving scan results with options for including raw output.
    """
    def __init__(self, has_raw_output=True, parent=None):
        """
        Initializes the save scan dialog.

        Args:
            has_raw_output (bool): Whether raw output is available
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Save Scan Results")
        layout = QVBoxLayout(self)

        # Information label
        info_label = QLabel("Choose save options:")
        layout.addWidget(info_label)

        # Checkbox for including raw output
        self.include_raw_checkbox = QCheckBox("Include raw output in XML file")
        self.include_raw_checkbox.setChecked(True)  # Checked by default
        self.include_raw_checkbox.setEnabled(has_raw_output)
        if not has_raw_output:
            self.include_raw_checkbox.setToolTip("No raw output available")
        layout.addWidget(self.include_raw_checkbox)

        # Standard OK and Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def include_raw_output(self):
        """
        Returns whether to include raw output.

        Returns:
            bool: True if raw output should be included
        """
        return self.include_raw_checkbox.isChecked()


# --- Profile Save Dialog ---
class SaveProfileDialog(QDialog):
    """
    A simple dialog window to prompt the user for a profile name when saving.
    """
    def __init__(self, parent=None):
        """Initializes the dialog."""
        super().__init__(parent)
        self.setWindowTitle("Save Profile")
        layout = QVBoxLayout(self)

        # Form layout for label and input field
        self.form_layout = QFormLayout()
        self.profile_name_input = QLineEdit(self)
        self.form_layout.addRow("Profile Name:", self.profile_name_input)
        layout.addLayout(self.form_layout)

        # Standard OK and Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept) # Connect OK button to accept() slot
        self.button_box.rejected.connect(self.reject) # Connect Cancel button to reject() slot
        layout.addWidget(self.button_box)

    def get_profile_name(self):
        """
        Returns the text entered by the user in the profile name input field.

        Returns:
            str: The entered profile name, stripped of leading/trailing whitespace.
        """
        return self.profile_name_input.text().strip()

# --- CSV Export Column Selection Dialog ---
class CSVExportDialog(QDialog):
    """
    Dialog for selecting which columns to export to CSV.
    """
    def __init__(self, column_headers, parent=None):
        """
        Initialize the CSV export dialog.

        Args:
            column_headers: List of column header names from the table
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Export to CSV")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Select columns to export:")
        layout.addWidget(instructions)

        # Checkboxes for each column
        self.column_checkboxes = []
        for header in column_headers:
            checkbox = QCheckBox(header)
            checkbox.setChecked(True)  # All columns selected by default
            self.column_checkboxes.append(checkbox)
            layout.addWidget(checkbox)

        # Select All / Deselect All buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        layout.addLayout(button_layout)

        # OK and Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _select_all(self):
        """Select all column checkboxes."""
        for checkbox in self.column_checkboxes:
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Deselect all column checkboxes."""
        for checkbox in self.column_checkboxes:
            checkbox.setChecked(False)

    def get_selected_columns(self):
        """
        Get indices of selected columns.

        Returns:
            List of column indices that are selected
        """
        return [i for i, checkbox in enumerate(self.column_checkboxes) if checkbox.isChecked()]

# --- Main Window ---
class MainWindow(QMainWindow):
    """
    The main application window for NeoZen.

    Provides the user interface for configuring Nmap scans, viewing results,
    managing profiles, and accessing scan details. Includes NSE script output display.
    """
    # List of Nmap flags that typically require root/administrator privileges
    PRIVILEGED_FLAGS = ['-sS', '-sU', '-O', '-A']

    def __init__(self):
        """Initializes the main window, sets up UI components, and loads profiles."""
        super().__init__()

        # Initialize core components
        self.profile_manager = ProfileManager() # Handles loading/saving profiles
        self.profiles = self.profile_manager.load_profiles() # Load existing profiles
        self.scanner_thread = None # Placeholder for the background scanner thread
        self.last_scan_xml_path = None # Path to temp XML file from the last completed scan
        self.current_scan_data = {} # Stores the fully parsed data from the last scan/loaded file
        self._current_status_message = "Ready" # Base message for the status bar
        self.results_saved = False # Track if scan results have been saved
        self.host_notes = {} # Store user notes for each host IP {host_ip: note_text}
        self.current_selected_host = None # Track currently selected host for notes

        # --- Window Setup ---
        self.setWindowTitle("NeoZen - Modern Nmap GUI")
        self.setWindowIcon(QIcon(get_icon_path()))
        self.setGeometry(100, 100, 950, 900) # Set initial position and size

        # --- Build UI Components ---
        self._create_actions() # Define menu actions
        self._create_menu_bar() # Create the main menu bar
        self._create_central_widget() # Create the central layout and widgets
        self._create_status_bar() # Create the status bar with a label
        self._connect_signals() # Connect UI element signals to methods (slots)

        # --- Initial UI State ---
        self._update_command_display() # Show initial placeholder command
        self._check_and_warn_privileged_scan() # Check initial profile/scan type

    def _create_actions(self):
        """Creates QAction objects for menu items and connects their triggers."""
        # File -> Open
        self.open_action = QAction("&Open Scan Results...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setStatusTip("Open saved Nmap XML scan results")
        self.open_action.triggered.connect(self.open_scan_results)

        # File -> Save
        self.save_action = QAction("&Save Scan Results...", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setStatusTip("Save scan results (with optional raw output)")
        self.save_action.setEnabled(False) # Initially disabled
        self.save_action.triggered.connect(self.save_scan_results)

        # File -> Export to CSV
        self.export_csv_action = QAction("&Export to CSV...", self)
        self.export_csv_action.setShortcut("Ctrl+E")
        self.export_csv_action.setStatusTip("Export device details table to CSV file")
        self.export_csv_action.setEnabled(False) # Initially disabled
        self.export_csv_action.triggered.connect(self.export_to_csv)

        # File -> Exit
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close) # Use the built-in close method

        # Help -> About
        self.about_action = QAction("&About NeoZen", self)
        self.about_action.setStatusTip("Show information about NeoZen")
        self.about_action.triggered.connect(self.show_about_dialog)


    def _create_menu_bar(self):
        """Creates the main menu bar and adds the defined actions."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.export_csv_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)


    def _create_central_widget(self):
        """Creates the central widget and arranges all UI elements within it."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Main vertical layout for the entire central area
        main_layout = QVBoxLayout(central_widget)

        # --- Top Configuration Section ---
        # Group config widgets together for organization
        config_widget = QWidget()
        config_main_layout = QVBoxLayout(config_widget)
        config_main_layout.setContentsMargins(0,0,0,0) # Remove extra spacing

        # Target and Profile selection row
        top_row_layout = QHBoxLayout()
        target_label = QLabel("Target:")
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter IP address, hostname, or network range")
        profile_label = QLabel("Profile:")
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Custom Scan") # Default, non-saved option
        self.profile_combo.addItems(sorted(self.profiles.keys())) # Add loaded profiles
        self.profile_combo.setToolTip("Select a saved scan profile or choose 'Custom Scan'")
        top_row_layout.addWidget(target_label)
        top_row_layout.addWidget(self.target_input, 1) # Allow target input to stretch
        top_row_layout.addWidget(profile_label)
        top_row_layout.addWidget(self.profile_combo, 1) # Allow profile combo to stretch

        # Scan Type and Custom Arguments row (using a grid for alignment)
        scan_config_layout = QGridLayout()
        scan_type_label = QLabel("Scan Type:")
        self.scan_type_combo = QComboBox()
        # Add predefined scan types with associated arguments and tooltips
        self.scan_type_combo.addItem("Intense scan (-T4 -A -v)", "-T4 -A -v")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "Intense Scan (includes OS detection, requires privileges)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("Intense scan plus UDP (-T4 -A -sU -v)", "-T4 -A -sU -v")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "Intense Scan + UDP (requires privileges)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("Intense scan, all TCP ports (-p 1-65535 -T4 -A -v)", "-p 1-65535 -T4 -A -v")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "Intense Scan, All Ports (requires privileges)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("Ping scan (-sn)", "-sn")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "Ping Scan (Host Discovery Only)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("Quick scan (-T4 -F)", "-T4 -F")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "Quick Scan (Fast scan, limited ports)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("Regular scan (Default Nmap)", "")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "Regular Scan (Default Nmap behavior, may use -sS if run as root)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("TCP SYN scan (-sS)", "-sS")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "TCP SYN Scan (Stealth Scan, requires privileges)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("TCP Connect scan (-sT)", "-sT")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "TCP Connect Scan (Reliable, does not require privileges)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.addItem("UDP scan (-sU)", "-sU")
        self.scan_type_combo.setItemData(self.scan_type_combo.count()-1, "UDP Scan (Requires privileges)", Qt.ItemDataRole.ToolTipRole)
        self.scan_type_combo.setToolTip("Select a common scan type (sets arguments below)")

        # OS Detection checkbox
        self.os_detection_checkbox = QCheckBox("Enable OS Detection (-O)")
        self.os_detection_checkbox.setChecked(True)  # Enabled by default
        self.os_detection_checkbox.setToolTip("Add OS detection to the scan (requires privileges)")

        # Service Version Detection checkbox
        self.service_detection_checkbox = QCheckBox("Enable Service/Version Detection (-sV)")
        self.service_detection_checkbox.setChecked(True)  # Enabled by default
        self.service_detection_checkbox.setToolTip("Probe open ports to determine service/version info (no privileges required)")

        custom_args_label = QLabel("Nmap Arguments:")
        self.custom_args_input = QLineEdit()
        self.custom_args_input.setPlaceholderText("e.g., -p 80,443 --script=vuln")
        self.custom_args_input.setToolTip("Arguments defined by Scan Type, or enter custom ones")

        # Custom Scan Builder button
        self.custom_scan_builder_btn = QPushButton("Build Custom Scan...")
        self.custom_scan_builder_btn.setToolTip("Open visual builder for creating custom scan arguments")

        scan_config_layout.addWidget(scan_type_label, 0, 0)
        scan_config_layout.addWidget(self.scan_type_combo, 0, 1)
        scan_config_layout.addWidget(self.os_detection_checkbox, 0, 2)
        scan_config_layout.addWidget(self.service_detection_checkbox, 0, 3)
        scan_config_layout.addWidget(custom_args_label, 1, 0)
        scan_config_layout.addWidget(self.custom_args_input, 1, 1, 1, 2)
        scan_config_layout.addWidget(self.custom_scan_builder_btn, 1, 3)

        # Command display row
        command_display_layout = QHBoxLayout()
        command_label = QLabel("Command:")
        self.command_display_line = QLineEdit()
        self.command_display_line.setReadOnly(True)
        self.command_display_line.setFont(QFont("Monospace")) # Use Monospace font
        self.command_display_line.setToolTip("The exact Nmap command that will be executed")
        command_display_layout.addWidget(command_label)
        command_display_layout.addWidget(self.command_display_line)

        # Add config layouts to the config group widget
        config_main_layout.addLayout(top_row_layout)
        config_main_layout.addLayout(scan_config_layout)
        config_main_layout.addLayout(command_display_layout)
        # --- End Config Section ---


        # --- Scan Control and Profile Buttons ---
        button_layout = QHBoxLayout()
        self.scan_button = QPushButton("Scan")
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setObjectName("stop_button")  # For custom styling
        self.stop_button.setEnabled(False) # Disabled initially
        self.save_profile_button = QPushButton("Save Profile")
        self.save_profile_button.setObjectName("save_profile_button")  # For custom styling
        self.delete_profile_button = QPushButton("Delete Profile")
        self.delete_profile_button.setObjectName("delete_profile_button")  # For custom styling
        self.delete_profile_button.setEnabled(False) # Disabled initially
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch() # Push scan/stop left, profile buttons right
        button_layout.addWidget(self.save_profile_button)
        button_layout.addWidget(self.delete_profile_button)

        # --- Parallel Scanning Controls ---
        parallel_layout = QHBoxLayout()
        self.parallel_scan_cb = QCheckBox("Enable Parallel Scanning")
        self.parallel_scan_cb.setToolTip("Discover live hosts first, then scan them in parallel for faster results")
        self.parallel_scan_cb.stateChanged.connect(self._on_parallel_scan_changed)

        workers_label = QLabel("Max Workers:")
        workers_label.setToolTip("Number of parallel scanner threads (1-10)")
        self.max_workers_spinbox = QSpinBox()
        self.max_workers_spinbox.setRange(1, 10)
        self.max_workers_spinbox.setValue(5)
        self.max_workers_spinbox.setEnabled(False)  # Disabled by default
        self.max_workers_spinbox.setToolTip("Number of parallel scanner threads")

        parallel_layout.addWidget(self.parallel_scan_cb)
        parallel_layout.addWidget(workers_label)
        parallel_layout.addWidget(self.max_workers_spinbox)
        parallel_layout.addStretch()

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False) # Hidden until scan starts
        self.progress_bar.setRange(0, 0) # Indeterminate progress style

        # --- Results Area (Splitter allows resizing) ---
        results_splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Top part of splitter: Tabbed Output/Results ---
        self.tab_widget = QTabWidget()
        # Define monospace font once
        monospace_font = QFont("Monospace")
        monospace_font.setStyleHint(QFont.StyleHint.TypeWriter)

        # Raw Output Tab
        self.raw_output_widget = QWidget()
        raw_output_layout = QVBoxLayout(self.raw_output_widget)
        raw_output_layout.setContentsMargins(0, 5, 0, 0) # Reduce margins
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(monospace_font)
        raw_output_layout.addWidget(self.output_area)
        self.tab_widget.addTab(self.raw_output_widget, "Raw Output")

        # Device Details Tab (Table View)
        self.parsed_results_widget = QWidget()
        parsed_results_layout = QVBoxLayout(self.parsed_results_widget)
        parsed_results_layout.setContentsMargins(0, 5, 0, 0)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["IP Address", "Hostname", "MAC Address", "Detected OS"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Make table read-only
        self.results_table.setAlternatingRowColors(True) # Improve readability
        self.results_table.verticalHeader().setVisible(False) # Hide default row numbers
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Select whole rows
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Allow only one row selected
        # Configure column resizing behavior
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # IP Address (allow resize)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Hostname (allow resize)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # MAC Address (allow resize)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Detected OS (stretch to fill)
        self.results_table.setSortingEnabled(True) # Allow sorting by column header clicks
        parsed_results_layout.addWidget(self.results_table)
        self.tab_widget.addTab(self.parsed_results_widget, "Device Details")

        # Add the tab widget to the top part of the splitter
        results_splitter.addWidget(self.tab_widget)

        # --- Bottom part of splitter: Host Details Area with Notes ---
        details_container = QWidget() # Use container for label + text area
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 5, 0, 0) # Adjust margins

        # Create a vertical splitter for Host Details and Notes
        details_splitter = QSplitter(Qt.Orientation.Vertical)

        # Device Details section (top)
        host_details_widget = QWidget()
        host_details_layout = QVBoxLayout(host_details_widget)
        host_details_layout.setContentsMargins(0, 0, 0, 0)
        details_label = QLabel("Device Details:")
        self.host_details_area = QTextEdit()
        self.host_details_area.setReadOnly(True)
        self.host_details_area.setFont(monospace_font) # Use consistent monospace font
        self.host_details_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) # Disable line wrapping
        host_details_layout.addWidget(details_label)
        host_details_layout.addWidget(self.host_details_area)

        # Notes section (bottom)
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        notes_label = QLabel("Notes for Selected Host:")
        self.notes_area = QTextEdit()
        self.notes_area.setPlaceholderText("Add your notes here... (automatically saved)")
        self.notes_area.setMaximumHeight(120)  # Limit height so details get more space
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_area)

        # Add both sections to the details splitter
        details_splitter.addWidget(host_details_widget)
        details_splitter.addWidget(notes_widget)
        details_splitter.setSizes([300, 100])  # Give more space to details

        # Add the details splitter to the main layout
        details_layout.addWidget(details_splitter)

        # Add the details container to the bottom part of the main results splitter
        results_splitter.addWidget(details_container)

        # --- Configure Splitter Sizes ---
        # Set initial relative sizes (e.g., 2/3 for tabs, 1/3 for details)
        results_splitter.setSizes([600, 300])

        # --- Add widgets to main application layout ---
        main_layout.addWidget(config_widget) # Add the top configuration group
        main_layout.addLayout(button_layout) # Add the button row
        main_layout.addLayout(parallel_layout) # Add the parallel scanning controls
        main_layout.addWidget(self.progress_bar) # Add the progress bar
        main_layout.addWidget(results_splitter, 1) # Add the results splitter, allow it to stretch


    def _create_status_bar(self):
        """Creates the status bar and adds a permanent label widget for messages."""
        self.status_label = QLabel(self._current_status_message)
        self.status_label.setObjectName("statusLabel") # For potential styling
        # Add the label as a permanent widget, allowing it to stretch
        self.statusBar().addPermanentWidget(self.status_label, stretch=1)

    def _connect_signals(self):
        """Connects signals from UI elements to their corresponding handler methods (slots)."""
        # Scan control buttons
        self.scan_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        # Target input field (allow pressing Enter to start scan)
        self.target_input.returnPressed.connect(self.start_scan)
        # Scan configuration changes
        self.scan_type_combo.currentIndexChanged.connect(self.update_args_from_scan_type)
        self.profile_combo.currentIndexChanged.connect(self.load_profile_settings)
        self.os_detection_checkbox.stateChanged.connect(self._update_command_display)
        self.os_detection_checkbox.stateChanged.connect(self._check_and_warn_privileged_scan)
        self.service_detection_checkbox.stateChanged.connect(self._update_command_display)
        # Profile management buttons
        self.save_profile_button.clicked.connect(self.save_current_profile)
        self.delete_profile_button.clicked.connect(self.delete_selected_profile)
        # Custom scan builder button
        self.custom_scan_builder_btn.clicked.connect(self.open_custom_scan_builder)
        # Results table selection -> Host Details update
        self.results_table.itemSelectionChanged.connect(self.display_host_details)
        # Notes area -> Save notes when changed
        self.notes_area.textChanged.connect(self.save_current_host_notes)
        # Update command display dynamically
        self.target_input.textChanged.connect(self._update_command_display)
        self.custom_args_input.textChanged.connect(self._update_command_display)
        # Update privilege warning dynamically
        self.custom_args_input.textChanged.connect(self._check_and_warn_privileged_scan)


    # --- Privilege Check ---
    def _on_parallel_scan_changed(self):
        """Handle parallel scanning option (enables/disables max workers spinbox)."""
        is_parallel = self.parallel_scan_cb.isChecked()
        self.max_workers_spinbox.setEnabled(is_parallel)

    def _check_and_warn_privileged_scan(self):
        """
        Checks the current Nmap arguments and OS detection checkbox for flags requiring elevation.
        Updates the status bar label with a warning message if needed.
        """
        args_string = self.custom_args_input.text()
        try:
            # Use shlex to handle quoted arguments correctly
            args_list = shlex.split(args_string)
        except ValueError:
            # Fallback to simple split if shlex fails (e.g., unmatched quotes)
            args_list = args_string.split()

        # Check if any of the defined privileged flags are present
        needs_privileges = any(flag in args_list for flag in self.PRIVILEGED_FLAGS)

        # OS detection checkbox also requires privileges
        if self.os_detection_checkbox.isChecked():
            needs_privileges = True

        # Construct the status message
        status_text = self._current_status_message
        if needs_privileges:
            # Append styled warning using HTML subset supported by QLabel
            warning_text = "<span style='color: red; font-weight: bold;'> (Requires Admin/Root Privileges)</span>"
            status_text += warning_text

        # Update the permanent status label
        self.status_label.setText(status_text)

    # --- Update Command Display ---
    def _update_command_display(self):
        """
        Constructs a string representing the Nmap command based on current
        UI settings (target, arguments, OS detection, service detection) and displays it in a read-only field.
        """
        target = self.target_input.text().strip()
        args_string = self.custom_args_input.text().strip()

        # Show placeholder if target is empty
        if not target:
            self.command_display_line.setText("nmap <target> [options...]")
            return

        # Start building the command string
        command_parts = ["nmap"]
        try:
            # Split arguments for potentially better joining later if needed
            # Filter ensures empty strings from split aren't included
            args_list = list(filter(None, shlex.split(args_string)))

            # Add OS detection flag if checkbox is checked and not already present
            if self.os_detection_checkbox.isChecked():
                # Only add -O if -A or -O is not already in the arguments
                if '-A' not in args_list and '-O' not in args_list:
                    args_list.append('-O')

            # Add service version detection flag if checkbox is checked and not already present
            if self.service_detection_checkbox.isChecked():
                # Only add -sV if -A or -sV is not already in the arguments
                if '-A' not in args_list and '-sV' not in args_list:
                    args_list.append('-sV')

            command_parts.extend(args_list)
        except ValueError:
            # If args are malformed, just append the raw string if it's not empty
            if args_string:
                 command_parts.append(args_string)
            # Still try to add -O if checkbox is checked
            if self.os_detection_checkbox.isChecked():
                if '-A' not in args_string and '-O' not in args_string:
                    command_parts.append('-O')
            # Still try to add -sV if checkbox is checked
            if self.service_detection_checkbox.isChecked():
                if '-A' not in args_string and '-sV' not in args_string:
                    command_parts.append('-sV')

        # Add target, quoting it using shlex.quote for safety if it contains spaces/special chars
        command_parts.append(shlex.quote(target))

        # Join parts into a single string for display
        display_command = " ".join(command_parts)
        self.command_display_line.setText(display_command)


    # --- Profile Methods ---
    def open_custom_scan_builder(self):
        """Opens the custom scan builder dialog to create scan arguments visually."""
        dialog = CustomScanDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the constructed arguments
            custom_args = dialog.get_arguments()
            # Set the arguments in the input field
            self.custom_args_input.setText(custom_args)
            # Make the field editable so user can further modify if needed
            self.custom_args_input.setReadOnly(False)
            self.custom_args_input.setToolTip("Custom arguments from scan builder (editable)")
            # Update command display and privilege warning
            self._update_command_display()
            self._check_and_warn_privileged_scan()

    def update_args_from_scan_type(self):
        """
        Updates the 'Nmap Arguments' input field based on the selected 'Scan Type'.
        Also triggers updates for command display and privilege warnings.
        """
        # Get the arguments stored in the selected combo box item's UserRole data
        arguments = self.scan_type_combo.currentData(Qt.ItemDataRole.UserRole)
        if arguments is not None:
            # Set the text and make read-only if using a preset
            self.custom_args_input.setText(arguments)
            self.custom_args_input.setReadOnly(True)
            self.custom_args_input.setToolTip("Arguments set by selected Scan Type")
        else:
            # Clear and make editable if no preset data (shouldn't happen now)
            self.custom_args_input.clear()
            self.custom_args_input.setReadOnly(False)
            self.custom_args_input.setToolTip("Enter custom Nmap arguments")

        # Update other UI elements that depend on the arguments
        self._update_command_display()
        self._check_and_warn_privileged_scan()


    def load_profile_settings(self):
        """
        Loads the target and arguments from the selected profile into the UI.
        Updates command display and privilege warnings accordingly.
        """
        selected_profile_name = self.profile_combo.currentText()
        is_custom = (selected_profile_name == "Custom Scan")

        if is_custom:
            # If "Custom Scan" is selected, reset scan type to default.
            # The signal from setCurrentIndex will trigger updates.
            self.scan_type_combo.setCurrentIndex(0)
            # Maybe clear target? Or leave it? User preference.
            # self.target_input.clear()
        elif selected_profile_name in self.profiles:
            # Load data from the selected profile
            profile_data = self.profiles[selected_profile_name]
            self.target_input.setText(profile_data.get("target", "")) # Load target
            saved_args = profile_data.get("arguments", "") # Load arguments

            # Try to find a matching preset Scan Type
            found_match = False
            for i in range(self.scan_type_combo.count()):
                if self.scan_type_combo.itemData(i, Qt.ItemDataRole.UserRole) == saved_args:
                    # If match found, select it. This triggers update_args_from_scan_type.
                    self.scan_type_combo.setCurrentIndex(i)
                    found_match = True
                    break

            # If no preset matched the saved arguments, treat them as custom
            if not found_match:
                 self.custom_args_input.setText(saved_args)
                 self.custom_args_input.setReadOnly(False) # Allow editing
                 self.custom_args_input.setToolTip("Custom arguments loaded from profile")
                 # Manually trigger updates since scan type didn't change
                 self._update_command_display()
                 self._check_and_warn_privileged_scan()
        else:
             # Handle error case where profile name is invalid
             QMessageBox.warning(self, "Profile Error", f"Could not load data for profile '{selected_profile_name}'.")
             self.profile_combo.setCurrentIndex(0) # Reset to "Custom Scan"

        # Enable/disable the delete button based on selection
        self.delete_profile_button.setEnabled(not is_custom and selected_profile_name in self.profiles)
        # Ensure command display is updated after potential target change
        self._update_command_display()


    def save_current_profile(self):
        """
        Prompts the user for a profile name and saves the current target and
        arguments settings under that name. Updates the profile list.
        """
        current_args = self.custom_args_input.text().strip()
        current_target = self.target_input.text().strip()

        # Show the dialog to get the profile name
        dialog = SaveProfileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_name = dialog.get_profile_name()

            # Validate profile name
            if not profile_name or profile_name == "Custom Scan":
                QMessageBox.warning(self, "Save Error", "Profile name cannot be empty or 'Custom Scan'.")
                return

            # Prepare profile data
            profile_data = {"arguments": current_args, "target": current_target}
            is_update = profile_name in self.profiles # Check if overwriting

            # Update internal dictionary and attempt to save to file
            self.profiles[profile_name] = profile_data
            if self.profile_manager.save_profiles(self.profiles):
                # Success: Update UI
                self._current_status_message = f"Profile '{profile_name}' saved."
                # Add to combo box if it's a new profile
                if not is_update:
                    self.profile_combo.addItem(profile_name)
                # Select the newly saved/updated profile (triggers other updates)
                self.profile_combo.setCurrentText(profile_name)
            else:
                # Failure: Show error and revert internal state
                QMessageBox.critical(self, "Save Error", "Failed to save profiles to disk.")
                # Remove the profile if it was newly added and save failed
                if not is_update:
                    if profile_name in self.profiles:
                         del self.profiles[profile_name]
                else:
                    # If update failed, reload profiles from disk to revert
                    self.profiles = self.profile_manager.load_profiles()
                    # Refresh combo box fully
                    self.profile_combo.clear()
                    self.profile_combo.addItem("Custom Scan")
                    self.profile_combo.addItems(sorted(self.profiles.keys()))
                    # Try to re-select the profile that failed to update
                    current_index = self.profile_combo.findText(profile_name)
                    self.profile_combo.setCurrentIndex(current_index if current_index >= 0 else 0)


    def delete_selected_profile(self):
        """
        Deletes the currently selected profile after confirmation.
        Updates the profile list and resets UI.
        """
        selected_profile_name = self.profile_combo.currentText()

        # Prevent deleting the "Custom Scan" placeholder or non-existent profiles
        if selected_profile_name == "Custom Scan" or selected_profile_name not in self.profiles:
            QMessageBox.warning(self, "Delete Error", "Cannot delete 'Custom Scan' or non-existent profile.")
            return

        # Confirm deletion with the user
        reply = QMessageBox.question(self, "Confirm Delete",
                                       f"Are you sure you want to delete the profile '{selected_profile_name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No) # Default to No

        if reply == QMessageBox.StandardButton.Yes:
            # Remove from internal dictionary and attempt to save
            original_profile_data = self.profiles.pop(selected_profile_name, None) # Keep data for revert
            if self.profile_manager.save_profiles(self.profiles):
                # Success: Update UI
                self._current_status_message = f"Profile '{selected_profile_name}' deleted."
                # Remove from combo box
                current_index = self.profile_combo.findText(selected_profile_name)
                if current_index >= 0:
                    self.profile_combo.removeItem(current_index)
                # Reset selection to "Custom Scan" (triggers other updates)
                self.profile_combo.setCurrentIndex(0)
            else:
                 # Failure: Show error and revert internal state
                 QMessageBox.critical(self, "Delete Error", "Failed to save profile changes after deletion.")
                 # Add profile back if save failed
                 if original_profile_data:
                      self.profiles[selected_profile_name] = original_profile_data
                 # Refresh combo box fully
                 self.profile_combo.clear()
                 self.profile_combo.addItem("Custom Scan")
                 self.profile_combo.addItems(sorted(self.profiles.keys()))
                 self.profile_combo.setCurrentIndex(0) # Reset to custom


    # --- Scan Methods ---
    def get_nmap_arguments(self):
        """
        Returns the Nmap arguments string including OS detection and service detection flags if enabled.

        Returns:
            str: Final Nmap arguments string
        """
        args_string = self.custom_args_input.text().strip()

        try:
            args_list = shlex.split(args_string) if args_string else []

            # Add OS detection flag if checkbox is checked and not already present
            if self.os_detection_checkbox.isChecked():
                # Only add -O if -A or -O is not already in the arguments
                if '-A' not in args_list and '-O' not in args_list:
                    args_list.append('-O')

            # Add service version detection flag if checkbox is checked and not already present
            if self.service_detection_checkbox.isChecked():
                # Only add -sV if -A or -sV is not already in the arguments
                if '-A' not in args_list and '-sV' not in args_list:
                    args_list.append('-sV')

            # Join back into string
            return ' '.join(args_list) if args_list else ''
        except ValueError:
            # If parsing fails, check with simple string operations
            result = args_string

            if self.os_detection_checkbox.isChecked():
                if '-A' not in args_string and '-O' not in args_string:
                    result = f"{result} -O" if result else "-O"

            if self.service_detection_checkbox.isChecked():
                if '-A' not in args_string and '-sV' not in args_string:
                    result = f"{result} -sV" if result else "-sV"

            return result

    def _cleanup_last_scan_file(self):
        """Safely removes the temporary XML file from the PREVIOUS scan."""
        # (Code remains the same)
        if self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path):
            try: os.remove(self.last_scan_xml_path); self.last_scan_xml_path = None
            except OSError as e: print(f"[Warning] Could not remove previous temp file {self.last_scan_xml_path}: {e}"); self.last_scan_xml_path = None
            except Exception as e: print(f"[Warning] Error during previous temp file cleanup: {e}"); self.last_scan_xml_path = None
        else: self.last_scan_xml_path = None

    def start_scan(self):
        """
        Validates input, cleans up old files, sets UI state, creates and
        starts the background scanner thread.
        """
        target = self.target_input.text().strip()
        # Basic validation
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please enter a target to scan.")
            return
        # Prevent starting scan if one is already running
        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A scan is already running.")
            return

        # Prepare for new scan
        self._cleanup_last_scan_file() # Remove temp file from previous scan
        self.current_scan_data = {} # Clear stored detailed results
        self.host_notes = {} # Clear notes from previous scan
        self.current_selected_host = None # Clear selected host
        self.host_details_area.clear() # Clear details view
        self.notes_area.clear() # Clear notes area
        nmap_args = self.get_nmap_arguments() # Get arguments from UI
        self.output_area.clear() # Clear raw output
        self.results_table.setRowCount(0) # Clear results table

        # Update UI state for scanning
        self._current_status_message = f"Starting scan on {target}..."
        self._set_ui_scan_state(scanning=True) # Disable config, enable stop button, etc.
        self._check_and_warn_privileged_scan() # Show status + warning

        # Create and configure the scanner thread
        # Use parallel scanner if enabled, otherwise use standard scanner
        if self.parallel_scan_cb.isChecked():
            max_workers = self.max_workers_spinbox.value()
            self.scanner_thread = QtParallelScannerAdapter(target, nmap_args, max_workers)
            # Connect progress signal for parallel scanning
            self.scanner_thread.scan_progress.connect(self.update_scan_progress)
            # Connect incremental host result signal for live table updates
            self.scanner_thread.scan_host_result.connect(self.process_host_result)
        else:
            self.scanner_thread = Scanner(target, nmap_args)

        # Connect common signals
        self.scanner_thread.scan_output.connect(self.append_output)
        self.scanner_thread.scan_results_ready.connect(self.process_scan_results)
        self.scanner_thread.scan_finished.connect(self.scan_complete)
        self.scanner_thread.scan_error.connect(self.scan_error_occurred)

        # Switch focus to raw output tab
        self.tab_widget.setCurrentWidget(self.raw_output_widget)
        # Start the thread execution (calls the Scanner.run() method)
        self.scanner_thread.start()

    def stop_scan(self):
        """
        Requests the background scanner thread to stop the Nmap process.
        """
        if self.scanner_thread and self.scanner_thread.isRunning():
            self._current_status_message = "Attempting to stop scan..."
            self._check_and_warn_privileged_scan() # Update status bar
            self.scanner_thread.stop() # Signal the thread to stop
            # UI state reset happens in scan_error_occurred slot when thread finishes stopping
        else:
            # Handle case where stop is clicked when no scan is running
            self._current_status_message = "No scan is currently running."
            self._reset_ui_after_scan(self._current_status_message)
            self._cleanup_last_scan_file() # Ensure cleanup if stop clicked while idle


    def append_output(self, text):
        """Appends text with timestamp to the 'Raw Output' text area and auto-scrolls."""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        timestamped_text = f"{timestamp} {text}"
        self.output_area.append(timestamped_text)
        # Move scrollbar to the bottom to show the latest output
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum())

    def update_scan_progress(self, current: int, total: int):
        """Update status bar with parallel scan progress."""
        self._current_status_message = f"Parallel scan progress: {current}/{total} hosts scanned"
        self._check_and_warn_privileged_scan()

    def process_host_result(self, host_data):
        """
        Slot connected to parallel scanner's scan_host_result signal.
        Adds individual host results to the table incrementally as they complete.
        """
        # Merge new host data with current scan data
        self.current_scan_data.update(host_data)
        # Add rows for this host to the table
        self._add_host_to_table(host_data)

    def _add_host_to_table(self, host_data):
        """
        Adds table rows for a single host's scan results.

        Args:
            host_data: Dictionary with single host IP as key and host info as value
        """
        self.results_table.setSortingEnabled(False)  # Disable sorting during addition

        for host, data in host_data.items():
            hostname = data.get('hostname', '')
            # Format host display (include IP)
            display_host = f"{hostname} ({host})" if hostname and hostname != host else host
            # Get MAC address for this host
            mac_address = data.get('mac', '')
            vendor = data.get('vendor', '')
            mac_display = f"{mac_address} ({vendor})" if mac_address and vendor else mac_address
            protocols = data.get('protocols', {})

            # If no port/protocol info, but host is up, show a single row for the host
            if not protocols:
                if data.get('state') == 'up':
                    row_position = self.results_table.rowCount()
                    self.results_table.insertRow(row_position)
                    host_item = QTableWidgetItem(display_host)
                    host_item.setData(Qt.ItemDataRole.UserRole, host)
                    self.results_table.setItem(row_position, 0, host_item)
                    self.results_table.setItem(row_position, 1, QTableWidgetItem(mac_display))
                    self.results_table.setItem(row_position, 4, QTableWidgetItem(data.get('state', 'unknown')))
                    self.results_table.setItem(row_position, 5, QTableWidgetItem("(No ports found/reported)"))
                continue

            # If ports exist, iterate through protocols and ports
            for proto, ports in protocols.items():
                for port, port_data in ports.items():
                    row_position = self.results_table.rowCount()
                    self.results_table.insertRow(row_position)
                    # Create table items for each cell
                    host_item = QTableWidgetItem(display_host)
                    host_item.setData(Qt.ItemDataRole.UserRole, host)
                    mac_item = QTableWidgetItem(mac_display)
                    proto_item = QTableWidgetItem(proto)
                    port_item = QTableWidgetItem(str(port))
                    state_item = QTableWidgetItem(port_data.get('state', ''))
                    service_item = QTableWidgetItem(port_data.get('name', ''))
                    product_item = QTableWidgetItem(port_data.get('product', ''))
                    version_item = QTableWidgetItem(port_data.get('version', ''))
                    # Set items in the current row
                    self.results_table.setItem(row_position, 0, host_item)
                    self.results_table.setItem(row_position, 1, mac_item)
                    self.results_table.setItem(row_position, 2, proto_item)
                    self.results_table.setItem(row_position, 3, port_item)
                    self.results_table.setItem(row_position, 4, state_item)
                    self.results_table.setItem(row_position, 5, service_item)
                    self.results_table.setItem(row_position, 6, product_item)
                    self.results_table.setItem(row_position, 7, version_item)

        self.results_table.setSortingEnabled(True)  # Re-enable sorting

    def process_scan_results(self, results_data):
        """
        Slot connected to scanner's scan_results_ready signal.
        Stores the full parsed data and triggers the table update.
        """
        self.current_scan_data = results_data # Store for the details view
        self.display_parsed_results_table(results_data) # Update the table
        # Clear details view - selection is lost when table repopulates
        self.host_details_area.clear()


    def display_parsed_results_table(self, results_data):
        """Populates the 'Device List' table with summarized scan data."""
        self.results_table.setSortingEnabled(False) # Disable sorting during population
        self.results_table.setRowCount(0) # Clear existing rows
        row_position = 0
        # Iterate through each host in the results
        for host, host_data in results_data.items():
            hostname = host_data.get('hostname', '')
            # Only show hostname if it's different from the IP
            display_hostname = hostname if (hostname and hostname != host) else ''
            # Get MAC address for this host
            mac_address = host_data.get('mac', '')
            vendor = host_data.get('vendor', '')
            mac_display = f"{mac_address} ({vendor})" if mac_address and vendor else mac_address

            # Get best OS match
            osmatches = host_data.get('osmatch', [])
            detected_os = 'Unknown'
            if osmatches:
                # Sort by accuracy and get the best match
                sorted_matches = sorted(osmatches, key=lambda x: int(x.get('accuracy', '0')), reverse=True)
                detected_os = sorted_matches[0].get('name', 'Unknown')
                accuracy = sorted_matches[0].get('accuracy', '')
                if accuracy:
                    detected_os += f" ({accuracy}%)"

            # Add one row per device
            self.results_table.insertRow(row_position)
            ip_item = QTableWidgetItem(host)
            # Store the actual IP address in the item's data for later retrieval
            ip_item.setData(Qt.ItemDataRole.UserRole, host)
            hostname_item = QTableWidgetItem(display_hostname)
            mac_item = QTableWidgetItem(mac_display)
            os_item = QTableWidgetItem(detected_os)

            # Set items in the current row
            self.results_table.setItem(row_position, 0, ip_item) # IP Address column
            self.results_table.setItem(row_position, 1, hostname_item) # Hostname column
            self.results_table.setItem(row_position, 2, mac_item) # MAC column
            self.results_table.setItem(row_position, 3, os_item) # OS column
            row_position += 1

        self.results_table.setSortingEnabled(True) # Re-enable sorting


    def display_host_details(self):
        """
        Slot connected to table selection changes. Displays detailed information
        (MAC, OS, Ports, Scripts) for the selected device in the Device Details area.
        """
        selected_items = self.results_table.selectedItems()
        self.host_details_area.clear() # Clear previous details

        # Ensure an item is actually selected
        if not selected_items:
            return

        # Get the host IP address stored in the first column's UserRole data
        selected_row = self.results_table.currentRow()
        host_item = self.results_table.item(selected_row, 0)
        if not host_item: return # Should have an item if a row is selected
        host_ip = host_item.data(Qt.ItemDataRole.UserRole)

        # Check if we have detailed data stored for this IP
        if host_ip and host_ip in self.current_scan_data:
            details = self.current_scan_data[host_ip]
            details_text = [] # Build details as a list of strings

            # Basic Info
            details_text.append(f"Host Details: {host_ip}")
            details_text.append(f"Hostname: {details.get('hostname', 'N/A')}")
            details_text.append(f"State: {details.get('state', 'N/A')}")
            mac = details.get('mac', ''); vendor = details.get('vendor', '')
            if mac:
                mac_line = f"MAC Address: {mac}"
                if vendor: mac_line += f" ({vendor})"
                details_text.append(mac_line)

            # OS Detection Info
            osmatches = details.get('osmatch', [])
            details_text.append("\n--- OS Detection ---")
            if osmatches:
                # Sort OS matches by accuracy (highest first)
                for match in sorted(osmatches, key=lambda x: int(x.get('accuracy', '0')), reverse=True):
                    details_text.append(f"  Name: {match.get('name')} (Accuracy: {match.get('accuracy')} %)")
                    # Display OS classes associated with the match
                    for osclass in match.get('osclasses', []):
                         details_text.append(f"    Class: {osclass.get('vendor', '')} {osclass.get('osfamily', '')} {osclass.get('osgen', '')} (Type: {osclass.get('type', '')}, Acc: {osclass.get('accuracy')}%)\n")
            else:
                 details_text.append("  No match found or OS detection not performed.")

            # Ports/Services Info
            protocols = details.get('protocols', {})
            details_text.append("\n--- Ports/Services ---")
            if protocols:
                # Iterate through sorted protocols (tcp, udp)
                for proto, ports in sorted(protocols.items()):
                    details_text.append(f"  Protocol: {proto}")
                    # Iterate through sorted ports for this protocol
                    for port, port_data in sorted(ports.items()):
                        state = port_data.get('state', ''); name = port_data.get('name', ''); prod = port_data.get('product', ''); ver = port_data.get('version', ''); extra = port_data.get('extrainfo', '')
                        port_line = f"    {port:<5} {state:<10} {name:<15}" # Basic port info
                        # Append product/version/extra info if available
                        if prod: port_line += f" {prod}"
                        if ver: port_line += f" (version {ver})"
                        if extra: port_line += f" ({extra})"
                        details_text.append(port_line)

                        # Display NSE script output for this port
                        scripts = port_data.get('script', [])
                        if scripts:
                            for script in scripts:
                                script_id = script.get('id', 'unknown_script'); script_output = script.get('output', '').strip()
                                if script_output: # Only show if there's output
                                    details_text.append(f"      |_ Script: {script_id}")
                                    # Indent script output lines
                                    for line in script_output.splitlines():
                                         details_text.append(f"         {line.strip()}")
            else:
                # Handle case where host is up but no ports reported
                if details.get('state') == 'up':
                     details_text.append("  No open/reported ports found.")

            # Host Script Info
            host_scripts = details.get('hostscript', [])
            if host_scripts:
                details_text.append("\n--- Host Scripts ---")
                for script in host_scripts:
                    script_id = script.get('id', 'unknown_script'); script_output = script.get('output', '').strip()
                    if script_output: # Only show if there's output
                        details_text.append(f"  Script: {script_id}")
                        # Indent script output lines
                        for line in script_output.splitlines():
                             details_text.append(f"    {line.strip()}")

            # Set the formatted text in the details area
            self.host_details_area.setText("\n".join(details_text))
        else:
            # Handle case where data for the selected host isn't found
            self.host_details_area.setText(f"No detailed data available for selected host.")

        # Load notes for the selected host
        self.current_selected_host = host_ip
        if host_ip and host_ip in self.host_notes:
            # Temporarily disconnect signal to avoid triggering save while loading
            self.notes_area.textChanged.disconnect(self.save_current_host_notes)
            self.notes_area.setPlainText(self.host_notes[host_ip])
            self.notes_area.textChanged.connect(self.save_current_host_notes)
        else:
            # Clear notes area if no notes exist for this host
            self.notes_area.textChanged.disconnect(self.save_current_host_notes)
            self.notes_area.clear()
            self.notes_area.textChanged.connect(self.save_current_host_notes)

    def save_current_host_notes(self):
        """
        Saves the current notes text to the host_notes dictionary for the selected host.
        Called automatically when notes text changes.
        """
        if self.current_selected_host:
            notes_text = self.notes_area.toPlainText().strip()
            if notes_text:
                self.host_notes[self.current_selected_host] = notes_text
            else:
                # Remove empty notes from dictionary
                if self.current_selected_host in self.host_notes:
                    del self.host_notes[self.current_selected_host]

    def save_notes_to_file(self, base_filename):
        """
        Saves host notes to a JSON file alongside the scan results.

        Args:
            base_filename (str): Base filename (without extension) for the notes file

        Returns:
            bool: True if save was successful, False otherwise
        """
        if not self.host_notes:
            return True  # No notes to save, but not an error

        notes_filename = base_filename + "_notes.json"
        try:
            with open(notes_filename, 'w', encoding='utf-8') as f:
                json.dump(self.host_notes, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving notes: {e}")
            return False

    def load_notes_from_file(self, base_filename):
        """
        Loads host notes from a JSON file.

        Args:
            base_filename (str): Base filename (without extension) for the notes file
        """
        notes_filename = base_filename + "_notes.json"
        if os.path.exists(notes_filename):
            try:
                with open(notes_filename, 'r', encoding='utf-8') as f:
                    self.host_notes = json.load(f)
            except Exception as e:
                print(f"Error loading notes: {e}")
                self.host_notes = {}
        else:
            self.host_notes = {}

    def _set_ui_scan_state(self, scanning: bool):
        """Enables/disables UI elements based on whether a scan is running."""
        # Disable/enable configuration widgets
        self.scan_button.setEnabled(not scanning)
        self.stop_button.setEnabled(scanning)
        self.progress_bar.setVisible(scanning)
        self.profile_combo.setEnabled(not scanning)
        self.scan_type_combo.setEnabled(not scanning)
        self.os_detection_checkbox.setEnabled(not scanning)
        self.service_detection_checkbox.setEnabled(not scanning)
        self.custom_args_input.setEnabled(not scanning)
        self.custom_scan_builder_btn.setEnabled(not scanning)
        self.save_profile_button.setEnabled(not scanning)
        # Parallel scanning controls
        self.parallel_scan_cb.setEnabled(not scanning)
        # Max workers spinbox enabled only when not scanning AND parallel scan is checked
        self.max_workers_spinbox.setEnabled(not scanning and self.parallel_scan_cb.isChecked())
        # Delete button enabled only when not scanning AND a non-custom profile is selected
        self.delete_profile_button.setEnabled(not scanning and self.profile_combo.currentIndex() > 0)
        # File menu actions
        # Save enabled only when not scanning AND (results from last scan exist OR we have scan data)
        has_xml = bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path))
        has_data = bool(self.current_scan_data)
        self.save_action.setEnabled(not scanning and (has_xml or has_data))
        self.open_action.setEnabled(not scanning) # Allow opening when idle
        # Export enabled when not scanning AND table has data
        self.export_csv_action.setEnabled(not scanning and self.results_table.rowCount() > 0)

        # Clear the temporary file path and reset saved flag when starting a new scan
        if scanning:
             self.last_scan_xml_path = None
             self.results_saved = False


    def _reset_ui_after_scan(self, status_message):
        """Resets UI elements to idle state after scan finishes or errors."""
        self._current_status_message = status_message # Update base status
        self._set_ui_scan_state(scanning=False) # Re-enable UI elements
        self._check_and_warn_privileged_scan() # Update status bar text/warning
        self.scanner_thread = None # Clear reference to finished thread


    def scan_complete(self, message, temp_xml_path):
        """
        Slot connected to scanner's scan_finished signal.
        Stores the temp XML path and enables the save action.
        """
        # Store path for potential saving (empty string for parallel scans)
        self.last_scan_xml_path = temp_xml_path if temp_xml_path else None
        self.results_saved = False  # Mark results as unsaved when scan completes
        self._reset_ui_after_scan(message) # Reset UI to idle state
        # Explicitly re-evaluate save action state
        # Enable save if we have either an XML file OR scan data from parallel scan
        has_xml = bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path))
        has_data = bool(self.current_scan_data)
        self.save_action.setEnabled(has_xml or has_data)


    def scan_error_occurred(self, error_message):
        """
        Slot connected to scanner's scan_error signal.
        Displays error, clears results/details, and resets UI.
        """
        # Show error message box only if the message isn't already in raw output
        if error_message not in self.output_area.toPlainText():
             QMessageBox.critical(self, "Scan Error / Stopped", error_message)
        # Clear any potentially incomplete results
        self.last_scan_xml_path = None
        self.current_scan_data = {}
        self.host_details_area.clear()
        # Reset UI state
        self._reset_ui_after_scan(f"Scan Error / Stopped: {error_message}")

    # --- File Menu Methods ---
    def open_scan_results(self):
        """
        Prompts the user to select an Nmap XML file, parses it,
        and displays the results in the UI.
        """
        # Prevent opening while a scan is active
        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.warning(self, "Scan Running", "Cannot open results while a scan is in progress.")
            return

        # Open file dialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Nmap Scan Results", "", # Parent, Caption, Start Dir
            "Nmap XML Files (*.xml);;All Files (*)" # Filter
        )

        # Proceed only if a filename was selected
        if filename:
            self._cleanup_last_scan_file() # Clean up any temp file from previous run scan
            self.current_scan_data = {} # Clear previous data
            self.host_details_area.clear() # Clear details view
            self._current_status_message = f"Opening {filename}..."; self._check_and_warn_privileged_scan()

            try:
                # Read XML file content
                with open(filename, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                if not xml_content:
                     QMessageBox.warning(self, "Empty File", f"The file '{filename}' is empty.")
                     self._current_status_message = "Failed to open empty file."; self._check_and_warn_privileged_scan()
                     return

                # Parse the XML content using the same logic as Scanner.run
                nm = nmap.PortScanner()
                scan_data = nm.analyse_nmap_xml_scan(nmap_xml_output=xml_content)
                parsed_results = {} # Dictionary to hold results from file

                # (Parsing logic - identical to the one in Scanner.run)
                if 'scan' in scan_data and isinstance(scan_data['scan'], dict):
                     for host_ip, host_scan_data in scan_data['scan'].items():
                          if not isinstance(host_scan_data, dict): continue
                          hostname = ''; hostnames_list = host_scan_data.get('hostnames', [])
                          if isinstance(hostnames_list, list) and len(hostnames_list) > 0: hostname_entry = hostnames_list[0];
                          if isinstance(hostname_entry, dict): hostname = hostname_entry.get('name', '')
                          state = 'unknown'; status_info = host_scan_data.get('status', {})
                          if isinstance(status_info, dict): state = status_info.get('state', 'unknown')
                          mac_address = ''; vendor = ''; addresses_info = host_scan_data.get('addresses', {})
                          if isinstance(addresses_info, dict): mac_address = addresses_info.get('mac', '');
                          if mac_address and 'vendor' in host_scan_data and isinstance(host_scan_data['vendor'], dict): vendor = host_scan_data['vendor'].get(mac_address, '')
                          host_data_for_ui = {'hostname': hostname, 'state': state, 'mac': mac_address, 'vendor': vendor, 'osmatch': [], 'protocols': {}, 'hostscript': []}
                          os_info = host_scan_data.get('osmatch', [])
                          if isinstance(os_info, list):
                               for match in os_info:
                                    if isinstance(match, dict):
                                         os_details = {'name': match.get('name', 'Unknown OS'),'accuracy': match.get('accuracy', '0'),'line': match.get('line', ''),'osclasses': []}
                                         osclasses = match.get('osclass', [])
                                         if isinstance(osclasses, list):
                                              for osclass in osclasses:
                                                   if isinstance(osclass, dict): os_details['osclasses'].append({'type': osclass.get('type', ''),'vendor': osclass.get('vendor', ''),'osfamily': osclass.get('osfamily', ''),'osgen': osclass.get('osgen', ''),'accuracy': osclass.get('accuracy', '')})
                                         host_data_for_ui['osmatch'].append(os_details)
                          host_script_info = host_scan_data.get('hostscript', [])
                          if isinstance(host_script_info, list):
                              for script_item in host_script_info:
                                  if isinstance(script_item, dict): host_data_for_ui['hostscript'].append({'id': script_item.get('id', ''),'output': script_item.get('output', '')})
                          for proto in ['tcp', 'udp', 'ip', 'sctp']:
                               if proto in host_scan_data and isinstance(host_scan_data[proto], dict):
                                    if proto not in host_data_for_ui['protocols']: host_data_for_ui['protocols'][proto] = {}
                                    for port_str, port_data in host_scan_data[proto].items():
                                         if not isinstance(port_data, dict): continue
                                         try:
                                              port_int = int(port_str)
                                              port_script_output = []
                                              script_info = port_data.get('script', None)
                                              if isinstance(script_info, dict): port_script_output.append({'id': script_info.get('id', ''),'output': script_info.get('output', '')})
                                              elif isinstance(script_info, list):
                                                   for script_item in script_info:
                                                        if isinstance(script_item, dict): port_script_output.append({'id': script_item.get('id', ''),'output': script_item.get('output', '')})
                                              host_data_for_ui['protocols'][proto][port_int] = {'state': port_data.get('state', 'unknown'), 'name': port_data.get('name', ''),'version': port_data.get('version', ''), 'product': port_data.get('product', ''),'extrainfo': port_data.get('extrainfo', ''), 'cpe': port_data.get('cpe', ''), 'script': port_script_output}
                                         except (ValueError, TypeError): continue
                          parsed_results[host_ip] = host_data_for_ui
                else:
                     # Handle XML files that might only contain summary info (e.g., from -sn)
                     host_info = "(No host details found in XML)"
                     if 'nmap' in scan_data and 'hosts' in scan_data['nmap']:
                          num_hosts = scan_data['nmap']['hosts'].get('up', 0); total_hosts = scan_data['nmap']['hosts'].get('total', 0)
                          host_info = f"({num_hosts} host(s) up / {total_hosts} total)"
                     QMessageBox.information(self, "Scan Info", f"Loaded file contains scan summary but no detailed host results {host_info}.")

                # --- Extract raw output if embedded ---
                raw_output_text = None
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        xml_content = f.read()

                    # Look for embedded raw output
                    if '<!-- NEOZEN_RAW_OUTPUT' in xml_content:
                        start_marker = '<!-- NEOZEN_RAW_OUTPUT\n'
                        end_marker = '\nNEOZEN_RAW_OUTPUT -->'
                        start_idx = xml_content.find(start_marker)
                        end_idx = xml_content.find(end_marker, start_idx)

                        if start_idx != -1 and end_idx != -1:
                            start_idx += len(start_marker)
                            raw_output_text = xml_content[start_idx:end_idx]
                            # Unescape comment terminators
                            raw_output_text = raw_output_text.replace('--&gt;', '-->')
                except Exception as e:
                    print(f"Error extracting raw output: {e}")

                # Update UI with loaded data
                self.current_scan_data = parsed_results # Store loaded data

                # Display raw output if available, otherwise show placeholder
                if raw_output_text:
                    self.output_area.setText(raw_output_text)
                else:
                    self.output_area.setText(f"--- Results loaded from: {filename} ---\n\n(Raw output was not saved with this scan)")

                self.display_parsed_results_table(parsed_results) # Update table

                # Load notes if they exist
                base_filename = os.path.splitext(filename)[0]  # Remove .xml extension
                self.load_notes_from_file(base_filename)

                self._current_status_message = f"Successfully loaded results from {filename}"
                self._check_and_warn_privileged_scan()
                # Cannot save a loaded file via the temp file mechanism
                self.last_scan_xml_path = None
                self.results_saved = True  # Mark as saved since we're loading from a saved file
                self.save_action.setEnabled(False)

            except FileNotFoundError:
                 QMessageBox.critical(self, "Error", f"File not found: {filename}")
                 self._current_status_message = "Error opening file."; self._check_and_warn_privileged_scan()
            except Exception as e:
                # Catch parsing errors or other issues
                QMessageBox.critical(self, "Error Opening/Parsing File", f"Could not open or parse {filename}:\n{e}")
                self._current_status_message = f"Error opening/parsing file: {e}"; self._check_and_warn_privileged_scan()

    def save_scan_results(self):
        """
        Prompts the user for save options and filename, then saves the scan results.
        For regular scans: saves XML file with optional raw output.
        For parallel scans: saves raw output and JSON data.

        Returns:
            bool: True on success, False on failure or cancellation.
        """
        # Check if results are available to save
        has_xml = bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path))
        has_data = bool(self.current_scan_data)

        if not has_xml and not has_data:
            QMessageBox.warning(self, "No Results", "No scan results available to save. Please run a scan first.")
            return False

        # Check if raw output is available
        raw_output = self.output_area.toPlainText().strip()
        has_raw_output = bool(raw_output)

        # Show save options dialog
        options_dialog = SaveScanDialog(has_raw_output=has_raw_output, parent=self)
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            self._current_status_message = "Save cancelled."
            self._check_and_warn_privileged_scan()
            return False

        include_raw = options_dialog.include_raw_output()

        # Suggest a default filename
        suggested_filename = "nmap_scan_results.xml"
        # Open "Save As" dialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Nmap Scan Results", suggested_filename,
            "Nmap XML Files (*.xml);;All Files (*)"
        )

        # Proceed only if a filename was provided (user didn't cancel)
        if filename:
            try:
                if has_xml:
                    # Regular scan: Save XML file with optional raw output
                    # Read the original XML content
                    with open(self.last_scan_xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()

                    # If user wants to include raw output, embed it in the XML
                    if include_raw and raw_output:
                        # Insert raw output as a comment near the end of the XML file (before </nmaprun>)
                        raw_output_escaped = raw_output.replace('-->', '--&gt;')  # Escape comment terminators
                        raw_comment = f"\n<!-- NEOZEN_RAW_OUTPUT\n{raw_output_escaped}\nNEOZEN_RAW_OUTPUT -->\n"

                        # Insert before closing nmaprun tag
                        if '</nmaprun>' in xml_content:
                            xml_content = xml_content.replace('</nmaprun>', f"{raw_comment}</nmaprun>")
                        else:
                            # If no closing tag, append at end
                            xml_content += raw_comment

                    # Write the modified XML to the target file
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(xml_content)

                else:
                    # Parallel scan: Save as JSON with raw output
                    base_filename = os.path.splitext(filename)[0]
                    json_filename = base_filename + ".json"
                    txt_filename = base_filename + "_output.txt"

                    # Save parsed data as JSON
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(self.current_scan_data, f, indent=2, ensure_ascii=False)

                    # Save raw output if requested
                    if include_raw and raw_output:
                        with open(txt_filename, 'w', encoding='utf-8') as f:
                            f.write(raw_output)

                # Save notes if any exist
                if self.host_notes:
                    base_filename = os.path.splitext(filename)[0]  # Remove .xml/.json extension
                    self.save_notes_to_file(base_filename)

                status_msg = f"Scan results saved to {filename}"
                if not has_xml:
                    status_msg = f"Scan results saved as JSON to {os.path.splitext(filename)[0]}.json"
                if include_raw and raw_output:
                    status_msg += " (with raw output)"
                self._current_status_message = status_msg
                self._check_and_warn_privileged_scan()
                self.results_saved = True  # Mark results as saved
                return True # Indicate success
            except Exception as e:
                # Handle errors during file operations
                QMessageBox.critical(self, "Save Error", f"Could not save results to {filename}:\n{e}")
                self._current_status_message = f"Error saving results: {e}"
                self._check_and_warn_privileged_scan()
                return False # Indicate failure
        else:
            # User cancelled the save dialog
            self._current_status_message = "Save cancelled."
            self._check_and_warn_privileged_scan()
            return False # Indicate cancellation

    def export_to_csv(self):
        """
        Exports the device details table to a CSV file.
        Prompts user to select columns and filename.
        """
        # Check if there's data to export
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "No scan results available to export.")
            return

        # Get column headers
        column_headers = []
        for col in range(self.results_table.columnCount()):
            header_item = self.results_table.horizontalHeaderItem(col)
            column_headers.append(header_item.text() if header_item else f"Column {col}")

        # Show column selection dialog
        column_dialog = CSVExportDialog(column_headers, self)
        if column_dialog.exec() != QDialog.DialogCode.Accepted:
            self._current_status_message = "Export cancelled."
            self._check_and_warn_privileged_scan()
            return

        selected_columns = column_dialog.get_selected_columns()

        # Check if at least one column is selected
        if not selected_columns:
            QMessageBox.warning(self, "No Columns Selected", "Please select at least one column to export.")
            return

        # Open file save dialog
        suggested_filename = "neozen_scan_export.csv"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", suggested_filename,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not filename:
            self._current_status_message = "Export cancelled."
            self._check_and_warn_privileged_scan()
            return

        try:
            # Collect additional columns: IP, MAC, OS
            # These will be added to the export even if not in the visible table
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Write header row with selected columns + IP, MAC, OS
                header_row = [column_headers[i] for i in selected_columns]
                # Add additional columns if not already selected
                additional_headers = []
                if 0 not in selected_columns:  # Host column
                    additional_headers.append("IP Address")
                if 1 not in selected_columns:  # MAC column
                    additional_headers.append("MAC Address")
                additional_headers.append("Detected OS")

                writer.writerow(header_row + additional_headers)

                # Track exported rows to avoid duplicates (entire row must be unique)
                exported_rows = set()
                exported_count = 0

                # Write data rows - only unique rows
                for row in range(self.results_table.rowCount()):
                    row_data = []

                    # Get selected columns data
                    for col in selected_columns:
                        item = self.results_table.item(row, col)
                        row_data.append(item.text() if item else "")

                    # Get IP address from Host column's UserRole data
                    host_item = self.results_table.item(row, 0)
                    ip_address = ""
                    if host_item:
                        ip_address = host_item.data(Qt.ItemDataRole.UserRole) or ""

                    # Get MAC if not already in selected columns
                    if 0 not in selected_columns:
                        row_data.append(ip_address)

                    if 1 not in selected_columns:
                        mac_item = self.results_table.item(row, 1)
                        row_data.append(mac_item.text() if mac_item else "")

                    # Get OS information from current_scan_data
                    detected_os = ""
                    if ip_address:
                        # Try to find the host data - IP might be in different formats
                        host_data = None
                        if ip_address in self.current_scan_data:
                            host_data = self.current_scan_data[ip_address]
                        else:
                            # Try stripping whitespace and checking again
                            ip_clean = ip_address.strip()
                            if ip_clean in self.current_scan_data:
                                host_data = self.current_scan_data[ip_clean]

                        if host_data:
                            osmatch = host_data.get('osmatch', [])
                            if osmatch and len(osmatch) > 0:
                                # Get the highest accuracy OS match
                                best_match = osmatch[0]
                                os_name = best_match.get('name', '')
                                os_accuracy = best_match.get('accuracy', '')
                                detected_os = f"{os_name} ({os_accuracy}%)" if os_accuracy else os_name

                    row_data.append(detected_os)

                    # Create a tuple from row_data to use as set key (lists aren't hashable)
                    row_tuple = tuple(row_data)

                    # Skip if we've already exported this exact row
                    if row_tuple in exported_rows:
                        continue

                    # Mark this row as exported
                    exported_rows.add(row_tuple)

                    writer.writerow(row_data)
                    exported_count += 1

            self._current_status_message = f"Exported {exported_count} unique rows to {filename}"
            self._check_and_warn_privileged_scan()
            QMessageBox.information(self, "Export Successful",
                                   f"Successfully exported {exported_count} unique rows to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export to CSV:\n{e}")
            self._current_status_message = f"Export failed: {e}"
            self._check_and_warn_privileged_scan()

    def show_about_dialog(self):
        """Displays a simple About dialog box."""
        QMessageBox.about(self, "About NeoZen",
                          "NeoZen - A Modern Nmap GUI\n\n"
                          "Version: 0.1 (Development)\n"
                          "Built with Python and PyQt6.\n"
                          "Provides a graphical interface for the Nmap Security Scanner.")

    def closeEvent(self, event):
        """
        Handles the window close event (e.g., clicking the 'X' button).
        Prompts the user to stop a running scan or save unsaved results.
        """
        should_close = True # Assume closing is allowed initially

        # 1. Check if scan is running
        if self.scanner_thread and self.scanner_thread.isRunning():
            reply = QMessageBox.question(self, 'Scan in Progress',
                                           "A scan is currently running. Stop scan and exit?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No) # Default to No
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_scan() # Request stop
                # Wait briefly for thread to potentially finish
                if self.scanner_thread:
                    self.scanner_thread.wait(1500) # Wait up to 1.5 seconds
                # Scan might still be stopping, but proceed to check save prompt
            else:
                # User chose not to stop scan, so prevent closing
                should_close = False
                event.ignore()
                return # Stop processing the close event

        # 2. If not running (or just stopped), check for unsaved results
        # Check if we have unsaved results (either XML file or scan data) AND results haven't been saved yet
        has_xml = bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path))
        has_data = bool(self.current_scan_data)
        if should_close and (has_xml or has_data) and not self.results_saved:
            # Create a custom message box for Save/Don't Save/Cancel
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Unsaved Scan Results")
            msg_box.setText("The results of the last scan have not been saved.")
            msg_box.setInformativeText("Do you want to save the results before exiting?")
            # Add buttons with specific roles
            save_label = "&Save XML" if has_xml else "&Save Results"
            save_button = msg_box.addButton(save_label, QMessageBox.ButtonRole.AcceptRole)
            discard_button = msg_box.addButton("&Don't Save", QMessageBox.ButtonRole.DestructiveRole)
            cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(save_button) # Make Save the default
            msg_box.setIcon(QMessageBox.Icon.Question)

            msg_box.exec() # Show the dialog and wait for user choice
            clicked_button = msg_box.clickedButton()

            # Handle user's choice
            if clicked_button == save_button:
                # Try to save; if save fails or is cancelled, prevent closing
                if not self.save_scan_results():
                    should_close = False
                    event.ignore()
                    return
                # If save successful, should_close remains True
            elif clicked_button == discard_button:
                # User chose not to save, allow closing
                should_close = True
            else: # Cancel button was clicked
                should_close = False
                event.ignore()
                return

        # 3. If closing is allowed, clean up temp file and accept the event
        if should_close:
            self._cleanup_last_scan_file() # Clean up before exiting
            event.accept() # Allow the window to close
        else:
            # This case should be covered by returns above, but as safety
            event.ignore() # Prevent the window from closing


# --- Main Execution Block ---
if __name__ == '__main__':
    # Standard Qt application setup
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # Start the event loop and exit with its return code
    sys.exit(app.exec())
