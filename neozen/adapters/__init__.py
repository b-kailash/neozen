"""
GUI framework adapters for NmapScanner core.

This package provides framework-specific wrappers around the pure Python
NmapScanner, allowing it to be used with different GUI frameworks and
communication patterns.
"""

from .qt_scanner import QtScannerAdapter
from .web_scanner import WebScannerAdapter

__all__ = ['QtScannerAdapter', 'WebScannerAdapter']
