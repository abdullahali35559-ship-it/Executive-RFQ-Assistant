// RFQ Agent - Dashboard Logic

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Dashboard] RFQ Agent Dashboard Initializing...');

    // Load dashboard data
    try {
        await loadDashboardStats();
        await loadRecentActivity();
        if (typeof applyPreset === 'function') applyPreset('today');
    } catch (e) { console.error('[Dashboard] Init error:', e); }

    console.log('[Dashboard] Dashboard Ready');
});

// Start polling immediately, outside of any blocks to be safe
console.log('[Dashboard] Starting agent status polling loop...');
setInterval(checkAgentStatus, 5000);
checkAgentStatus(); 

// Load dashboard statistics
async function loadDashboardStats() {
    try {
        // For now, we'll use static data until backend API is ready
        // TODO: Replace with actual API call when backend endpoints are ready

        const stats = {
            activeTenders: 0,
            unreadEmails: 0,
            pendingRFIs: 0,
            totalClients: 3  // From your database screenshot
        };

        // Try to fetch from API
        try {
            const response = await window.RFQAgentAPI.getDashboardStats();
            if (response && response.success && response.data) {
                Object.assign(stats, response.data);
            } else if (response && !response.success) {
                console.warn('API returned success=false, using defaults');
            }
        } catch (error) {
            console.log('Using static stats (API not available yet)');
        }

        // Update DOM
        updateStatCard('activeTenders', stats.activeTenders);
        updateStatCard('unreadEmails', stats.unreadEmails);
        updateStatCard('pendingRFIs', stats.pendingRFIs);
        updateStatCard('totalClients', stats.totalClients);

        // Update status labels
        const tenderStatus = document.getElementById('activeTendersStatus');
        if (tenderStatus) tenderStatus.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><polyline points="20 6 9 17 4 12"></polyline></svg>Up to date';

        const emailStatus = document.getElementById('unreadEmailsStatus');
        if (emailStatus) emailStatus.innerHTML = stats.unprocessedEmails > 0
            ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>${stats.unprocessedEmails} unprocessed`
            : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><polyline points="20 6 9 17 4 12"></polyline></svg>All processed';

    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showError('Failed to load dashboard statistics');
    }
}

// Update a stat card
function updateStatCard(id, value) {
    const element = document.getElementById(id);
    if (element) {
        // Animate the value change
        animateValue(element, parseInt(element.textContent) || 0, value, 500);
    }
}

// Animate number changes
function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current);
    }, 16);
}

// Load recent activity (kept for compat)
async function loadRecentActivity() { }

// ── SESSION SUMMARY WIDGET ────────────────────────────────────────────────

function toLocalISOString(d) {
    // Returns YYYY-MM-DDTHH:MM suitable for datetime-local input
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function applyPreset(preset) {
    const now = new Date();
    let from, to;

    if (preset === 'today') {
        from = new Date(now); from.setHours(0, 0, 0, 0);
        to = new Date(now); to.setHours(23, 59, 59, 999);
    } else if (preset === '8h') {
        from = new Date(now.getTime() - 8 * 60 * 60 * 1000);
        to = now;
    } else if (preset === '24h') {
        from = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        to = now;
    } else if (preset === 'week') {
        from = new Date(now); from.setDate(now.getDate() - 7); from.setHours(0, 0, 0, 0);
        to = now;
    }

    document.getElementById('sessionFrom').value = toLocalISOString(from);
    document.getElementById('sessionTo').value = toLocalISOString(to);

    // Highlight active preset button
    document.querySelectorAll('[id^="preset-"]').forEach(b => {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
    });
    const btn = document.getElementById(`preset-${preset}`);
    if (btn) { btn.classList.remove('btn-secondary'); btn.classList.add('btn-primary'); }

    loadSessionSummary();
}

async function loadSessionSummary() {
    const fromValRaw = document.getElementById('sessionFrom').value;
    const toValRaw = document.getElementById('sessionTo').value;
    const results = document.getElementById('sessionResults');

    if (!fromValRaw || !toValRaw) {
        results.innerHTML = `<p style="color:var(--accent-red);padding:1rem;">Please select both From and To times.</p>`;
        return;
    }

    results.innerHTML = `<div style="text-align:center;padding:1.5rem;color:var(--text-muted);">
        <div style="width:28px;height:28px;border:3px solid #e5e7eb;border-top-color:var(--primary-orange);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 8px;"></div>
        Loading...
    </div>`;

    try {
        // Convert local HTML input values to standard UTC ISO strings for backend
        const fromVal = new Date(fromValRaw).toISOString();
        const toVal = new Date(toValRaw).toISOString();

        const resp = await fetch(`http://localhost:8000/api/session-summary?from_time=${encodeURIComponent(fromVal)}&to_time=${encodeURIComponent(toVal)}`);
        const data = await resp.json();

        if (!data.success) throw new Error(data.detail || 'API error');

        if (data.count === 0) {
            results.innerHTML = `
                <div style="text-align:center;padding:2rem;color:var(--text-muted);">
                    <svg width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="margin:0 auto 8px;display:block;opacity:0.4"><path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7"/><path d="M4 13h16v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z"/></svg>
                    <p style="font-size:0.9rem;">No tender emails processed in this time window.</p>
                </div>`;
            return;
        }

        const rows = data.data.map(e => `
            <div class="activity-item" style="display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;padding:12px 16px;">
                <div>
                    <div style="font-weight:600;font-size:0.88rem;color:var(--text-primary);">${e.subject || '(No Subject)'}</div>
                    <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">
                        From: ${e.sender || '—'} &nbsp;·&nbsp;
                        Processed: ${e.processed_at ? new Date(e.processed_at).toLocaleString() : '—'}
                    </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;flex-shrink:0;">
                    ${e.tender_id ? `<span style="background:#FFF4F0;color:var(--primary-orange);font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:20px;border:1px solid #FFD5CC;">${e.tender_id}</span>` : ''}
                    <span style="background:#D1FAE5;color:#065F46;font-size:0.72rem;font-weight:600;padding:3px 8px;border-radius:20px;">${e.doc_count} doc${e.doc_count !== 1 ? 's' : ''}</span>
                </div>
            </div>`).join('');

        results.innerHTML = `
            <div style="font-size:0.78rem;color:var(--text-muted);padding:8px 16px;border-bottom:1px solid var(--border-light);background:var(--bg-light);border-radius:var(--radius-md) var(--radius-md) 0 0;">
                Found <strong>${data.count}</strong> tender email${data.count !== 1 ? 's' : ''} processed between
                <strong>${new Date(fromVal).toLocaleString()}</strong> and <strong>${new Date(toVal).toLocaleString()}</strong>
            </div>
            ${rows}`;
    } catch (err) {
        results.innerHTML = `<p style="color:var(--accent-red);padding:1rem;">Error: ${err.message}</p>`;
        console.error('Session summary error:', err);
    }
}

