// NeoZen Web Interface JavaScript

// Configuration
const API_BASE = window.location.origin;
const socket = io(API_BASE);

// Global error handler for authentication
function handleAuthError(response) {
    if (response.status === 401) {
        alert('Your session has expired. Please login again.');
        window.location.href = '/login';
        return true;
    }
    return false;
}

// State
let isScanning = false;
let scanResults = {};
let selectedDeviceIp = null;
let deviceNotes = {}; // Store notes per device IP (loaded from server)

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
const downloadXmlBtn = document.getElementById('download-xml-btn');
const exportCsvBtn = document.getElementById('export-csv-btn');
const statusDiv = document.getElementById('status');
const commandDisplayText = document.getElementById('command-display-text');
const rawOutputDiv = document.getElementById('raw-output');
const devicesBody = document.getElementById('devices-body');
const portsBody = document.getElementById('ports-body');
const deviceBasicInfo = document.getElementById('device-basic-info');
const deviceDetailsTitle = document.getElementById('device-details-title');
const deviceNotesInput = document.getElementById('device-notes-input');
const saveNotesBtn = document.getElementById('save-notes-btn');
const connectionStatus = document.getElementById('connection-status');
const connectionText = document.getElementById('connection-text');
const logoutBtn = document.getElementById('logout-btn');

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
    scanResults = data.results;
    displayDeviceList(data.results);
    switchTab('devices');
});

socket.on('scan_started', (data) => {
    isScanning = true;
    updateUIState();
    updateStatus(`Scan started: ${data.target}`);
    rawOutputDiv.textContent = '';
    // Clear previous results and disable export buttons
    scanResults = {};
    selectedDeviceIp = null;
    devicesBody.innerHTML = '<tr><td colspan="3" class="no-data">Scanning...</td></tr>';
    portsBody.innerHTML = '<tr><td colspan="6" class="no-data">No device selected</td></tr>';
    deviceBasicInfo.innerHTML = '';
    deviceDetailsTitle.textContent = 'Select a device from the Device List';
    downloadXmlBtn.disabled = true;
    exportCsvBtn.disabled = true;
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
    // Enable export buttons after successful scan
    downloadXmlBtn.disabled = false;
    exportCsvBtn.disabled = false;
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
downloadXmlBtn.addEventListener('click', downloadXml);
exportCsvBtn.addEventListener('click', exportCsv);
saveNotesBtn.addEventListener('click', saveDeviceNotes);
logoutBtn.addEventListener('click', logout);

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

    // Build and display the command
    const command = `nmap ${args.trim()} ${target}`;
    commandDisplayText.value = command;

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

        if (handleAuthError(response)) return;

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

async function logout() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok) {
            // Redirect to login page
            window.location.href = '/login';
        } else {
            alert(data.error || 'Failed to logout');
        }
    } catch (error) {
        console.error('Logout error:', error);
        alert('Failed to logout');
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

function displayDeviceList(results) {
    devicesBody.innerHTML = '';

    if (!results || Object.keys(results).length === 0) {
        devicesBody.innerHTML = '<tr><td colspan="3" class="no-data">No results found</td></tr>';
        return;
    }

    // Display device list (one row per device)
    for (const [host, hostData] of Object.entries(results)) {
        const hostname = hostData.hostname || '';
        const displayHost = hostname && hostname !== host ? `${hostname} (${host})` : host;
        const macAddress = hostData.mac || '';
        const vendor = hostData.vendor || '';
        const macDisplay = macAddress && vendor ? `${macAddress} (${vendor})` : macAddress;

        // Get best OS match
        const osmatches = hostData.osmatch || [];
        let detectedOS = 'Unknown';
        if (osmatches.length > 0) {
            // Sort by accuracy and get the best match
            const sortedMatches = osmatches.sort((a, b) => {
                return parseInt(b.accuracy || '0') - parseInt(a.accuracy || '0');
            });
            detectedOS = sortedMatches[0].name;
            if (sortedMatches[0].accuracy) {
                detectedOS += ` (${sortedMatches[0].accuracy}%)`;
            }
        }

        const row = devicesBody.insertRow();
        row.dataset.hostIp = host;
        row.dataset.sortHost = displayHost;
        row.dataset.sortMac = macDisplay;
        row.dataset.sortOs = detectedOS;
        row.innerHTML = `
            <td>${displayHost}</td>
            <td>${macDisplay}</td>
            <td>${detectedOS}</td>
        `;

        // Add click handler
        row.addEventListener('click', () => {
            selectDevice(host, row);
        });
    }

    // Enable sorting after populating the table
    initializeTableSorting();
}

function initializeTableSorting() {
    const headers = document.querySelectorAll('#devices-table th');
    headers.forEach((header, index) => {
        header.classList.add('sortable');
        header.addEventListener('click', () => sortDeviceTable(index));
    });
}

function sortDeviceTable(columnIndex) {
    const table = document.getElementById('devices-table');
    const tbody = devicesBody;
    const rows = Array.from(tbody.querySelectorAll('tr')).filter(row => !row.querySelector('.no-data'));

    if (rows.length === 0) return;

    const headers = table.querySelectorAll('th');
    const currentHeader = headers[columnIndex];

    // Determine sort direction
    let sortDirection = 'asc';
    if (currentHeader.classList.contains('sort-asc')) {
        sortDirection = 'desc';
    }

    // Clear all sort indicators
    headers.forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
    });

    // Set current sort indicator
    currentHeader.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');

    // Get the data attribute for sorting
    const sortKeys = ['sortHost', 'sortMac', 'sortOs'];
    const sortKey = sortKeys[columnIndex];

    // Sort rows
    rows.sort((a, b) => {
        const aValue = a.dataset[sortKey] || '';
        const bValue = b.dataset[sortKey] || '';

        const comparison = aValue.localeCompare(bValue, undefined, { numeric: true, sensitivity: 'base' });
        return sortDirection === 'asc' ? comparison : -comparison;
    });

    // Re-append rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
}

