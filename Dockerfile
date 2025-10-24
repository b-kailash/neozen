# NeoZen Docker Container - Minimal Build
# A lightweight containerized version of NeoZen with Nmap and X11 support

FROM python:3.11-slim

LABEL maintainer="NeoZen Contributors"
LABEL description="NeoZen - Modern Nmap GUI (minimal container)"
LABEL version="0.1.0"

# Set display for X11 forwarding
ENV DISPLAY=:0 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Install only essential dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    libxcb1 \
    libxkbcommon-x11-0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libdbus-1-3 \
    libegl1 \
    libgl1 \
    libglib2.0-0 \
    sudo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with minimal setup
RUN useradd -m -u 1000 neozen && \
    echo "neozen ALL=(ALL) NOPASSWD: /usr/bin/nmap" > /etc/sudoers.d/neozen && \
    chmod 0440 /etc/sudoers.d/neozen

WORKDIR /app

# Copy only necessary files
COPY --chown=neozen:neozen requirements.txt pyproject.toml ./
COPY --chown=neozen:neozen neozen/ ./neozen/
COPY --chown=neozen:neozen main.py ./

USER neozen

# Install Python dependencies without cache
RUN pip install --no-cache-dir --user -e .

# Add user pip binaries to PATH
ENV PATH="/home/neozen/.local/bin:$PATH"

# Health check - lightweight
HEALTHCHECK --interval=60s --timeout=5s --start-period=5s --retries=2 \
    CMD nmap --version > /dev/null || exit 1

# Default command
CMD ["python3", "main.py"]
