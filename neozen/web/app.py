"""
NeoZen Web Application
Flask-based web interface for NeoZen with REST API and WebSocket support
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import json
import os
from pathlib import Path
from datetime import datetime

from neozen.core.profiles import ProfileManager

# Initialize Flask app
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = 'neozen-web-secret-key'

# Enable CORS for API access
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
current_scanner = None
scan_lock = threading.Lock()
profile_manager = ProfileManager()
scan_results = {}
scan_output = []
last_xml_path = None  # Store path to last scan's XML file


# --- Web Routes ---

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """Get all saved scan profiles"""
    profiles = profile_manager.load_profiles()
    return jsonify({'profiles': profiles})


@app.route('/api/profiles', methods=['POST'])
def save_profile():
    """Save a new scan profile"""
    data = request.json
    profile_name = data.get('name')
    target = data.get('target')
    arguments = data.get('arguments')

    if not profile_name or not target:
        return jsonify({'error': 'Profile name and target are required'}), 400

    profiles = profile_manager.load_profiles()
    profiles[profile_name] = {'target': target, 'arguments': arguments}

    if profile_manager.save_profiles(profiles):
        return jsonify({'success': True, 'message': f'Profile "{profile_name}" saved'})
    else:
        return jsonify({'error': 'Failed to save profile'}), 500


@app.route('/api/profiles/<profile_name>', methods=['DELETE'])
def delete_profile(profile_name):
    """Delete a scan profile"""
    profiles = profile_manager.load_profiles()

    if profile_name in profiles:
        del profiles[profile_name]
        if profile_manager.save_profiles(profiles):
            return jsonify({'success': True, 'message': f'Profile "{profile_name}" deleted'})
        else:
            return jsonify({'error': 'Failed to delete profile'}), 500
    else:
        return jsonify({'error': 'Profile not found'}), 404


@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Start a new Nmap scan (supports both standard and parallel scanning)"""
    global current_scanner, scan_output, scan_results

    data = request.json
    target = data.get('target')
    arguments = data.get('arguments', '')
    parallel = data.get('parallel', False)  # Enable parallel scanning
    max_workers = data.get('max_workers', 5)  # Number of parallel workers

    if not target:
        return jsonify({'error': 'Target is required'}), 400

    with scan_lock:
        if current_scanner and current_scanner.is_alive():
            return jsonify({'error': 'A scan is already running'}), 409

        # Clear previous scan data
        scan_output = []
        scan_results = {}

        # Create core scanner with custom callbacks for state management + SocketIO
        from neozen.core.scanner_core import NmapScanner, ParallelNmapScanner

        def on_output_callback(text):
            """Handle output: update state and emit SocketIO event"""
            scan_output.append(text)
            socketio.emit('scan_output', {'text': text})

        def on_results_callback(results):
            """Handle results: update state and emit SocketIO event"""
            global scan_results
            scan_results = results
            socketio.emit('scan_results', {'results': results})

        def on_finished_callback(message, xml_path):
            """Handle completion: store XML path and emit SocketIO event"""
            global last_xml_path
            last_xml_path = xml_path
            print(f"[DEBUG] on_finished_callback called with xml_path: {xml_path}")
            print(f"[DEBUG] File exists: {os.path.exists(xml_path) if xml_path else False}")
            socketio.emit('scan_finished', {'message': message, 'xml_path': xml_path})

        def on_error_callback(error):
            """Handle errors: emit SocketIO event"""
            socketio.emit('scan_error', {'error': error})

        def on_progress_callback(current, total):
            """Handle progress updates (parallel scanning only): emit SocketIO event"""
            socketio.emit('scan_progress', {'current': current, 'total': total})

        # Create scanner with custom callbacks (parallel or standard)
        if parallel:
            current_scanner = ParallelNmapScanner(
                target, arguments,
                max_workers=max_workers,
                on_output=on_output_callback,
                on_results=on_results_callback,
                on_finished=on_finished_callback,
                on_error=on_error_callback,
                on_progress=on_progress_callback
            )
        else:
            current_scanner = NmapScanner(
                target, arguments,
                on_output=on_output_callback,
                on_results=on_results_callback,
                on_finished=on_finished_callback,
                on_error=on_error_callback
            )

        # Start scan
        current_scanner.start()

        # Notify clients
        scan_mode = 'parallel' if parallel else 'standard'
        socketio.emit('scan_started', {
            'target': target,
            'arguments': arguments,
            'mode': scan_mode,
            'max_workers': max_workers if parallel else None
        })

        return jsonify({
            'success': True,
            'message': f'{scan_mode.capitalize()} scan started',
            'mode': scan_mode
        })


