"""
NeoZen Web Application
Flask-based web interface for NeoZen with REST API and WebSocket support
Multi-user support with authentication and scan history
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import threading
import json
import os
from pathlib import Path
from datetime import datetime

from neozen.core.profiles import ProfileManager
from neozen.web.models import db, User, Scan, DeviceNote, init_db

# Initialize Flask app
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'neozen-web-secret-key-change-in-production')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///neozen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_db(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

# Enable CORS for API access
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Per-user scan management
class ScanSession:
    """Manages a single user's scan session"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.scanner = None
        self.scan_results = {}
        self.scan_output = []
        self.last_xml_path = None
        self.scan_db_id = None
        self.lock = threading.Lock()

# Global scan manager: user_id -> ScanSession
user_sessions = {}
sessions_lock = threading.Lock()

def get_user_session(user_id):
    """Get or create a scan session for a user"""
    with sessions_lock:
        if user_id not in user_sessions:
            user_sessions[user_id] = ScanSession(user_id)
        return user_sessions[user_id]

# Profile manager (still global but user-agnostic)
profile_manager = ProfileManager()


# --- Web Routes ---

@app.route('/login')
def login_page():
    """Serve the login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and create session"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        })
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/current-user', methods=['GET'])
def current_user_info():
    """Get current authenticated user info"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'is_admin': current_user.is_admin
            }
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/')
@login_required
def index():
    """Serve the main web interface"""
    return render_template('index.html', user=current_user)


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
@login_required
def start_scan():
    """Start a new Nmap scan (supports both standard and parallel scanning)"""
    user_session = get_user_session(current_user.id)

    data = request.json
    target = data.get('target')
    arguments = data.get('arguments', '')
    parallel = data.get('parallel', False)  # Enable parallel scanning
    max_workers = data.get('max_workers', 5)  # Number of parallel workers

    if not target:
        return jsonify({'error': 'Target is required'}), 400

    with user_session.lock:
        if user_session.scanner and user_session.scanner.is_alive():
            return jsonify({'error': 'A scan is already running'}), 409

        # Clear previous scan data
        user_session.scan_output = []
        user_session.scan_results = {}

        # Create scan record in database
        scan_record = Scan(
            user_id=current_user.id,
            target=target,
            arguments=arguments,
            parallel=parallel,
            max_workers=max_workers,
            status='running'
        )
        db.session.add(scan_record)
        db.session.commit()
        user_session.scan_db_id = scan_record.id

        # Get user's SocketIO room
        user_room = f"user_{current_user.id}"

        # Create core scanner with custom callbacks for state management + SocketIO
        from neozen.core.scanner_core import NmapScanner, ParallelNmapScanner

        def on_output_callback(text):
            """Handle output: update state and emit SocketIO event to user's room"""
            user_session.scan_output.append(text)
            socketio.emit('scan_output', {'text': text}, room=user_room)

        def on_results_callback(results):
            """Handle results: update state and emit SocketIO event to user's room"""
            user_session.scan_results = results
            socketio.emit('scan_results', {'results': results}, room=user_room)

        def on_finished_callback(message, xml_path):
            """Handle completion: store XML path, update DB, and emit SocketIO event to user's room"""
            user_session.last_xml_path = xml_path
            print(f"[DEBUG] on_finished_callback called with xml_path: {xml_path}")
            print(f"[DEBUG] File exists: {os.path.exists(xml_path) if xml_path else False}")

            # Update scan record in database
            scan_record = Scan.query.get(user_session.scan_db_id)
            if scan_record:
                scan_record.status = 'completed'
                scan_record.completed_at = datetime.utcnow()
                scan_record.results_path = xml_path
                scan_record.results_count = len(user_session.scan_results)
                db.session.commit()

            socketio.emit('scan_finished', {'message': message, 'xml_path': xml_path}, room=user_room)

        def on_error_callback(error):
            """Handle errors: update DB and emit SocketIO event to user's room"""
            # Update scan record in database
            scan_record = Scan.query.get(user_session.scan_db_id)
            if scan_record:
                scan_record.status = 'failed'
                scan_record.completed_at = datetime.utcnow()
                scan_record.error_message = str(error)
                db.session.commit()

            socketio.emit('scan_error', {'error': error}, room=user_room)

        def on_progress_callback(current, total):
            """Handle progress updates (parallel scanning only): emit SocketIO event to user's room"""
            socketio.emit('scan_progress', {'current': current, 'total': total}, room=user_room)

        # Create scanner with custom callbacks (parallel or standard)
        if parallel:
            user_session.scanner = ParallelNmapScanner(
                target, arguments,
                max_workers=max_workers,
                on_output=on_output_callback,
                on_results=on_results_callback,
                on_finished=on_finished_callback,
                on_error=on_error_callback,
                on_progress=on_progress_callback
            )
        else:
            user_session.scanner = NmapScanner(
                target, arguments,
                on_output=on_output_callback,
                on_results=on_results_callback,
                on_finished=on_finished_callback,
                on_error=on_error_callback
            )

        # Start scan
        user_session.scanner.start()

        # Notify client in their room
        scan_mode = 'parallel' if parallel else 'standard'
        socketio.emit('scan_started', {
            'target': target,
            'arguments': arguments,
            'mode': scan_mode,
            'max_workers': max_workers if parallel else None
        }, room=user_room)

        return jsonify({
            'success': True,
            'message': f'{scan_mode.capitalize()} scan started',
            'mode': scan_mode,
            'scan_id': scan_record.id
        })


