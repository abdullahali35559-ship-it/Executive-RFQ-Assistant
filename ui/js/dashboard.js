// RFQ Agent - Executive Dashboard Logic
let forceDisplayUntil = 0;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Dashboard] Script loaded, checking API availability...');
    if (window.RFQAgentAPIReady) {
        initDashboard();
    } else {
        window.addEventListener('RFQAgentAPIReady', initDashboard);
    }
});

async function initDashboard() {
    console.log('[Dashboard] API Ready. Initializing Executive Assistant Dashboard...');

    // Load initial data (NON-BLOCKING for instant UI feel)
    loadDashboardData();

    // Start a single, persistent polling interval
    setInterval(loadDashboardData, 30000); // Main stats every 30s
    setInterval(checkAgentStatus, 2000);    // Agent status every 2s (Faster for better UX)

    // Welcome message time-awareness
    const hours = new Date().getHours();
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) {
        if (hours < 12) welcome.textContent = "Good morning, Abdullah. Here is your priority list.";
        else if (hours < 18) welcome.textContent = "Good afternoon, Abdullah. Here is your priority list.";
        else welcome.textContent = "Good evening, Abdullah. Here is your priority list.";
    }

    // Initialize Flatpickr for booking modal
    if (typeof flatpickr !== 'undefined') {
        flatpickr('#bookingDate', {
            dateFormat: "Y-m-d",
            minDate: "today",
            defaultDate: "today"
        });
        flatpickr('#bookingTime', {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            defaultDate: "09:00"
        });
    }
    // Initialize session summary
    applySessionPreset('today');
}

async function loadDashboardData() {
    try {
        console.log('[Dashboard] Refreshing all data pulses...');
        // 1. Kick off stats and other independent fetches immediately (NON-BLOCKING)
        loadPulseStats();
        loadMorningBrief();
        loadPriorityList();
        loadPendingDrafts();
        loadTasks();
        loadFollowups();

        // 2. Calendar data is shared, so we fetch it once then update dependent widgets
        window.RFQAgentAPI.getCalendarEvents(7).then(response => {
            const calendarData = response.success ? response.data : [];
            loadAgendaWidget(calendarData);
            loadHoldQueue(calendarData);
        }).catch(err => console.error('[Dashboard] Calendar load error:', err));

    } catch (e) {
        console.error('[Dashboard] Data load error:', e);
    }
}


async function loadMorningBrief() {
    const container = document.getElementById('morningBriefContainer');
    const briefText = document.getElementById('morningBriefText');
    if (!container || !briefText) return;

    try {
        const response = await window.RFQAgentAPI.getMorningBrief();
        if (response.success && response.brief) {
            briefText.textContent = response.brief;
            container.style.display = 'block';
        }
    } catch (e) { console.error('Morning brief error:', e); }
}

async function triggerSync() {
    const btnSync = document.getElementById('btnSyncAll');
    const panel = document.getElementById('syncProgressContainer');
    const syncBar = document.getElementById('syncProgressBar');
    const syncPercent = document.getElementById('syncPercentLabel');
    const syncStatus = document.getElementById('progressTitleText');

    if (!btnSync || !panel) return;

    // Show the progress panel
    panel.style.display = 'block';
    
    // Reset Progress
    if (syncBar) syncBar.style.width = '0%';
    if (syncPercent) syncPercent.textContent = '0%';
    if (syncStatus) syncStatus.textContent = 'Syncing Intelligence...';
    btnSync.disabled = true;

    forceDisplayUntil = Date.now() + 10000; // Stay visible for 10s grace

    try {
        console.log("ELITE-SYNC: Triggering Agent...");
        await window.RFQAgentAPI.processEmails();
        
        // Call status check immediately for instant feedback
        checkAgentStatus();
    } catch (e) {
        console.error("Sync trigger failed", e);
        if (panel) panel.style.display = 'none';
        if (btnSync) btnSync.disabled = false;
    }
}

let lastLogTimestamp = null;

