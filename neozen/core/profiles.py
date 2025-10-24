import json
import os
from pathlib import Path
import sys
import platform  # Import platform module
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

class ProfileManager:
    """
    Handles loading and saving of Nmap scan profiles to a JSON file.

    Manages profiles in a platform-specific configuration directory.
    """

    def __init__(self, filename="scan_profiles.json"):
        """
        Initializes the ProfileManager and determines the profile file path.

        Args:
            filename (str): The name of the file to store profiles in.
                            Defaults to "scan_profiles.json".
        """
        self.profile_path = self._get_profile_path(filename)
        logger.debug(f"Profile path set to: {self.profile_path}")

    def _get_profile_path(self, filename):
        """
        Determines the appropriate platform-specific path for the profile file.

        Follows XDG Base Directory Specification on Linux/Unix and uses
        standard locations on Windows and macOS.

        Args:
            filename (str): The base name for the profile file.

        Returns:
            pathlib.Path: The full path object for the profile file.
        """
        app_name = "NeoZen" # Application name used for directory

        # Determine base config directory based on OS
        if platform.system() == "Windows":
            # Use %APPDATA% environment variable on Windows
            base_dir = Path(os.getenv('APPDATA', ''))
        elif platform.system() == "Darwin":
            # Use ~/Library/Application Support on macOS
            base_dir = Path.home() / "Library" / "Application Support"
        else:
            # Use XDG_CONFIG_HOME or default to ~/.config on Linux/other Unix
            xdg_config_home = os.getenv('XDG_CONFIG_HOME')
            if xdg_config_home:
                base_dir = Path(xdg_config_home)
            else:
                base_dir = Path.home() / ".config"

        # Construct the application-specific config directory path
        config_dir = base_dir / app_name

        # Create the application-specific directory if it doesn't exist
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not create config directory {config_dir}: {e}")
            # Fallback to current directory if config dir creation fails
            config_dir = Path(".")
        except Exception as e:
            logger.warning(f"Unexpected error creating config directory {config_dir}: {e}")
            config_dir = Path(".")


        # Return the full path to the profile file
        return config_dir / filename

    def load_profiles(self):
        """
        Loads scan profiles from the JSON file specified during initialization.

        Returns:
            dict: A dictionary containing the loaded profiles {profile_name: profile_data}.
                  Returns an empty dictionary if the file doesn't exist, is invalid,
                  or cannot be read.
        """
        # Check if the profile file exists
        if not self.profile_path.exists():
            logger.info(f"Profile file not found at {self.profile_path}. Starting fresh.")
            return {}  # Return empty dict if file doesn't exist

        # Try to open and read the file
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
                # Basic validation: ensure the loaded data is a dictionary
                if not isinstance(profiles, dict):
                    logger.warning(f"Profile file {self.profile_path} does not contain a valid dictionary. Ignoring.")
                    return {}
                logger.info(f"Successfully loaded profiles from {self.profile_path}")
                return profiles
        except json.JSONDecodeError as e:
            # Handle errors if the file contains invalid JSON
            logger.error(f"Could not decode JSON from {self.profile_path}: {e}. Starting with empty profiles.")
            return {}
        except OSError as e:
            # Handle file system errors (e.g., permission denied)
            logger.error(f"Could not read profile file {self.profile_path}: {e}")
            return {}
        except Exception as e:
            # Catch any other unexpected errors during loading
            logger.error(f"An unexpected error occurred loading profiles: {e}")
            return {}


    def save_profiles(self, profiles):
        """
        Saves the given profiles dictionary to the JSON file.

        Overwrites the existing file with the new data.

        Args:
            profiles (dict): The dictionary of profiles {profile_name: profile_data} to save.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        try:
            # Open the file in write mode ('w'), which creates/overwrites it
            with open(self.profile_path, 'w', encoding='utf-8') as f:
                # Dump the dictionary to the file as JSON, with indentation for readability
                json.dump(profiles, f, indent=4)
            logger.info(f"Successfully saved profiles to {self.profile_path}")
            return True
        except OSError as e:
            # Handle file system errors during writing
            logger.error(f"Could not write profile file {self.profile_path}: {e}")
            return False
        except TypeError as e:
            # Handle errors if the profiles dictionary contains non-serializable types
            logger.error(f"Could not serialize profiles to JSON: {e}")
            return False
        except Exception as e:
            # Catch any other unexpected errors during saving
            logger.error(f"An unexpected error occurred saving profiles: {e}")
            return False

# Example usage block (only runs if the script is executed directly)
if __name__ == "__main__":
    # Use a distinct test file name to avoid overwriting actual profiles
    manager = ProfileManager("test_profiles.json")

    # Load existing or create new
    current_profiles = manager.load_profiles()
    print(f"Loaded test profiles: {current_profiles}")

    # Add/update some sample profiles
    current_profiles["My Test Scan"] = {"target": "localhost", "arguments": "-T4 -F"}
    current_profiles["Another Scan"] = {"target": "192.168.1.0/24", "arguments": "-sn"}

    # Save the updated profiles
    if manager.save_profiles(current_profiles):
        print("Test profiles saved successfully.")
    else:
        print("Failed to save test profiles.")

    # Load again to verify the save worked
    reloaded_profiles = manager.load_profiles()
    print(f"Reloaded test profiles: {reloaded_profiles}")

    # Clean up the test file
    try:
        # Use unlink() from pathlib.Path to delete the file
        manager.profile_path.unlink()
        print("Test profile file removed.")
    except FileNotFoundError:
        print("Test profile file was not found (already removed or never created).")
    except OSError as e:
        print(f"Error removing test profile file: {e}")