function selectDevice(hostIp, rowElement) {
    selectedDeviceIp = hostIp;

    // Update row selection styling
    document.querySelectorAll('#devices-body tr').forEach(tr => tr.classList.remove('selected'));
    rowElement.classList.add('selected');

    // Display device details
    showDeviceDetails(hostIp);

    // Switch to Device Details tab
    switchTab('details');
}

function showDeviceDetails(hostIp) {
    const hostData = scanResults[hostIp];

    if (!hostData) {
        deviceDetailsTitle.textContent = 'Device not found';
        deviceBasicInfo.innerHTML = '';
        portsBody.innerHTML = '<tr><td colspan="6" class="no-data">Device not found</td></tr>';
        return;
    }

    // Update title
    const hostname = hostData.hostname || '';
    const displayHost = hostname && hostname !== hostIp ? `${hostname} (${hostIp})` : hostIp;
    deviceDetailsTitle.textContent = `Device Details: ${displayHost}`;

    // Display basic info
    const macAddress = hostData.mac || 'N/A';
    const vendor = hostData.vendor || '';
    const macDisplay = vendor ? `${macAddress} (${vendor})` : macAddress;
    const state = hostData.state || 'unknown';

    // Get OS detection info
    const osmatches = hostData.osmatch || [];
    let osInfo = 'Unknown';
    if (osmatches.length > 0) {
        const sortedMatches = osmatches.sort((a, b) => {
            return parseInt(b.accuracy || '0') - parseInt(a.accuracy || '0');
        });
        osInfo = sortedMatches.map(match => {
            return `${match.name} (${match.accuracy}% accuracy)`;
        }).join('<br>');
    }

    deviceBasicInfo.innerHTML = `
        <div class="info-label">IP Address:</div>
        <div class="info-value">${hostIp}</div>
        <div class="info-label">Hostname:</div>
        <div class="info-value">${hostname || 'N/A'}</div>
        <div class="info-label">State:</div>
        <div class="info-value">${state}</div>
        <div class="info-label">MAC Address:</div>
        <div class="info-value">${macDisplay}</div>
        <div class="info-label">Detected OS:</div>
        <div class="info-value">${osInfo}</div>
    `;

    // Display ports
    portsBody.innerHTML = '';
    const protocols = hostData.protocols || {};

    if (Object.keys(protocols).length === 0) {
        portsBody.innerHTML = '<tr><td colspan="6" class="no-data">No open ports found</td></tr>';
    } else {
        // Display all ports
        for (const [proto, ports] of Object.entries(protocols)) {
            for (const [port, portData] of Object.entries(ports)) {
                const row = portsBody.insertRow();
                row.innerHTML = `
                    <td>${port}</td>
                    <td>${proto}</td>
                    <td>${portData.state || ''}</td>
                    <td>${portData.name || ''}</td>
                    <td>${portData.product || ''}</td>
                    <td>${portData.version || ''}</td>
                `;
            }
        }
    }

    // Load notes for this device
    deviceNotesInput.value = deviceNotes[hostIp] || '';
}

async function saveDeviceNotes() {
    if (!selectedDeviceIp) {
        alert('No device selected');
        return;
    }

    const notes = deviceNotesInput.value;

    try {
        const response = await fetch(`${API_BASE}/api/devices/${encodeURIComponent(selectedDeviceIp)}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes })
        });

        if (handleAuthError(response)) return;

        const data = await response.json();

        if (response.ok) {
            deviceNotes[selectedDeviceIp] = notes;
            updateStatus(`Notes saved for ${selectedDeviceIp}`);
        } else {
            alert(data.error || 'Failed to save notes');
        }
    } catch (error) {
        console.error('Failed to save notes:', error);
        alert('Failed to save notes');
    }
}

// Load all device notes from server
async function loadDeviceNotes() {
    try {
        const response = await fetch(`${API_BASE}/api/devices/notes`);

        if (handleAuthError(response)) return;

        const data = await response.json();

        if (response.ok && data.notes) {
            // Convert notes object format
            deviceNotes = {};
            for (const [ip, noteData] of Object.entries(data.notes)) {
                deviceNotes[ip] = noteData.notes || '';
            }
        }
    } catch (error) {
        console.error('Failed to load notes:', error);
    }
}

function updateStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.style.borderLeftColor = type === 'error' ? '#e74c3c' : '#667eea';
}

function downloadXml() {
    window.location.href = `${API_BASE}/api/scan/download-xml`;
}

function exportCsv() {
    window.location.href = `${API_BASE}/api/scan/export-csv`;
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
loadDeviceNotes();
updateUIState();
