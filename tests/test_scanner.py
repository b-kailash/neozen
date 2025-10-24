"""
Tests for the Scanner class
"""
import pytest
from neozen.core.scanner import Scanner


class TestScanner:
    """Test suite for Scanner"""

    def test_scanner_initialization(self):
        """Test that Scanner initializes with correct parameters"""
        target = "127.0.0.1"
        arguments = "-sV -T4"

        scanner = Scanner(target, arguments)

        assert scanner.target == target
        assert scanner.base_arguments == arguments
        assert scanner._is_running is True
        assert scanner.nmap_process is None

    def test_build_command_basic(self):
        """Test building a basic nmap command"""
        scanner = Scanner("127.0.0.1", "-sV")
        command = scanner._build_command()

        # Command should not be None
        assert command is not None

        # Should contain nmap executable
        assert "nmap" in command

        # Should contain the target
        assert "127.0.0.1" in command

        # Should add verbosity automatically
        assert any("-v" in arg for arg in command)

    def test_build_command_with_arguments(self):
        """Test building command with various arguments"""
        scanner = Scanner("192.168.1.0/24", "-sS -p 80,443")
        command = scanner._build_command()

        assert command is not None
        assert "192.168.1.0/24" in command
        assert "-sS" in command
        assert "-p" in command
        assert "80,443" in command

    def test_build_command_adds_xml_output(self):
        """Test that build_command adds XML output argument"""
        scanner = Scanner("localhost", "")
        command = scanner._build_command()

        assert command is not None
        # Should contain -oX flag for XML output
        assert "-oX" in command

        # Should have created temp file path
        assert scanner.temp_xml_file_path is not None

    def test_build_command_preserves_user_xml(self):
        """Test that user-specified XML output is preserved"""
        scanner = Scanner("localhost", "-oX myfile.xml")
        command = scanner._build_command()

        assert command is not None
        assert "-oX" in command
        assert "myfile.xml" in command
