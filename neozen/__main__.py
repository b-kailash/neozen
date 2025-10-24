"""
Main entry point for NeoZen when run as a module or installed package.
"""
import sys
import shutil
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon


def check_nmap_installed():
    """
    Check if nmap is available in the system PATH.

    Returns:
        bool: True if nmap is found, False otherwise.
    """
    if shutil.which("nmap") is None:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Nmap Not Found")
        msg.setText("Nmap is not installed or not found in your system PATH.")
        msg.setInformativeText(
            "Please install Nmap before using NeoZen:\n\n"
            "• Linux (Debian/Ubuntu): sudo apt install nmap\n"
            "• Linux (Fedora/RHEL): sudo dnf install nmap\n"
            "• macOS (Homebrew): brew install nmap\n"
            "• Windows: Download from https://nmap.org/download.html\n\n"
            "After installation, ensure 'nmap' is in your system PATH."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return False
    return True


def main():
    """Main entry point for the NeoZen application."""
    # Create the Qt application instance
    app = QApplication(sys.argv)
    app.setApplicationName("NeoZen")
    app.setOrganizationName("NeoZen")

    # Set application icon
    from neozen.resources import get_icon_path
    app.setWindowIcon(QIcon(get_icon_path()))

    # Apply modern styling
    from neozen.ui.styles import apply_modern_style
    apply_modern_style(app)

    # Check if Nmap is installed before proceeding
    if not check_nmap_installed():
        return 1

    # Import here to avoid import errors before Qt is initialized
    from neozen.ui.main_window import MainWindow

    # Create and show the main window
    main_window = MainWindow()
    main_window.show()

    # Start the Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