async function checkAgentStatus() {
    try {
        const response = await window.RFQAgentAPI.getAgentStatus();
        const panel = document.getElementById('syncProgressContainer');
        const syncBar = document.getElementById('syncProgressBar');
        const syncPercent = document.getElementById('syncPercentLabel');
        const syncStatus = document.getElementById('progressTitleText');
        const btnSync = document.getElementById('btnSyncAll');

        if (!panel) return;

        const isRecentlyTriggered = Date.now() < forceDisplayUntil;

        if (response.active || isRecentlyTriggered) {
            panel.style.display = 'block';
            
            // Calculate percentage
            let percent = 5;
            if (response.total > 0) {
                percent = Math.round((response.current / response.total) * 90) + 10;
            } else if (response.status && (response.status.includes('No new emails') || response.status.includes('Complete'))) {
                percent = 100;
            } else if (response.status && response.status.includes('Fetching')) {
                percent = 15;
            } else if (response.status && response.status.includes('Analyzing')) {
                percent = 30;
            }

            if (percent > 100) percent = 100;

            if (syncBar) {
                syncBar.style.width = percent + '%';
                if (percent === 100) {
                    syncBar.classList.add('bg-success');
                    syncBar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
                } else {
                    syncBar.classList.remove('bg-success');
                    syncBar.style.background = '';
                }
            }
            
            if (syncPercent) syncPercent.textContent = percent + '%';
            
            if (percent === 100) {
                // Keep visible for a bit after reaching 100%
                if (btnSync) btnSync.disabled = false;
                
                // If it just finished, refresh data
                if (response.active === false && isRecentlyTriggered) {
                    // Start cooling down the "force display" so it closes in 3 seconds
                    if (!window._syncFinishTime) {
                        window._syncFinishTime = Date.now();
                        loadDashboardData();
                    }
                    
                    // After 3 seconds of being at 100%, we can allow it to close
                    if (Date.now() - window._syncFinishTime > 3000) {
                        forceDisplayUntil = 0;
                        window._syncFinishTime = null;
                    }
                }
            } else {
                if (btnSync) btnSync.disabled = true;
                window._syncFinishTime = null;
            }

            if (syncStatus) {
                let newStatus = response.status || 'Syncing...';
                if (percent === 100 && !newStatus.includes('Error')) {
                    newStatus = "✅ Sync Complete. Dashboard Updated.";
                }
                if (syncStatus.textContent !== newStatus) {
                    syncStatus.textContent = newStatus;
                }
                
                if (newStatus.includes('Error')) {
                    syncStatus.style.color = '#ef4444';
                    syncStatus.style.fontWeight = '700';
                } else {
                    syncStatus.style.color = '';
                    syncStatus.style.fontWeight = '';
                }
            }

        } else {
            // Task is not active and force-display has expired
            panel.style.display = 'none';
            if (btnSync) btnSync.disabled = false;
        }
    } catch (e) {
        console.warn('[StatusPoller] Error:', e);
    }
}

async function loadPulseStats() {
    try {
        const stats = await window.RFQAgentAPI.getDashboardStats();
        if (stats.success) {
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val !== undefined ? val : '0';
            };
            setVal('statActiveTenders', stats.activeTenders);
            setVal('statUnprocessed', stats.unprocessedCount);
            setVal('statIncomplete', stats.incompleteTenders);
            setVal('statUrgent', stats.urgentCount);
        }
    } catch (e) { console.error('Stats load error:', e); }
}

// ── SESSION SUMMARY LOGIC ──────────────────────────────────────────────────

function toLocalISOString(d) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function applySessionPreset(preset) {
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

    // Update button styles
    ['8h', '24h', 'today', 'week'].forEach(p => {
        const btn = document.getElementById(`preset-${p}`);
        if (btn) {
            btn.classList.toggle('btn-primary', p === preset);
            btn.classList.toggle('btn-secondary', p !== preset);
        }
    });

    loadSessionSummary();
}

