import nmap # Import the python-nmap library
import subprocess # To potentially manage the process directly if needed
import psutil # To find and terminate child processes
from PyQt6.QtCore import QThread, pyqtSignal, QObject # QObject needed for signals
import os # For OS specific operations if needed
import time # For potential delays if needed

class Scanner(QThread):
    """
    Worker thread for running Nmap scans asynchronously.
    Uses python-nmap to interact with the Nmap executable.
    Emits raw output during scan and structured results upon completion.
    """
    # --- Signals ---
    # Emits chunks of Nmap output (stdout/stderr or parsed info)
    scan_output = pyqtSignal(str)
    # Emits structured scan results when the scan finishes successfully
    scan_results_ready = pyqtSignal(dict)
    # Emits when the scan finishes successfully (passes final status message)
    scan_finished = pyqtSignal(str)
    # Emits when an error occurs or scan is stopped (passes error message)
    scan_error = pyqtSignal(str)

    def __init__(self, target, arguments):
        """
        Initialize the scanner thread.

        Args:
            target (str): The target host(s)/network(s) for the scan.
            arguments (str): Nmap command-line arguments (e.g., '-T4 -A -v').
        """
        super().__init__() # Initialize the QThread base class
        self.target = target
        self.arguments = arguments
        self._is_running = True # Flag to control the thread loop/scan process
        self.nmap_process = None # To hold the nmap process object if needed

    def run(self):
        """
        The main execution method of the thread. Called when thread.start() is invoked.
        """
        self._is_running = True
        nm = None
        parsed_results = {} # Dictionary to hold structured results

        try:
            # --- Initialize python-nmap PortScanner ---
            try:
                nm = nmap.PortScanner()
                # Emit Nmap version info early
                self.scan_output.emit(f"Using Nmap version: {nm.nmap_version()}")
            except nmap.PortScannerError as e:
                self.scan_error.emit(f"Nmap executable not found or permission error: {e}")
                return # Exit the thread
            except Exception as e:
                 self.scan_error.emit(f"Error initializing Nmap: {e}")
                 return

            self.scan_output.emit(f"Starting scan on {self.target} with args: {self.arguments}")
            self.scan_output.emit("-" * 30)

            # --- Execute the scan ---
            # Check if still running before starting the blocking call
            if not self._is_running:
                 self.scan_error.emit("Scan stopped before starting.")
                 return

            # This is the blocking call
            # Consider adding -oX - argument to get XML output directly if needed later
            scan_result = nm.scan(hosts=self.target, arguments=self.arguments)

            # --- Process Results (if scan wasn't stopped) ---
            if self._is_running:
                self.scan_output.emit("-" * 30)
                self.scan_output.emit("Scan complete. Parsing results...")

                # Structure the results
                parsed_results = {}
                if nm.all_hosts():
                    for host in nm.all_hosts():
                        host_data = {
                            'hostname': nm[host].hostname(),
                            'state': nm[host].state(),
                            'protocols': {}
                        }
                        for proto in nm[host].all_protocols():
                            host_data['protocols'][proto] = {}
                            ports = nm[host][proto].keys()
                            for port in sorted(ports):
                                port_info = nm[host][proto][port]
                                host_data['protocols'][proto][port] = {
                                    'state': port_info.get('state', 'unknown'),
                                    'name': port_info.get('name', ''),
                                    'version': port_info.get('version', ''),
                                    'product': port_info.get('product', ''),
                                    'extrainfo': port_info.get('extrainfo', ''),
                                    'cpe': port_info.get('cpe', '')
                                }
                        parsed_results[host] = host_data
                    self.scan_results_ready.emit(parsed_results) # Emit structured data
                else:
                     self.scan_output.emit("No hosts found or all hosts are down.")
                     self.scan_results_ready.emit({}) # Emit empty results

                # --- Emit Finished Signal ---
                scan_info = nm.scaninfo()
                final_message = f"Scan finished. Command: {scan_info.get('command_line', 'N/A')}"
                self.scan_finished.emit(final_message)
            else:
                # Scan was stopped during the blocking call (or just after)
                self.scan_error.emit("Scan stopped by user.")

        except nmap.PortScannerError as e:
            # Handle errors during the scan execution itself
             if self._is_running: # Only report error if not intentionally stopped
                self.scan_error.emit(f"Nmap scan error: {e}")
        except Exception as e:
            # Catch any other unexpected errors
             if self._is_running:
                self.scan_error.emit(f"An unexpected error occurred: {e}")
        finally:
            self._is_running = False # Ensure flag is reset


    def stop(self):
        """
        Requests the thread to stop scanning.
        Attempts to find and terminate the underlying Nmap process.
        """
        self.scan_output.emit("Stop signal received. Attempting to terminate Nmap process...")
        self._is_running = False # Signal the run loop to stop processing results

        # --- Find and Terminate Nmap Process ---
        try:
            # Get current process PID
            current_pid = os.getpid()
            current_process = psutil.Process(current_pid)
            # Find child processes named 'nmap' or 'nmap.exe'
            children = current_process.children(recursive=True)
            nmap_found = False
            for proc in children:
                try:
                    # Check if process name is 'nmap' or 'nmap.exe'
                    if proc.name().lower() in ['nmap', 'nmap.exe']:
                        self.scan_output.emit(f"Found Nmap process (PID: {proc.pid}). Terminating...")
                        proc.terminate() # Try graceful termination first
                        try:
                            proc.wait(timeout=1) # Wait briefly
                        except psutil.TimeoutExpired:
                            self.scan_output.emit(f"Nmap process (PID: {proc.pid}) did not terminate gracefully. Killing...")
                            proc.kill() # Force kill if necessary
                        nmap_found = True
                        # break # Decide if you expect multiple nmap children
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process might have already finished or permissions issue
                    continue
                except Exception as term_err:
                     self.scan_output.emit(f"Error during termination attempt for PID {proc.pid}: {term_err}")


            if not nmap_found:
                 self.scan_output.emit("Could not find running Nmap child process to terminate.")

        except psutil.NoSuchProcess:
             self.scan_output.emit("Current process not found (should not happen).")
        except Exception as e:
            self.scan_output.emit(f"Error trying to terminate Nmap process: {e}")

        # The run() method should detect self._is_running is False and exit,
        # eventually emitting scan_error("Scan stopped by user.")

