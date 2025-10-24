"""
Pytest configuration and fixtures for NeoZen tests
"""
import pytest
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_profile_data():
    """Fixture providing sample profile data for tests"""
    return {
        "Intense Scan": {
            "target": "192.168.1.1",
            "arguments": "-T4 -A -v"
        },
        "Quick Scan": {
            "target": "localhost",
            "arguments": "-T4 -F"
        },
        "Ping Scan": {
            "target": "192.168.1.0/24",
            "arguments": "-sn"
        }
    }