async function loadSessionSummary() {
    const fromValRaw = document.getElementById('sessionFrom').value;
    const toValRaw = document.getElementById('sessionTo').value;
    const results = document.getElementById('sessionResults');

    if (!fromValRaw || !toValRaw) return;

    results.innerHTML = `<div style="text-align:center;padding:1.5rem;color:var(--text-muted);">
        <div class="spinner-small" style="margin:0 auto 10px;"></div>
        Analyzing construction pulse...
    </div>`;

    try {
        const fromVal = new Date(fromValRaw).toISOString();
        const toVal = new Date(toValRaw).toISOString();

        const data = await window.RFQAgentAPI.getSessionSummary(fromVal, toVal);

        if (data.count === 0) {
            results.innerHTML = `
                <div style="text-align:center;padding:2rem;color:var(--text-muted);">
                    <p style="font-size:0.85rem;">No tender emails processed in this time window.</p>
                </div>`;
            return;
        }

        const rows = data.data.map(e => `
            <div class="activity-item" style="display:grid;grid-template-columns: 1fr auto; padding: 12px 16px; border-bottom: 1px solid #f3f4f6;">
                <div>
                    <div style="font-weight:600;font-size:0.85rem;color:var(--text-primary);">${e.subject || '(No Subject)'}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px;">
                        From: ${e.sender} &nbsp;·&nbsp; Processed: ${new Date(e.processed_at).toLocaleTimeString()}
                    </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    ${e.thread_id ? `<span class="badge" style="background:#fff4f0; color:var(--primary-orange); border:1px solid #ffd5cc; font-size:0.65rem;">${e.thread_id}</span>` : ''}
                    <span class="badge" style="background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd; font-size:0.65rem;">${e.doc_count} Docs</span>
                </div>
            </div>
        `).join('');

        results.innerHTML = `
            <div style="font-size:0.7rem; color:var(--text-muted); padding:8px 16px; background:#f8fafc; border-bottom:1px solid #e5e7eb; font-weight:600; text-transform:uppercase;">
                Identified ${data.count} Tender Activity Pulse(s)
            </div>
            ${rows}
        `;
    } catch (err) {
        results.innerHTML = `<div style="padding:1rem;color:var(--accent-red);font-size:0.8rem;">Error: ${err.message}</div>`;
    }
}

function showNotice(msg) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; 
        background: var(--primary-orange); color: white; 
        padding: 12px 24px; border-radius: 8px; 
        box-shadow: var(--shadow-lg); z-index: 9999;
        font-weight: 600; animation: slideUp 0.3s ease-out;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

async function loadTasks() {
    const list = document.getElementById('aiTaskList');
    if (!list) return;

    try {
        console.log('[Dashboard] Loading tasks...');
        const response = await window.RFQAgentAPI.getTasks();
        console.log('[Dashboard] Tasks response:', response);

        if (!response || !response.success) {
            throw new Error(response ? response.error : 'No response from API');
        }

        if (response.data && response.data.length > 0) {
            list.innerHTML = response.data.map(t => `
                <div class="activity-item" style="padding: 12px 16px; align-items: center;">
                    <div class="activity-icon-wrapper" style="background: rgba(156, 39, 176, 0.05);">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9c27b0" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title" style="font-size: 0.8rem; font-weight: 500;">${t.task}</div>
                        <div class="activity-meta" style="font-size: 0.65rem;">From: ${t.sender} &nbsp;·&nbsp; ${t.subject.substring(0, 30)}...</div>
                    </div>
                </div>
            `).join('');
        } else {
            list.innerHTML = `<div style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.8rem;">No action items identified.</div>`;
        }
    } catch (e) { 
        console.error('Tasks load error:', e); 
        list.innerHTML = `<div style="text-align: center; padding: 1rem; color: var(--accent-red); font-size: 0.8rem;">
            Failed to load tasks.<br>
            <small style="opacity: 0.7;">Error: ${e.message}</small>
        </div>`;
    }
}