@app.route('/api/scan/stop', methods=['POST'])
@login_required
def stop_scan():
    """Stop the current scan"""
    user_session = get_user_session(current_user.id)
    user_room = f"user_{current_user.id}"

    with user_session.lock:
        if user_session.scanner and user_session.scanner.is_alive():
            user_session.scanner.stop()

            # Update scan record in database
            if user_session.scan_db_id:
                scan_record = Scan.query.get(user_session.scan_db_id)
                if scan_record:
                    scan_record.status = 'stopped'
                    scan_record.completed_at = datetime.utcnow()
                    db.session.commit()

            socketio.emit('scan_stopped', {}, room=user_room)
            return jsonify({'success': True, 'message': 'Scan stopped'})
        else:
            return jsonify({'error': 'No scan is running'}), 400


@app.route('/api/scan/status', methods=['GET'])
@login_required
def scan_status():
    """Get current scan status"""
    user_session = get_user_session(current_user.id)

    with user_session.lock:
        is_running = user_session.scanner and user_session.scanner.is_alive()
        return jsonify({
            'running': is_running,
            'output_lines': len(user_session.scan_output),
            'results_count': len(user_session.scan_results)
        })


@app.route('/api/scan/output', methods=['GET'])
@login_required
def get_scan_output():
    """Get current scan output"""
    user_session = get_user_session(current_user.id)
    return jsonify({'output': user_session.scan_output})


@app.route('/api/scan/results', methods=['GET'])
@login_required
def get_scan_results():
    """Get current scan results"""
    user_session = get_user_session(current_user.id)
    return jsonify({'results': user_session.scan_results})


@app.route('/api/scan/download-xml', methods=['GET'])
@login_required
def download_xml():
    """Download the results file from the last scan (XML or JSON for parallel scans)"""
    user_session = get_user_session(current_user.id)

    print(f"[DEBUG] download_xml called, last_xml_path: {user_session.last_xml_path}")

    if not user_session.last_xml_path:
        return jsonify({'error': 'No scan results available. Please run a scan first.'}), 404

    if not os.path.exists(user_session.last_xml_path):
        print(f"[DEBUG] File does not exist at path: {user_session.last_xml_path}")
        return jsonify({'error': f'Scan results file not found at: {user_session.last_xml_path}'}), 404

    from flask import send_file
    import time

    # Generate filename with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')

    # Check if it's JSON (parallel scan) or XML (regular scan)
    if user_session.last_xml_path.endswith('.json'):
        filename = f'neozen_parallel_scan_{timestamp}.json'
        mimetype = 'application/json'
    else:
        filename = f'neozen_scan_{timestamp}.xml'
        mimetype = 'application/xml'

    return send_file(
        user_session.last_xml_path,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )


