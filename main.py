import sys
from PyQt6.QtWidgets import QApplication
from neozen.ui.main_window import MainWindow

# Main execution block
if __name__ == "__main__":
    # Create the QApplication instance
    # sys.argv allows passing command-line arguments to the application, if needed.
    app = QApplication(sys.argv)

    # Create an instance of the main window
    main_window = MainWindow()

    # Show the main window
    main_window.show()

    # Start the Qt event loop.
    # This call blocks until the application exits (e.g., the main window is closed).
    # It processes events like button clicks, window resizing, etc.
    sys.exit(app.exec())
