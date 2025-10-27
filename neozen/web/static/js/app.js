// NeoZen Web Interface JavaScript

// Configuration
const API_BASE = window.location.origin;
const socket = io(API_BASE);

// State
let isScanning = false;

// DOM Elements
const targetInput = document.getElementById('target');
const profileSelect = document.getElementById('profile');
const scanTypeSelect = document.getElementById('scan-type');
const customArgumentsGroup = document.getElementById('custom-arguments-group');
const argumentsInput = document.getElementById('arguments');
const osDetectionCheckbox = document.getElementById('os-detection');
const serviceDetectionCheckbox = document.getElementById('service-detection');
const parallelScanCheckbox = document.getElementById('parallel-scan');
const maxWorkersInput = document.getElementById('max-workers');
const scanBtn = document.getElementById('scan-btn');
const stopBtn = document.getElementById('stop-btn');
const saveProfileBtn = document.getElementById('save-profile-btn');
const statusDiv = document.getElementById('status');
const rawOutputDiv = document.getElementById('raw-output');
const resultsBody = document.getElementById('results-body');
const connectionStatus = document.getElementById('connection-status');
const connectionText = document.getElementById('connection-text');

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// WebSocket Event Handlers
socket.on('connect', () => {
    console.log('Connected to server');
    connectionStatus.classList.add('connected');
    connectionStatus.classList.remove('disconnected');
    connectionText.textContent = 'Connected';
    updateStatus('Connected to NeoZen server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    connectionStatus.classList.remove('connected');
    connectionStatus.classList.add('disconnected');
    connectionText.textContent = 'Disconnected';
    updateStatus('Disconnected from server');
});

socket.on('scan_output', (data) => {
    appendOutput(data.text);
});

socket.on('scan_results', (data) => {
    console.log('Received scan_results event:', data);
    console.log('Results object:', data.results);
    console.log('Number of hosts:', Object.keys(data.results || {}).length);
    displayResults(data.results);
    switchTab('results');
});

socket.on('scan_started', (data) => {
    isScanning = true;
    updateUIState();
    updateStatus(`Scan started: ${data.target}`);
    rawOutputDiv.textContent = '';
});

socket.on('scan_stopped', () => {
    isScanning = false;
    updateUIState();
    updateStatus('Scan stopped');
});

socket.on('scan_finished', (data) => {
    isScanning = false;
    updateUIState();
    updateStatus(data.message);
});

socket.on('scan_progress', (data) => {
    updateStatus(`Parallel scan progress: ${data.current}/${data.total} hosts scanned`);
});

socket.on('scan_error', (data) => {
    isScanning = false;
    updateUIState();
    updateStatus(`Error: ${data.error}`, 'error');
    alert(`Scan Error: ${data.error}`);
});

// Button Event Handlers
scanBtn.addEventListener('click', startScan);
stopBtn.addEventListener('click', stopScan);
saveProfileBtn.addEventListener('click', saveProfile);

// Profile selection
profileSelect.addEventListener('change', loadProfile);

// Scan type selection
scanTypeSelect.addEventListener('change', () => {
    const scanType = scanTypeSelect.value;
    if (scanType === 'custom') {
        customArgumentsGroup.style.display = 'block';
    } else {
        customArgumentsGroup.style.display = 'none';
    }
});

// Checkbox handlers
osDetectionCheckbox.addEventListener('change', updateArguments);
serviceDetectionCheckbox.addEventListener('change', updateArguments);
parallelScanCheckbox.addEventListener('change', () => {
    maxWorkersInput.disabled = !parallelScanCheckbox.checked;
});

// Functions
async function loadProfiles() {
    try {
        const response = await fetch(`${API_BASE}/api/profiles`);
        const data = await response.json();

        // Clear and repopulate profile select
        profileSelect.innerHTML = '<option value="">Custom Scan</option>';

        for (const [name, profile] of Object.entries(data.profiles)) {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            profileSelect.appendChild(option);
        }
    } catch (error) {
        console.error('Failed to load profiles:', error);
    }
}

function loadProfile() {
    const profileName = profileSelect.value;

    if (!profileName) {
        return;
    }

    fetch(`${API_BASE}/api/profiles`)
        .then(res => res.json())
        .then(data => {
            const profile = data.profiles[profileName];
            if (profile) {
                targetInput.value = profile.target || '';
                argumentsInput.value = profile.arguments || '';
            }
        })
        .catch(error => console.error('Failed to load profile:', error));
}

async function startScan() {
    const target = targetInput.value.trim();

    if (!target) {
        alert('Please enter a target');
        return;
    }

    // Build arguments from scan type or custom input
    let args = '';
    const scanType = scanTypeSelect.value;

    if (scanType === 'custom') {
        // Use custom arguments
        args = argumentsInput.value.trim();
    } else {
        // Use predefined scan type
        args = scanType;
    }

    // Add OS detection if checked and not already present (unless using scan type that includes -A)
    if (osDetectionCheckbox.checked && !args.includes('-O') && !args.includes('-A')) {
        args += ' -O';
    }

    // Add service detection if checked and not already present (unless using scan type that includes -A)
    if (serviceDetectionCheckbox.checked && !args.includes('-sV') && !args.includes('-A')) {
        args += ' -sV';
    }

    try {
        // Build request body with parallel scanning options
        const requestBody = {
            target,
            arguments: args.trim(),
            parallel: parallelScanCheckbox.checked,
            max_workers: parseInt(maxWorkersInput.value) || 5
        };

        const response = await fetch(`${API_BASE}/api/scan/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (response.ok) {
            updateStatus(data.message);
        } else {
            alert(data.error || 'Failed to start scan');
        }
    } catch (error) {
        console.error('Failed to start scan:', error);
        alert('Failed to start scan');
    }
}

async function stopScan() {
    try {
        const response = await fetch(`${API_BASE}/api/scan/stop`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            updateStatus(data.message);
        } else {
            alert(data.error || 'Failed to stop scan');
        }
    } catch (error) {
        console.error('Failed to stop scan:', error);
    }
}

async function saveProfile() {
    const name = prompt('Enter profile name:');

    if (!name) {
        return;
    }

    const target = targetInput.value.trim();
    const args = argumentsInput.value.trim();

    try {
        const response = await fetch(`${API_BASE}/api/profiles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, target, arguments: args })
        });

        const data = await response.json();

        if (response.ok) {
            updateStatus(data.message);
            await loadProfiles();
            profileSelect.value = name;
        } else {
            alert(data.error || 'Failed to save profile');
        }
    } catch (error) {
        console.error('Failed to save profile:', error);
        alert('Failed to save profile');
    }
}