// Note: applyPreset('today') is now handled in the main DOMContentLoaded listener

// Quick Action: Process Emails
async function processEmails() {
    try {
        // Show progress panel immediately
        const panel = document.getElementById('progressPanel');
        if (panel) panel.style.display = 'block';
        document.getElementById('progressStatus').textContent = 'Starting agent...';
        document.getElementById('progressBar').style.width = '5%';

        const result = await window.RFQAgentAPI.processEmails();
        
        showSuccess(`Processing started! You can monitor progress above.`);

    } catch (error) {
        showError('Failed to start processing. Make sure backend is running.');
        console.error(error);
    }
}

let lastLogTimestamp = null;
let forceDisplayUntil = 0;

// Quick Action: Process Emails
async function processEmails() {
    try {
        // Show progress panel immediately and force it to stay for 30s
        const panel = document.getElementById('progressPanel');
        if (panel) {
            panel.style.display = 'block';
            document.getElementById('progressStatus').textContent = 'Starting agent...';
            document.getElementById('progressBar').style.width = '5%';
            document.getElementById('progressPercent').textContent = '5%';
            document.getElementById('progressLogs').innerHTML = '<div style="color:var(--primary-orange);font-style:italic;">Initializing connection...</div>';
        }
        
        forceDisplayUntil = Date.now() + 30000; 

        await window.RFQAgentAPI.processEmails();
        showSuccess(`Processing started!`);

    } catch (error) {
        showError('Failed to start processing. Make sure backend is running.');
        console.error(error);
    }
}

