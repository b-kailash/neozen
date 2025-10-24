"""
Modern styling for NeoZen application using Qt Style Sheets (QSS)
"""

MODERN_STYLE = """
/* Main Window */
QMainWindow {
    background-color: #f5f5f5;
}

/* Input Fields */
QLineEdit {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #2c3e50;
}

QLineEdit:focus {
    border: 2px solid #7e22ce;
    background-color: #fefefe;
}

QLineEdit:read-only {
    background-color: #f8f9fa;
    color: #6c757d;
}

/* Combo Boxes */
QComboBox {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #2c3e50;
    min-height: 20px;
}

QComboBox:hover {
    border: 2px solid #b8b8b8;
}

QComboBox:focus {
    border: 2px solid #7e22ce;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #7e22ce;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    selection-background-color: #7e22ce;
    selection-color: white;
    padding: 4px;
}

/* Buttons */
QPushButton {
    background-color: #7e22ce;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #6b1fb8;
}

QPushButton:pressed {
    background-color: #5a1a9a;
}

QPushButton:disabled {
    background-color: #d0d0d0;
    color: #888888;
}

/* Stop Button - Red variant */
QPushButton#stop_button {
    background-color: #dc3545;
}

QPushButton#stop_button:hover {
    background-color: #c82333;
}

QPushButton#stop_button:pressed {
    background-color: #bd2130;
}

/* Secondary Buttons */
QPushButton#save_profile_button,
QPushButton#delete_profile_button {
    background-color: #6c757d;
}

QPushButton#save_profile_button:hover,
QPushButton#delete_profile_button:hover {
    background-color: #5a6268;
}

QPushButton#save_profile_button:pressed,
QPushButton#delete_profile_button:pressed {
    background-color: #4e555b;
}

/* Text Areas */
QTextEdit {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    color: #2c3e50;
}

QTextEdit:focus {
    border: 2px solid #7e22ce;
}

/* Tables */
QTableWidget {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    gridline-color: #e0e0e0;
    selection-background-color: #e9d5ff;
    selection-color: #2c3e50;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #e9d5ff;
    color: #2c3e50;
}

QHeaderView::section {
    background-color: #7e22ce;
    color: white;
    padding: 10px;
    border: none;
    font-weight: 600;
    font-size: 13px;
}

QHeaderView::section:first {
    border-top-left-radius: 8px;
}

QHeaderView::section:last {
    border-top-right-radius: 8px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    background-color: white;
    top: -2px;
}

QTabBar::tab {
    background-color: #f8f9fa;
    color: #6c757d;
    border: 2px solid #e0e0e0;
    border-bottom: none;
    padding: 10px 20px;
    margin-right: 2px;
    font-size: 13px;
    font-weight: 500;
}

QTabBar::tab:first {
    border-top-left-radius: 8px;
}

QTabBar::tab:last {
    border-top-right-radius: 8px;
    margin-right: 0px;
}

QTabBar::tab:selected {
    background-color: white;
    color: #7e22ce;
    border-bottom: 2px solid white;
}

QTabBar::tab:hover:!selected {
    background-color: #e9ecef;
}

/* Progress Bar */
QProgressBar {
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    text-align: center;
    background-color: #f8f9fa;
    height: 20px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #7e22ce, stop:1 #a855f7);
    border-radius: 6px;
}

/* Labels */
QLabel {
    color: #2c3e50;
    font-size: 13px;
    font-weight: 500;
}

/* Status Bar */
QStatusBar {
    background-color: #f8f9fa;
    border-top: 2px solid #e0e0e0;
    color: #6c757d;
    font-size: 12px;
}

QStatusBar QLabel {
    color: #6c757d;
    font-weight: normal;
}

/* Menu Bar */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 2px solid #e0e0e0;
    padding: 4px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 8px 12px;
    border-radius: 4px;
    color: #2c3e50;
}

QMenuBar::item:selected {
    background-color: #e9d5ff;
    color: #7e22ce;
}

QMenu {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 30px 8px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #e9d5ff;
    color: #7e22ce;
}

QMenu::separator {
    height: 2px;
    background-color: #e0e0e0;
    margin: 4px 10px;
}

/* Splitter */
QSplitter::handle {
    background-color: #e0e0e0;
    border-radius: 2px;
}

QSplitter::handle:hover {
    background-color: #7e22ce;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

/* Scroll Bars */
QScrollBar:vertical {
    border: none;
    background-color: #f8f9fa;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e0;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7e22ce;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #f8f9fa;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e0;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #7e22ce;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Message Boxes */
QMessageBox {
    background-color: white;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 8px 16px;
}

/* Tool Tips */
QToolTip {
    background-color: #2c3e50;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""

def apply_modern_style(app):
    """Apply the modern stylesheet to the application"""
    app.setStyleSheet(MODERN_STYLE)
