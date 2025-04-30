import sys
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread # Import QThread for later use
from neozen.core.scanner import Scanner # Import the Scanner thread class

class MainWindow(QMainWindow):
    """
    Main application window for NeoZen.
    Includes tabs for raw output and parsed results.
    """
    def __init__(self):
        super().__init__() # Call the constructor of the parent class (QMainWindow)

        self.setWindowTitle("NeoZen - Modern Nmap GUI")
        self.setGeometry(100, 100, 900, 700) # x, y, width, height - Increased size

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget) # Main vertical layout

        # --- Target Input Area ---
        target_layout = QHBoxLayout() # Horizontal layout for target label and input
        target_label = QLabel("Target:")
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter IP address, hostname, or network range (e.g., 192.168.1.1, scanme.nmap.org, 10.0.0.0/24)")
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_input)

        # --- Scan Control Buttons ---
        button_layout = QHBoxLayout() # Horizontal layout for buttons
        self.scan_button = QPushButton("Scan")
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setEnabled(False) # Initially disabled
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch() # Push buttons to the left

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False) # Initially hidden
        self.progress_bar.setRange(0, 0) # Indeterminate progress

        # --- Tabbed Output Area ---
        self.tab_widget = QTabWidget()

        # --- Raw Output Tab ---
        self.raw_output_widget = QWidget() # Widget to hold the layout for this tab
        raw_output_layout = QVBoxLayout(self.raw_output_widget)
        raw_output_layout.setContentsMargins(0, 5, 0, 0) # Remove extra margins
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True) # Make it non-editable
        self.output_area.setFontFamily("monospace") # Use a monospaced font for output
        raw_output_layout.addWidget(self.output_area)
        self.tab_widget.addTab(self.raw_output_widget, "Raw Output")

        # --- Parsed Results Tab ---
        self.parsed_results_widget = QWidget()
        parsed_results_layout = QVBoxLayout(self.parsed_results_widget)
        parsed_results_layout.setContentsMargins(0, 5, 0, 0)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7) # Host, Proto, Port, State, Service, Product, Version
        self.results_table.setHorizontalHeaderLabels(["Host", "Proto", "Port", "State", "Service", "Product", "Version"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Read-only
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False) # Hide row numbers
        # Adjust column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Host
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Proto
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Port
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # State
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # Service
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch) # Product
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) # Version
        self.results_table.setSortingEnabled(True) # Allow sorting by clicking headers

        parsed_results_layout.addWidget(self.results_table)
        self.tab_widget.addTab(self.parsed_results_widget, "Parsed Results")

        # --- Add layouts and widgets to main layout ---
        main_layout.addLayout(target_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.tab_widget) # Add the tab widget instead of just output_area

        # --- Status Bar ---
        self.statusBar().showMessage("Ready")

        # --- Nmap Scanner Thread ---
        self.scanner_thread = None # Placeholder for the thread object

        # --- Connect Signals and Slots ---
        self.scan_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        self.target_input.returnPressed.connect(self.start_scan) # Allow pressing Enter in target field

    def start_scan(self):
        """
        Slot to handle starting the Nmap scan.
        """
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please enter a target to scan.")
            return

        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A scan is already running.")
            return

        # Clear previous output and results
        self.output_area.clear()
        self.results_table.setRowCount(0) # Clear table rows
        self.statusBar().showMessage(f"Starting scan on {target}...")
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)

        # --- Create and start the scanner thread ---
        # For now, using a simple intense scan argument '-T4 -A -v'
        nmap_args = "-T4 -A -v" # Example arguments
        self.scanner_thread = Scanner(target, nmap_args)

        # Connect signals from the thread to slots in this window
        self.scanner_thread.scan_output.connect(self.append_output)
        self.scanner_thread.scan_results_ready.connect(self.display_parsed_results) # Connect new signal
        self.scanner_thread.scan_finished.connect(self.scan_complete)
        self.scanner_thread.scan_error.connect(self.scan_error_occurred)

        # Switch to Raw Output tab when scan starts
        self.tab_widget.setCurrentWidget(self.raw_output_widget)

        # Start the thread's run() method
        self.scanner_thread.start()

    def stop_scan(self):
        """
        Slot to handle stopping the currently running scan.
        """
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.statusBar().showMessage("Attempting to stop scan...")
            self.scanner_thread.stop() # Ask the thread to stop
        else:
            self.statusBar().showMessage("No scan is currently running.")
            self.stop_button.setEnabled(False)
            self.scan_button.setEnabled(True)
            self.progress_bar.setVisible(False)


    def append_output(self, text):
        """
        Slot to append text (received from the scanner thread) to the raw output area.
        """
        self.output_area.append(text)
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum()) # Auto-scroll

    def display_parsed_results(self, results_data):
        """
        Slot to populate the results table with structured data from the scan.

        Args:
            results_data (dict): Dictionary containing parsed scan results
                                 Format: {host: {'state': ..., 'hostname': ..., 'protocols': {proto: {port: {...}}}}}
        """
        self.results_table.setSortingEnabled(False) # Disable sorting during population for speed
        self.results_table.setRowCount(0) # Clear previous results

        row_position = 0
        for host, host_data in results_data.items():
            hostname = host_data.get('hostname', '')
            if hostname and hostname != host:
                 display_host = f"{hostname} ({host})"
            else:
                 display_host = host

            protocols = host_data.get('protocols', {})
            if not protocols: # Handle hosts found but no open/filtered ports reported
                if host_data.get('state') == 'up':
                     self.results_table.insertRow(row_position)
                     self.results_table.setItem(row_position, 0, QTableWidgetItem(display_host))
                     self.results_table.setItem(row_position, 1, QTableWidgetItem("")) # Proto
                     self.results_table.setItem(row_position, 2, QTableWidgetItem("")) # Port
                     self.results_table.setItem(row_position, 3, QTableWidgetItem(host_data.get('state', 'unknown'))) # State
                     self.results_table.setItem(row_position, 4, QTableWidgetItem("(No ports found/reported)")) # Service
                     self.results_table.setItem(row_position, 5, QTableWidgetItem("")) # Product
                     self.results_table.setItem(row_position, 6, QTableWidgetItem("")) # Version
                     row_position += 1
                continue # Skip hosts with no protocols if state isn't 'up'

            for proto, ports in protocols.items():
                for port, port_data in ports.items():
                    self.results_table.insertRow(row_position)
                    # Create QTableWidgetItem for each cell
                    host_item = QTableWidgetItem(display_host)
                    proto_item = QTableWidgetItem(proto)
                    port_item = QTableWidgetItem(str(port)) # Port number needs to be string
                    state_item = QTableWidgetItem(port_data.get('state', ''))
                    service_item = QTableWidgetItem(port_data.get('name', ''))
                    product_item = QTableWidgetItem(port_data.get('product', ''))
                    version_item = QTableWidgetItem(port_data.get('version', ''))

                    # Set items in the table row
                    self.results_table.setItem(row_position, 0, host_item)
                    self.results_table.setItem(row_position, 1, proto_item)
                    self.results_table.setItem(row_position, 2, port_item)
                    self.results_table.setItem(row_position, 3, state_item)
                    self.results_table.setItem(row_position, 4, service_item)
                    self.results_table.setItem(row_position, 5, product_item)
                    self.results_table.setItem(row_position, 6, version_item)

                    row_position += 1

        self.results_table.setSortingEnabled(True) # Re-enable sorting
        # Switch to Parsed Results tab when results are ready
        if results_data:
            self.tab_widget.setCurrentWidget(self.parsed_results_widget)


    def scan_complete(self, message):
        """
        Slot called when the scanner thread finishes successfully.
        """
        self.statusBar().showMessage(message)
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.scanner_thread = None # Clear the thread reference

    def scan_error_occurred(self, error_message):
        """
        Slot called when the scanner thread encounters an error or is stopped.
        """
        # Avoid showing duplicate error messages if the error was already in output
        if error_message not in self.output_area.toPlainText():
             QMessageBox.critical(self, "Scan Error / Stopped", error_message)
        self.statusBar().showMessage(f"Scan Error / Stopped: {error_message}")
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.scanner_thread = None # Clear the thread reference

    def closeEvent(self, event):
        """
        Handles the main window close event to ensure the scan stops.
        """
        if self.scanner_thread and self.scanner_thread.isRunning():
            reply = QMessageBox.question(self, 'Scan in Progress',
                                           "A scan is currently running. Stop scan and exit?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_scan()
                # Wait briefly for the thread to potentially terminate
                if self.scanner_thread:
                    self.scanner_thread.wait(1500) # Wait up to 1.5 seconds
                event.accept() # Close the window
            else:
                event.ignore() # Do not close the window
        else:
            event.accept() # No scan running, close normally


# Example of running just this file for testing (optional)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
