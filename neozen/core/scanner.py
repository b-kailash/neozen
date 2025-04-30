import nmap # Still used for parsing XML results and getting version
import subprocess # Used for running Nmap directly
import psutil # To find and terminate child processes
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import os
import shlex # To split arguments safely, especially on non-Windows
import sys # To check platform
import json # For debugging output
import tempfile # For creating temporary file for XML output

class Scanner(QThread):
    """
    Worker thread for running Nmap scans asynchronously using subprocess.
    Captures live human-readable stdout/stderr for Raw Output tab.
    Saves XML to a temporary file and parses it upon completion.
    Passes back the temp file path upon completion.
    Cleanup of temp file is handled by the main window.
    """
    # --- Signals ---
    scan_output = pyqtSignal(str)
    scan_results_ready = pyqtSignal(dict)
    scan_finished = pyqtSignal(str, str) # (status_message, temp_xml_path)
    scan_error = pyqtSignal(str)

    def __init__(self, target, arguments):
        super().__init__()
        self.target = target
        self.base_arguments = arguments # Arguments from the UI
        self._is_running = True
        self.nmap_process = None # Will hold the subprocess object
        self.temp_xml_file_path = None # Path to the temporary XML file for the CURRENT scan

    def _cleanup_temp_file(self):
        """Safely removes the temporary XML file if it exists."""
        cleanup_path = self.temp_xml_file_path # Store path before potentially clearing it
        if cleanup_path and os.path.exists(cleanup_path):
            try:
                os.remove(cleanup_path)
                self.scan_output.emit(f"[Debug] Cleaned up temp file (Scanner instance): {cleanup_path}")
                # Only clear the path variable if deletion was successful
                if self.temp_xml_file_path == cleanup_path:
                     self.temp_xml_file_path = None
            except OSError as e:
                self.scan_output.emit(f"[Warning] Could not remove temp file {cleanup_path}: {e}")
            except Exception as e:
                 self.scan_output.emit(f"[Warning] Error during temp file cleanup: {e}")
        else:
             # Clear the path variable if it was already None or file didn't exist
             self.temp_xml_file_path = None


    def _build_command(self):
        """Builds the full Nmap command list, saving XML to a temp file."""
        nmap_path = "nmap"
        if sys.platform == "win32": args_list = self.base_arguments.split()
        else: args_list = shlex.split(self.base_arguments)
        command = [nmap_path]
        command.extend(filter(None, args_list))
        command.append(self.target)

        # --- Create Temp File for XML Output ---
        # Note: We don't clean up old files here; MainWindow handles previous scan's file
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode='w', encoding='utf-8')
            self.temp_xml_file_path = temp_file.name # Store path for THIS scan instance
            temp_file.close()
            self.scan_output.emit(f"[Debug] Using temp file for XML: {self.temp_xml_file_path}")
        except Exception as e:
            self.scan_error.emit(f"Failed to create temporary file for XML output: {e}")
            return None

        # --- Add XML output argument ---
        output_arg_present = any(arg.startswith("-oX") or arg.startswith("-oA") for arg in command)
        if not output_arg_present:
             command.extend(["-oX", self.temp_xml_file_path])
        else:
             command = [arg for arg in command if arg != '-oX' and arg != '-']
             if not any(arg.startswith("-oX") or arg.startswith("-oA") for arg in command):
                  command.extend(["-oX", self.temp_xml_file_path])

        verbosity_present = any(arg.startswith("-v") for arg in command)
        if not verbosity_present: command.append("-v")
        return command

    def run(self):
        """
        The main execution method of the thread. Runs Nmap via subprocess.
        Reads stdout/stderr for live output, reads temp file for XML parsing.
        Does NOT clean up the temp file itself; MainWindow is responsible.
        """
        self._is_running = True
        command = []
        # Store the path locally in run scope
        local_temp_xml_path = None

        try:
            command = self._build_command()
            if command is None: return
            local_temp_xml_path = self.temp_xml_file_path # Store path used for this run

            self.scan_output.emit(f"Executing command list: {command!r}")
            self.scan_output.emit(f"Joined command: {' '.join(shlex.quote(str(s)) for s in command)}")
            self.scan_output.emit("-" * 30)

            self.nmap_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                bufsize=1, universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            if self.nmap_process.stdout:
                for line in iter(self.nmap_process.stdout.readline, ''):
                    if not self._is_running:
                        self.scan_output.emit("\n[Scan manually stopped during output reading]")
                        if self.nmap_process.poll() is None:
                            self.nmap_process.terminate()
                            try: self.nmap_process.wait(timeout=1)
                            except subprocess.TimeoutExpired: self.nmap_process.kill()
                        break
                    self.scan_output.emit(line.rstrip())
                self.nmap_process.stdout.close()

            return_code = self.nmap_process.wait()
            self.scan_output.emit("-" * 30)

            if self._is_running:
                if return_code == 0:
                    self.scan_output.emit("Nmap process finished successfully. Reading & parsing results file...")
                    full_xml_output = ""
                    if local_temp_xml_path and os.path.exists(local_temp_xml_path):
                        try:
                            with open(local_temp_xml_path, 'r', encoding='utf-8') as f:
                                full_xml_output = f.read()
                        except Exception as read_err:
                            self.scan_output.emit(f"[Error] Failed to read temporary XML file {local_temp_xml_path}: {read_err}")
                            self.scan_error.emit(f"Failed to read scan results file: {read_err}")
                            return # Cannot proceed without XML
                    else:
                        self.scan_output.emit("[Error] Temporary XML file not found or path invalid.")
                        self.scan_error.emit("Scan results file not found.")
                        return # Cannot proceed without XML

                    if not full_xml_output.strip():
                         self.scan_output.emit("[Warning] XML results file is empty.")
                         self.scan_results_ready.emit({})
                         self.scan_finished.emit(f"Scan finished (XML empty). Command: {' '.join(shlex.quote(str(s)) for s in command)}", local_temp_xml_path or "")
                         return

                    try:
                        nm = nmap.PortScanner()
                        scan_data = nm.analyse_nmap_xml_scan(nmap_xml_output=full_xml_output)
                        parsed_results = {}

                        # (Parsing logic remains the same)
                        if 'scan' in scan_data and isinstance(scan_data['scan'], dict):
                             for host_ip, host_scan_data in scan_data['scan'].items():
                                  if not isinstance(host_scan_data, dict): continue
                                  hostname = ''
                                  hostnames_list = host_scan_data.get('hostnames', [])
                                  if isinstance(hostnames_list, list) and len(hostnames_list) > 0:
                                       hostname_entry = hostnames_list[0]
                                       if isinstance(hostname_entry, dict): hostname = hostname_entry.get('name', '')
                                  state = 'unknown'
                                  status_info = host_scan_data.get('status', {})
                                  if isinstance(status_info, dict): state = status_info.get('state', 'unknown')
                                  host_data_for_ui = {'hostname': hostname, 'state': state, 'protocols': {}}
                                  for proto in ['tcp', 'udp', 'ip', 'sctp']:
                                       if proto in host_scan_data and isinstance(host_scan_data[proto], dict):
                                            if proto not in host_data_for_ui['protocols']: host_data_for_ui['protocols'][proto] = {}
                                            for port_str, port_data in host_scan_data[proto].items():
                                                 if not isinstance(port_data, dict): continue
                                                 try:
                                                      port_int = int(port_str)
                                                      host_data_for_ui['protocols'][proto][port_int] = {
                                                           'state': port_data.get('state', 'unknown'), 'name': port_data.get('name', ''),
                                                           'version': port_data.get('version', ''), 'product': port_data.get('product', ''),
                                                           'extrainfo': port_data.get('extrainfo', ''), 'cpe': port_data.get('cpe', '')}
                                                 except (ValueError, TypeError): continue
                                  parsed_results[host_ip] = host_data_for_ui
                        else:
                             if 'nmap' in scan_data and 'hosts' in scan_data['nmap']:
                                  num_hosts = scan_data['nmap']['hosts'].get('up', 0)
                                  total_hosts = scan_data['nmap']['hosts'].get('total', 0)
                                  self.scan_output.emit(f"Scan data indicates {num_hosts} host(s) up out of {total_hosts} scanned (no port details).")
                             else:
                                  self.scan_output.emit("No hosts found in scan data or scan data structure invalid.")

                        # Emit results and finished signal (including temp file path)
                        self.scan_results_ready.emit(parsed_results)
                        # Pass the path that was actually used for this scan run
                        self.scan_finished.emit(f"Scan finished. Command: {' '.join(shlex.quote(str(s)) for s in command)}", local_temp_xml_path or "")

                    except Exception as parse_err:
                        self.scan_output.emit(f"[Error] Failed to parse Nmap XML from file {local_temp_xml_path}: {parse_err}")
                        self.scan_error.emit(f"Failed to parse Nmap XML results: {parse_err}")

                else:
                    self.scan_error.emit(f"Nmap process exited with error code: {return_code}")
            else:
                self.scan_error.emit("Scan stopped by user.")

        except FileNotFoundError:
            self.scan_error.emit(f"Nmap command ('{command[0]}' if command else 'nmap') not found. Is Nmap installed and in PATH?")
            self._is_running = False
        except Exception as e:
             if self._is_running:
                self.scan_error.emit(f"An unexpected error occurred in scanner thread: {e}")
             self._is_running = False
        finally:
            # --- REMOVED cleanup call from here ---
            # self._cleanup_temp_file()
            self.nmap_process = None # Clear process reference

    def stop(self):
        """
        Requests the thread to stop scanning by terminating the Nmap process.
        Also cleans up the temporary file associated *with this specific thread*.
        """
        self.scan_output.emit("Stop signal received...")
        self._is_running = False # Signal the run loop to stop processing

        # --- Terminate Process ---
        if self.nmap_process and self.nmap_process.poll() is None:
            pid_to_terminate = self.nmap_process.pid
            self.scan_output.emit(f"Attempting to terminate Nmap process (PID: {pid_to_terminate})...")
            try:
                parent = psutil.Process(pid_to_terminate)
                children = parent.children(recursive=True)
                for child in children:
                     try: child.terminate()
                     except psutil.NoSuchProcess: continue
                     except Exception as child_term_err: self.scan_output.emit(f"Error terminating child process {child.pid}: {child_term_err}")
                parent.terminate()
                try:
                    gone, alive = psutil.wait_procs([parent] + children, timeout=2)
                    if alive:
                         self.scan_output.emit(f"Processes {[p.pid for p in alive]} did not terminate gracefully. Killing...")
                         for p in alive:
                              try: p.kill()
                              except psutil.NoSuchProcess: pass
                              except Exception as kill_err: self.scan_output.emit(f"Error killing process {p.pid}: {kill_err}")
                except Exception as wait_err:
                     self.scan_output.emit(f"Error waiting for process termination: {wait_err}")
                     try: # Fallback kill
                          if parent.is_running(): parent.kill()
                          for child in children:
                               if child.is_running(): child.kill()
                     except: pass
            except psutil.NoSuchProcess: self.scan_output.emit(f"Nmap process (PID: {pid_to_terminate}) already finished or could not be found.")
            except Exception as e: self.scan_output.emit(f"Error trying to terminate Nmap process: {e}")
        else:
             self.scan_output.emit("No active Nmap process found to stop.")

        # --- Clean up THIS thread's temp file if stopped ---
        # This prevents leaving temp files around if scan is stopped manually
        self._cleanup_temp_file()