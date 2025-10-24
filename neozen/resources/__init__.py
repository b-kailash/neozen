"""
Resources package for NeoZen
Contains icons, images, and other static assets
"""
import os
from pathlib import Path

RESOURCES_DIR = Path(__file__).parent


def get_icon_path():
    """Get the path to the application icon"""
    return str(RESOURCES_DIR / "icon.svg")