async function loadPriorityList() {
    const list = document.getElementById('priorityList');
    try {
        const response = await window.RFQAgentAPI.getThreads();
        if (response.success) {
            // Filter for Urgent or Meeting Request or any thread with a meeting suggestion
            const priorities = response.data.filter(t =>
                t.tags.some(tag => ['Urgent', 'Meeting Request', 'High Priority'].includes(tag.name)) ||
                (t.meeting_suggestion && t.meeting_suggestion.start_time)
            ).slice(0, 10); // Increase slice to see more

            if (priorities.length === 0) {
                list.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted);"><p style="font-size: 0.85rem;">No immediate actions required. You are up to date.</p></div>`;
                return;
            }

            list.innerHTML = priorities.map(t => {
                const sug = t.meeting_suggestion;
                const hasMeeting = sug && sug.start_time;

                // Cross-check with calendar stats if needed or just use the booked flag
                const isBooked = sug && sug.booked;

                return `
                    <div class="activity-item" style="flex-direction: column; align-items: flex-start; gap: 8px;">
                        <div onclick="window.location.href='threads.html?id=${t.thread_id}'" style="cursor: pointer; width: 100%; display: flex; justify-content: space-between;">
                            <div style="flex: 1;">
                                <div style="font-weight: 600; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
                                    <span style="color: ${t.status === 'urgent' ? '#f44336' : (hasMeeting && !isBooked ? '#2196f3' : '#6366f1')};">●</span> ${t.subject}
                                </div>
                                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                                    From: ${t.contact_name || 'Unknown'} &nbsp;·&nbsp; ${t.tags.map(tag => `<span class="badge" style="font-size: 0.65rem; padding: 2px 6px; background: ${tag.color}22; color: ${tag.color};">${tag.name}</span>`).join(' ')}
                                </div>
                            </div>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--text-muted);"><polyline points="9 18 15 12 9 6"></polyline></svg>
                        </div>
                        
                        ${hasMeeting && !isBooked ? `
                        <div style="width: 100%; background: rgba(33, 150, 243, 0.05); border: 1px dashed rgba(33, 150, 243, 0.3); border-radius: 6px; padding: 8px; margin-top: 4px; display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-size: 0.75rem; color: var(--text-primary);">
                                <span style="font-weight: 600; color: #2196f3;">Suggested Meeting:</span> ${sug.topic} 
                                <br><span style="color: var(--text-muted); font-size: 0.7rem;">
                                    ${(sug.start_time && !isNaN(new Date(sug.start_time).getTime()))
                            ? new Date(sug.start_time).toLocaleString()
                            : 'Time Pending Confirmation'}
                                </span>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick="bookMeeting('${t.thread_id}')" style="font-size: 0.7rem; padding: 4px 12px; background: #2196f3; border-color: #2196f3; box-shadow: 0 2px 4px rgba(33, 150, 243, 0.2);">
                                Book Now
                            </button>
                        </div>
                        ` : (hasMeeting && isBooked ? `
                        <div style="width: 100%; background: rgba(76, 175, 80, 0.05); border: 1px solid rgba(76, 175, 80, 0.2); border-radius: 6px; padding: 8px; margin-top: 4px; display: flex; align-items: center; gap: 8px;">
                            <div style="width: 20px; height: 20px; border-radius: 50%; background: #4caf50; display: flex; align-items: center; justify-content: center;">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="4"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            </div>
                            <div style="font-size: 0.75rem; color: #2e7d32; font-weight: 600;">Meeting successfully on calendar</div>
                        </div>
                        ` : '')}
                    </div>
                `;
            }).join('');
        }
    } catch (e) { console.error('Priority load error:', e); }
}

