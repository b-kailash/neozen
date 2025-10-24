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

from neozen.core.scanner import Scanner
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
    """Start a new Nmap scan"""
    global current_scanner, scan_output, scan_results

    data = request.json
    target = data.get('target')
    arguments = data.get('arguments', '')

    if not target:
        return jsonify({'error': 'Target is required'}), 400

    with scan_lock:
        if current_scanner and current_scanner.isRunning():
            return jsonify({'error': 'A scan is already running'}), 409

        # Clear previous scan data
        scan_output = []
        scan_results = {}

        # Create and configure scanner
        current_scanner = Scanner(target, arguments)
        current_scanner.scan_output.connect(handle_scan_output)
        current_scanner.scan_results_ready.connect(handle_scan_results)
        current_scanner.scan_finished.connect(handle_scan_finished)
        current_scanner.scan_error.connect(handle_scan_error)

        # Start scan
        current_scanner.start()

        # Notify clients
        socketio.emit('scan_started', {'target': target, 'arguments': arguments})

        return jsonify({'success': True, 'message': 'Scan started'})


@app.route('/api/scan/stop', methods=['POST'])
def stop_scan():
    """Stop the current scan"""
    global current_scanner

    with scan_lock:
        if current_scanner and current_scanner.isRunning():
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
        is_running = current_scanner and current_scanner.isRunning()
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


# --- Signal Handlers ---

def handle_scan_output(text):
    """Handle scan output from Scanner"""
    global scan_output
    scan_output.append(text)
    socketio.emit('scan_output', {'text': text})


def handle_scan_results(results):
    """Handle scan results from Scanner"""
    global scan_results
    scan_results = results
    socketio.emit('scan_results', {'results': results})


def handle_scan_finished(message, temp_xml_path):
    """Handle scan completion"""
    socketio.emit('scan_finished', {
        'message': message,
        'xml_path': temp_xml_path
    })


def handle_scan_error(error_message):
    """Handle scan errors"""
    socketio.emit('scan_error', {'error': error_message})


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
