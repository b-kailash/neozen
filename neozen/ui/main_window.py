import sys
import json # For saving/loading profiles
import os
from pathlib import Path # For cross-platform path handling

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox # Added QComboBox, QDialog, etc.
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from neozen.core.scanner import Scanner
from neozen.core.profiles import ProfileManager # Import the new ProfileManager

# --- Profile Save Dialog ---
class SaveProfileDialog(QDialog):
    """Simple dialog to get a name for saving a profile."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Profile")
        layout = QVBoxLayout(self)

        self.form_layout = QFormLayout()
        self.profile_name_input = QLineEdit(self)
        self.form_layout.addRow("Profile Name:", self.profile_name_input)
        layout.addLayout(self.form_layout)

        # Standard buttons (OK & Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept) # Connect OK to accept
        self.button_box.rejected.connect(self.reject) # Connect Cancel to reject
        layout.addWidget(self.button_box)

    def get_profile_name(self):
        """Returns the entered profile name."""
        return self.profile_name_input.text().strip()

# --- Main Window ---
class MainWindow(QMainWindow):
    """
    Main application window for NeoZen.
    Includes scan configuration options and profile management.
    """
    def __init__(self):
        super().__init__()

        # --- Profile Manager ---
        self.profile_manager = ProfileManager()
        self.profiles = self.profile_manager.load_profiles() # Load profiles on startup

        self.setWindowTitle("NeoZen - Modern Nmap GUI")
        self.setGeometry(100, 100, 950, 750) # Adjusted size for new controls

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget) # Main vertical layout

        # --- Top Row: Target and Profile Selection ---
        top_row_layout = QHBoxLayout()
        target_label = QLabel("Target:")
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter IP address, hostname, or network range")

        profile_label = QLabel("Profile:")
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Custom Scan") # Default option
        self.profile_combo.addItems(sorted(self.profiles.keys())) # Populate with loaded profiles
        self.profile_combo.setToolTip("Select a saved scan profile or choose 'Custom Scan'")

        top_row_layout.addWidget(target_label)
        top_row_layout.addWidget(self.target_input, 1) # Give target input more stretch
        top_row_layout.addWidget(profile_label)
        top_row_layout.addWidget(self.profile_combo, 1) # Give profile combo stretch

        # --- Scan Configuration Area ---
        config_layout = QGridLayout() # Use grid for better alignment

        # Scan Type / Technique (Example - more can be added)
        scan_type_label = QLabel("Scan Type:")
        self.scan_type_combo = QComboBox()
        # These map roughly to Zenmap profiles / common use cases
        self.scan_type_combo.addItem("Intense scan (-T4 -A -v)", "-T4 -A -v")
        self.scan_type_combo.addItem("Intense scan plus UDP (-T4 -A -sU -v)", "-T4 -A -sU -v")
        self.scan_type_combo.addItem("Intense scan, all TCP ports (-p 1-65535 -T4 -A -v)", "-p 1-65535 -T4 -A -v")
        self.scan_type_combo.addItem("Ping scan (-sn)", "-sn")
        self.scan_type_combo.addItem("Quick scan (-T4 -F)", "-T4 -F")
        self.scan_type_combo.addItem("Regular scan (Default Nmap)", "") # No args = default
        self.scan_type_combo.addItem("TCP SYN scan (-sS)", "-sS") # Needs root/admin
        self.scan_type_combo.addItem("TCP Connect scan (-sT)", "-sT")
        self.scan_type_combo.addItem("UDP scan (-sU)", "-sU") # Often needs root/admin
        self.scan_type_combo.setToolTip("Select a common scan type (sets arguments below)")

        # Custom Arguments
        custom_args_label = QLabel("Nmap Arguments:")
        self.custom_args_input = QLineEdit()
        self.custom_args_input.setPlaceholderText("e.g., -p 80,443 -sV --script=vuln")
        self.custom_args_input.setToolTip("Arguments defined by Scan Type, or enter custom ones")

        config_layout.addWidget(scan_type_label, 0, 0)
        config_layout.addWidget(self.scan_type_combo, 0, 1)
        config_layout.addWidget(custom_args_label, 1, 0)
        config_layout.addWidget(self.custom_args_input, 1, 1)

        # --- Scan Control and Profile Buttons ---
        button_layout = QHBoxLayout()
        self.scan_button = QPushButton("Scan")
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setEnabled(False)
        self.save_profile_button = QPushButton("Save Profile")
        self.delete_profile_button = QPushButton("Delete Profile")
        self.delete_profile_button.setEnabled(False) # Enabled only when a profile is selected

        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch() # Push scan buttons left
        button_layout.addWidget(self.save_profile_button)
        button_layout.addWidget(self.delete_profile_button)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        # --- Tabbed Output Area ---
        self.tab_widget = QTabWidget()
        # Raw Output Tab
        self.raw_output_widget = QWidget()
        raw_output_layout = QVBoxLayout(self.raw_output_widget)
        raw_output_layout.setContentsMargins(0, 5, 0, 0)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFontFamily("monospace")
        raw_output_layout.addWidget(self.output_area)
        self.tab_widget.addTab(self.raw_output_widget, "Raw Output")
        # Parsed Results Tab
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

        # --- Add layouts and widgets to main layout ---
        main_layout.addLayout(top_row_layout)
        main_layout.addLayout(config_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.tab_widget)

        # --- Status Bar ---
        self.statusBar().showMessage("Ready")

        # --- Nmap Scanner Thread ---
        self.scanner_thread = None

        # --- Connect Signals and Slots ---
        self.scan_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        self.target_input.returnPressed.connect(self.start_scan)
        self.scan_type_combo.currentIndexChanged.connect(self.update_args_from_scan_type)
        self.profile_combo.currentIndexChanged.connect(self.load_profile_settings) # Connect profile selection
        self.save_profile_button.clicked.connect(self.save_current_profile) # Connect save button
        self.delete_profile_button.clicked.connect(self.delete_selected_profile) # Connect delete button

        # --- Initial State ---
        self.update_args_from_scan_type() # Set initial args based on default scan type
        self.load_profile_settings() # Update delete button state based on initial profile selection


    def update_args_from_scan_type(self):
        """Updates the custom arguments input based on the selected scan type."""
        # Retrieve the arguments stored as data in the combo box item
        arguments = self.scan_type_combo.currentData(Qt.ItemDataRole.UserRole)
        if arguments is not None:
            self.custom_args_input.setText(arguments)
            self.custom_args_input.setReadOnly(True) # Make read-only when using preset
            self.custom_args_input.setToolTip("Arguments set by selected Scan Type")
        else:
            # Handle case where data might be missing (shouldn't happen with current setup)
            self.custom_args_input.clear()
            self.custom_args_input.setReadOnly(False)
            self.custom_args_input.setToolTip("Enter custom Nmap arguments")


    def load_profile_settings(self):
        """Loads settings from the selected profile into the UI controls."""
        selected_profile_name = self.profile_combo.currentText()

        if selected_profile_name == "Custom Scan":
            # Reset to default or clear fields for custom scan
            self.target_input.clear() # Or keep target? User decision.
            self.scan_type_combo.setCurrentIndex(0) # Reset to first scan type
            self.update_args_from_scan_type()
            self.delete_profile_button.setEnabled(False)
        elif selected_profile_name in self.profiles:
            profile_data = self.profiles[selected_profile_name]
            self.target_input.setText(profile_data.get("target", ""))

            # Try to match saved arguments to a scan type
            saved_args = profile_data.get("arguments", "")
            found_match = False
            for i in range(self.scan_type_combo.count()):
                item_args = self.scan_type_combo.itemData(i, Qt.ItemDataRole.UserRole)
                if item_args == saved_args:
                    self.scan_type_combo.setCurrentIndex(i)
                    found_match = True
                    break

            # If no match, set args directly (might imply a custom scan was saved)
            # Or potentially add a "Saved Custom" item to scan_type_combo? Simpler to just set args.
            self.custom_args_input.setText(saved_args)
            if found_match:
                 self.custom_args_input.setReadOnly(True)
                 self.custom_args_input.setToolTip("Arguments set by selected Scan Type")
            else: # Args didn't match a preset type
                 self.custom_args_input.setReadOnly(False) # Allow editing if it was custom
                 self.custom_args_input.setToolTip("Custom arguments loaded from profile")


            self.delete_profile_button.setEnabled(True) # Enable delete for saved profiles
        else:
            # Profile name exists in combo but not in loaded data (error state)
             QMessageBox.warning(self, "Profile Error", f"Could not load data for profile '{selected_profile_name}'.")
             self.profile_combo.setCurrentIndex(0) # Reset to custom
             self.delete_profile_button.setEnabled(False)


    def save_current_profile(self):
        """Saves the current UI settings (target, args) as a new profile."""
        current_args = self.custom_args_input.text().strip()
        current_target = self.target_input.text().strip() # Optional: include target in profile?

        dialog = SaveProfileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_name = dialog.get_profile_name()
            if not profile_name:
                QMessageBox.warning(self, "Save Error", "Profile name cannot be empty.")
                return
            if profile_name == "Custom Scan":
                 QMessageBox.warning(self, "Save Error", "'Custom Scan' is a reserved name.")
                 return

            profile_data = {
                "arguments": current_args,
                "target": current_target # Save target as well
            }

            # Add or update profile
            is_update = profile_name in self.profiles
            self.profiles[profile_name] = profile_data

            if self.profile_manager.save_profiles(self.profiles):
                self.statusBar().showMessage(f"Profile '{profile_name}' saved.")
                # Update combo box
                if not is_update:
                    self.profile_combo.addItem(profile_name)
                # Select the newly saved/updated profile
                self.profile_combo.setCurrentText(profile_name)
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save profiles to disk.")
                # Revert if save failed
                if not is_update:
                    del self.profiles[profile_name]
                else:
                    # Need to restore old profile data if update failed - requires loading again
                    self.profiles = self.profile_manager.load_profiles() # Reload to be safe


    def delete_selected_profile(self):
        """Deletes the currently selected profile."""
        selected_profile_name = self.profile_combo.currentText()

        if selected_profile_name == "Custom Scan" or selected_profile_name not in self.profiles:
            QMessageBox.warning(self, "Delete Error", "Cannot delete 'Custom Scan' or non-existent profile.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                       f"Are you sure you want to delete the profile '{selected_profile_name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            del self.profiles[selected_profile_name]
            if self.profile_manager.save_profiles(self.profiles):
                self.statusBar().showMessage(f"Profile '{selected_profile_name}' deleted.")
                # Remove from combo box and reset UI
                current_index = self.profile_combo.findText(selected_profile_name)
                if current_index >= 0:
                    self.profile_combo.removeItem(current_index)
                self.profile_combo.setCurrentIndex(0) # Go back to Custom Scan
            else:
                 QMessageBox.critical(self, "Delete Error", "Failed to save profile changes after deletion.")
                 # Add profile back if save failed
                 self.profiles = self.profile_manager.load_profiles() # Reload to be safe


    def get_nmap_arguments(self):
        """Constructs the Nmap arguments string from UI controls."""
        # For Phase 3, we simply use the text in the custom_args_input
        # In the future, this could combine selections from checkboxes etc.
        return self.custom_args_input.text().strip()

    def start_scan(self):
        """
        Slot to handle starting the Nmap scan using current settings.
        """
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please enter a target to scan.")
            return

        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A scan is already running.")
            return

        nmap_args = self.get_nmap_arguments() # Get args from UI

        # Clear previous output and results
        self.output_area.clear()
        self.results_table.setRowCount(0)
        self.statusBar().showMessage(f"Starting scan on {target} with args: {nmap_args}...")
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        # Disable config while scanning
        self.profile_combo.setEnabled(False)
        self.scan_type_combo.setEnabled(False)
        self.custom_args_input.setEnabled(False)
        self.save_profile_button.setEnabled(False)
        self.delete_profile_button.setEnabled(False)


        # --- Create and start the scanner thread ---
        self.scanner_thread = Scanner(target, nmap_args) # Pass constructed args

        # Connect signals from the thread to slots in this window
        self.scanner_thread.scan_output.connect(self.append_output)
        self.scanner_thread.scan_results_ready.connect(self.display_parsed_results)
        self.scanner_thread.scan_finished.connect(self.scan_complete)
        self.scanner_thread.scan_error.connect(self.scan_error_occurred)

        # Switch to Raw Output tab when scan starts
        self.tab_widget.setCurrentWidget(self.raw_output_widget)

        self.scanner_thread.start()

    def stop_scan(self):
        """Slot to handle stopping the currently running scan."""
        # (Implementation remains the same as Phase 2)
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.statusBar().showMessage("Attempting to stop scan...")
            self.scanner_thread.stop()
        else:
            self._reset_ui_after_scan("No scan is currently running.")

    def append_output(self, text):
        """Slot to append text to the raw output area."""
        # (Implementation remains the same as Phase 2)
        self.output_area.append(text)
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum())

    def display_parsed_results(self, results_data):
        """Slot to populate the results table."""
        # (Implementation remains the same as Phase 2)
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

    def _reset_ui_after_scan(self, status_message):
        """Helper method to reset UI elements after scan finishes or errors."""
        self.statusBar().showMessage(status_message)
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        # Re-enable config
        self.profile_combo.setEnabled(True)
        self.scan_type_combo.setEnabled(True)
        # Only enable custom args if not using a preset scan type? Check current state.
        self.custom_args_input.setEnabled(True) # Re-enable for now, might need refinement
        self.save_profile_button.setEnabled(True)
        # Only enable delete if a profile is selected
        self.delete_profile_button.setEnabled(self.profile_combo.currentIndex() > 0)

        self.scanner_thread = None # Clear the thread reference

    def scan_complete(self, message):
        """Slot called when the scanner thread finishes successfully."""
        self._reset_ui_after_scan(message)

    def scan_error_occurred(self, error_message):
        """Slot called when the scanner thread encounters an error or is stopped."""
        if error_message not in self.output_area.toPlainText():
             QMessageBox.critical(self, "Scan Error / Stopped", error_message)
        self._reset_ui_after_scan(f"Scan Error / Stopped: {error_message}")

    def closeEvent(self, event):
        """Handles the main window close event."""
        # (Implementation remains the same as Phase 2)
        if self.scanner_thread and self.scanner_thread.isRunning():
            reply = QMessageBox.question(self, 'Scan in Progress',
                                           "A scan is currently running. Stop scan and exit?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_scan()
                if self.scanner_thread:
                    self.scanner_thread.wait(1500)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

# Example of running just this file for testing (optional)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