@app.route('/api/scans/history', methods=['GET'])
@login_required
def scan_history():
    """Get scan history for the current user"""
    scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.started_at.desc()).all()
    return jsonify({
        'scans': [scan.to_dict() for scan in scans]
    })

@app.route('/api/scans/<int:scan_id>', methods=['GET'])
@login_required
def get_scan(scan_id):
    """Get details of a specific scan"""
    scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404
    return jsonify({'scan': scan.to_dict()})

@app.route('/api/scans/<int:scan_id>', methods=['DELETE'])
@login_required
def delete_scan(scan_id):
    """Delete a scan from history"""
    scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404

    # Delete the results file if it exists
    if scan.results_path and os.path.exists(scan.results_path):
        try:
            os.remove(scan.results_path)
        except Exception as e:
            print(f"[WARNING] Failed to delete scan results file: {e}")

    db.session.delete(scan)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Scan deleted'})

@app.route('/api/devices/notes', methods=['GET'])
@login_required
def get_all_device_notes():
    """Get all device notes for the current user"""
    notes = DeviceNote.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'notes': {note.host_ip: note.to_dict() for note in notes}
    })

@app.route('/api/devices/<host_ip>/notes', methods=['GET'])
@login_required
def get_device_notes(host_ip):
    """Get notes for a specific device"""
    note = DeviceNote.query.filter_by(user_id=current_user.id, host_ip=host_ip).first()
    if note:
        return jsonify({'note': note.to_dict()})
    else:
        return jsonify({'note': None})

@app.route('/api/devices/<host_ip>/notes', methods=['POST', 'PUT'])
@login_required
def save_device_notes(host_ip):
    """Save or update notes for a device"""
    data = request.json
    notes_text = data.get('notes', '')

    # Find or create device note
    note = DeviceNote.query.filter_by(user_id=current_user.id, host_ip=host_ip).first()
    if note:
        note.notes = notes_text
        note.updated_at = datetime.utcnow()
    else:
        note = DeviceNote(
            user_id=current_user.id,
            host_ip=host_ip,
            notes=notes_text
        )
        db.session.add(note)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Notes saved', 'note': note.to_dict()})

@app.route('/api/devices/<host_ip>/notes', methods=['DELETE'])
@login_required
def delete_device_notes(host_ip):
    """Delete notes for a device"""
    note = DeviceNote.query.filter_by(user_id=current_user.id, host_ip=host_ip).first()
    if note:
        db.session.delete(note)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notes deleted'})
    else:
        return jsonify({'error': 'Notes not found'}), 404

@app.route('/api/scan/export-csv', methods=['GET'])
@login_required
def export_csv():
    """Export scan results to CSV"""
    user_session = get_user_session(current_user.id)

    if not user_session.scan_results or len(user_session.scan_results) == 0:
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
    for host, host_data in user_session.scan_results.items():
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

    # If user is authenticated, join their personal room
    if current_user.is_authenticated:
        user_room = f"user_{current_user.id}"
        join_room(user_room)
        print(f'User {current_user.username} joined room: {user_room}')
        emit('connected', {
            'message': 'Connected to NeoZen server',
            'user': {
                'id': current_user.id,
                'username': current_user.username
            }
        })
    else:
        emit('connected', {'message': 'Connected to NeoZen server (not authenticated)'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        user_room = f"user_{current_user.id}"
        leave_room(user_room)
        print(f'User {current_user.username} left room: {user_room}')
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
