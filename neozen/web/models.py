"""
Database models for NeoZen web application
Multi-user support with authentication and scan history
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    scans = db.relationship('Scan', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notes = db.relationship('DeviceNote', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Scan(db.Model):
    """Scan history model"""
    __tablename__ = 'scans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    target = db.Column(db.String(255), nullable=False)
    arguments = db.Column(db.Text)
    parallel = db.Column(db.Boolean, default=False)
    max_workers = db.Column(db.Integer, default=5)

    # Status: 'queued', 'running', 'completed', 'failed', 'stopped'
    status = db.Column(db.String(20), default='queued', index=True)

    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Results storage
    results_path = db.Column(db.String(500))  # Path to XML/JSON file
    results_count = db.Column(db.Integer, default=0)  # Number of hosts found
    error_message = db.Column(db.Text)

    def __repr__(self):
        return f'<Scan {self.id}: {self.target} ({self.status})>'

    def to_dict(self):
        """Convert scan to dictionary for API responses"""
        return {
            'id': self.id,
            'target': self.target,
            'arguments': self.arguments,
            'parallel': self.parallel,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'results_count': self.results_count,
            'error_message': self.error_message
        }


class DeviceNote(db.Model):
    """Device notes model (per user)"""
    __tablename__ = 'device_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    host_ip = db.Column(db.String(45), nullable=False)  # IPv4 or IPv6
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'host_ip', name='unique_user_host'),
    )

    def __repr__(self):
        return f'<DeviceNote {self.host_ip} by User {self.user_id}>'

    def to_dict(self):
        """Convert note to dictionary for API responses"""
        return {
            'host_ip': self.host_ip,
            'notes': self.notes,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def init_db(app):
    """Initialize the database"""
    db.init_app(app)

    with app.app_context():
        # Create all tables
        db.create_all()

        # Create default admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@neozen.local', is_admin=True)
            admin.set_password('admin')  # Default password - should be changed!
            db.session.add(admin)
            db.session.commit()
            print("[INFO] Created default admin user (username: admin, password: admin)")
            print("[WARNING] Please change the default admin password!")
