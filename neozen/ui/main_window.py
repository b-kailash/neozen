import sys
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread # Import QThread for later use
from neozen.core.scanner import Scanner # Import the Scanner thread class

class MainWindow(QMainWindow):
    """
    Main application window for NeoZen.
    """
    def __init__(self):
        super().__init__() # Call the constructor of the parent class (QMainWindow)

        self.setWindowTitle("NeoZen - Modern Nmap GUI")
        self.setGeometry(100, 100, 800, 600) # x, y, width, height

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

        # --- Output Area ---
        output_label = QLabel("Nmap Output:")
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True) # Make it non-editable
        self.output_area.setFontFamily("monospace") # Use a monospaced font for output

        # --- Add layouts and widgets to main layout ---
        main_layout.addLayout(target_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(output_label)
        main_layout.addWidget(self.output_area) # Add the output area

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

        # Clear previous output
        self.output_area.clear()
        self.statusBar().showMessage(f"Starting scan on {target}...")
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)

        # --- Create and start the scanner thread ---
        # For now, using a simple intense scan argument '-T4 -A -v'
        # We will add more options later
        nmap_args = "-T4 -A -v" # Example arguments
        self.scanner_thread = Scanner(target, nmap_args)

        # Connect signals from the thread to slots in this window
        self.scanner_thread.scan_output.connect(self.append_output)
        self.scanner_thread.scan_finished.connect(self.scan_complete)
        self.scanner_thread.scan_error.connect(self.scan_error_occurred)

        # Start the thread's run() method
        self.scanner_thread.start()

    def stop_scan(self):
        """
        Slot to handle stopping the currently running scan.
        """
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.statusBar().showMessage("Attempting to stop scan...")
            self.scanner_thread.stop() # Ask the thread to stop
            # Buttons will be re-enabled in scan_complete or scan_error_occurred
        else:
            self.statusBar().showMessage("No scan is currently running.")
            self.stop_button.setEnabled(False)
            self.scan_button.setEnabled(True)
            self.progress_bar.setVisible(False)


    def append_output(self, text):
        """
        Slot to append text (received from the scanner thread) to the output area.
        """
        self.output_area.append(text)
        self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum()) # Auto-scroll

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
        self.statusBar().showMessage(f"Scan Error: {error_message}")
        QMessageBox.critical(self, "Scan Error", error_message)
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
                # Wait briefly for the thread to potentially terminate (optional, might need refinement)
                if self.scanner_thread:
                    self.scanner_thread.wait(1000) # Wait up to 1 second
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
