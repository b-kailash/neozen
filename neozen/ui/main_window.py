import sys
import json
import os
import nmap
import shutil
from pathlib import Path
import shlex # Import shlex for safer argument splitting/joining

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QFileDialog,
    QAbstractItemView, QSplitter # Added QSplitter
)
from PyQt6.QtGui import QAction, QFont # Added QFont
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from neozen.core.scanner import Scanner
from neozen.core.profiles import ProfileManager

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

        # --- Window Setup ---
        self.setWindowTitle("NeoZen - Modern Nmap GUI")
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
        self.save_action.setStatusTip("Save results of the last completed scan")
        self.save_action.setEnabled(False) # Initially disabled
        self.save_action.triggered.connect(self.save_scan_results)

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
        custom_args_label = QLabel("Nmap Arguments:")
        self.custom_args_input = QLineEdit()
        self.custom_args_input.setPlaceholderText("e.g., -p 80,443 -sV --script=vuln")
        self.custom_args_input.setToolTip("Arguments defined by Scan Type, or enter custom ones")
        scan_config_layout.addWidget(scan_type_label, 0, 0)
        scan_config_layout.addWidget(self.scan_type_combo, 0, 1)
        scan_config_layout.addWidget(custom_args_label, 1, 0)
        scan_config_layout.addWidget(self.custom_args_input, 1, 1)

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
        self.stop_button.setEnabled(False) # Disabled initially
        self.save_profile_button = QPushButton("Save Profile")
        self.delete_profile_button = QPushButton("Delete Profile")
        self.delete_profile_button.setEnabled(False) # Disabled initially
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch() # Push scan/stop left, profile buttons right
        button_layout.addWidget(self.save_profile_button)
        button_layout.addWidget(self.delete_profile_button)

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

        # Parsed Results Tab (Table View)
        self.parsed_results_widget = QWidget()
        parsed_results_layout = QVBoxLayout(self.parsed_results_widget)
        parsed_results_layout.setContentsMargins(0, 5, 0, 0)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(["Host", "Proto", "Port", "State", "Service", "Product", "Version"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Make table read-only
        self.results_table.setAlternatingRowColors(True) # Improve readability
        self.results_table.verticalHeader().setVisible(False) # Hide default row numbers
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Select whole rows
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Allow only one row selected
        # Configure column resizing behavior
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Host (allow resize)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Proto (fit content)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Port (fit content)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # State (allow resize)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # Service (allow resize)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch) # Product (stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) # Version (stretch)
        self.results_table.setSortingEnabled(True) # Allow sorting by column header clicks
        parsed_results_layout.addWidget(self.results_table)
        self.tab_widget.addTab(self.parsed_results_widget, "Parsed Results")

        # Add the tab widget to the top part of the splitter
        results_splitter.addWidget(self.tab_widget)

        # --- Bottom part of splitter: Host Details Area ---
        details_container = QWidget() # Use container for label + text area
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 5, 0, 0) # Adjust margins
        details_label = QLabel("Host Details:")
        self.host_details_area = QTextEdit()
        self.host_details_area.setReadOnly(True)
        self.host_details_area.setFont(monospace_font) # Use consistent monospace font
        self.host_details_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) # Disable line wrapping
        details_layout.addWidget(details_label)
        details_layout.addWidget(self.host_details_area)

        # Add the details container to the bottom part of the splitter
        results_splitter.addWidget(details_container)

        # --- Configure Splitter Sizes ---
        # Set initial relative sizes (e.g., 2/3 for tabs, 1/3 for details)
        results_splitter.setSizes([600, 300])

        # --- Add widgets to main application layout ---
        main_layout.addWidget(config_widget) # Add the top configuration group
        main_layout.addLayout(button_layout) # Add the button row
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
        # Profile management buttons
        self.save_profile_button.clicked.connect(self.save_current_profile)
        self.delete_profile_button.clicked.connect(self.delete_selected_profile)
        # Results table selection -> Host Details update
        self.results_table.itemSelectionChanged.connect(self.display_host_details)
        # Update command display dynamically
        self.target_input.textChanged.connect(self._update_command_display)
        self.custom_args_input.textChanged.connect(self._update_command_display)
        # Update privilege warning dynamically
        self.custom_args_input.textChanged.connect(self._check_and_warn_privileged_scan)


    # --- Privilege Check ---
    def _check_and_warn_privileged_scan(self):
        """
        Checks the current Nmap arguments for flags requiring elevation.
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
        UI settings (target, arguments) and displays it in a read-only field.
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
            command_parts.extend(args_list)
        except ValueError:
            # If args are malformed, just append the raw string if it's not empty
            if args_string:
                 command_parts.append(args_string)

        # Add target, quoting it using shlex.quote for safety if it contains spaces/special chars
        command_parts.append(shlex.quote(target))

        # Join parts into a single string for display
        display_command = " ".join(command_parts)
        self.command_display_line.setText(display_command)


    # --- Profile Methods ---
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
        """Returns the Nmap arguments string currently shown in the input field."""
        return self.custom_args_input.text().strip()

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
        self.host_details_area.clear() # Clear details view
        nmap_args = self.get_nmap_arguments() # Get arguments from UI
        self.output_area.clear() # Clear raw output
        self.results_table.setRowCount(0) # Clear results table

        # Update UI state for scanning
        self._current_status_message = f"Starting scan on {target}..."
        self._set_ui_scan_state(scanning=True) # Disable config, enable stop button, etc.
        self._check_and_warn_privileged_scan() # Show status + warning

        # Create and configure the scanner thread
        self.scanner_thread = Scanner(target, nmap_args)
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
        """Appends text to the 'Raw Output' text area and auto-scrolls."""
        self.output_area.append(text)
        # Move scrollbar to the bottom to show the latest output
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum())

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
        """Populates the 'Parsed Results' table with summarized scan data."""
        self.results_table.setSortingEnabled(False) # Disable sorting during population
        self.results_table.setRowCount(0) # Clear existing rows
        row_position = 0
        # Iterate through each host in the results
        for host, host_data in results_data.items():
            hostname = host_data.get('hostname', '')
            # Format host display (include IP)
            display_host = f"{hostname} ({host})" if hostname and hostname != host else host
            protocols = host_data.get('protocols', {})

            # If no port/protocol info, but host is up, show a single row for the host
            if not protocols:
                if host_data.get('state') == 'up':
                     self.results_table.insertRow(row_position)
                     host_item = QTableWidgetItem(display_host)
                     # Store the actual IP address in the item's data for later retrieval
                     host_item.setData(Qt.ItemDataRole.UserRole, host)
                     self.results_table.setItem(row_position, 0, host_item) # Host column
                     self.results_table.setItem(row_position, 3, QTableWidgetItem(host_data.get('state', 'unknown'))) # State column
                     self.results_table.setItem(row_position, 4, QTableWidgetItem("(No ports found/reported)")) # Service column
                     row_position += 1
                continue # Skip hosts with no protocols if not 'up'

            # If ports exist, iterate through protocols and ports
            for proto, ports in protocols.items():
                for port, port_data in ports.items():
                    self.results_table.insertRow(row_position)
                    # Create table items for each cell
                    host_item = QTableWidgetItem(display_host)
                    host_item.setData(Qt.ItemDataRole.UserRole, host) # Store IP
                    proto_item = QTableWidgetItem(proto)
                    port_item = QTableWidgetItem(str(port)) # Port must be string
                    state_item = QTableWidgetItem(port_data.get('state', ''))
                    service_item = QTableWidgetItem(port_data.get('name', ''))
                    product_item = QTableWidgetItem(port_data.get('product', ''))
                    version_item = QTableWidgetItem(port_data.get('version', ''))
                    # Set items in the current row
                    self.results_table.setItem(row_position, 0, host_item)
                    self.results_table.setItem(row_position, 1, proto_item)
                    self.results_table.setItem(row_position, 2, port_item)
                    self.results_table.setItem(row_position, 3, state_item)
                    self.results_table.setItem(row_position, 4, service_item)
                    self.results_table.setItem(row_position, 5, product_item)
                    self.results_table.setItem(row_position, 6, version_item)
                    row_position += 1

        self.results_table.setSortingEnabled(True) # Re-enable sorting


    def display_host_details(self):
        """
        Slot connected to table selection changes. Displays detailed information
        (MAC, OS, Ports, Scripts) for the selected host in the Host Details area.
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


    def _set_ui_scan_state(self, scanning: bool):
        """Enables/disables UI elements based on whether a scan is running."""
        # Disable/enable configuration widgets
        self.scan_button.setEnabled(not scanning)
        self.stop_button.setEnabled(scanning)
        self.progress_bar.setVisible(scanning)
        self.profile_combo.setEnabled(not scanning)
        self.scan_type_combo.setEnabled(not scanning)
        self.custom_args_input.setEnabled(not scanning)
        self.save_profile_button.setEnabled(not scanning)
        # Delete button enabled only when not scanning AND a non-custom profile is selected
        self.delete_profile_button.setEnabled(not scanning and self.profile_combo.currentIndex() > 0)
        # File menu actions
        # Save enabled only when not scanning AND results from last scan exist
        self.save_action.setEnabled(not scanning and bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path)))
        self.open_action.setEnabled(not scanning) # Allow opening when idle

        # Clear the temporary file path when starting a new scan
        if scanning:
             self.last_scan_xml_path = None


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
        self.last_scan_xml_path = temp_xml_path # Store path for potential saving
        self._reset_ui_after_scan(message) # Reset UI to idle state
        # Explicitly re-evaluate save action state now that path is stored
        self.save_action.setEnabled(bool(self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path)))


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

                # Update UI with loaded data
                self.current_scan_data = parsed_results # Store loaded data
                self.output_area.setText(f"--- Results loaded from: {filename} ---\n\n(Raw output not available for loaded files)")
                self.display_parsed_results_table(parsed_results) # Update table
                self._current_status_message = f"Successfully loaded results from {filename}"
                self._check_and_warn_privileged_scan()
                # Cannot save a loaded file via the temp file mechanism
                self.last_scan_xml_path = None
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
        Prompts the user for a filename and copies the temporary XML result file
        from the last completed scan to the chosen location.

        Returns:
            bool: True on success, False on failure or cancellation.
        """
        # Check if results are available to save
        if not self.last_scan_xml_path or not os.path.exists(self.last_scan_xml_path):
            QMessageBox.warning(self, "No Results", "No scan results available to save. Please run a scan first.")
            return False

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
                # Copy the temporary file to the desired location
                shutil.copyfile(self.last_scan_xml_path, filename)
                self._current_status_message = f"Scan results saved to {filename}"
                self._check_and_warn_privileged_scan()
                # Optional: Disable save action after successful save?
                # self.save_action.setEnabled(False)
                # self.last_scan_xml_path = None # Clear path after saving? Or allow multiple saves?
                return True # Indicate success
            except Exception as e:
                # Handle errors during file copy
                QMessageBox.critical(self, "Save Error", f"Could not save results to {filename}:\n{e}")
                self._current_status_message = f"Error saving results: {e}"
                self._check_and_warn_privileged_scan()
                return False # Indicate failure
        else:
            # User cancelled the save dialog
            self._current_status_message = "Save cancelled."
            self._check_and_warn_privileged_scan()
            return False # Indicate cancellation

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
        # Check if last_scan_xml_path exists and points to a real file
        if should_close and self.last_scan_xml_path and os.path.exists(self.last_scan_xml_path):
            # Create a custom message box for Save/Don't Save/Cancel
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Unsaved Scan Results")
            msg_box.setText("The results of the last scan have not been saved.")
            msg_box.setInformativeText("Do you want to save the results before exiting?")
            # Add buttons with specific roles
            save_button = msg_box.addButton("&Save", QMessageBox.ButtonRole.AcceptRole)
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
