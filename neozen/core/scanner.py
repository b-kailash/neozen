import nmap # Import the python-nmap library
import subprocess # To potentially manage the process directly if needed
import psutil # To find and terminate child processes
from PyQt6.QtCore import QThread, pyqtSignal
import os # For OS specific operations if needed

class Scanner(QThread):
    """
    Worker thread for running Nmap scans asynchronously.
    Uses python-nmap to interact with the Nmap executable.
    """
    # --- Signals ---
    # Emits chunks of Nmap output (stdout/stderr or parsed info)
    scan_output = pyqtSignal(str)
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
        try:
            # --- Initialize python-nmap PortScanner ---
            # We need to handle potential errors if nmap executable is not found
            try:
                nm = nmap.PortScanner()
            except nmap.PortScannerError as e:
                self.scan_error.emit(f"Nmap executable not found or permission error: {e}")
                return # Exit the thread

            self.scan_output.emit(f"Starting Nmap {nm.nmap_version()} scan on {self.target} with args: {self.arguments}")
            self.scan_output.emit("-" * 30)

            # --- Execute the scan ---
            # python-nmap's scan method blocks until the scan is complete.
            # It internally calls the nmap executable.
            # We need a way to potentially interrupt this.
            # Unfortunately, python-nmap doesn't offer a non-blocking scan or
            # direct process control easily. We might need to manage the
            # subprocess ourselves for better 'stop' functionality later.
            # For now, we rely on python-nmap's blocking call.
            # The 'stop' method will try to find and kill the process.

            # Check if still running before starting the blocking call
            if not self._is_running:
                 self.scan_error.emit("Scan stopped before starting.")
                 return

            # This is the blocking call
            scan_result = nm.scan(hosts=self.target, arguments=self.arguments)

            # --- Process Results (if scan wasn't stopped) ---
            if self._is_running:
                self.scan_output.emit("-" * 30)
                self.scan_output.emit("Scan Results:")

                if not nm.all_hosts():
                    self.scan_output.emit("No hosts found or all hosts are down.")
                else:
                    for host in nm.all_hosts():
                        self.scan_output.emit(f"\nHost: {host} ({nm[host].hostname()})")
                        self.scan_output.emit(f"State: {nm[host].state()}")
                        for proto in nm[host].all_protocols():
                            self.scan_output.emit(f"Protocol: {proto}")
                            ports = nm[host][proto].keys()
                            for port in sorted(ports):
                                state = nm[host][proto][port]['state']
                                name = nm[host][proto][port]['name']
                                version = nm[host][proto][port]['version']
                                product = nm[host][proto][port]['product']
                                self.scan_output.emit(f"  Port: {port:<5}\tState: {state:<10}\tService: {name:<15}\tVersion: {product} {version}")

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
        # This is a bit complex because python-nmap doesn't expose the process object.
        # We need to find the 'nmap' process potentially started by this script.
        # This might require refinement depending on the OS and exact setup.
        try:
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            nmap_found = False
            for proc in children:
                # Check if process name is 'nmap' or 'nmap.exe'
                if proc.name().lower() in ['nmap', 'nmap.exe']:
                    self.scan_output.emit(f"Found Nmap process (PID: {proc.pid}). Terminating...")
                    proc.terminate() # Try graceful termination first
                    try:
                        proc.wait(timeout=2) # Wait a bit for it to exit
                    except psutil.TimeoutExpired:
                        self.scan_output.emit(f"Nmap process (PID: {proc.pid}) did not terminate gracefully. Killing...")
                        proc.kill() # Force kill if necessary
                    nmap_found = True
                    break # Assume only one direct nmap child for now
            if not nmap_found:
                 self.scan_output.emit("Could not find running Nmap process to terminate.")

        except Exception as e:
            self.scan_output.emit(f"Error trying to terminate Nmap process: {e}")

        # The run() method should detect self._is_running is False and exit,
        # eventually emitting scan_error("Scan stopped by user.")
