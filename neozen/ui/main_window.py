import sys
import json # For saving/loading profiles
import os
import nmap # For parsing loaded XML
import shutil # For copying files (saving results)
from pathlib import Path # For cross-platform path handling

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QFileDialog
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from neozen.core.scanner import Scanner
from neozen.core.profiles import ProfileManager

# --- Profile Save Dialog (remains the same) ---
class SaveProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Profile")
        layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.profile_name_input = QLineEdit(self)
        self.form_layout.addRow("Profile Name:", self.profile_name_input)
        layout.addLayout(self.form_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    def get_profile_name(self):
        return self.profile_name_input.text().strip()

# --- Main Window ---
class MainWindow(QMainWindow):
    """
    Main application window for NeoZen.
    Includes scan configuration, profiles, and save/load results functionality.
    Manages cleanup of temporary scan files and prompts to save on close.
    """
    def __init__(self):
        super().__init__()

        self.profile_manager = ProfileManager()
        self.profiles = self.profile_manager.load_profiles()
        self.scanner_thread = None
        self.last_scan_xml_path = None # To store path of temp XML from LAST completed scan

        self.setWindowTitle("NeoZen - Modern Nmap GUI")
        self.setGeometry(100, 100, 950, 750)

        self._create_actions() # Create menu actions
        self._create_menu_bar() # Create the menu bar
        self._create_central_widget() # Create the main UI layout
        self._connect_signals() # Connect signals and slots

        # --- Initial State ---
        self.statusBar().showMessage("Ready")
        self.update_args_from_scan_type()
        self.load_profile_settings()

    def _create_actions(self):
        """Create QAction objects for menu items."""
        self.open_action = QAction("&Open Scan Results...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setStatusTip("Open saved Nmap XML scan results")
        self.open_action.triggered.connect(self.open_scan_results)

        self.save_action = QAction("&Save Scan Results...", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setStatusTip("Save results of the last completed scan")
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self.save_scan_results) # Connect to save method directly

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close)

        self.about_action = QAction("&About NeoZen", self)
        self.about_action.setStatusTip("Show information about NeoZen")
        self.about_action.triggered.connect(self.show_about_dialog)


    def _create_menu_bar(self):
        """Create the main menu bar."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)


    def _create_central_widget(self):
        """Create the central widget and its layout."""
        # (Code remains the same as previous version)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        top_row_layout = QHBoxLayout()
        target_label = QLabel("Target:")
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter IP address, hostname, or network range")
        profile_label = QLabel("Profile:")
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Custom Scan")
        self.profile_combo.addItems(sorted(self.profiles.keys()))
        self.profile_combo.setToolTip("Select a saved scan profile or choose 'Custom Scan'")
        top_row_layout.addWidget(target_label)
        top_row_layout.addWidget(self.target_input, 1)
        top_row_layout.addWidget(profile_label)
        top_row_layout.addWidget(self.profile_combo, 1)
        config_layout = QGridLayout()
        scan_type_label = QLabel("Scan Type:")
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItem("Intense scan (-T4 -A -v)", "-T4 -A -v")
        self.scan_type_combo.addItem("Intense scan plus UDP (-T4 -A -sU -v)", "-T4 -A -sU -v")
        self.scan_type_combo.addItem("Intense scan, all TCP ports (-p 1-65535 -T4 -A -v)", "-p 1-65535 -T4 -A -v")
        self.scan_type_combo.addItem("Ping scan (-sn)", "-sn")
        self.scan_type_combo.addItem("Quick scan (-T4 -F)", "-T4 -F")
        self.scan_type_combo.addItem("Regular scan (Default Nmap)", "")
        self.scan_type_combo.addItem("TCP SYN scan (-sS)", "-sS")
        self.scan_type_combo.addItem("TCP Connect scan (-sT)", "-sT")
        self.scan_type_combo.addItem("UDP scan (-sU)", "-sU")
        self.scan_type_combo.setToolTip("Select a common scan type (sets arguments below)")
        custom_args_label = QLabel("Nmap Arguments:")
        self.custom_args_input = QLineEdit()
        self.custom_args_input.setPlaceholderText("e.g., -p 80,443 -sV --script=vuln")
        self.custom_args_input.setToolTip("Arguments defined by Scan Type, or enter custom ones")
        config_layout.addWidget(scan_type_label, 0, 0)
        config_layout.addWidget(self.scan_type_combo, 0, 1)
        config_layout.addWidget(custom_args_label, 1, 0)
        config_layout.addWidget(self.custom_args_input, 1, 1)
        button_layout = QHBoxLayout()
        self.scan_button = QPushButton("Scan")
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setEnabled(False)
        self.save_profile_button = QPushButton("Save Profile")
        self.delete_profile_button = QPushButton("Delete Profile")
        self.delete_profile_button.setEnabled(False)
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_profile_button)
        button_layout.addWidget(self.delete_profile_button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        self.tab_widget = QTabWidget()
        self.raw_output_widget = QWidget()
        raw_output_layout = QVBoxLayout(self.raw_output_widget)
        raw_output_layout.setContentsMargins(0, 5, 0, 0)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFontFamily("monospace")
        raw_output_layout.addWidget(self.output_area)
        self.tab_widget.addTab(self.raw_output_widget, "Raw Output")
        self.parsed_results_widget = QWidget()
        parsed_results_layout = QVBoxLayout(self.parsed_results_widget)
        parsed_results_layout.setContentsMargins(0, 5, 0, 0)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(["Host", "Proto", "Port", "State", "Service", "Product", "Version"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSortingEnabled(True)
        parsed_results_layout.addWidget(self.results_table)
        self.tab_widget.addTab(self.parsed_results_widget, "Parsed Results")
        main_layout.addLayout(top_row_layout)
        main_layout.addLayout(config_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.tab_widget)


    def _connect_signals(self):
        """Connect signals from widgets to slots."""
        # (Code remains the same as previous version)
        self.scan_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        self.target_input.returnPressed.connect(self.start_scan)
        self.scan_type_combo.currentIndexChanged.connect(self.update_args_from_scan_type)
        self.profile_combo.currentIndexChanged.connect(self.load_profile_settings)
        self.save_profile_button.clicked.connect(self.save_current_profile)
        self.delete_profile_button.clicked.connect(self.delete_selected_profile)


    # --- Profile Methods (remain the same) ---
    def update_args_from_scan_type(self):
        arguments = self.scan_type_combo.currentData(Qt.ItemDataRole.UserRole)
        if arguments is not None:
            self.custom_args_input.setText(arguments)
            self.custom_args_input.setReadOnly(True)
            self.custom_args_input.setToolTip("Arguments set by selected Scan Type")
        else:
            self.custom_args_input.clear()
            self.custom_args_input.setReadOnly(False)
            self.custom_args_input.setToolTip("Enter custom Nmap arguments")

    def load_profile_settings(self):
        selected_profile_name = self.profile_combo.currentText()
        is_custom = (selected_profile_name == "Custom Scan")
        if is_custom:
            self.scan_type_combo.setCurrentIndex(0)
            self.update_args_from_scan_type()
        elif selected_profile_name in self.profiles:
            profile_data = self.profiles[selected_profile_name]
            self.target_input.setText(profile_data.get("target", ""))
            saved_args = profile_data.get("arguments", "")
            found_match = False
            for i in range(self.scan_type_combo.count()):
                item_args = self.scan_type_combo.itemData(i, Qt.ItemDataRole.UserRole)
                if item_args == saved_args:
                    self.scan_type_combo.setCurrentIndex(i)
                    found_match = True
                    break
            self.custom_args_input.setText(saved_args)
            self.custom_args_input.setReadOnly(found_match)
            self.custom_args_input.setToolTip("Arguments set by selected Scan Type" if found_match else "Custom arguments loaded from profile")
        else:
             QMessageBox.warning(self, "Profile Error", f"Could not load data for profile '{selected_profile_name}'.")
             self.profile_combo.setCurrentIndex(0)
        self.delete_profile_button.setEnabled(not is_custom and selected_profile_name in self.profiles)

    def save_current_profile(self):
        current_args = self.custom_args_input.text().strip()
        current_target = self.target_input.text().strip()
        dialog = SaveProfileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_name = dialog.get_profile_name()
            if not profile_name or profile_name == "Custom Scan":
                QMessageBox.warning(self, "Save Error", "Profile name cannot be empty or 'Custom Scan'.")
                return
            profile_data = {"arguments": current_args, "target": current_target}
            is_update = profile_name in self.profiles
            self.profiles[profile_name] = profile_data
            if self.profile_manager.save_profiles(self.profiles):
                self.statusBar().showMessage(f"Profile '{profile_name}' saved.")
                if not is_update: self.profile_combo.addItem(profile_name)
                self.profile_combo.setCurrentText(profile_name)
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save profiles to disk.")
                if not is_update: del self.profiles[profile_name]
                else: self.profiles = self.profile_manager.load_profiles()

    def delete_selected_profile(self):
        selected_profile_name = self.profile_combo.currentText()
        if selected_profile_name == "Custom Scan" or selected_profile_name not in self.profiles:
            QMessageBox.warning(self, "Delete Error", "Cannot delete 'Custom Scan' or non-existent profile.")
            return
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete profile '{selected_profile_name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.profiles[selected_profile_name]
            if self.profile_manager.save_profiles(self.profiles):
                self.statusBar().showMessage(f"Profile '{selected_profile_name}' deleted.")
                current_index = self.profile_combo.findText(selected_profile_name)
                if current_index >= 0: self.profile_combo.removeItem(current_index)
                self.profile_combo.setCurrentIndex(0)
            else:
                 QMessageBox.critical(self, "Delete Error", "Failed to save profile changes after deletion.")
                 self.profiles = self.profile_manager.load_profiles()

    # --- Scan Methods ---
    def get_nmap_arguments(self):
        return self.custom_args_input.text().strip()

    def _cleanup_last_scan_file(self):
        """Safely removes the temporary XML file from the PREVIOUS scan."""
        if self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path):
            try:
                os.remove(self.last_scan_xml_path)
                # Show message only if cleanup happens, not every time
                self.statusBar().showMessage(f"Cleaned up previous scan file: {os.path.basename(self.last_scan_xml_path)}", 2000)
                self.last_scan_xml_path = None
            except OSError as e:
                print(f"[Warning] Could not remove previous temp file {self.last_scan_xml_path}: {e}")
                self.last_scan_xml_path = None # Clear path even if removal fails
            except Exception as e:
                 print(f"[Warning] Error during previous temp file cleanup: {e}")
                 self.last_scan_xml_path = None
        else:
             self.last_scan_xml_path = None # Clear path if it was None or file didn't exist

    def start_scan(self):
        """Slot to handle starting the Nmap scan."""
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please enter a target to scan.")
            return
        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A scan is already running.")
            return

        self._cleanup_last_scan_file() # Clean up previous file

        nmap_args = self.get_nmap_arguments()
        self.output_area.clear()
        self.results_table.setRowCount(0)
        self.statusBar().showMessage(f"Starting scan on {target} with args: {nmap_args}...")
        self._set_ui_scan_state(scanning=True)

        self.scanner_thread = Scanner(target, nmap_args)
        self.scanner_thread.scan_output.connect(self.append_output)
        self.scanner_thread.scan_results_ready.connect(self.display_parsed_results)
        self.scanner_thread.scan_finished.connect(self.scan_complete)
        self.scanner_thread.scan_error.connect(self.scan_error_occurred)
        self.tab_widget.setCurrentWidget(self.raw_output_widget)
        self.scanner_thread.start()

    def stop_scan(self):
        """Slot to handle stopping the currently running scan."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.statusBar().showMessage("Attempting to stop scan...")
            self.scanner_thread.stop()
        else:
            self._reset_ui_after_scan("No scan is currently running.")
            self._cleanup_last_scan_file()

    def append_output(self, text):
        """Slot to append text to the raw output area."""
        self.output_area.append(text)
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum())

    def display_parsed_results(self, results_data):
        """Slot to populate the results table."""
        # (Implementation remains the same)
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        row_position = 0
        for host, host_data in results_data.items():
            hostname = host_data.get('hostname', '')
            display_host = f"{hostname} ({host})" if hostname and hostname != host else host
            protocols = host_data.get('protocols', {})
            if not protocols:
                if host_data.get('state') == 'up':
                     self.results_table.insertRow(row_position)
                     self.results_table.setItem(row_position, 0, QTableWidgetItem(display_host))
                     self.results_table.setItem(row_position, 3, QTableWidgetItem(host_data.get('state', 'unknown')))
                     self.results_table.setItem(row_position, 4, QTableWidgetItem("(No ports found/reported)"))
                     row_position += 1
                continue
            for proto, ports in protocols.items():
                for port, port_data in ports.items():
                    self.results_table.insertRow(row_position)
                    self.results_table.setItem(row_position, 0, QTableWidgetItem(display_host))
                    self.results_table.setItem(row_position, 1, QTableWidgetItem(proto))
                    self.results_table.setItem(row_position, 2, QTableWidgetItem(str(port)))
                    self.results_table.setItem(row_position, 3, QTableWidgetItem(port_data.get('state', '')))
                    self.results_table.setItem(row_position, 4, QTableWidgetItem(port_data.get('name', '')))
                    self.results_table.setItem(row_position, 5, QTableWidgetItem(port_data.get('product', '')))
                    self.results_table.setItem(row_position, 6, QTableWidgetItem(port_data.get('version', '')))
                    row_position += 1
        self.results_table.setSortingEnabled(True)
        if results_data:
            self.tab_widget.setCurrentWidget(self.parsed_results_widget)

    def _set_ui_scan_state(self, scanning: bool):
        """Enable/disable UI elements based on scanning state."""
        # (Code remains the same as previous version)
        self.scan_button.setEnabled(not scanning)
        self.stop_button.setEnabled(scanning)
        self.progress_bar.setVisible(scanning)
        self.profile_combo.setEnabled(not scanning)
        self.scan_type_combo.setEnabled(not scanning)
        self.custom_args_input.setEnabled(not scanning)
        self.save_profile_button.setEnabled(not scanning)
        self.delete_profile_button.setEnabled(not scanning and self.profile_combo.currentIndex() > 0)
        self.save_action.setEnabled(not scanning and bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path)))
        self.open_action.setEnabled(not scanning)
        if scanning: self.last_scan_xml_path = None

    def _reset_ui_after_scan(self, status_message):
        """Helper method to reset UI elements after scan finishes or errors."""
        self.statusBar().showMessage(status_message)
        self._set_ui_scan_state(scanning=False)
        self.scanner_thread = None

    def scan_complete(self, message, temp_xml_path):
        """Slot called when the scanner thread finishes successfully."""
        self.last_scan_xml_path = temp_xml_path
        self._reset_ui_after_scan(message)
        self.save_action.setEnabled(bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path)))

    def scan_error_occurred(self, error_message):
        """Slot called when the scanner thread encounters an error or is stopped."""
        if error_message not in self.output_area.toPlainText():
             QMessageBox.critical(self, "Scan Error / Stopped", error_message)
        self.last_scan_xml_path = None
        self._reset_ui_after_scan(f"Scan Error / Stopped: {error_message}")

    # --- File Menu Methods ---
    def open_scan_results(self):
        """Opens an Nmap XML file and displays its results."""
        # (Code remains the same as previous version)
        if self.scanner_thread and self.scanner_thread.isRunning():
             QMessageBox.warning(self, "Scan Running", "Cannot open results while a scan is in progress.")
             return
        filename, _ = QFileDialog.getOpenFileName(self, "Open Nmap Scan Results", "", "Nmap XML Files (*.xml);;All Files (*)")
        if filename:
            self._cleanup_last_scan_file()
            self.statusBar().showMessage(f"Opening {filename}...")
            try:
                with open(filename, 'r', encoding='utf-8') as f: xml_content = f.read()
                if not xml_content:
                     QMessageBox.warning(self, "Empty File", f"The file '{filename}' is empty.")
                     self.statusBar().showMessage("Failed to open empty file.")
                     return
                nm = nmap.PortScanner()
                scan_data = nm.analyse_nmap_xml_scan(nmap_xml_output=xml_content)
                parsed_results = {}
                if 'scan' in scan_data and isinstance(scan_data['scan'], dict):
                     for host_ip, host_scan_data in scan_data['scan'].items():
                          if not isinstance(host_scan_data, dict): continue
                          hostname = ''
                          hostnames_list = host_scan_data.get('hostnames', [])
                          if isinstance(hostnames_list, list) and len(hostnames_list) > 0:
                               hostname_entry = hostnames_list[0]
                               if isinstance(hostname_entry, dict): hostname = hostname_entry.get('name', '')
                          state = 'unknown'
                          status_info = host_scan_data.get('status', {})
                          if isinstance(status_info, dict): state = status_info.get('state', 'unknown')
                          host_data_for_ui = {'hostname': hostname, 'state': state, 'protocols': {}}
                          for proto in ['tcp', 'udp', 'ip', 'sctp']:
                               if proto in host_scan_data and isinstance(host_scan_data[proto], dict):
                                    if proto not in host_data_for_ui['protocols']: host_data_for_ui['protocols'][proto] = {}
                                    for port_str, port_data in host_scan_data[proto].items():
                                         if not isinstance(port_data, dict): continue
                                         try:
                                              port_int = int(port_str)
                                              host_data_for_ui['protocols'][proto][port_int] = {
                                                   'state': port_data.get('state', 'unknown'), 'name': port_data.get('name', ''),
                                                   'version': port_data.get('version', ''), 'product': port_data.get('product', ''),
                                                   'extrainfo': port_data.get('extrainfo', ''), 'cpe': port_data.get('cpe', '')}
                                         except (ValueError, TypeError): continue
                          parsed_results[host_ip] = host_data_for_ui
                else:
                     host_info = "(No host details found in XML)"
                     if 'nmap' in scan_data and 'hosts' in scan_data['nmap']:
                          num_hosts = scan_data['nmap']['hosts'].get('up', 0)
                          total_hosts = scan_data['nmap']['hosts'].get('total', 0)
                          host_info = f"({num_hosts} host(s) up / {total_hosts} total)"
                     QMessageBox.information(self, "Scan Info", f"Loaded file contains scan summary but no detailed host results {host_info}.")

                self.output_area.setText(f"--- Results loaded from: {filename} ---\n\n(Raw output not available for loaded files)")
                self.display_parsed_results(parsed_results)
                self.statusBar().showMessage(f"Successfully loaded results from {filename}")
                self.last_scan_xml_path = None
                self.save_action.setEnabled(False)
            except FileNotFoundError:
                 QMessageBox.critical(self, "Error", f"File not found: {filename}")
                 self.statusBar().showMessage("Error opening file.")
            except Exception as e:
                QMessageBox.critical(self, "Error Opening/Parsing File", f"Could not open or parse {filename}:\n{e}")
                self.statusBar().showMessage(f"Error opening/parsing file: {e}")

    # --- MODIFIED: save_scan_results to return success/failure ---
    def save_scan_results(self):
        """
        Saves the XML results of the last completed scan to a file.
        Returns True on success, False on failure or cancellation.
        """
        if not self.last_scan_xml_path or not os.path.exists(self.last_scan_xml_path):
            QMessageBox.warning(self, "No Results", "No scan results available to save. Please run a scan first.")
            return False # Indicate failure

        suggested_filename = "nmap_scan_results.xml"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Nmap Scan Results",
            suggested_filename,
            "Nmap XML Files (*.xml);;All Files (*)"
        )

        if filename:
            try:
                shutil.copyfile(self.last_scan_xml_path, filename)
                self.statusBar().showMessage(f"Scan results saved to {filename}")
                # Optional: Maybe disable save action after successful save?
                # self.save_action.setEnabled(False)
                return True # Indicate success
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save results to {filename}:\n{e}")
                self.statusBar().showMessage(f"Error saving results: {e}")
                return False # Indicate failure
        else:
            # User cancelled the save dialog
            self.statusBar().showMessage("Save cancelled.")
            return False # Indicate cancellation

    def show_about_dialog(self):
        """Displays a simple About dialog."""
        QMessageBox.about(self, "About NeoZen",
                          "NeoZen - A Modern Nmap GUI\n\n"
                          "Built with Python and PyQt.")

    # --- MODIFIED: closeEvent to prompt for save ---
    def closeEvent(self, event):
        """Handles the main window close event, prompting to save if necessary."""
        should_close = True # Assume we can close unless something stops us

        # 1. Check if scan is running
        if self.scanner_thread and self.scanner_thread.isRunning():
            reply = QMessageBox.question(self, 'Scan in Progress', "Scan running. Stop and exit?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_scan()
                if self.scanner_thread: self.scanner_thread.wait(1500)
                # Proceed to check for unsaved results after stopping
            else:
                should_close = False # User chose not to stop scan
                event.ignore()
                return # Don't proceed further

        # 2. If not running (or stopped), check for unsaved results
        if should_close and self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path):
            # Use custom button text for clarity
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Unsaved Scan Results")
            msg_box.setText("The results of the last scan have not been saved.")
            msg_box.setInformativeText("Do you want to save the results before exiting?")
            save_button = msg_box.addButton("&Save", QMessageBox.ButtonRole.AcceptRole)
            discard_button = msg_box.addButton("&Don't Save", QMessageBox.ButtonRole.DestructiveRole)
            cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(save_button)
            msg_box.setIcon(QMessageBox.Icon.Question)

            msg_box.exec()

            clicked_button = msg_box.clickedButton()

            if clicked_button == save_button:
                # Attempt to save; if user cancels save dialog, don't close
                if not self.save_scan_results():
                    should_close = False # Save failed or was cancelled
                    event.ignore()
                    return # Stop processing close event
                # If save was successful, should_close remains True
            elif clicked_button == discard_button:
                # User chose not to save, proceed to close
                should_close = True
            else: # Cancel button clicked
                should_close = False
                event.ignore()
                return # Stop processing close event

        # 3. If we should close, perform cleanup and accept
        if should_close:
            self._cleanup_last_scan_file()
            event.accept()
        else:
            # This case should technically be covered by returns above, but as safety
            event.ignore()


# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