function updateArguments() {
    // This function can be expanded to dynamically update the arguments field
    // based on checkbox states if needed
}

function appendOutput(text) {
    rawOutputDiv.textContent += text + '\n';
    rawOutputDiv.scrollTop = rawOutputDiv.scrollHeight;
}

function displayResults(results) {
    resultsBody.innerHTML = '';

    if (!results || Object.keys(results).length === 0) {
        resultsBody.innerHTML = '<tr><td colspan="8" class="no-data">No results found</td></tr>';
        return;
    }

    // Parse and display results
    for (const [host, hostData] of Object.entries(results)) {
        const hostname = hostData.hostname || '';
        const displayHost = hostname && hostname !== host ? `${hostname} (${host})` : host;
        const macAddress = hostData.mac || '';
        const vendor = hostData.vendor || '';
        const macDisplay = macAddress && vendor ? `${macAddress} (${vendor})` : macAddress;
        const protocols = hostData.protocols || {};

        if (Object.keys(protocols).length === 0) {
            // Host is up but no ports
            const row = resultsBody.insertRow();
            row.innerHTML = `
                <td>${displayHost}</td>
                <td>${macDisplay}</td>
                <td colspan="6" class="no-data">No open ports found</td>
            `;
            continue;
        }

        // Display each port
        for (const [proto, ports] of Object.entries(protocols)) {
            for (const [port, portData] of Object.entries(ports)) {
                const row = resultsBody.insertRow();
                row.innerHTML = `
                    <td>${displayHost}</td>
                    <td>${macDisplay}</td>
                    <td>${proto}</td>
                    <td>${port}</td>
                    <td>${portData.state || ''}</td>
                    <td>${portData.name || ''}</td>
                    <td>${portData.product || ''}</td>
                    <td>${portData.version || ''}</td>
                `;
            }
        }
    }
}

function updateStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.style.borderLeftColor = type === 'error' ? '#e74c3c' : '#667eea';
}

function updateUIState() {
    scanBtn.disabled = isScanning;
    stopBtn.disabled = !isScanning;
    targetInput.disabled = isScanning;
    argumentsInput.disabled = isScanning;
    profileSelect.disabled = isScanning;
    osDetectionCheckbox.disabled = isScanning;
    serviceDetectionCheckbox.disabled = isScanning;
    parallelScanCheckbox.disabled = isScanning;
    // Max workers input enabled only when not scanning AND parallel scan is checked
    maxWorkersInput.disabled = isScanning || !parallelScanCheckbox.checked;
    saveProfileBtn.disabled = isScanning;
}

// Visual Scan Builder Modal
const visualBuilderBtn = document.getElementById('visual-builder-btn');
const scanBuilderModal = document.getElementById('scan-builder-modal');
const modalCloseBtn = document.getElementById('modal-close-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');
const modalApplyBtn = document.getElementById('modal-apply-btn');
const builderCommandPreview = document.getElementById('builder-command-preview');

// Modal control buttons
visualBuilderBtn.addEventListener('click', openScanBuilder);
modalCloseBtn.addEventListener('click', closeScanBuilder);
modalCancelBtn.addEventListener('click', closeScanBuilder);
modalApplyBtn.addEventListener('click', applyScanBuilderSettings);