async function checkAgentStatus() {
    try {
        const response = await window.RFQAgentAPI.getAgentStatus();
        const panel = document.getElementById('progressPanel');
        if (!panel) return;

        const isTriggered = Date.now() < forceDisplayUntil;

        if (response.success && (response.is_active || isTriggered)) {
            panel.style.display = 'block';
            
            const logs = response.latest_logs || [];
            if (logs.length > 0) {
                const latest = logs[0];
                document.getElementById('progressStatus').textContent = latest.action;
                
                // Calculate rough progress
                let percent = 10;
                const isComplete = latest.action.toLowerCase().includes('complete') || latest.action.includes('Finished');
                
                if (isComplete) {
                    percent = 100;
                    forceDisplayUntil = 0;
                    document.getElementById('progressTitleText').textContent = 'Processing Session Complete';
                    const spinner = panel.querySelector('.spinner-small');
                    if (spinner) spinner.style.display = 'none';
                } else {
                    document.getElementById('progressTitleText').textContent = 'Agent Processing in Progress...';
                    const spinner = panel.querySelector('.spinner-small');
                    if (spinner) spinner.style.display = 'block';
                    
                    if (latest.action.includes('Processing file')) {
                        const match = latest.action.match(/(\d+)\/(\d+)/);
                        if (match) {
                            const current = parseInt(match[1]);
                            const total = parseInt(match[2]);
                            percent = 20 + Math.floor((current / total) * 70);
                        }
                    } else if (latest.action.includes('Classifying')) percent = 20;
                    else if (latest.action.includes('Checking provider')) percent = 15;
                }
                
                document.getElementById('progressBar').style.width = `${percent}%`;
                document.getElementById('progressPercent').textContent = `${percent}%`;

                // Update logs display
                const logsContainer = document.getElementById('progressLogs');
                if (logsContainer && latest.timestamp !== lastLogTimestamp) {
                    const logHtml = logs.slice(0, 5).map(l => `
                        <div style="margin-bottom: 4px; border-bottom: 1px solid #EEE; padding-bottom: 2px;">
                            <span style="color: var(--primary-orange); font-weight: 600;">[${new Date(l.timestamp).toLocaleTimeString()}]</span> 
                            ${l.action} ${l.details.filename ? `- ${l.details.filename}` : ''}
                        </div>
                    `).join('');
                    logsContainer.innerHTML = logHtml;
                    lastLogTimestamp = latest.timestamp;
                }
            }
        } else {
            // Only hide if NOT active and NOT forced
            const percentLabel = document.getElementById('progressPercent');
            const currentPercent = percentLabel ? parseInt(percentLabel.textContent) : 0;
            // Stay visible for a few seconds even after completion
            if (currentPercent === 100 || currentPercent === 0 || isNaN(currentPercent)) {
                panel.style.display = 'none';
            }
        }
    } catch (err) {
        console.error('Error checking agent status:', err);
    }
}

// Quick Action: View Tenders
function viewTenders() {
    window.location.href = 'tenders.html';
}

// Quick Action: Check System Status
async function checkSystem() {
    try {
        showLoading('Checking system status...');

        const status = await window.RFQAgentAPI.getSystemStatus();

        hideLoading();

        // Show status modal
        showSystemStatus(status);

    } catch (error) {
        hideLoading();
        showError('Could not reach backend server. Make sure FastAPI is running on port 8000.');
        console.error(error);
    }
}

// Quick Action: Open Settings
function openSettings() {
    window.location.href = 'settings.html';
}

// Show system status modal
function showSystemStatus(status) {
    const modal = `
        <div class="modal">
            <div class="modal-content">
                <h2>System Status</h2>
                <div class="status-grid">
                    <div class="status-item">
                        <span class="status-indicator ${status.database ? 'status-online' : 'status-offline'}"></span>
                        <span>Database: ${status.database ? 'Connected' : 'Disconnected'}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-indicator ${status.gmail ? 'status-online' : 'status-offline'}"></span>
                        <span>Gmail: ${status.gmail ? 'Connected' : 'Not configured'}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-indicator ${status.outlook ? 'status-online' : 'status-offline'}"></span>
                        <span>Outlook: ${status.outlook ? 'Connected' : 'Not configured'}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-indicator ${status.llm ? 'status-online' : 'status-offline'}"></span>
                        <span>LLM: ${status.llm ? 'Online' : 'Offline'}</span>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="closeModal()">Close</button>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
}

// UI Helper Functions
function showLoading(message = 'Loading...') {
    const loader = `
        <div id="loading-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        ">
            <div style="
                background: white;
                padding: 2rem 3rem;
                border-radius: 12px;
                text-align: center;
            ">
                <div style="
                    width: 40px;
                    height: 40px;
                    border: 4px solid #E5E7EB;
                    border-top-color: #2563EB;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 1rem;
                "></div>
                <div>${message}</div>
            </div>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    `;
    document.body.insertAdjacentHTML('beforeend', loader);
}

function hideLoading() {
    const loader = document.getElementById('loading-overlay');
    if (loader) {
        loader.remove();
    }
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showError(message) {
    showToast(message, 'error');
}

function showToast(message, type = 'info') {
    const colors = {
        success: '#10B981',
        error: '#EF4444',
        info: '#FF5C35'
    };

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: white;
        color: ${colors[type]};
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-left: 4px solid ${colors[type]};
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.remove();
    }
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }
    
    .modal-content {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        min-width: 400px;
        max-width: 90%;
    }
    
    .status-grid {
        display: grid;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .status-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        background: var(--bg-light);
        border-radius: 8px;
    }
`;
document.head.appendChild(style);

console.log('📊 Dashboard script loaded');
