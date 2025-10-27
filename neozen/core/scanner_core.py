"""
Pure Python Nmap scanner with callback-based communication.

This module provides a GUI-framework agnostic scanner that uses callbacks
instead of framework-specific signals, making it reusable across different
interface types (desktop, web, CLI, API).
"""

import nmap  # Used for parsing XML results
import subprocess  # Used for running Nmap directly
import psutil  # To find and terminate child processes
import threading  # Pure Python threading instead of QThread
import os
import shlex  # To split arguments safely
import tempfile  # For creating temporary file for XML output
import platform  # For platform-specific checks
from typing import Callable, Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class NmapScanner(threading.Thread):
    """
    Pure Python Nmap scanner that uses callbacks for communication.

    This class is GUI-framework agnostic and can be used with any interface
    by providing callback functions for output, results, completion, and errors.

    Captures live human-readable stdout/stderr output.
    Saves XML to a temporary file and parses it upon completion, including
    OS/MAC/NSE details. Passes back the temp file path upon completion.
    """

    def __init__(
        self,
        target: str,
        arguments: str,
        on_output: Optional[Callable[[str], None]] = None,
        on_results: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_finished: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the scanner thread with callbacks.

        Args:
            target: The target host(s)/network(s) for the scan.
            arguments: Nmap command-line arguments.
            on_output: Callback for live output text (called with str).
            on_results: Callback for parsed results (called with dict).
            on_finished: Callback for completion (called with message, xml_path).
            on_error: Callback for errors (called with error message).
        """
        super().__init__(daemon=True)
        self.target = target
        self.base_arguments = arguments
        self._is_running = True  # Flag to control the thread loop/scan process
        self.nmap_process = None  # Will hold the subprocess.Popen object
        self.temp_xml_file_path = None  # Path to the temporary XML file

        # Store callbacks (use no-op lambdas if None)
        self._on_output = on_output or (lambda x: None)
        self._on_results = on_results or (lambda x: None)
        self._on_finished = on_finished or (lambda x, y: None)
        self._on_error = on_error or (lambda x: None)

    def _cleanup_temp_file(self):
        """
        Safely removes the temporary XML file created by this thread instance.

        This is called internally on stop or by the caller before starting
        a new scan or on application exit.
        """
        cleanup_path = self.temp_xml_file_path
        if cleanup_path and os.path.exists(cleanup_path):
            try:
                os.remove(cleanup_path)
                # Only clear the path variable if deletion was successful
                if self.temp_xml_file_path == cleanup_path:
                    self.temp_xml_file_path = None
            except OSError as e:
                # Log non-critical warning if cleanup fails
                self._on_output(f"[Warning] Could not remove temp file {cleanup_path}: {e}")
            except Exception as e:
                # Catch other potential errors during cleanup
                self._on_output(f"[Warning] Error during temp file cleanup: {e}")
        else:
            # Clear the path variable if it was already None or file didn't exist
            self.temp_xml_file_path = None

    def _build_command(self):
        """
        Constructs the full Nmap command as a list of arguments.

        This includes the Nmap executable path, user-provided arguments,
        the target, and ensures necessary arguments like XML output to a
        temporary file (`-oX <tempfile>`) and verbosity (`-v`) are included.

        On Linux systems, prepends 'sudo' if running as non-root user to allow
        privileged scans (OS detection, SYN scans, etc.).

        Returns:
            list: A list of strings representing the command and its arguments,
                  ready for subprocess.Popen. Returns None if temp file creation fails.
        """
        nmap_path = "nmap"

        # On Linux, use sudo if not running as root (to allow privileged scans)
        use_sudo = False
        if platform.system() != "Windows":
            try:
                use_sudo = os.geteuid() != 0  # Check if not root
            except AttributeError:
                # os.geteuid() not available (shouldn't happen on Linux, but just in case)
                pass

        # Split base arguments safely using shlex
        if platform.system() == "Windows":
            # Simple split for typical Nmap args on Windows
            args_list = self.base_arguments.split()
        else:
            # shlex handles Unix-style quoting better
            try:
                args_list = shlex.split(self.base_arguments)
            except ValueError as e:
                # Handle potential parsing errors in user input
                self._on_output(f"[Warning] Could not parse arguments using shlex: {e}. Using simple split.")
                args_list = self.base_arguments.split()

        # Construct the initial command list
        if use_sudo:
            command = ["sudo", nmap_path]
        else:
            command = [nmap_path]
        command.extend(filter(None, args_list))  # Filter out empty strings
        command.append(self.target)

        # --- Create Temp File for XML Output ---
        try:
            # delete=False prevents automatic deletion on file close
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=".xml", mode='w', encoding='utf-8'
            )
            self.temp_xml_file_path = temp_file.name
            temp_file.close()  # Close handle so Nmap can write to it

            # If using sudo, change ownership to root and make writable
            # This allows sudo nmap to fully control the temp file (delete, recreate, write)
            if use_sudo:
                try:
                    # Use sudo chown to change ownership to root:root
                    subprocess.run(['sudo', 'chown', 'root:root', self.temp_xml_file_path],
                                   check=True, capture_output=True)
                except Exception as chown_error:
                    self._on_output(f"[Warning] Failed to change temp file ownership: {chown_error}")
        except Exception as e:
            self._on_error(f"Failed to create temporary file for XML output: {e}")
            return None  # Indicate error

        # --- Add XML output argument (-oX <file>) ---
        output_arg_present = any(
            arg.startswith("-oX") or arg.startswith("-oA") for arg in command
        )
        if not output_arg_present:
            command.extend(["-oX", self.temp_xml_file_path])

        # --- Ensure Verbosity (-v) ---
        verbosity_present = any(arg.startswith("-v") for arg in command)
        if not verbosity_present:
            command.append("-v")

        return command

    def run(self):
        """
        The main execution method of the thread, called by thread.start().

        Builds the command, runs Nmap using subprocess.Popen, reads live
        output, waits for completion, reads the temporary XML file, parses it
        (including OS, MAC, port, and NSE details), and invokes the callbacks.
        """
        self._is_running = True
        command = []
        local_temp_xml_path = None

        try:
            # Build the command list, including the temp file path
            command = self._build_command()
            if command is None:  # Check if _build_command failed
                return  # Error callback was already invoked
            local_temp_xml_path = self.temp_xml_file_path

            # Log the command being executed
            self._on_output(f"Executing command list: {command!r}")
            self._on_output(f"Joined command: {' '.join(shlex.quote(str(s)) for s in command)}")
            self._on_output("-" * 30)

            # --- Start Nmap process ---
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

            # --- Read stdout/stderr for live output ---
            if self.nmap_process.stdout:
                for line in iter(self.nmap_process.stdout.readline, ''):
                    # Check if stop() method has been called
                    if not self._is_running:
                        self._on_output("\n[Scan manually stopped during output reading]")
                        if self.nmap_process.poll() is None:
                            self.nmap_process.terminate()
                            try:
                                self.nmap_process.wait(timeout=1)
                            except subprocess.TimeoutExpired:
                                self.nmap_process.kill()
                        break

                    # Emit the raw line to the callback
                    self._on_output(line.rstrip())

                self.nmap_process.stdout.close()

            # --- Wait for Nmap process to complete ---
            return_code = self.nmap_process.wait()
            self._on_output("-" * 30)

            # --- Process Results (if scan wasn't stopped) ---
            if self._is_running:
                if return_code == 0:
                    self._on_output("Nmap process finished successfully. Reading & parsing results file...")

                    # If we used sudo, change ownership back to current user so we can read the file
                    if use_sudo and local_temp_xml_path and os.path.exists(local_temp_xml_path):
                        try:
                            import pwd
                            username = pwd.getpwuid(os.getuid()).pw_name
                            subprocess.run(['sudo', 'chown', f'{username}:{username}', local_temp_xml_path],
                                          check=True, capture_output=True)
                            self._on_output(f"[Debug] Changed XML file ownership back to {username}")
                        except Exception as chown_err:
                            self._on_output(f"[Warning] Failed to change XML file ownership back: {chown_err}")

                    # --- Read the Temporary XML File ---
                    full_xml_output = ""
                    if local_temp_xml_path and os.path.exists(local_temp_xml_path):
                        try:
                            with open(local_temp_xml_path, 'r', encoding='utf-8') as f:
                                full_xml_output = f.read()
                        except Exception as read_err:
                            self._on_output(f"[Error] Failed to read temporary XML file {local_temp_xml_path}: {read_err}")
                            self._on_error(f"Failed to read scan results file: {read_err}")
                            return
                    else:
                        self._on_output("[Error] Temporary XML file not found or path invalid.")
                        self._on_error("Scan results file not found.")
                        return

                    # Check if XML content is empty
                    if not full_xml_output.strip():
                        self._on_output("[Warning] XML results file is empty.")
                        self._on_results({})  # Emit empty results
                        self._on_finished(
                            f"Scan finished (XML empty). Command: {' '.join(shlex.quote(str(s)) for s in command)}",
                            local_temp_xml_path or ""
                        )
                        return

                    # --- Parse XML Output ---
                    try:
                        parsed_results = self._parse_xml(full_xml_output)

                        # --- Emit results and finished callback ---
                        self._on_results(parsed_results)
                        self._on_finished(
                            f"Scan finished. Command: {' '.join(shlex.quote(str(s)) for s in command)}",
                            local_temp_xml_path or ""
                        )

                    except Exception as parse_err:
                        self._on_output(f"[Error] Failed to parse Nmap XML from file {local_temp_xml_path}: {parse_err}")
                        self._on_error(f"Failed to parse Nmap XML results: {parse_err}")

                else:
                    # Handle non-zero exit code from Nmap
                    self._on_error(f"Nmap process exited with error code: {return_code}")
            else:
                # Handle case where scan was stopped before results processing
                self._on_error("Scan stopped by user.")

        except FileNotFoundError:
            self._on_error(f"Nmap command ('{command[0]}' if command else 'nmap') not found. Is Nmap installed and in PATH?")
            self._is_running = False
        except Exception as e:
            if self._is_running:
                self._on_error(f"An unexpected error occurred in scanner thread: {e}")
            self._is_running = False
        finally:
            # Ensure the process reference is cleared
            self.nmap_process = None

    def _parse_xml(self, full_xml_output: str) -> Dict[str, Any]:
        """
        Parse Nmap XML output into structured data.

        Args:
            full_xml_output: XML string from Nmap output

        Returns:
            Dictionary with structured host/port/service data
        """
        nm = nmap.PortScanner()
        scan_data = nm.analyse_nmap_xml_scan(nmap_xml_output=full_xml_output)
        parsed_results = {}

        # Check structure validity
        if 'scan' in scan_data and isinstance(scan_data['scan'], dict):
            # Iterate through each host found in the scan results
            for host_ip, host_scan_data in scan_data['scan'].items():
                if not isinstance(host_scan_data, dict):
                    continue

                # Extract basic host info
                hostname = ''
                hostnames_list = host_scan_data.get('hostnames', [])
                if isinstance(hostnames_list, list) and len(hostnames_list) > 0:
                    hostname_entry = hostnames_list[0]
                    if isinstance(hostname_entry, dict):
                        hostname = hostname_entry.get('name', '')

                state = 'unknown'
                status_info = host_scan_data.get('status', {})
                if isinstance(status_info, dict):
                    state = status_info.get('state', 'unknown')

                mac_address = ''
                vendor = ''
                addresses_info = host_scan_data.get('addresses', {})
                if isinstance(addresses_info, dict):
                    mac_address = addresses_info.get('mac', '')
                    if mac_address and 'vendor' in host_scan_data and isinstance(host_scan_data['vendor'], dict):
                        vendor = host_scan_data['vendor'].get(mac_address, '')

                # Initialize dictionary for this host's data
                host_data_for_ui = {
                    'hostname': hostname,
                    'state': state,
                    'mac': mac_address,
                    'vendor': vendor,
                    'osmatch': [],
                    'protocols': {},
                    'hostscript': []
                }

                # Extract OS detection results
                os_info = host_scan_data.get('osmatch', [])
                if isinstance(os_info, list):
                    for match in os_info:
                        if isinstance(match, dict):
                            os_details = {
                                'name': match.get('name', 'Unknown OS'),
                                'accuracy': match.get('accuracy', '0'),
                                'line': match.get('line', ''),
                                'osclasses': []
                            }
                            osclasses = match.get('osclass', [])
                            if isinstance(osclasses, list):
                                for osclass in osclasses:
                                    if isinstance(osclass, dict):
                                        os_details['osclasses'].append({
                                            'type': osclass.get('type', ''),
                                            'vendor': osclass.get('vendor', ''),
                                            'osfamily': osclass.get('osfamily', ''),
                                            'osgen': osclass.get('osgen', ''),
                                            'accuracy': osclass.get('accuracy', '')
                                        })
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
                for proto in ['tcp', 'udp', 'ip', 'sctp']:
                    if proto in host_scan_data and isinstance(host_scan_data[proto], dict):
                        if proto not in host_data_for_ui['protocols']:
                            host_data_for_ui['protocols'][proto] = {}

                        for port_str, port_data in host_scan_data[proto].items():
                            if not isinstance(port_data, dict):
                                continue
                            try:
                                port_int = int(port_str)

                                # Extract Port-level NSE script results
                                port_script_output = []
                                script_info = port_data.get('script', None)
                                if isinstance(script_info, dict):
                                    port_script_output.append({
                                        'id': script_info.get('id', ''),
                                        'output': script_info.get('output', '')
                                    })
                                elif isinstance(script_info, list):
                                    for script_item in script_info:
                                        if isinstance(script_item, dict):
                                            port_script_output.append({
                                                'id': script_item.get('id', ''),
                                                'output': script_item.get('output', '')
                                            })

                                # Store all port details including scripts
                                host_data_for_ui['protocols'][proto][port_int] = {
                                    'state': port_data.get('state', 'unknown'),
                                    'name': port_data.get('name', ''),
                                    'version': port_data.get('version', ''),
                                    'product': port_data.get('product', ''),
                                    'extrainfo': port_data.get('extrainfo', ''),
                                    'cpe': port_data.get('cpe', ''),
                                    'script': port_script_output
                                }
                            except (ValueError, TypeError):
                                self._on_output(f"[Warning] Skipping invalid port number format for host {host_ip}, proto {proto}, port '{port_str}'")
                                continue

                # Store the processed data for this host
                parsed_results[host_ip] = host_data_for_ui
        else:
            # Handle cases like ping scan where 'scan' might be empty
            if 'nmap' in scan_data and 'hosts' in scan_data['nmap']:
                num_hosts = scan_data['nmap']['hosts'].get('up', 0)
                total_hosts = scan_data['nmap']['hosts'].get('total', 0)
                self._on_output(f"Scan data indicates {num_hosts} host(s) up out of {total_hosts} scanned (no port details).")
            else:
                self._on_output("No hosts found in scan data or scan data structure invalid.")

        return parsed_results

    def stop(self):
        """
        Request the thread to stop scanning by terminating the Nmap process.
        Also cleans up the temporary file associated with this thread.
        """
        self._on_output("Stop signal received...")
        self._is_running = False

        # --- Terminate Process ---
        if self.nmap_process and self.nmap_process.poll() is None:
            pid_to_terminate = self.nmap_process.pid
            self._on_output(f"Attempting to terminate Nmap process (PID: {pid_to_terminate})...")
            try:
                # Use psutil to find the process and its children
                parent = psutil.Process(pid_to_terminate)
                children = parent.children(recursive=True)

                # Terminate children first
                for child in children:
                    try:
                        self._on_output(f"Terminating child process (PID: {child.pid})...")
                        child.terminate()
                    except psutil.NoSuchProcess:
                        self._on_output(f"Child process (PID: {child.pid}) already exited.")
                        continue
                    except Exception as child_term_err:
                        self._on_output(f"Error terminating child process {child.pid}: {child_term_err}")

                # Terminate parent process
                self._on_output(f"Terminating main Nmap process (PID: {pid_to_terminate})...")
                parent.terminate()

                # Wait briefly for termination
                try:
                    gone, alive = psutil.wait_procs([parent] + children, timeout=2)
                    for p in gone:
                        self._on_output(f"Process {p.pid} terminated.")

                    # If any are still alive, kill them forcefully
                    if alive:
                        self._on_output(f"Processes {[p.pid for p in alive]} did not terminate gracefully. Killing...")
                        for p in alive:
                            try:
                                p.kill()
                                self._on_output(f"Process {p.pid} killed.")
                            except psutil.NoSuchProcess:
                                self._on_output(f"Process {p.pid} already exited before kill.")
                            except Exception as kill_err:
                                self._on_output(f"Error killing process {p.pid}: {kill_err}")
                except Exception as wait_err:
                    self._on_output(f"Error waiting for process termination: {wait_err}")
                    # Fallback kill
                    try:
                        if parent.is_running():
                            parent.kill()
                        for child in children:
                            if child.is_running():
                                child.kill()
                    except:
                        pass

            except psutil.NoSuchProcess:
                self._on_output(f"Nmap process (PID: {pid_to_terminate}) already finished or could not be found.")
            except Exception as e:
                self._on_output(f"Error trying to terminate Nmap process: {e}")
        else:
            self._on_output("No active Nmap process found to stop.")

        # --- Clean up temp file if stopped ---
        self._cleanup_temp_file()


class ParallelNmapScanner(threading.Thread):
    """
    Multi-threaded Nmap scanner that discovers live hosts first, then scans them in parallel.

    This scanner optimizes scanning performance by:
    1. Running a fast discovery scan (-sn) to identify live hosts
    2. Dividing discovered hosts among worker threads
    3. Each worker performs a full scan on its assigned hosts
    4. Aggregating results from all workers

    Uses the same callback interface as NmapScanner for compatibility.
    """

    def __init__(
        self,
        target: str,
        arguments: str,
        max_workers: int = 5,
        on_output: Optional[Callable[[str], None]] = None,
        on_results: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_finished: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_host_result: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the parallel scanner with callbacks.

        Args:
            target: The target network/range for scanning (e.g., "192.168.1.0/24")
            arguments: Nmap arguments for the full scan (discovery will use -sn)
            max_workers: Maximum number of parallel scanner threads (default: 5)
            on_output: Callback for live output text
            on_results: Callback for aggregated parsed results
            on_finished: Callback for completion (message, xml_path)
            on_error: Callback for errors
            on_progress: Callback for progress updates (current, total)
            on_host_result: Callback for individual host results (called as each host completes)
        """
        super().__init__(daemon=True)
        self.target = target
        self.scan_arguments = arguments
        self.max_workers = max_workers
        self._is_running = True
        self._scanners: List[NmapScanner] = []
        self._executor: Optional[ThreadPoolExecutor] = None

        # Store callbacks
        self._on_output = on_output or (lambda x: None)
        self._on_results = on_results or (lambda x: None)
        self._on_finished = on_finished or (lambda x, y: None)
        self._on_error = on_error or (lambda x: None)
        self._on_progress = on_progress or (lambda x, y: None)
        self._on_host_result = on_host_result or (lambda x: None)

    def _discover_live_hosts(self) -> List[str]:
        """
        Run a fast ping scan to discover live hosts in the target range.

        Returns:
            List of live host IP addresses
        """
        live_hosts = []
        discovery_complete = threading.Event()
        discovery_error = threading.Event()

        def on_discovery_output(text: str):
            self._on_output(f"[Discovery] {text}")

        def on_discovery_results(results: Dict[str, Any]):
            nonlocal live_hosts
            # Extract all host IPs that are 'up'
            for host_ip, host_data in results.items():
                if host_data.get('state') == 'up':
                    live_hosts.append(host_ip)
            discovery_complete.set()

        def on_discovery_finished(message: str, xml_path: str):
            self._on_output(f"[Discovery] {message}")
            discovery_complete.set()

        def on_discovery_error(error: str):
            self._on_output(f"[Discovery Error] {error}")
            discovery_error.set()
            discovery_complete.set()

        # Create discovery scanner with -sn (ping scan, no port scan)
        self._on_output(f"Phase 1: Discovering live hosts in {self.target}...")
        discovery_scanner = NmapScanner(
            target=self.target,
            arguments="-sn",  # Ping scan only
            on_output=on_discovery_output,
            on_results=on_discovery_results,
            on_finished=on_discovery_finished,
            on_error=on_discovery_error
        )

        self._scanners.append(discovery_scanner)
        discovery_scanner.start()

        # Wait for discovery to complete (with timeout)
        discovery_complete.wait(timeout=300)  # 5 minute timeout

        if discovery_error.is_set():
            self._on_output("[Discovery] Failed to complete host discovery")
            return []

        if not self._is_running:
            self._on_output("[Discovery] Stopped by user")
            return []

        self._on_output(f"[Discovery] Found {len(live_hosts)} live host(s): {', '.join(live_hosts)}")
        return live_hosts

    def _scan_host(self, host: str, worker_id: int) -> Dict[str, Any]:
        """
        Scan a single host using NmapScanner.

        Args:
            host: IP address to scan
            worker_id: Worker thread identifier

        Returns:
            Parsed results dictionary for this host
        """
        results = {}
        scan_complete = threading.Event()
        scan_error = threading.Event()

        def on_worker_output(text: str):
            self._on_output(f"[Worker-{worker_id}] {text}")

        def on_worker_results(worker_results: Dict[str, Any]):
            nonlocal results
            results = worker_results
            scan_complete.set()

        def on_worker_finished(message: str, xml_path: str):
            self._on_output(f"[Worker-{worker_id}] Completed scan of {host}")
            scan_complete.set()

        def on_worker_error(error: str):
            self._on_output(f"[Worker-{worker_id} Error] {error}")
            scan_error.set()
            scan_complete.set()

        # Create scanner for this host
        scanner = NmapScanner(
            target=host,
            arguments=self.scan_arguments,
            on_output=on_worker_output,
            on_results=on_worker_results,
            on_finished=on_worker_finished,
            on_error=on_worker_error
        )

        self._scanners.append(scanner)
        scanner.start()

        # Wait for scan to complete
        scan_complete.wait(timeout=600)  # 10 minute timeout per host

        if scan_error.is_set() or not self._is_running:
            return {}

        return results

    def run(self):
        """
        Main execution method: discover hosts, then scan them in parallel.
        """
        try:
            # Phase 1: Discovery
            live_hosts = self._discover_live_hosts()

            if not live_hosts:
                self._on_output("No live hosts found. Scan complete.")
                self._on_results({})
                self._on_finished("Scan complete (no live hosts)", "")
                return

            if not self._is_running:
                self._on_error("Scan stopped during discovery phase")
                return

            # Phase 2: Parallel scanning
            self._on_output(f"\nPhase 2: Scanning {len(live_hosts)} live host(s) using {self.max_workers} workers...")
            aggregated_results = {}
            completed_count = 0
            total_hosts = len(live_hosts)

            # Use ThreadPoolExecutor for parallel scanning
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

            # Submit all host scans
            future_to_host = {
                self._executor.submit(self._scan_host, host, idx + 1): host
                for idx, host in enumerate(live_hosts)
            }

            # Process results as they complete
            for future in as_completed(future_to_host):
                if not self._is_running:
                    self._on_output("Scan stopped by user")
                    break

                host = future_to_host[future]
                try:
                    host_results = future.result()
                    if host_results:
                        aggregated_results.update(host_results)
                        # Emit incremental host result
                        self._on_host_result(host_results)

                    completed_count += 1
                    self._on_progress(completed_count, total_hosts)
                    self._on_output(f"Progress: {completed_count}/{total_hosts} hosts scanned")

                except Exception as e:
                    self._on_output(f"Error scanning host {host}: {e}")

            # Shutdown executor
            self._executor.shutdown(wait=True)

            if not self._is_running:
                self._on_error("Scan stopped by user")
                return

            # Emit final results
            self._on_output(f"\nScan complete! Scanned {len(aggregated_results)} host(s)")
            self._on_results(aggregated_results)
            self._on_finished(
                f"Parallel scan complete: {len(aggregated_results)} host(s) scanned",
                ""  # No single XML file for parallel scans
            )

        except Exception as e:
            if self._is_running:
                self._on_error(f"Parallel scan failed: {e}")
            self._is_running = False

    def stop(self):
        """
        Stop the parallel scan by terminating all worker scanners.
        """
        self._on_output("Stopping parallel scan...")
        self._is_running = False

        # Stop all active scanners
        for scanner in self._scanners:
            if scanner.is_alive():
                scanner.stop()

        # Shutdown executor if running
        if self._executor:
            self._executor.shutdown(wait=False)

        self._on_output("Parallel scan stopped")
