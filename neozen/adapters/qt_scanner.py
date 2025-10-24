"""
PyQt6 adapter for NmapScanner.

This module provides a Qt-specific wrapper around the pure Python NmapScanner,
translating callbacks into Qt signals for use in PyQt6 applications.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from neozen.core.scanner_core import NmapScanner


class QtScannerAdapter(QObject):
    """
    Qt adapter that wraps pure Python NmapScanner with Qt signals.

    This adapter maintains identical interface to the old Scanner class for
    backward compatibility, allowing existing PyQt6 code to work without changes.

    The adapter translates callback-based communication from NmapScanner into
    Qt signals that can be connected to slots in Qt applications.
    """

    # Qt signals (identical to old Scanner class)
    scan_output = pyqtSignal(str)
    scan_results_ready = pyqtSignal(dict)
    scan_finished = pyqtSignal(str, str)  # (status_message, temp_xml_path)
    scan_error = pyqtSignal(str)

    def __init__(self, target: str, arguments: str):
        """
        Initialize Qt scanner adapter.

        Args:
            target: The target host(s)/network(s) for the scan.
            arguments: Nmap command-line arguments.
        """
        super().__init__()

        # Create core scanner with Qt signal callbacks
        # Each callback simply emits the corresponding Qt signal
        self.scanner = NmapScanner(
            target=target,
            arguments=arguments,
            on_output=self.scan_output.emit,
            on_results=self.scan_results_ready.emit,
            on_finished=self.scan_finished.emit,
            on_error=self.scan_error.emit
        )

    def start(self):
        """Start the scan thread."""
        self.scanner.start()

    def stop(self):
        """Stop the running scan."""
        self.scanner.stop()

    def isRunning(self) -> bool:
        """
        Check if scan is running.

        Returns:
            bool: True if the scanner thread is alive, False otherwise.
        """
        return self.scanner.is_alive()

    def wait(self, msecs: int = -1) -> bool:
        """
        Wait for thread to finish (Qt compatibility method).

        Args:
            msecs: Maximum time to wait in milliseconds. -1 means wait forever.

        Returns:
            bool: True if thread finished, False if timeout occurred.
        """
        timeout = None if msecs == -1 else msecs / 1000.0
        self.scanner.join(timeout=timeout)
        return not self.scanner.is_alive()