// Close modal on background click
scanBuilderModal.addEventListener('click', (e) => {
    if (e.target === scanBuilderModal) {
        closeScanBuilder();
    }
});

// Builder option change listeners
document.querySelectorAll('#scan-builder-modal input').forEach(input => {
    input.addEventListener('change', updateBuilderPreview);
});

// Aggressive scan handling
document.getElementById('builder-aggressive').addEventListener('change', function() {
    const isAggressive = this.checked;
    document.getElementById('builder-os-detection').disabled = isAggressive;
    document.getElementById('builder-version-detection').disabled = isAggressive;
    document.getElementById('builder-script-scan').disabled = isAggressive;
    if (isAggressive) {
        document.getElementById('builder-os-detection').checked = false;
        document.getElementById('builder-version-detection').checked = false;
        document.getElementById('builder-script-scan').checked = false;
    }
    updateBuilderPreview();
});

// Parallel scan handling
document.getElementById('builder-parallel').addEventListener('change', function() {
    document.getElementById('builder-max-workers').disabled = !this.checked;
});

// Very verbose handling
document.getElementById('builder-very-verbose').addEventListener('change', function() {
    if (this.checked) {
        document.getElementById('builder-verbose').checked = false;
    }
    updateBuilderPreview();
});

// Ping scan handling (disable port options)
document.querySelectorAll('input[name="scan-technique"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const isPingScan = this.value === 'sn' && this.checked;
        document.querySelectorAll('input[name="port-spec"]').forEach(portRadio => {
            portRadio.disabled = isPingScan;
            if (isPingScan) portRadio.checked = false;
        });
        updateBuilderPreview();
    });
});

function openScanBuilder() {
    scanBuilderModal.classList.add('show');
    updateBuilderPreview();
}

function closeScanBuilder() {
    scanBuilderModal.classList.remove('show');
}

function updateBuilderPreview() {
    const args = [];

    // Scan technique
    const scanTech = document.querySelector('input[name="scan-technique"]:checked');
    if (scanTech) {
        args.push(`-${scanTech.value}`);
    }

    // Port specification
    const portSpec = document.querySelector('input[name="port-spec"]:checked');
    if (portSpec) {
        args.push(`-${portSpec.value}`);
    }

    // Timing
    const timing = document.querySelector('input[name="timing"]:checked');
    if (timing) {
        args.push(`-${timing.value}`);
    }

    // Detection & Enumeration
    if (document.getElementById('builder-aggressive').checked) {
        args.push('-A');
    } else {
        if (document.getElementById('builder-os-detection').checked) args.push('-O');
        if (document.getElementById('builder-version-detection').checked) args.push('-sV');
        if (document.getElementById('builder-script-scan').checked) args.push('-sC');
    }

    // Other options
    if (document.getElementById('builder-very-verbose').checked) {
        args.push('-vv');
    } else if (document.getElementById('builder-verbose').checked) {
        args.push('-v');
    }

    if (document.getElementById('builder-reason').checked) args.push('--reason');
    if (document.getElementById('builder-no-dns').checked) args.push('-n');

    // Build command preview
    const command = 'nmap ' + args.join(' ') + ' <target>';
    builderCommandPreview.textContent = command;
}

function applyScanBuilderSettings() {
    const args = [];

    // Scan technique
    const scanTech = document.querySelector('input[name="scan-technique"]:checked');
    if (scanTech) {
        args.push(`-${scanTech.value}`);
    }

    // Port specification
    const portSpec = document.querySelector('input[name="port-spec"]:checked');
    if (portSpec) {
        args.push(`-${portSpec.value}`);
    }

    // Timing
    const timing = document.querySelector('input[name="timing"]:checked');
    if (timing) {
        args.push(`-${timing.value}`);
    }

    // Detection & Enumeration
    if (document.getElementById('builder-aggressive').checked) {
        args.push('-A');
    } else {
        if (document.getElementById('builder-os-detection').checked) args.push('-O');
        if (document.getElementById('builder-version-detection').checked) args.push('-sV');
        if (document.getElementById('builder-script-scan').checked) args.push('-sC');
    }

    // Other options
    if (document.getElementById('builder-very-verbose').checked) {
        args.push('-vv');
    } else if (document.getElementById('builder-verbose').checked) {
        args.push('-v');
    }

    if (document.getElementById('builder-reason').checked) args.push('--reason');
    if (document.getElementById('builder-no-dns').checked) args.push('-n');

    // Apply to main form
    scanTypeSelect.value = 'custom';
    customArgumentsGroup.style.display = 'block';
    argumentsInput.value = args.join(' ');

    // Apply parallel scanning settings
    const parallelEnabled = document.getElementById('builder-parallel').checked;
    const maxWorkers = parseInt(document.getElementById('builder-max-workers').value);
    parallelScanCheckbox.checked = parallelEnabled;
    maxWorkersInput.value = maxWorkers;
    maxWorkersInput.disabled = !parallelEnabled;

    // Close modal
    closeScanBuilder();
}

// Initialize
loadProfiles();
updateUIState();