async function loadPendingDrafts() {
    const list = document.getElementById('pendingDraftsList');
    try {
        const response = await window.RFQAgentAPI.getDrafts();
        if (response.success && response.data) {
            const drafts = (response.data || []).slice(0, 3);
            if (drafts.length === 0) {
                list.innerHTML = `<div style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.85rem;">No drafts pending approval.</div>`;
                return;
            }

            list.innerHTML = drafts.map(d => `
                <div class="activity-item" onclick="window.location.href='drafts.html'" style="cursor: pointer;">
                    <div style="flex: 1;">
                        <div style="font-weight: 500; font-size: 0.85rem;">Draft for: ${d.subject}</div>
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">Recipient: ${d.to}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) { console.error('Drafts load error:', e); }
}

async function loadAgendaWidget(eventsData = null) {
    const list = document.getElementById('dashboardMeetingsList');
    if (!list) return;

    try {
        let events = eventsData;
        if (!events) {
            const response = await window.RFQAgentAPI.getCalendarEvents(7);
            events = response.success ? response.data : [];
        }

        const now = new Date();
        const upcomingEvents = events.filter(ev => {
            if (!ev.start) return false;
            const evDate = new Date(ev.start);
            if (isNaN(evDate.getTime())) return false;
            // Only show events that haven't ended yet
            const evEnd = ev.end ? new Date(ev.end) : new Date(evDate.getTime() + 30*60000);
            return evEnd > now;
        }).sort((a, b) => new Date(a.start) - new Date(b.start)).slice(0, 5);

        if (upcomingEvents.length === 0) {
            list.innerHTML = `<div style="text-align: center; padding: 1.5rem; color: var(--text-muted);">
                <p style="font-size: 0.85rem;">No more meetings scheduled for today.</p>
            </div>`;
            return;
        }

        list.innerHTML = upcomingEvents.map(ev => {
            const startDate = new Date(ev.start);
            const timeStr = startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const isToday = startDate.toDateString() === now.toDateString();
            const dayStr = isToday ? 'Today' : startDate.toLocaleDateString([], { weekday: 'short', day: 'numeric' });
            
            const attendees = ev.attendees || [];
            const attendeeText = attendees.length > 0 ? 
                `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">With: ${attendees.slice(0, 2).map(a => typeof a === 'string' ? a.split('@')[0] : (a.name || a.email.split('@')[0])).join(', ')}${attendees.length > 2 ? ' + others' : ''}</div>` 
                : '';

            return `
                <div class="activity-item" style="padding: 12px 16px; border-bottom: 1px solid #f3f4f6; flex-direction: column; align-items: flex-start; gap: 4px;">
                    <div style="display: flex; justify-content: space-between; width: 100%; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary);">${ev.title}</div>
                            <div style="font-size: 0.75rem; color: var(--primary-orange); font-weight: 600; margin-top: 2px;">
                                ${dayStr} at ${timeStr}
                            </div>
                            ${attendeeText}
                        </div>
                        ${ev.link ? `
                            <a href="${ev.link}" target="_blank" class="btn btn-primary btn-sm" style="font-size: 0.7rem; padding: 4px 10px; background: #FFF4F0; color: var(--primary-orange); border: 1px solid var(--primary-orange); box-shadow: none;">
                                Join
                            </a>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) { console.error('Agenda load error:', e); }
}

async function loadHoldQueue(eventsData = null) {
    const card = document.getElementById('approvalCenterCard');
    const list = document.getElementById('holdQueueList');
    const badge = document.getElementById('holdCountBadge');
    if (!card || !list) return;

    try {
        let events = eventsData;
        if (!events) {
            const response = await window.RFQAgentAPI.getCalendarEvents(7);
            events = response.success ? response.data : [];
        }
        
        const holds = events.filter(ev => ev.title.includes('[HOLD]'));

        if (badge) badge.textContent = `${holds.length} Pending`;
        card.style.display = holds.length > 0 ? 'block' : 'none';
        
        if (holds.length === 0) return;

        list.innerHTML = holds.map(h => {
                const attendees = h.attendees || [];
                const attendeeLabel = attendees.length > 0
                    ? `<div style="font-size:0.75rem; color:var(--text-secondary); background:rgba(0,0,0,0.03); padding:4px 8px; border-radius:6px; margin-top:8px; display:inline-block;">
                        <strong>Participants:</strong> ${attendees.map(a => a.name || a.email.split('@')[0]).join(', ')}
                       </div>`
                    : '<div style="font-size:0.7rem; color:var(--text-muted); margin-top:8px; font-style:italic;">No other participants added</div>';

                return `
                <div class="activity-item" style="padding: 16px; flex-direction: column; align-items: flex-start; gap: 10px; border-left: 3px solid var(--primary-orange);">
                    <div style="display: flex; justify-content: space-between; width: 100%; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">${h.title.replace('[HOLD]', '').trim()}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                                Scheduled: ${new Date(h.start).toLocaleString()} (${h.source})
                            </div>
                            ${attendeeLabel}
                        </div>
                        <div class="badge" style="background: rgba(255, 92, 53, 0.1); color: var(--primary-orange); font-weight: 700; letter-spacing: 0.5px;">PENDING APPROVAL</div>
                    </div>
                    <div style="display: flex; gap: 8px; width: 100%; margin-top: 5px;">
                        <button class="btn btn-primary btn-sm" onclick="confirmHold('${h.source}', '${h.id}')" style="flex: 1; font-size: 0.78rem; padding: 10px; font-weight: 600;">
                            Approve & Notify Client
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="RFQAgentAPI.deleteCalendarEvent('${h.source}', '${h.id}').then(() => loadDashboardData())" style="padding: 10px; border-color: #fecaca; background: #fef2f2; color: #ef4444;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path></svg>
                        </button>
                    </div>
                </div>
                `;
            }).join('');
    } catch (e) {
        console.error('[HoldQueue] Error loading:', e);
    }
}

async function confirmHold(provider, eventId) {
    try {
        showLoading('Confirming meeting & sending notifications...');
        const resp = await fetch(`${window.location.origin}/api/calendar/events/confirm`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ provider, event_id: eventId })
        });
        const result = await resp.json();
        hideLoading();

        if (result.success) {
            showToast('Meeting confirmed! The client has been notified.', 'success');
            loadDashboardData();
        } else {
            showError('Confirmation failed: ' + result.error);
        }
    } catch (e) {
        hideLoading();
        showError('Network error during confirmation.');
    }
}

