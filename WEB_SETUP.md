# NeoZen Web Dashboard - Setup Guide

**Complete instructions for deploying the NeoZen web interface**

---

## Table of Contents

1. [Quick Start (Docker)](#quick-start-docker)
2. [Docker Deployment](#docker-deployment)
3. [Manual Python Installation](#manual-python-installation)
4. [Production Deployment](#production-deployment)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Quick Start (Docker)

**The fastest way to get NeoZen running:**

```bash
# Clone the repository
git clone https://github.com/yourusername/neozen.git
cd neozen

# Start the web interface
docker-compose --profile web up -d
```

**Access the interface:**
- **From the same machine:** http://localhost:8080
- **From other devices on your network:** http://YOUR_SERVER_IP:8080

**Default credentials:**
- Username: `admin`
- Password: `admin`

⚠️ **Change the default password immediately after first login!**

**To stop:**
```bash
docker-compose --profile web down
```

---

## Docker Deployment

### Prerequisites

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 1.29+ (included with Docker Desktop)
- **Nmap** (installed automatically in container)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/neozen.git
cd neozen
```

### Step 2: Review Configuration

The default configuration works for most users. Optional configurations:

**Environment Variables** (create `.env` file):
```bash
# Secret key for session management (recommended for production)
SECRET_KEY=your-secure-random-key-here

# Database URL (default: SQLite in /app/data)
DATABASE_URL=sqlite:////app/data/neozen.db

# Or use PostgreSQL for production
# DATABASE_URL=postgresql://user:password@localhost/neozen
```

**Generate a secure secret key:**
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Step 3: Start the Container

```bash
# Start in detached mode (runs in background)
docker-compose --profile web up -d

# Or start with logs visible (for debugging)
docker-compose --profile web up
```

### Step 4: Verify Deployment

**Check container status:**
```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
neozen-web-1        "python -m neozen.we…"   neozen-web          running             0.0.0.0:8080->8080/tcp
```

**View logs:**
```bash
docker-compose logs -f neozen-web
```

### Step 5: Access the Interface

**Find your server's IP address:**

**Linux/macOS:**
```bash
hostname -I | awk '{print $1}'
```

**Windows:**
```powershell
ipconfig | findstr IPv4
```

**Access URLs:**
- Local: http://localhost:8080
- Network: http://YOUR_SERVER_IP:8080

### Step 6: Login and Change Password

1. Open browser to http://localhost:8080
2. Login with default credentials (`admin` / `admin`)
3. **Important:** Change the default password immediately
   - Currently requires direct database access (see [Security Best Practices](#security-best-practices))
   - User management UI coming in future release

### Managing the Container

**Stop the container:**
```bash
docker-compose --profile web down
```

**Restart the container:**
```bash
docker-compose --profile web restart
```

**Update to latest version:**
```bash
git pull
docker-compose --profile web down
docker-compose --profile web up -d --build
```

**View resource usage:**
```bash
docker stats neozen-web-1
```

**Access container shell:**
```bash
docker exec -it neozen-web-1 bash
```

---

## Manual Python Installation

### Prerequisites

- **Python** 3.7 or higher
- **Nmap** installed and in PATH
- **sudo** access for privileged scans (OS detection, SYN scans)

### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nmap python3 python3-pip python3-venv
```

**Fedora/RHEL/CentOS:**
```bash
sudo dnf install nmap python3 python3-pip
```

**macOS (with Homebrew):**
```bash
brew install nmap python3
```

**Windows:**
1. Download Nmap from https://nmap.org/download.html
2. Install Python from https://python.org/downloads/
3. Ensure both are in system PATH

### Step 2: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/neozen.git
cd neozen

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows
```

### Step 3: Install Dependencies

**Web interface only (minimal):**
```bash
pip install -e ".[web]"
```

**Or install from requirements:**
```bash
pip install flask>=2.3.0 flask-socketio>=5.3.0 flask-cors>=4.0.0 \
    python-socketio>=5.9.0 flask-sqlalchemy>=3.0.0 flask-login>=0.6.0 \
    python-nmap>=0.7.1 psutil>=5.9.0
```

### Step 4: Configure Sudoers (Linux/macOS)

For privileged scans (OS detection, SYN scans), configure passwordless sudo for nmap:

```bash
# Edit sudoers file (use visudo for safety)
sudo visudo

# Add this line (replace 'yourusername' with your username)
yourusername ALL=(root) NOPASSWD: /usr/bin/nmap
```

**Verify:**
```bash
sudo -n nmap --version
# Should run without prompting for password
```

### Step 5: Run the Web Server

```bash
# From the neozen directory with venv activated
python -m neozen.web.app
```

**The server will start on http://0.0.0.0:8080**

**Alternative: Use Flask development server:**
```bash
export FLASK_APP=neozen.web.app
flask run --host=0.0.0.0 --port=8080
```

### Step 6: Run as a Service (Optional)

**Create systemd service (Linux):**

```bash
sudo nano /etc/systemd/system/neozen-web.service
```

**Service file content:**
```ini
[Unit]
Description=NeoZen Web Dashboard
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/neozen
Environment="PATH=/path/to/neozen/venv/bin"
ExecStart=/path/to/neozen/venv/bin/python -m neozen.web.app
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable neozen-web
sudo systemctl start neozen-web
sudo systemctl status neozen-web
```

---

## Production Deployment

### Using Nginx Reverse Proxy with SSL

**1. Install Nginx and Certbot:**
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

**2. Configure Nginx:**
```bash
sudo nano /etc/nginx/sites-available/neozen
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

**3. Enable site and get SSL certificate:**
```bash
sudo ln -s /etc/nginx/sites-available/neozen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate (follow prompts)
sudo certbot --nginx -d your-domain.com
```

### Using PostgreSQL Database

**1. Install PostgreSQL:**
```bash
sudo apt install postgresql postgresql-contrib
```

**2. Create database and user:**
```bash
sudo -u postgres psql

CREATE DATABASE neozen;
CREATE USER neozen WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE neozen TO neozen;
\q
```

**3. Install Python PostgreSQL driver:**
```bash
pip install psycopg2-binary
```

**4. Configure environment variable:**
```bash
export DATABASE_URL="postgresql://neozen:your-secure-password@localhost/neozen"
```

Or in Docker `.env` file:
```
DATABASE_URL=postgresql://neozen:your-secure-password@postgres:5432/neozen
```

### Using Gunicorn (Production WSGI Server)

**1. Install Gunicorn:**
```bash
pip install gunicorn eventlet
```

**2. Run with Gunicorn:**
```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8080 neozen.web.app:app
```

**Note:** SocketIO requires eventlet worker and single worker (`-w 1`)

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Auto-generated | Flask secret key for sessions (set for production!) |
| `DATABASE_URL` | `sqlite:///neozen.db` | Database connection string |
| `FLASK_ENV` | `production` | Flask environment (`development` or `production`) |
| `FLASK_DEBUG` | `False` | Enable debug mode (DO NOT use in production) |

### Database Configuration

**SQLite (Default):**
```bash
DATABASE_URL=sqlite:///neozen.db  # Relative path
DATABASE_URL=sqlite:////app/data/neozen.db  # Absolute path
```

**PostgreSQL:**
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

**MySQL:**
```bash
DATABASE_URL=mysql://user:password@host:port/database
```

### Docker Volumes

By default, the Docker setup persists data in a named volume:

```yaml
volumes:
  neozen-data:  # Stores database and scan results
```

**To use a host directory instead:**

Edit `docker-compose.yml`:
```yaml
services:
  neozen-web:
    volumes:
      - ./data:/app/data  # Use local ./data directory
```

### Network Configuration

**Change port (Docker):**

Edit `docker-compose.yml`:
```yaml
ports:
  - "8888:8080"  # Maps host port 8888 to container port 8080
```

**Change port (Manual):**
```bash
python -m neozen.web.app --port 8888
```

Or in code (`neozen/web/app.py`):
```python
run_server(host='0.0.0.0', port=8888)
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs neozen-web
```

**Common issues:**
- Port 8080 already in use → Change port in `docker-compose.yml`
- Permission denied → Run with `sudo` or add user to docker group
- Image build failed → Check Docker installation and network

### Database Errors

**"No such table" errors:**
```bash
# Delete database and restart (WARNING: loses all data)
docker-compose down -v
docker-compose --profile web up -d
```

**Database locked:**
- SQLite doesn't support high concurrency
- Use PostgreSQL for production with multiple users

### Nmap Permission Errors

**In Docker:**
- Should work automatically (sudoers configured)
- Check logs: `docker-compose logs neozen-web`

**Manual installation:**
- Verify sudoers configuration: `sudo -n nmap --version`
- Ensure nmap path is correct: `which nmap`

### WebSocket Connection Issues

**Symptoms:** No real-time updates, "Disconnected" status

**Solutions:**
1. Check reverse proxy configuration (WebSocket support)
2. Verify firewall allows connections
3. Check browser console for errors (F12)
4. Try different browser (clear cache)

### Can't Access from Other Devices

**Check server IP:**
```bash
hostname -I  # Linux/macOS
ipconfig     # Windows
```

**Check firewall:**
```bash
# Linux (UFW)
sudo ufw allow 8080/tcp
sudo ufw status

# Linux (iptables)
sudo iptables -L -n | grep 8080
```

**Verify container binding:**
```bash
docker-compose ps
# Should show "0.0.0.0:8080->8080/tcp"
```

### High Memory Usage

**Limit Docker memory:**

Edit `docker-compose.yml`:
```yaml
services:
  neozen-web:
    deploy:
      resources:
        limits:
          memory: 512M
```

---

## Security Best Practices

### 1. Change Default Credentials

**Using Python shell:**
```bash
docker exec -it neozen-web-1 python3

>>> from neozen.web.models import db, User
>>> from neozen.web.app import app
>>> with app.app_context():
...     admin = User.query.filter_by(username='admin').first()
...     admin.set_password('your-new-secure-password')
...     db.session.commit()
>>> exit()
```

### 2. Use Strong Secret Key

**Generate secure key:**
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

**Set in environment or `.env` file:**
```bash
SECRET_KEY=your-generated-key-here
```

### 3. Enable HTTPS

**Never expose HTTP in production!** Use:
- Nginx/Apache reverse proxy with Let's Encrypt SSL
- Caddy (automatic HTTPS)
- Cloud load balancer with SSL termination

### 4. Restrict Network Access

**Firewall rules (allow specific IPs only):**
```bash
# Allow from specific network
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Block all other
sudo ufw default deny incoming
```

**Or use SSH tunnel for remote access:**
```bash
# On client machine
ssh -L 8080:localhost:8080 user@server
# Then access http://localhost:8080
```

### 5. Regular Updates

```bash
# Update container
git pull
docker-compose --profile web down
docker-compose --profile web up -d --build

# Update Python installation
git pull
source venv/bin/activate
pip install -e ".[web]" --upgrade
```

### 6. Database Backups

**SQLite:**
```bash
# Backup
docker cp neozen-web-1:/app/data/neozen.db ./backup-$(date +%Y%m%d).db

# Restore
docker cp ./backup.db neozen-web-1:/app/data/neozen.db
docker-compose restart neozen-web
```

**PostgreSQL:**
```bash
# Backup
pg_dump -U neozen -h localhost neozen > backup.sql

# Restore
psql -U neozen -h localhost neozen < backup.sql
```

### 7. Monitor Logs

**Docker:**
```bash
docker-compose logs -f --tail=100 neozen-web
```

**Systemd service:**
```bash
sudo journalctl -u neozen-web -f
```

### 8. Limit User Permissions

- Create separate users for different teams
- Implement role-based access control (future feature)
- Audit scan history regularly

### 9. Use Read-Only Filesystem (Advanced)

For extra security, run container with read-only root filesystem:

```yaml
services:
  neozen-web:
    read_only: true
    tmpfs:
      - /tmp
      - /app/instance
```

### 10. Network Isolation

**Restrict Docker network:**
```yaml
services:
  neozen-web:
    networks:
      - internal

networks:
  internal:
    internal: true  # No external access
```

---

## Additional Resources

- **Main README:** [README.md](README.md)
- **Architecture Documentation:** [CLAUDE.md](CLAUDE.md)
- **Issue Tracker:** https://github.com/yourusername/neozen/issues
- **Nmap Documentation:** https://nmap.org/book/man.html
- **Flask Documentation:** https://flask.palletsprojects.com/
- **Docker Documentation:** https://docs.docker.com/

---

## Getting Help

**Having issues?**

1. Check logs: `docker-compose logs neozen-web`
2. Review [Troubleshooting](#troubleshooting) section
3. Search existing issues: https://github.com/yourusername/neozen/issues
4. Create new issue with:
   - OS and version
   - Docker version (`docker --version`)
   - Complete error logs
   - Steps to reproduce

**Security issues:** Please email security@yourdomain.com instead of creating public issues.