@app.route('/api/scan/stop', methods=['POST'])
def stop_scan():
    """Stop the current scan"""
    global current_scanner

    with scan_lock:
        if current_scanner and current_scanner.is_alive():
            current_scanner.stop()
            socketio.emit('scan_stopped', {})
            return jsonify({'success': True, 'message': 'Scan stopped'})
        else:
            return jsonify({'error': 'No scan is running'}), 400


@app.route('/api/scan/status', methods=['GET'])
def scan_status():
    """Get current scan status"""
    global current_scanner

    with scan_lock:
        is_running = current_scanner and current_scanner.is_alive()
        return jsonify({
            'running': is_running,
            'output_lines': len(scan_output),
            'results_count': len(scan_results)
        })


@app.route('/api/scan/output', methods=['GET'])
def get_scan_output():
    """Get current scan output"""
    return jsonify({'output': scan_output})


@app.route('/api/scan/results', methods=['GET'])
def get_scan_results():
    """Get current scan results"""
    return jsonify({'results': scan_results})


@app.route('/api/scan/download-xml', methods=['GET'])
def download_xml():
    """Download the results file from the last scan (XML or JSON for parallel scans)"""
    global last_xml_path

    print(f"[DEBUG] download_xml called, last_xml_path: {last_xml_path}")

    if not last_xml_path:
        return jsonify({'error': 'No scan results available. Please run a scan first.'}), 404

    if not os.path.exists(last_xml_path):
        print(f"[DEBUG] File does not exist at path: {last_xml_path}")
        return jsonify({'error': f'Scan results file not found at: {last_xml_path}'}), 404

    from flask import send_file
    import time

    # Generate filename with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')

    # Check if it's JSON (parallel scan) or XML (regular scan)
    if last_xml_path.endswith('.json'):
        filename = f'neozen_parallel_scan_{timestamp}.json'
        mimetype = 'application/json'
    else:
        filename = f'neozen_scan_{timestamp}.xml'
        mimetype = 'application/xml'

    return send_file(
        last_xml_path,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )


@app.route('/api/scan/export-csv', methods=['GET'])
def export_csv():
    """Export scan results to CSV"""
    global scan_results

    if not scan_results or len(scan_results) == 0:
        return jsonify({'error': 'No scan results available'}), 404

    import csv
    import io
    import time
    from flask import send_file

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Host', 'MAC Address', 'Protocol', 'Port', 'State', 'Service', 'Product', 'Version'])

    # Track unique rows to avoid duplicates
    exported_rows = set()

    # Write data
    for host, host_data in scan_results.items():
        hostname = host_data.get('hostname', '')
        display_host = f"{hostname} ({host})" if hostname and hostname != host else host
        mac_address = host_data.get('mac', '')
        vendor = host_data.get('vendor', '')
        mac_display = f"{mac_address} ({vendor})" if mac_address and vendor else mac_address
        protocols = host_data.get('protocols', {})

        if not protocols:
            # Host with no ports
            row = (display_host, mac_display, '', '', host_data.get('state', 'unknown'), '(No ports found)', '', '')
            if row not in exported_rows:
                writer.writerow(row)
                exported_rows.add(row)
        else:
            # Host with ports
            for proto, ports in protocols.items():
                for port, port_data in ports.items():
                    row = (
                        display_host,
                        mac_display,
                        proto,
                        port,
                        port_data.get('state', ''),
                        port_data.get('name', ''),
                        port_data.get('product', ''),
                        port_data.get('version', '')
                    )
                    if row not in exported_rows:
                        writer.writerow(row)
                        exported_rows.add(row)

    # Generate filename with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f'neozen_scan_export_{timestamp}.csv'

    # Convert to bytes
    output.seek(0)
    bytes_output = io.BytesIO(output.getvalue().encode('utf-8'))
    bytes_output.seek(0)

    return send_file(
        bytes_output,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )


# --- WebSocket Events ---

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to NeoZen server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')


# --- Application Factory ---

def create_app():
    """Create and configure the Flask application"""
    return app


def run_server(host='0.0.0.0', port=8080, debug=False):
    """Run the web server"""
    print(f"Starting NeoZen Web Server on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server(debug=True)