async function loadPulseStats() {
    try {
        const response = await window.RFQAgentAPI.getDashboardStats();
        if (response.success) {
            console.log('[Dashboard] Pulse Stats updated:', response.data);
            
            // Update the new top stats grid
            if (document.getElementById('statActiveTenders')) {
                document.getElementById('statActiveTenders').textContent = response.data.activeTenders || 0;
            }
            if (document.getElementById('statUnprocessed')) {
                document.getElementById('statUnprocessed').textContent = response.data.unprocessedEmails || 0;
            }
            if (document.getElementById('statIncomplete')) {
                document.getElementById('statIncomplete').textContent = response.data.incompleteTenders || 0;
            }
            if (document.getElementById('statUrgent')) {
                document.getElementById('statUrgent').textContent = response.data.urgentTasks || 0;
            }

            // Update footer pulse numbers if they exist
            if (document.getElementById('totalPulledNum')) {
                document.getElementById('totalPulledNum').textContent = response.data.unprocessedEmails || 0;
            }
            if (document.getElementById('totalMeetingsNum')) {
                document.getElementById('totalMeetingsNum').textContent = response.data.calendarEvents || 0;
            }

            // Populate the specialized construction widgets
            renderMissingCategories(response.data.topMissingCategories || []);
            loadProjectPulse();
        }
    } catch (e) { console.error('Pulse stats error:', e); }
}

function renderMissingCategories(data) {
    const list = document.getElementById('missingCategoriesList');
    if (!list) return;

    if (!data || data.length === 0) {
        list.innerHTML = `<div style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.8rem;">No systemic document deficits detected.</div>`;
        return;
    }

    list.innerHTML = data.map(cat => `
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
                <span style="font-weight: 600; color: var(--text-primary);">${cat.category}</span>
                <span style="color: #f59e0b; font-weight: 700;">${cat.count} Missing</span>
            </div>
            <div style="height: 6px; background: #fef3c7; border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${Math.min(cat.count * 10, 100)}%; background: #f59e0b;"></div>
            </div>
        </div>
    `).join('');
}

