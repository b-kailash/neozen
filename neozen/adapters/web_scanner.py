"""
Flask/SocketIO adapter for NmapScanner.

This module provides a web-specific wrapper around the pure Python NmapScanner,
translating callbacks into SocketIO events for use in Flask web applications.
"""

from neozen.core.scanner_core import NmapScanner


class WebScannerAdapter:
    """
    Web adapter that wraps pure Python NmapScanner with SocketIO events.

    This adapter emits SocketIO events for real-time communication with
    web clients, allowing browser-based interfaces to receive scan updates.

    No PyQt6 dependencies required - this adapter works with pure Flask.
    """

    def __init__(self, target: str, arguments: str, socketio):
        """
        Initialize web scanner adapter.

        Args:
            target: The target host(s)/network(s) for the scan.
            arguments: Nmap command-line arguments.
            socketio: Flask-SocketIO instance for emitting events to web clients.
        """
        self.socketio = socketio

        # Create core scanner with SocketIO event callbacks
        # Each callback emits a SocketIO event with appropriate payload
        self.scanner = NmapScanner(
            target=target,
            arguments=arguments,
            on_output=lambda text: socketio.emit('scan_output', {'text': text}),
            on_results=lambda results: socketio.emit('scan_results', {'results': results}),
            on_finished=lambda msg, path: socketio.emit('scan_finished', {
                'message': msg,
                'xml_path': path
            }),
            on_error=lambda err: socketio.emit('scan_error', {'error': err})
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
