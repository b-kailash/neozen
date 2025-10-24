import sys
import shutil
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
# Import the main window class from our UI package
from neozen.ui.main_window import MainWindow
from neozen.ui.styles import apply_modern_style
from neozen.resources import get_icon_path


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


# Main execution block: This code runs only when the script is executed directly
if __name__ == "__main__":
    # Create the QApplication instance.
    # sys.argv allows passing command-line arguments to the application,
    # which is standard practice for Qt applications.
    app = QApplication(sys.argv)
    app.setApplicationName("NeoZen")
    app.setOrganizationName("NeoZen")

    # Set application icon
    app.setWindowIcon(QIcon(get_icon_path()))

    # Apply modern styling
    apply_modern_style(app)

    # Check if Nmap is installed before proceeding
    if not check_nmap_installed():
        sys.exit(1)

    # Create an instance of our main application window.
    main_window = MainWindow()

    # Make the main window visible on the screen.
    main_window.show()

    # Start the Qt event loop.
    # This call is blocking and will keep the application running,
    # processing user interactions (button clicks, key presses, etc.)
    # and other events until the application is explicitly quit
    # (e.g., the main window is closed).
    # sys.exit() ensures that the application exits cleanly and returns
    # the appropriate exit code.
    sys.exit(app.exec())