async function loadProjectPulse() {
    const list = document.getElementById('projectPulseList');
    if (!list) return;

    try {
        const response = await window.RFQAgentAPI.getThreads();
        if (response.success) {
            // Get threads with meta_data (deadline or location)
            const pulseData = response.data.filter(t => t.meta_data && (t.meta_data.submission_deadline || t.meta_data.location)).slice(0, 5);

            if (pulseData.length === 0) {
                list.innerHTML = `<div style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.8rem;">No project intelligence extracted yet.</div>`;
                return;
            }

            list.innerHTML = pulseData.map(t => {
                const meta = t.meta_data;
                const deadline = meta.submission_deadline ? new Date(meta.submission_deadline) : null;
                const deadlineStr = deadline && !isNaN(deadline.getTime()) ? deadline.toLocaleDateString() : (meta.submission_deadline || 'N/A');
                
                return `
                    <div style="padding: 10px 0; border-bottom: 1px solid #f3f4f6;">
                        <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary); margin-bottom: 4px;">${t.subject}</div>
                        <div style="display: flex; gap: 15px; font-size: 0.75rem;">
                            <div style="display: flex; align-items: center; gap: 4px; color: #ef4444; font-weight: 600;">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                                Due: ${deadlineStr}
                            </div>
                            <div style="display: flex; align-items: center; gap: 4px; color: var(--text-muted);">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                                ${meta.location || 'Unknown'}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) { console.error('Project pulse error:', e); }
}

async function loadFollowups() {
    const list = document.getElementById('followupList');
    const badge = document.getElementById('followupCountBadge');
    if (!list) return;

    try {
        console.log('[Dashboard] Loading follow-ups...');
        const response = await window.RFQAgentAPI.getFollowups();
        console.log('[Dashboard] Follow-ups response:', response);

        if (!response || !response.success) {
            throw new Error(response ? response.error : 'No response from API');
        }

        const followups = response.data || [];

        if (badge) {
            badge.textContent = `${followups.length} Pending`;
            badge.style.display = followups.length > 0 ? 'inline-block' : 'none';
        }

        if (followups.length === 0) {
            list.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">
                <p>No stale threads detected. All threads are current.</p>
            </div>`;
            return;
        }

        list.innerHTML = followups.map(f => `
            <div class="activity-item" style="flex-direction: column; align-items: flex-start; gap: 8px; padding: 16px;">
                <div style="width: 100%; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">${f.subject}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">To: ${f.recipient}</div>
                    </div>
                    <div style="font-size: 0.7rem; color: #9c27b0; font-weight: 600; background: rgba(156, 39, 176, 0.05); padding: 2px 8px; border-radius: 4px;">
                        No reply in 3 days
                    </div>
                </div>
                
                <div style="background: var(--bg-light); padding: 12px; border-radius: 8px; width: 100%; font-size: 0.8rem; border: 1px solid var(--border-light); line-height: 1.4; color: var(--text-secondary);">
                    "${(f && f.suggested_body) ? f.suggested_body.substring(0, 150) + (f.suggested_body.length > 150 ? '...' : '') : 'No suggestion available'}"
                </div>
                
                <div style="display: flex; gap: 8px; margin-top: 4px; width: 100%;">
                    <button class="btn btn-primary btn-sm" onclick="approveFollowup(${f.id})" style="background: #9c27b0; border-color: #9c27b0; font-size: 0.75rem; padding: 6px 12px;">
                        Approve Draft
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="dismissFollowup(${f.id})" style="font-size: 0.75rem; padding: 6px 12px;">
                        Dismiss
                    </button>
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error('[Dashboard] Follow-up load error:', e);
        list.innerHTML = `<div style="text-align: center; padding: 1rem; color: var(--accent-red); font-size: 0.8rem;">
            Failed to load follow-up suggestions.<br>
            <small style="opacity: 0.7;">Error: ${e.message}</small>
        </div>`;
    }
}

async function approveFollowup(id) {
    try {
        showLoading('Creating draft...');
        const result = await window.RFQAgentAPI.approveFollowup(id);
        hideLoading();

        if (result.status === 'success') {
            showSuccess('Follow-up draft created in your mailbox!');
            loadDashboardData(); // Refresh UI
        } else {
            showError('Failed to create draft.');
        }
    } catch (e) {
        hideLoading();
        showError('Error creating follow-up draft: ' + e.message);
    }
}

let currentBookingThreadId = null;

async function bookMeeting(threadId) {
    currentBookingThreadId = threadId;
    try {
        showLoading('Loading suggestion details...');
        const response = await window.RFQAgentAPI.getThreads();
        hideLoading();

        const thread = response.data.find(t => t.thread_id === threadId);

        if (thread && thread.meeting_suggestion) {
            const sug = thread.meeting_suggestion;

            document.getElementById('bookingTitle').value = sug.topic || thread.subject;
            document.getElementById('bookingAttendees').value = thread.sender_email || "";

            const start = new Date(sug.start_time);
            if (!isNaN(start.getTime())) {
                document.getElementById('bookingDate').value = start.toISOString().split('T')[0];
                document.getElementById('bookingTime').value = start.toTimeString().split(' ')[0].substring(0, 5);
            } else {
                // Fallback to today if invalid
                const today = new Date();
                document.getElementById('bookingDate').value = today.toISOString().split('T')[0];
                document.getElementById('bookingTime').value = "10:00";
            }

            if (document.getElementById('bookingProvider')) {
                document.getElementById('bookingProvider').value = 'google'; // Default
            }

            openBookingModal();
        } else {
            showError('No meeting suggestion found for this thread.');
        }
    } catch (e) {
        hideLoading();
        showError('Could not load suggestion: ' + e.message);
    }
}

function openBookingModal() {
    console.log("DEBUG: Opening Booking Modal");
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
        // Add one-time listener for outside click
        const outsideClickListener = (e) => {
            if (e.target === modal) {
                closeBookingModal();
                modal.removeEventListener('click', outsideClickListener);
            }
        };
        modal.addEventListener('click', outsideClickListener);
    }
}

function closeBookingModal() {
    console.log("DEBUG: Closing Booking Modal (Force)");
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.classList.remove('active');
        // Force hide with style if class removal fails to trigger CSS
        modal.style.display = 'none';

        // Remove 'active' class from all other potential modals just in case
        document.querySelectorAll('.modal').forEach(m => {
            m.classList.remove('active');
            m.style.display = 'none';
        });
    }
    currentBookingThreadId = null;

    // Also reset form fields
    const fields = ['bookingTitle', 'bookingAttendees', 'bookingDate', 'bookingTime'];
    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) el.value = '';
    });
}

// Global escape key listener
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeBookingModal();
    }
});

// Expose to window for inline onclicks
window.closeBookingModal = closeBookingModal;
window.openBookingModal = openBookingModal;
window.bookMeeting = bookMeeting;
window.handleBookingSubmit = handleBookingSubmit;

async function handleBookingSubmit(event) {
    event.preventDefault();
    const btn = document.getElementById('btnConfirmBooking');
    const originalText = btn.textContent;

    const attendeesRaw = document.getElementById('bookingAttendees').value;
    const attendees = attendeesRaw.split(',').map(e => e.trim()).filter(e => e);

    // Email Validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    for (const email of attendees) {
        if (!emailRegex.test(email)) {
            showError(`Invalid email address: ${email}`);
            return;
        }
    }

    btn.disabled = true;
    btn.textContent = 'Scheduling...';

    try {
        const date = document.getElementById('bookingDate').value;
        const time = document.getElementById('bookingTime').value;
        const start = new Date(`${date}T${time}:00`);
        const end = new Date(start.getTime() + 60 * 60000); // Default 1 hour

        const meetingData = {
            title: document.getElementById('bookingTitle').value,
            attendees: document.getElementById('bookingAttendees').value.split(',').map(e => e.trim()).filter(e => e),
            start_time: start.toISOString(),
            end_time: end.toISOString(),
            provider: document.getElementById('bookingProvider').value,
            description: `Booked via Dashboard Suggestion for Thread: ${currentBookingThreadId}`,
            thread_id: currentBookingThreadId,
            notify_guests: document.getElementById('bookingNotifyGuests').checked
        };

        const result = await window.RFQAgentAPI.createCalendarEvent(meetingData);
        if (result.success) {
            showSuccess('Meeting scheduled successfully.');
            closeBookingModal();
            loadDashboardData();
        } else {
            showError('Failed: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        showError('Error: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function loadRecentActivity() { }
// Redundant session summary code removed.



// Note: applyPreset('today') is now handled in the main DOMContentLoaded listener

// Quick Action: Process Emails
// Note: This is now handled in the main checkAgentStatus loop and processEmails trigger below.
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

// Duplicate checkAgentStatus removed.

// Quick Action: View Threads
function viewThreads() {
    window.location.href = 'threads.html';
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
