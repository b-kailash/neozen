import json
import os
from pathlib import Path
import sys

class ProfileManager:
    """Handles loading and saving of scan profiles."""

    def __init__(self, filename="scan_profiles.json"):
        """
        Initializes the ProfileManager.

        Args:
            filename (str): The name of the file to store profiles in.
        """
        self.profile_path = self._get_profile_path(filename)

    def _get_profile_path(self, filename):
        """Determines the appropriate path for the profile file."""
        # Use a platform-specific config directory
        if sys.platform == "win32":
            # Use %APPDATA% on Windows
            config_dir = Path(os.getenv('APPDATA', '')) / "NeoZen"
        elif sys.platform == "darwin":
            # Use ~/Library/Application Support on macOS
            config_dir = Path.home() / "Library" / "Application Support" / "NeoZen"
        else:
            # Use ~/.config on Linux/other Unix-like systems (XDG Base Directory Spec)
            config_dir = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / ".config")) / "NeoZen"

        # Create the directory if it doesn't exist
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create config directory {config_dir}: {e}")
            # Fallback to current directory if config dir fails
            config_dir = Path(".")

        return config_dir / filename

    def load_profiles(self):
        """Loads profiles from the JSON file."""
        if not self.profile_path.exists():
            return {} # Return empty dict if file doesn't exist

        try:
            with open(self.profile_path, 'r') as f:
                profiles = json.load(f)
                # Basic validation: ensure it's a dictionary
                if not isinstance(profiles, dict):
                    print(f"Warning: Profile file {self.profile_path} does not contain a valid dictionary. Ignoring.")
                    return {}
                return profiles
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.profile_path}. Starting with empty profiles.")
            return {}
        except OSError as e:
            print(f"Error: Could not read profile file {self.profile_path}: {e}")
            return {}
        except Exception as e:
             print(f"An unexpected error occurred loading profiles: {e}")
             return {}


    def save_profiles(self, profiles):
        """
        Saves the given profiles dictionary to the JSON file.

        Args:
            profiles (dict): The dictionary of profiles to save.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        try:
            with open(self.profile_path, 'w') as f:
                json.dump(profiles, f, indent=4) # Use indent for readability
            return True
        except OSError as e:
            print(f"Error: Could not write profile file {self.profile_path}: {e}")
            return False
        except TypeError as e:
             print(f"Error: Could not serialize profiles to JSON: {e}")
             return False
        except Exception as e:
             print(f"An unexpected error occurred saving profiles: {e}")
             return False

# Example usage (optional, for testing this module directly)
if __name__ == "__main__":
    manager = ProfileManager("test_profiles.json") # Use a test file

    # Load existing or create new
    current_profiles = manager.load_profiles()
    print(f"Loaded profiles: {current_profiles}")

    # Add/update a profile
    current_profiles["My Test Scan"] = {"target": "localhost", "arguments": "-T4 -F"}
    current_profiles["Another Scan"] = {"target": "192.168.1.0/24", "arguments": "-sn"}

    # Save
    if manager.save_profiles(current_profiles):
        print("Profiles saved successfully.")
    else:
        print("Failed to save profiles.")

    # Load again to verify
    reloaded_profiles = manager.load_profiles()
    print(f"Reloaded profiles: {reloaded_profiles}")

    # Clean up test file
    try:
        manager.profile_path.unlink()
        print("Test profile file removed.")
    except OSError:
        pass
