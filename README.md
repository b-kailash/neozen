import nmap # Still used for parsing XML results and getting version
import subprocess # Used for running Nmap directly
import psutil # To find and terminate child processes
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import os
import shlex # To split arguments safely, especially on non-Windows
import sys # To check platform
import json # For debugging output
import tempfile # For creating temporary file for XML output
import platform # For platform-specific checks

class Scanner(QThread):
    """
    Worker thread for running Nmap scans asynchronously using subprocess.

    Captures live human-readable stdout/stderr for Raw Output tab.
    Saves XML to a temporary file and parses it upon completion, including OS/MAC/NSE details.
    Passes back the temp file path upon completion.
    Cleanup of temp file is handled by the main window.
    """
    # --- Signals ---
    scan_output = pyqtSignal(str)
    scan_results_ready = pyqtSignal(dict) # Emits richer host data now
    scan_finished = pyqtSignal(str, str) # (status_message, temp_xml_path)
    scan_error = pyqtSignal(str)

    def __init__(self, target, arguments):
        """
        Initializes the scanner thread.

        Args:
            target (str): The target host(s)/network(s) for the scan.
            arguments (str): Nmap command-line arguments provided by the user/profile.
        """
        super().__init__() # Initialize the QThread base class
        self.target = target
        self.base_arguments = arguments # Arguments from the UI
        self._is_running = True # Flag to control the thread loop/scan process
        self.nmap_process = None # Will hold the subprocess.Popen object
        self.temp_xml_file_path = None # Path to the temporary XML file for the CURRENT scan

    def _cleanup_temp_file(self):
        """
        Safely removes the temporary XML file created by this thread instance, if it exists.
        This is called internally on stop or by MainWindow before starting a new scan
        or on application exit.
        """
        cleanup_path = self.temp_xml_file_path # Store path before potentially clearing it
        if cleanup_path and os.path.exists(cleanup_path):
            try:
                os.remove(cleanup_path)
                # self.scan_output.emit(f"[Debug] Cleaned up temp file (Scanner instance): {cleanup_path}") # Commented out
                # Only clear the path variable if deletion was successful
                if self.temp_xml_file_path == cleanup_path:
                     self.temp_xml_file_path = None
            except OSError as e:
                # Log non-critical warning if cleanup fails
                self.scan_output.emit(f"[Warning] Could not remove temp file {cleanup_path}: {e}")
            except Exception as e:
                 # Catch other potential errors during cleanup
                 self.scan_output.emit(f"[Warning] Error during temp file cleanup: {e}")
        else:
             # Clear the path variable if it was already None or file didn't exist
             self.temp_xml_file_path = None


    def _build_command(self):
        """
        Constructs the full Nmap command as a list of arguments.

        This includes the Nmap executable path, user-provided arguments,
        the target, and ensures necessary arguments like XML output to a
        temporary file (`-oX <tempfile>`) and verbosity (`-v`) are included.

        Returns:
            list: A list of strings representing the command and its arguments,
                  ready for subprocess.Popen. Returns None if temp file creation fails.
        """
        # Assume 'nmap' is in the system PATH. A more robust solution might
        # involve searching common locations or using a user-configurable path.
        nmap_path = "nmap"

        # Split base arguments safely using shlex, handling potential quotes.
        # Windows splitting might need adjustments if paths with spaces are common.
        if platform.system() == "Windows":
             # Simple split might suffice for typical Nmap args on Windows
             args_list = self.base_arguments.split()
        else:
             # shlex handles Unix-style quoting better
             try:
                 args_list = shlex.split(self.base_arguments)
             except ValueError as e:
                 # Handle potential parsing errors in user input
                 self.scan_output.emit(f"[Warning] Could not parse arguments using shlex: {e}. Using simple split.")
                 args_list = self.base_arguments.split()


        # Construct the initial command list
        command = [nmap_path]
        command.extend(filter(None, args_list)) # Filter out empty strings from split
        command.append(self.target)

        # --- Create Temp File for XML Output ---
        # This file will store the detailed scan results for parsing later.
        try:
            # delete=False prevents automatic deletion on file close.
            # We manage deletion manually via _cleanup_temp_file().
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode='w', encoding='utf-8')
            self.temp_xml_file_path = temp_file.name # Store path for THIS scan instance
            temp_file.close() # Close handle so Nmap can write to it
            # self.scan_output.emit(f"[Debug] Using temp file for XML: {self.temp_xml_file_path}") # Commented out
        except Exception as e:
            self.scan_error.emit(f"Failed to create temporary file for XML output: {e}")
            return None # Indicate error

        # --- Add XML output argument (-oX <file>) ---
        # Check if any XML/All output format is already specified by the user.
        output_arg_present = any(arg.startswith("-oX") or arg.startswith("-oA") for arg in command)
        if not output_arg_present:
             # If not, add argument to output XML to our temp file.
             command.extend(["-oX", self.temp_xml_file_path])
        # Note: If user specified -oA, Nmap *should* still create the -oX file.
        # If user specified -oX with a *different* file, this logic might need refinement.

        # --- Ensure Verbosity (-v) ---
        # Verbosity helps provide progress updates in the raw output.
        verbosity_present = any(arg.startswith("-v") for arg in command)
        if not verbosity_present:
            command.append("-v")

        # Ensure script scanning if -A or -sC is present for NSE output
        # if not any(arg == '-A' or arg == '-sC' for arg in command):
        #      # Maybe add -sC if user wants script output later? For now, rely on profile.
        #      pass

        return command

    def run(self):
        """
        The main execution method of the thread, called by thread.start().

        Builds the command, runs Nmap using subprocess.Popen, reads live
        output, waits for completion, reads the temporary XML file, parses it
        (including OS, MAC, port, and NSE details), and emits the appropriate signals.
        """
        self._is_running = True
        command = []
        # Store the path locally in run scope to ensure it's available even if
        # self.temp_xml_file_path is cleared prematurely by another thread action (unlikely but safe).
        local_temp_xml_path = None

        try:
            # Build the command list, including the temp file path
            command = self._build_command()
            if command is None: # Check if _build_command failed (e.g., temp file error)
                 return # Error signal was already emitted
            local_temp_xml_path = self.temp_xml_file_path # Store path used for this run

            # Log the command being executed (useful for debugging)
            self.scan_output.emit(f"Executing command list: {command!r}") # Raw list representation
            self.scan_output.emit(f"Joined command: {' '.join(shlex.quote(str(s)) for s in command)}") # User-friendly string
            self.scan_output.emit("-" * 30)

            # --- Start Nmap process ---
            # Use Popen for non-blocking execution and access to streams.
            # stderr=STDOUT redirects Nmap's error output to the same stream as standard output.
            # text=True decodes streams as text using default encoding.
            # bufsize=1 enables line buffering for more immediate output.
            # creationflags prevents console window popup on Windows.
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            self.nmap_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creationflags
            )

            # --- Read stdout/stderr for Raw Output Tab ---
            # Process the output stream line by line as it arrives.
            if self.nmap_process.stdout:
                for line in iter(self.nmap_process.stdout.readline, ''):
                    # Check if the stop() method has been called
                    if not self._is_running:
                        self.scan_output.emit("\n[Scan manually stopped during output reading]")
                        # Attempt to terminate if stop() hasn't already killed it
                        if self.nmap_process.poll() is None:
                            self.nmap_process.terminate()
                            try: self.nmap_process.wait(timeout=1)
                            except subprocess.TimeoutExpired: self.nmap_process.kill()
                        break # Exit the reading loop

                    # Emit the raw line (with trailing whitespace removed) to the GUI
                    self.scan_output.emit(line.rstrip())

                # Close the stdout stream once Nmap finishes or loop breaks
                self.nmap_process.stdout.close()

            # --- Wait for Nmap process to complete ---
            # This blocks until the Nmap process actually exits.
            return_code = self.nmap_process.wait()
            self.scan_output.emit("-" * 30) # Separator after raw output

            # --- Process Results (if scan wasn't stopped) ---
            if self._is_running:
                # Check Nmap's exit code
                if return_code == 0:
                    self.scan_output.emit("Nmap process finished successfully. Reading & parsing results file...")

                    # --- Read the Temporary XML File ---
                    full_xml_output = ""
                    if local_temp_xml_path and os.path.exists(local_temp_xml_path):
                        try:
                            with open(local_temp_xml_path, 'r', encoding='utf-8') as f:
                                full_xml_output = f.read()
                        except Exception as read_err:
                            # Handle errors reading the temp file
                            self.scan_output.emit(f"[Error] Failed to read temporary XML file {local_temp_xml_path}: {read_err}")
                            self.scan_error.emit(f"Failed to read scan results file: {read_err}")
                            return # Cannot proceed without XML
                    else:
                        # Handle case where temp file is missing
                        self.scan_output.emit("[Error] Temporary XML file not found or path invalid.")
                        self.scan_error.emit("Scan results file not found.")
                        return # Cannot proceed without XML

                    # Check if XML content is empty
                    if not full_xml_output.strip():
                         self.scan_output.emit("[Warning] XML results file is empty.")
                         self.scan_results_ready.emit({}) # Emit empty results
                         # Emit finished signal, including the path (even if empty)
                         self.scan_finished.emit(f"Scan finished (XML empty). Command: {' '.join(shlex.quote(str(s)) for s in command)}", local_temp_xml_path or "")
                         return

                    # --- Parse XML Output ---
                    try:
                        nm = nmap.PortScanner() # Create parser instance
                        # Use the analyse_nmap_xml_scan method from python-nmap
                        scan_data = nm.analyse_nmap_xml_scan(nmap_xml_output=full_xml_output)
                        parsed_results = {} # Dictionary to hold structured results for UI

                        # --- Data Extraction Logic ---
                        # Check structure validity
                        if 'scan' in scan_data and isinstance(scan_data['scan'], dict):
                            # Iterate through each host found in the scan results
                            for host_ip, host_scan_data in scan_data['scan'].items():
                                if not isinstance(host_scan_data, dict): continue # Skip invalid host data

                                # Extract basic host info (hostname, state, mac, vendor)
                                hostname = ''; hostnames_list = host_scan_data.get('hostnames', [])
                                if isinstance(hostnames_list, list) and len(hostnames_list) > 0:
                                     hostname_entry = hostnames_list[0]
                                     if isinstance(hostname_entry, dict): hostname = hostname_entry.get('name', '')
                                state = 'unknown'; status_info = host_scan_data.get('status', {})
                                if isinstance(status_info, dict): state = status_info.get('state', 'unknown')
                                mac_address = ''; vendor = ''; addresses_info = host_scan_data.get('addresses', {})
                                if isinstance(addresses_info, dict):
                                     mac_address = addresses_info.get('mac', '')
                                     # Vendor info might be at host level keyed by MAC
                                     if mac_address and 'vendor' in host_scan_data and isinstance(host_scan_data['vendor'], dict):
                                          vendor = host_scan_data['vendor'].get(mac_address, '')

                                # Initialize dictionary for this host's UI data
                                host_data_for_ui = {
                                    'hostname': hostname, 'state': state, 'mac': mac_address, 'vendor': vendor,
                                    'osmatch': [], 'protocols': {}, 'hostscript': [] # Add hostscript list
                                }

                                # Extract OS detection results
                                os_info = host_scan_data.get('osmatch', [])
                                if isinstance(os_info, list):
                                     for match in os_info:
                                          if isinstance(match, dict):
                                               os_details = {'name': match.get('name', 'Unknown OS'),'accuracy': match.get('accuracy', '0'),'line': match.get('line', ''),'osclasses': []}
                                               osclasses = match.get('osclass', [])
                                               if isinstance(osclasses, list):
                                                    for osclass in osclasses:
                                                         if isinstance(osclass, dict): os_details['osclasses'].append({'type': osclass.get('type', ''),'vendor': osclass.get('vendor', ''),'osfamily': osclass.get('osfamily', ''),'osgen': osclass.get('osgen', ''),'accuracy': osclass.get('accuracy', '')})
                                               host_data_for_ui['osmatch'].append(os_details)

                                # Extract Host-level NSE script results
                                host_script_info = host_scan_data.get('hostscript', [])
                                if isinstance(host_script_info, list):
                                    for script_item in host_script_info:
                                        if isinstance(script_item, dict):
                                            host_data_for_ui['hostscript'].append({
                                                'id': script_item.get('id', ''),
                                                'output': script_item.get('output', '')
                                            })

                                # Extract Port/Protocol/Service/Script results
                                for proto in ['tcp', 'udp', 'ip', 'sctp']: # Check common protocols
                                    if proto in host_scan_data and isinstance(host_scan_data[proto], dict):
                                        if proto not in host_data_for_ui['protocols']: host_data_for_ui['protocols'][proto] = {}
                                        # Iterate through ports found for this protocol
                                        for port_str, port_data in host_scan_data[proto].items():
                                            if not isinstance(port_data, dict): continue # Skip invalid port data
                                            try:
                                                port_int = int(port_str) # Convert port number to integer

                                                # Extract Port-level NSE script results
                                                port_script_output = []
                                                script_info = port_data.get('script', None)
                                                # Handle script output being single dict or list of dicts
                                                if isinstance(script_info, dict):
                                                     port_script_output.append({'id': script_info.get('id', ''), 'output': script_info.get('output', '')})
                                                elif isinstance(script_info, list):
                                                     for script_item in script_info:
                                                          if isinstance(script_item, dict): port_script_output.append({'id': script_item.get('id', ''), 'output': script_item.get('output', '')})

                                                # Store all port details including scripts
                                                host_data_for_ui['protocols'][proto][port_int] = {
                                                     'state': port_data.get('state', 'unknown'), 'name': port_data.get('name', ''),
                                                     'version': port_data.get('version', ''), 'product': port_data.get('product', ''),
                                                     'extrainfo': port_data.get('extrainfo', ''), 'cpe': port_data.get('cpe', ''),
                                                     'script': port_script_output
                                                }
                                            except (ValueError, TypeError):
                                                # Handle cases where port number isn't an integer
                                                self.scan_output.emit(f"[Warning] Skipping invalid port number format for host {host_ip}, proto {proto}, port '{port_str}'")
                                                continue # Skip invalid port entry

                                # Store the processed data for this host
                                parsed_results[host_ip] = host_data_for_ui
                        else:
                            # Handle cases like ping scan where 'scan' might be empty
                            if 'nmap' in scan_data and 'hosts' in scan_data['nmap']:
                                 num_hosts = scan_data['nmap']['hosts'].get('up', 0); total_hosts = scan_data['nmap']['hosts'].get('total', 0)
                                 self.scan_output.emit(f"Scan data indicates {num_hosts} host(s) up out of {total_hosts} scanned (no port details).")
                            else:
                                 self.scan_output.emit("No hosts found in scan data or scan data structure invalid.")

                        # --- DEBUGGING Block (Commented Out) ---
                        # self.scan_output.emit("--- DEBUG: Final Parsed Results ---")
                        # try:
                        #     debug_output = json.dumps(parsed_results, indent=2)
                        #     self.scan_output.emit(debug_output)
                        # except TypeError as json_err:
                        #     self.scan_output.emit(f"[Debug JSON Error: {json_err}]")
                        #     self.scan_output.emit(str(parsed_results))
                        # self.scan_output.emit("--- END DEBUG ---")
                        # --- END DEBUGGING ---

                        # --- Emit results and finished signal ---
                        self.scan_results_ready.emit(parsed_results)
                        self.scan_finished.emit(f"Scan finished. Command: {' '.join(shlex.quote(str(s)) for s in command)}", local_temp_xml_path or "")

                    except Exception as parse_err:
                        # Handle errors during XML parsing
                        self.scan_output.emit(f"[Error] Failed to parse Nmap XML from file {local_temp_xml_path}: {parse_err}")
                        # Optionally print beginning of XML for debugging
                        # self.scan_output.emit(f"--- XML Start ---\n{full_xml_output[:1000]}...\n--- XML End ---")
                        self.scan_error.emit(f"Failed to parse Nmap XML results: {parse_err}")

                else:
                    # Handle non-zero exit code from Nmap
                    self.scan_error.emit(f"Nmap process exited with error code: {return_code}")
            else:
                # Handle case where scan was stopped before results processing
                self.scan_error.emit("Scan stopped by user.")

        except FileNotFoundError:
            # Handle Nmap executable not being found
            self.scan_error.emit(f"Nmap command ('{command[0]}' if command else 'nmap') not found. Is Nmap installed and in PATH?")
            self._is_running = False
        except Exception as e:
             # Catch any other unexpected errors during thread execution
             if self._is_running:
                self.scan_error.emit(f"An unexpected error occurred in scanner thread: {e}")
             self._is_running = False
        finally:
            # --- Cleanup ---
            # Ensure the process reference is cleared
            self.nmap_process = None
            # Cleanup of the temp file is now handled by MainWindow to allow saving results.
            # We pass the temp file path back via the scan_finished signal.


    def stop(self):
        """
        Requests the thread to stop scanning by terminating the Nmap process.
        Also cleans up the temporary file associated *with this specific thread*.
        """
        self.scan_output.emit("Stop signal received...")
        self._is_running = False # Signal the run loop to stop processing

        # --- Terminate Process ---
        if self.nmap_process and self.nmap_process.poll() is None: # Check if process exists and is running
            pid_to_terminate = self.nmap_process.pid
            self.scan_output.emit(f"Attempting to terminate Nmap process (PID: {pid_to_terminate})...")
            try:
                # Use psutil to find the process and its children
                parent = psutil.Process(pid_to_terminate)
                children = parent.children(recursive=True)
                # Terminate children first
                for child in children:
                     try:
                          self.scan_output.emit(f"Terminating child process (PID: {child.pid})...")
                          child.terminate()
                     except psutil.NoSuchProcess:
                          self.scan_output.emit(f"Child process (PID: {child.pid}) already exited.")
                          continue # Child already exited
                     except Exception as child_term_err:
                          self.scan_output.emit(f"Error terminating child process {child.pid}: {child_term_err}")

                # Terminate parent process
                self.scan_output.emit(f"Terminating main Nmap process (PID: {pid_to_terminate})...")
                parent.terminate() # Use psutil terminate on the parent as well

                # Wait briefly for termination using psutil
                try:
                    gone, alive = psutil.wait_procs([parent] + children, timeout=2)
                    for p in gone: self.scan_output.emit(f"Process {p.pid} terminated.")
                    # If any are still alive, kill them forcefully
                    if alive:
                         self.scan_output.emit(f"Processes {[p.pid for p in alive]} did not terminate gracefully. Killing...")
                         for p in alive:
                              try: p.kill(); self.scan_output.emit(f"Process {p.pid} killed.")
                              except psutil.NoSuchProcess: self.scan_output.emit(f"Process {p.pid} already exited before kill.")
                              except Exception as kill_err: self.scan_output.emit(f"Error killing process {p.pid}: {kill_err}")
                except Exception as wait_err:
                     # Handle errors during waiting/killing
                     self.scan_output.emit(f"Error waiting for process termination: {wait_err}")
                     # Fallback kill just in case
                     try:
                          if parent.is_running(): parent.kill()
                          for child in children:
                               if child.is_running(): child.kill()
                     except: pass # Ignore errors during fallback kill

            except psutil.NoSuchProcess:
                 # Handle case where process finished between check and psutil call
                 self.scan_output.emit(f"Nmap process (PID: {pid_to_terminate}) already finished or could not be found.")
            except Exception as e:
                # Catch other errors during termination attempt
                self.scan_output.emit(f"Error trying to terminate Nmap process: {e}")
        else:
             # Handle case where process wasn't running when stop was called
             self.scan_output.emit("No active Nmap process found to stop.")

        # --- Clean up THIS thread's temp file if stopped ---
        # This prevents leaving temp files around if scan is stopped manually
        # before completion and MainWindow doesn't get the finished signal.
        self._cleanup_temp_file()