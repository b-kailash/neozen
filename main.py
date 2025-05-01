import sys
from PyQt6.QtWidgets import QApplication
# Import the main window class from our UI package
from neozen.ui.main_window import MainWindow

# Main execution block: This code runs only when the script is executed directly
if __name__ == "__main__":
    # Create the QApplication instance.
    # sys.argv allows passing command-line arguments to the application,
    # which is standard practice for Qt applications.
    app = QApplication(sys.argv)

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