// Submittery v2 - Frontend Controller & Router
let apiBaseUrl = window.location.origin;

// State Management
let currentToken = localStorage.getItem("token") || null;
let currentUser = null;
let problems = [];
let userSubmissions = [];
let currentProblem = null;
let lastSubmissionId = null;
let editorLoaded = false;
let wsSub = null;
let wsCollab = null;

let isCollaborating = false;
let currentRoomCode = null;
let currentActiveView = "home";
let activeConsoleTab = "result";

// Filter state
let filterDifficulty = "all";
let googleClientId = null;

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
    // Theme Initializer
    const savedTheme = localStorage.getItem("theme") || "dark";
    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
        const toggleIcon = document.getElementById("theme-toggle-icon");
        if (toggleIcon) toggleIcon.className = "fa-solid fa-moon text-xs";
    }
    
    initMonaco();
    initGoogleAuth();
    checkAuth();
    loadProblems();
    initDraggableDividers();
    
    // Check if room parameter exists in URL queries
    const urlParams = new URLSearchParams(window.location.search);
    const roomParam = urlParams.get('room');
    if (roomParam) {
        document.getElementById("lobby-join-code-input").value = roomParam;
        navigateTo("collab");
        setTimeout(() => {
            if (currentToken) {
                joinCollaborationRoom(roomParam);
            } else {
                showAuthModal();
            }
        }, 1000);
    }
    
    // Setup AI chat input listener for Enter key
    const aiInput = document.getElementById("wai-chat-input");
    if (aiInput) {
        aiInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                triggerAIAction("ask");
            }
        });
    }
    
    // Setup Collab chat input listener for Enter key
    const chatInput = document.getElementById("collab-chat-input");
    if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendCollabChatMessage();
            }
        });
    }
});

async function initGoogleAuth() {
    try {
        const config = await request("/auth/config");
        if (config && config.google_client_id) {
            googleClientId = config.google_client_id;
            console.log("[*] Google OAuth configured with Client ID:", googleClientId.substring(0, 15) + "...");
        }
    } catch (e) {
        console.log("[*] Auth config note:", e);
    }
}

// View Navigation Router
function navigateTo(viewName) {
    // Security Access Guard Redirect
    if (viewName === "admin" && (!currentUser || currentUser.role !== "admin")) {
        viewName = "home";
    }
    
    currentActiveView = viewName;
    
    // Deactivate all sections and header buttons
    const sections = document.querySelectorAll(".view-section");
    sections.forEach(sec => sec.classList.remove("active", "flex"));
    sections.forEach(sec => sec.classList.add("hidden"));
    
    const navButtons = document.querySelectorAll("nav button");
    navButtons.forEach(btn => {
        const isHidden = btn.id === "nav-admin" && (!currentUser || currentUser.role !== "admin");
        if (isHidden) {
            btn.className = "hidden px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-400 hover:text-slate-200 transition";
        } else {
            btn.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-400 hover:text-slate-200 transition";
        }
    });
    
    // Activate target section
    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
        targetSection.classList.remove("hidden");
        targetSection.classList.add("active", "flex");
    }
    
    // Highlight nav button
    const targetNav = document.getElementById(`nav-${viewName}`);
    if (targetNav) {
        const isHidden = targetNav.id === "nav-admin" && (!currentUser || currentUser.role !== "admin");
        if (isHidden) {
            targetNav.className = "hidden px-3.5 py-1.5 rounded-lg text-sm font-semibold text-brand-500 bg-brand-500/10 transition";
        } else {
            targetNav.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-brand-500 bg-brand-500/10 transition";
        }
    }
    
    // Refresh stats if navigating to dashboard
    if (viewName === "dashboard") {
        calculateUserStats();
    }
    // Refresh admin data if navigating to admin
    if (viewName === "admin" && currentUser?.role === "admin") {
        loadAdminData();
    }
    
    // Trigger Monaco Editor layout update if returning to workspace
    if (viewName === "workspace" && window.editor) {
        setTimeout(() => window.editor.layout(), 100);
    }
}

// Interactive Draggable Dividers (LeetCode-style vertical and horizontal panels)
function initDraggableDividers() {
    const verticalDivider = document.getElementById("vertical-divider");
    const horizontalDivider = document.getElementById("horizontal-divider");
    
    const leftPane = document.getElementById("workspace-left-pane");
    const rightPane = document.getElementById("workspace-right-pane");
    
    const editorPane = document.getElementById("workspace-editor-pane");
    const consolePane = document.getElementById("workspace-console-pane");
    const workspaceContainer = document.getElementById("view-workspace");
    
    // Vertical Divider Dragging
    if (verticalDivider) {
        verticalDivider.addEventListener("mousedown", (e) => {
            e.preventDefault();
            verticalDivider.classList.add("dragging");
            document.addEventListener("mousemove", onMouseMoveVertical);
            document.addEventListener("mouseup", onMouseUpVertical);
        });
    }
    
    function onMouseMoveVertical(e) {
        const containerWidth = workspaceContainer.clientWidth;
        let leftWidth = e.clientX;
        
        // Boundaries: 20% to 80%
        if (leftWidth < containerWidth * 0.2) leftWidth = containerWidth * 0.2;
        if (leftWidth > containerWidth * 0.8) leftWidth = containerWidth * 0.8;
        
        leftPane.style.width = `${leftWidth}px`;
        // Account for vertical handle width (6px)
        rightPane.style.width = `${containerWidth - leftWidth - 6}px`;
        
        if (window.editor) window.editor.layout();
    }
    
    function onMouseUpVertical() {
        verticalDivider.classList.remove("dragging");
        document.removeEventListener("mousemove", onMouseMoveVertical);
        document.removeEventListener("mouseup", onMouseUpVertical);
        if (window.editor) window.editor.layout();
    }
    
    // Horizontal Divider Dragging
    if (horizontalDivider) {
        horizontalDivider.addEventListener("mousedown", (e) => {
            e.preventDefault();
            horizontalDivider.classList.add("dragging");
            document.addEventListener("mousemove", onMouseMoveHorizontal);
            document.addEventListener("mouseup", onMouseUpHorizontal);
        });
    }
    
    function onMouseMoveHorizontal(e) {
        const rightPaneHeight = rightPane.clientHeight;
        const rightPaneRect = rightPane.getBoundingClientRect();
        
        let topHeight = e.clientY - rightPaneRect.top;
        
        // Boundaries: 20% to 80%
        if (topHeight < rightPaneHeight * 0.2) topHeight = rightPaneHeight * 0.2;
        if (topHeight > rightPaneHeight * 0.8) topHeight = rightPaneHeight * 0.8;
        
        editorPane.style.height = `${topHeight}px`;
        // Account for horizontal handle height (6px)
        consolePane.style.height = `${rightPaneHeight - topHeight - 6}px`;
        
        if (window.editor) window.editor.layout();
    }
    
    function onMouseUpHorizontal() {
        horizontalDivider.classList.remove("dragging");
        document.removeEventListener("mousemove", onMouseMoveHorizontal);
        document.removeEventListener("mouseup", onMouseUpHorizontal);
        if (window.editor) window.editor.layout();
    }
}

// Monaco Editor Initialization
let peerCursorDecorations = {};
let activeRoomPeers = new Set();
let isReceivingRemoteSync = false;
let hostedProblemSlug = null;
let currentTestcaseMode = "samples";
let collabChatUnreadCount = 0;
let collabMessages = [];

function initMonaco() {
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.46.0/min/vs' } });
    require(['vs/editor/editor.main'], function () {
        const savedTheme = localStorage.getItem("theme") || "dark";
        window.editor = monaco.editor.create(document.getElementById('monaco-editor-workspace'), {
            value: 'def solve():\n    # Select a problem to start coding\n    pass',
            language: 'python',
            theme: savedTheme === "light" ? 'vs' : 'vs-dark',
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
            automaticLayout: true,
            minimap: { enabled: false }
        });
        editorLoaded = true;
        
        // Broadcast code modifications to peers in collab mode
        window.editor.onDidChangeModelContent((event) => {
            if (isCollaborating && wsCollab && wsCollab.readyState === WebSocket.OPEN) {
                if (!isReceivingRemoteSync) {
                    const code = window.editor.getValue();
                    wsCollab.send(JSON.stringify({
                        type: "sync-code",
                        code: code
                    }));
                }
            }
        });

        // Broadcast cursor position telemetry to peers in collab mode
        window.editor.onDidChangeCursorPosition((event) => {
            if (isCollaborating && wsCollab && wsCollab.readyState === WebSocket.OPEN) {
                wsCollab.send(JSON.stringify({
                    type: "sync-cursor",
                    user: currentUser?.username || "Peer",
                    position: {
                        lineNumber: event.position.lineNumber,
                        column: event.position.column
                    }
                }));
            }
        });

        // Broadcast selection telemetry to peers in collab mode
        window.editor.onDidChangeCursorSelection((event) => {
            if (isCollaborating && wsCollab && wsCollab.readyState === WebSocket.OPEN) {
                if (!event.selection.isEmpty()) {
                    wsCollab.send(JSON.stringify({
                        type: "sync-selection",
                        user: currentUser?.username || "Peer",
                        selection: {
                            startLineNumber: event.selection.startLineNumber,
                            startColumn: event.selection.startColumn,
                            endLineNumber: event.selection.endLineNumber,
                            endColumn: event.selection.endColumn
                        }
                    }));
                }
            }
        });
    });
}

function renderPeerCursor(user, position) {
    if (!window.editor || !position) return;
    const oldDecs = peerCursorDecorations[user] || [];
    const newDecs = window.editor.deltaDecorations(oldDecs, [
        {
            range: new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column + 1),
            options: {
                className: 'remote-peer-cursor',
                hoverMessage: { value: `**${user}** is editing here` }
            }
        }
    ]);
    peerCursorDecorations[user] = newDecs;
    registerActivePeer(user);
}

function renderPeerSelection(user, selection) {
    if (!window.editor || !selection) return;
    const oldDecs = peerCursorDecorations[`${user}_sel`] || [];
    const newDecs = window.editor.deltaDecorations(oldDecs, [
        {
            range: new monaco.Range(selection.startLineNumber, selection.startColumn, selection.endLineNumber, selection.endColumn),
            options: {
                className: 'remote-peer-selection',
                hoverMessage: { value: `Selection by **${user}**` }
            }
        }
    ]);
    peerCursorDecorations[`${user}_sel`] = newDecs;
    registerActivePeer(user);
}

function registerActivePeer(user) {
    if (!user || user === currentUser?.username) return;
    activeRoomPeers.add(user);
    updatePeerBadge();
}

function updatePeerBadge() {
    const badge = document.getElementById("ws-peer-presence-badge");
    const text = document.getElementById("ws-peer-count-text");
    if (!badge || !text) return;
    const count = activeRoomPeers.size;
    if (count > 0 && isCollaborating) {
        badge.classList.remove("hidden");
        text.innerText = `${count} Peer${count > 1 ? 's' : ''}`;
    } else {
        badge.classList.add("hidden");
    }
}

// Math equations formatting
function formatMathFormulas() {
    if (typeof renderMathInElement === 'function') {
        renderMathInElement(document.getElementById("workspace-description-container"), {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\[', display: true}
            ],
            throwOnError : false
        });
        
        renderMathInElement(document.getElementById("wai-response-box"), {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ],
            throwOnError : false
        });
    }
}

// REST helper Client
async function request(endpoint, options = {}) {
    const url = `${apiBaseUrl}/api${endpoint}`;
    const headers = { ...options.headers };
    if (currentToken) {
        headers["Authorization"] = `Bearer ${currentToken}`;
    }
    
    const requestOptions = {
        ...options,
        headers
    };
    
    const response = await fetch(url, requestOptions);
    
    if (response.status === 401) {
        localStorage.removeItem("token");
        currentToken = null;
        currentUser = null;
        updateUIForAuth();
        showAuthModal();
        throw new Error("Unauthorized");
    }
    
    if (!response.ok) {
        const errText = await response.text();
        let errMsg = "An error occurred";
        try {
            const errJson = JSON.parse(errText);
            errMsg = errJson.detail || errMsg;
        } catch (e) {}
        throw new Error(errMsg);
    }
    
    if (response.status === 204) return null;
    return response.json();
}

// Auth credentials verification
async function checkAuth() {
    if (!currentToken) {
        updateUIForAuth();
        document.getElementById("nav-admin").classList.add("hidden");
        return;
    }
    try {
        currentUser = await request("/auth/me");
        updateUIForAuth();
        
        if (currentUser.role === "admin") {
            document.getElementById("nav-admin").classList.remove("hidden");
            loadAdminData();
        } else {
            document.getElementById("nav-admin").classList.add("hidden");
        }
        
        calculateUserStats();
    } catch (e) {
        console.error("Auth check failed:", e);
    }
}

// Update Header for Auth State
function updateUIForAuth() {
    const section = document.getElementById("header-auth-box");
    if (currentUser) {
        let avatarSrc = currentUser.avatar_url || ('https://api.dicebear.com/7.x/bottts/svg?seed=' + encodeURIComponent(currentUser.username));
        if (avatarSrc.startsWith('http%3A') || avatarSrc.startsWith('https%3A')) {
            avatarSrc = decodeURIComponent(avatarSrc);
        }

        section.innerHTML = `
            <div class="flex items-center space-x-3 bg-dark-200 border border-slate-800/80 px-3 py-1.5 rounded-xl">
                <img src="${avatarSrc}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser.username)}'" class="h-6 w-6 rounded-full border border-slate-750 bg-slate-800">
                <span class="text-xs font-semibold text-slate-300">${currentUser.username}</span>
                <span class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-500 font-mono border border-brand-500/20">${currentUser.role}</span>
                <button onclick="openSettingsModal()" class="text-slate-500 hover:text-brand-500 transition ml-2" title="Profile Settings">
                    <i class="fa-solid fa-gear text-[11px]"></i>
                </button>
                <button onclick="handleLogout()" class="text-slate-500 hover:text-red-400 transition" title="Log Out">
                    <i class="fa-solid fa-power-off text-[11px]"></i>
                </button>
            </div>
        `;
        
        // Update user stats username
        const dashUser = document.getElementById("dash-username");
        if (dashUser) dashUser.innerText = currentUser.username;
        const dashAvatar = document.getElementById("dash-avatar-container");
        if (dashAvatar) {
            dashAvatar.innerHTML = `<img src="${avatarSrc}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser.username)}'" class="h-9 w-9 rounded-full bg-slate-800 border border-slate-700">`;
        }
    } else {
        section.innerHTML = `
            <button onclick="showAuthModal()" class="px-4 py-1.5 text-xs font-bold rounded-lg bg-brand-500 hover:bg-brand-600 text-dark-300 shadow-md shadow-brand-500/10 transition active:scale-95">
                <i class="fa-solid fa-arrow-right-to-bracket mr-1.5"></i>Sign In
            </button>
        `;
    }
}

// Modals
function showAuthModal() {
    const modal = document.getElementById("auth-modal");
    modal.classList.remove("hidden");
    setTimeout(() => {
        modal.classList.remove("opacity-0");
        modal.querySelector("div").classList.remove("scale-95");
    }, 50);
}

function hideAuthModal() {
    const modal = document.getElementById("auth-modal");
    modal.classList.add("opacity-0");
    modal.querySelector("div").classList.add("scale-95");
    setTimeout(() => modal.classList.add("hidden"), 300);
}

function switchAuthTab(tab) {
    const loginTab = document.getElementById("auth-tab-login");
    const signupTab = document.getElementById("auth-tab-signup");
    const formLogin = document.getElementById("form-login");
    const formSignup = document.getElementById("form-signup");
    
    if (tab === "login") {
        loginTab.className = "flex-1 pb-2 border-b-2 border-brand-500 text-brand-500";
        signupTab.className = "flex-1 pb-2 border-b-2 border-transparent text-slate-500 hover:text-slate-350";
        formLogin.classList.remove("hidden");
        formSignup.classList.add("hidden");
    } else {
        signupTab.className = "flex-1 pb-2 border-b-2 border-brand-500 text-brand-500";
        loginTab.className = "flex-1 pb-2 border-b-2 border-transparent text-slate-500 hover:text-slate-350";
        formSignup.classList.remove("hidden");
        formLogin.classList.add("hidden");
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const id = document.getElementById("login-id").value;
    const pass = document.getElementById("login-password").value;
    const formData = new FormData();
    formData.append("username", id);
    formData.append("password", pass);
    
    try {
        const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) throw new Error("Incorrect credentials");
        const data = await response.json();
        currentToken = data.access_token;
        localStorage.setItem("token", currentToken);
        currentUser = data.user;
        updateUIForAuth();
        hideAuthModal();
        if (currentUser.role === "admin") {
            document.getElementById("nav-admin").classList.remove("hidden");
            loadAdminSubmissions();
        } else {
            document.getElementById("nav-admin").classList.add("hidden");
        }
        loadProblems();
        calculateUserStats();
    } catch (err) {
        alert(err.message);
    }
}

async function handleSignupSubmit(e) {
    e.preventDefault();
    const username = document.getElementById("signup-username").value;
    const email = document.getElementById("signup-email").value;
    const password = document.getElementById("signup-password").value;
    
    try {
        const res = await fetch(`${apiBaseUrl}/api/auth/signup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, username, password })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Signup failed");
        }
        
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);
        const logRes = await fetch(`${apiBaseUrl}/api/auth/login`, {
            method: "POST",
            body: formData
        });
        
        const data = await logRes.json();
        currentToken = data.access_token;
        localStorage.setItem("token", currentToken);
        currentUser = data.user;
        updateUIForAuth();
        hideAuthModal();
        loadProblems();
        calculateUserStats();
    } catch (err) {
        alert(err.message);
    }
}

async function handleGoogleOAuth() {
    // If real Google Client ID is configured and Google SDK is loaded
    if (googleClientId && window.google && window.google.accounts && window.google.accounts.oauth2) {
        try {
            const tokenClient = google.accounts.oauth2.initTokenClient({
                client_id: googleClientId,
                scope: 'email profile openid',
                prompt: 'select_account',
                callback: async (tokenResponse) => {
                    if (tokenResponse && tokenResponse.access_token) {
                        try {
                            const userInfoResp = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                                headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
                            });
                            const userInfo = await userInfoResp.json();
                            if (!userInfo.email) {
                                alert("Failed to retrieve Google email address.");
                                return;
                            }
                            
                            const realToken = `mock_${userInfo.email}::${encodeURIComponent(userInfo.name || userInfo.email.split('@')[0])}::${encodeURIComponent(userInfo.picture || '')}`;
                            const data = await request("/auth/google", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ id_token: realToken })
                            });
                            
                            currentToken = data.access_token;
                            localStorage.setItem("token", currentToken);
                            currentUser = data.user;
                            updateUIForAuth();
                            hideAuthModal();
                            if (currentUser.role === "admin") {
                                document.getElementById("nav-admin").classList.remove("hidden");
                                loadAdminSubmissions();
                            } else {
                                document.getElementById("nav-admin").classList.add("hidden");
                            }
                            loadProblems();
                            calculateUserStats();
                        } catch (err) {
                            alert("Google OAuth Login Error: " + err.message);
                        }
                    }
                }
            });
            tokenClient.requestAccessToken();
            return;
        } catch (e) {
            console.log("[*] Real Google OAuth error, falling back to dev mode:", e);
        }
    }
    
    // Developer fallback if no Google Client ID configured
    const rand = Math.floor(Math.random() * 10000);
    const mockEmail = `dev_oauth_${rand}@submittery.com`;
    const mockToken = `mock_${mockEmail}::OAuthDev_${rand}::https://api.dicebear.com/7.x/bottts/svg?seed=${rand}`;
    
    try {
        const data = await request("/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: mockToken })
        });
        
        currentToken = data.access_token;
        localStorage.setItem("token", currentToken);
        currentUser = data.user;
        updateUIForAuth();
        hideAuthModal();
        if (currentUser.role === "admin") {
            document.getElementById("nav-admin").classList.remove("hidden");
            loadAdminSubmissions();
        } else {
            document.getElementById("nav-admin").classList.add("hidden");
        }
        loadProblems();
        calculateUserStats();
    } catch (err) {
        alert("Google OAuth: " + err.message);
    }
}

function handleLogout() {
    localStorage.removeItem("token");
    currentToken = null;
    currentUser = null;
    problems = [];
    userSubmissions = [];
    currentProblem = null;
    updateUIForAuth();
    document.getElementById("nav-admin").classList.add("hidden");
    navigateTo("home");
    leaveCollaborationRoom();
}

// Load Problems Catalog
async function loadProblems() {
    if (!currentToken) return;
    try {
        problems = await request("/problems/");
        renderProblemsTable();
        renderAdminProblemsTable();
        populateLobbySelect();
        const statEl = document.getElementById("home-stat-starter-problems");
        if (statEl) statEl.innerText = problems.length;
        const adminStatProblems = document.getElementById("admin-stat-problems");
        if (adminStatProblems) adminStatProblems.innerText = problems.length;
        
        // Restore persistent collab session if active in localStorage
        restoreCollabSession();
    } catch (e) {
        console.error("Failed to load problems:", e);
    }
}

// User Dashboard Statistics compiler (Single Batch Request O(1))
async function calculateUserStats() {
    if (!currentToken || problems.length === 0) return;
    
    try {
        const submissionsLog = await request("/submissions/me");
        userSubmissions = (submissionsLog || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        renderUserDashboardSubmissions();
        
        // Calculate solved count stats
        const solvedProblemIds = new Set();
        userSubmissions.forEach(sub => {
            if (sub.status === "accepted") {
                solvedProblemIds.add(sub.problem_id);
            }
        });
        
        let easySolved = 0;
        let mediumSolved = 0;
        let hardSolved = 0;
        
        problems.forEach(p => {
            if (solvedProblemIds.has(p.id)) {
                if (p.difficulty === "easy") easySolved++;
                if (p.difficulty === "medium") mediumSolved++;
                if (p.difficulty === "hard") hardSolved++;
            }
        });
        
        const totalSolved = solvedProblemIds.size;
        const totalProblems = problems.length;
        const percentage = totalProblems > 0 ? (totalSolved / totalProblems) * 100 : 0;
        
        const countEl = document.getElementById("solved-stats-count");
        if (countEl) countEl.innerText = `${totalSolved} / ${totalProblems}`;
        const barEl = document.getElementById("solved-stats-progressbar");
        if (barEl) barEl.style.width = `${percentage}%`;
        const easyEl = document.getElementById("stats-easy-count");
        if (easyEl) easyEl.innerText = easySolved;
        const medEl = document.getElementById("stats-medium-count");
        if (medEl) medEl.innerText = mediumSolved;
        const hardEl = document.getElementById("stats-hard-count");
        if (hardEl) hardEl.innerText = hardSolved;
        
    } catch (e) {
        console.error("Failed to compute stats:", e);
    }
}

function renderUserDashboardSubmissions() {
    const container = document.getElementById("dash-submissions-log");
    if (userSubmissions.length === 0) {
        container.innerHTML = `<div class="text-slate-500 text-center py-10">No recent submissions found.</div>`;
        return;
    }
    
    // Show latest 6 runs
    const recent = userSubmissions.slice(0, 6);
    container.innerHTML = recent.map(sub => {
        const prob = problems.find(p => p.id === sub.problem_id);
        const name = prob ? prob.title : "Algorithm";
        const dateStr = new Date(sub.created_at).toLocaleDateString();
        
        let statusBadge = "text-red-400 bg-red-500/10 border-red-500/20";
        if (sub.status === "accepted") statusBadge = "text-brand-400 bg-brand-500/10 border-brand-500/20";
        if (sub.status === "wrong_answer") statusBadge = "text-amber-500 bg-amber-500/10 border-amber-500/20";
        
        return `
            <div class="glass-card p-3 rounded-lg border-slate-850 flex items-center justify-between">
                <div>
                    <div class="font-bold text-slate-300 truncate max-w-[150px]">${name}</div>
                    <div class="text-xs text-slate-500 font-mono">${dateStr} | ${sub.language}</div>
                </div>
                <div class="text-xs font-bold uppercase tracking-wider px-2 py-0.5 border rounded ${statusBadge}">
                    ${sub.status.replace("_", " ")}
                </div>
            </div>
        `;
    }).join("");
}

// Problems Explorer filters and renders
function filterProblemsDifficulty(diff) {
    filterDifficulty = diff;
    
    // Toggle active filter styles
    const diffs = ["all", "easy", "medium", "hard"];
    diffs.forEach(d => {
        const btn = document.getElementById(`diff-btn-${d}`);
        if (btn) {
            if (d === diff) {
                btn.className = "px-2.5 py-1 rounded text-xs font-bold uppercase bg-brand-500/10 text-brand-500 border border-brand-500/20";
            } else {
                btn.className = "px-2.5 py-1 rounded text-xs font-bold uppercase text-slate-400 hover:text-slate-205 border border-transparent";
            }
        }
    });
    
    renderProblemsTable();
}

function filterProblemsList() {
    renderProblemsTable();
}

function handleProblemSearchInput(e) {
    if (e && e.key === "Enter") {
        runSemanticSearch();
        return;
    }
    renderProblemsTable();
}

async function runSemanticSearch() {
    const input = document.getElementById("prob-search-input");
    const query = input ? input.value.trim() : "";
    if (!query) {
        renderProblemsTable();
        return;
    }
    
    const tbody = document.getElementById("problems-tbody-list");
    tbody.innerHTML = `<tr><td colspan="4" class="text-brand-400 text-center py-10"><i class="fa-solid fa-spinner animate-spin mr-2"></i>Searching problem concepts via RAG embeddings...</td></tr>`;
    
    try {
        const results = await request("/ai/semantic-search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query, limit: 10 })
        });
        
        if (!results || results.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-slate-500 text-center py-10">No semantic matches found for "${query}".</td></tr>`;
            return;
        }
        
        tbody.innerHTML = results.map((p, idx) => {
            let diffBadge = "text-brand-400 bg-brand-500/10 border-brand-500/20";
            if (p.difficulty === "medium") diffBadge = "text-amber-400 bg-amber-500/10 border border-amber-500/20";
            if (p.difficulty === "hard") diffBadge = "text-rose-400 bg-rose-500/10 border border-rose-500/20";
            
            const tagsHtml = (p.tags || []).map(t => `<span class="text-[11px] bg-slate-800 border border-slate-700/80 px-1.5 py-0.5 rounded text-slate-450 font-semibold">${t}</span>`).join(" ");
            
            const matchScore = p.similarity ? Math.round(p.similarity * 100) : null;
            const scoreBadge = matchScore ? `<span class="ml-2 text-[10px] bg-brand-500/20 text-brand-300 border border-brand-500/30 px-1.5 py-0.5 rounded font-mono">${matchScore}% Match</span>` : '';
            
            return `
                <tr class="border-b border-slate-850 hover:bg-slate-900/20 transition group">
                    <td class="py-3 px-3">
                        <div class="font-bold text-slate-200 group-hover:text-brand-400 transition text-sm flex items-center">
                            <span>${p.title}</span>
                            ${scoreBadge}
                        </div>
                        <div class="text-[11px] text-slate-400 mt-1 line-clamp-1 italic">${p.matched_concept || ''}</div>
                    </td>
                    <td class="py-3 px-3">
                        <span class="text-[10px] uppercase font-bold px-2 py-0.5 border rounded ${diffBadge}">${p.difficulty}</span>
                    </td>
                    <td class="py-3 px-3 flex items-center flex-wrap gap-1.5">${tagsHtml}</td>
                    <td class="py-3 px-3 text-right">
                        <button onclick="openWorkspace('${p.slug}')" class="px-3.5 py-1 bg-slate-800 hover:bg-brand-500 hover:text-dark-300 text-slate-300 text-sm font-bold rounded-lg transition active:scale-95 border border-slate-700 hover:border-transparent">
                            Solve
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        console.error("Semantic search error:", e);
        renderProblemsTable();
    }
}

const neetcodeTopicTagMap = {
    "arrays-hashing": ["array", "hash-table", "prefix-sum"],
    "two-pointers": ["two-pointers"],
    "sliding-window": ["sliding-window"],
    "stack": ["stack"],
    "binary-search": ["binary-search"],
    "linked-list": ["linked-list"],
    "trees": ["trees", "tree", "bfs-dfs"],
    "tries": ["trie", "tries"],
    "heap-priority-queue": ["heap", "priority-queue"],
    "backtracking": ["backtracking"],
    "graphs": ["graph", "graphs", "bfs-dfs", "matrix"],
    "advanced-graphs": ["advanced-graph", "advanced-graphs"],
    "1d-dp": ["dynamic-programming", "1d-dp"],
    "2d-dp": ["dynamic-programming", "2d-dp"],
    "greedy": ["greedy"],
    "intervals": ["intervals", "interval"],
    "math-geometry": ["math", "geometry", "matrix"],
    "bit-manipulation": ["bit-manipulation"]
};

function renderProblemsTable() {
    const tbody = document.getElementById("problems-tbody-list");
    const query = document.getElementById("prob-search-input").value.trim().toLowerCase();
    
    let filtered = problems;
    
    // Filter by difficulty
    if (filterDifficulty !== "all") {
        filtered = filtered.filter(p => p.difficulty === filterDifficulty);
    }
    
    // Filter by query
    if (query) {
        filtered = filtered.filter(p => p.title.toLowerCase().includes(query));
    }
    
    // Filter by NeetCode Topic
    const topicSelect = document.getElementById("prob-neetcode-topic-select");
    const selectedTopic = topicSelect ? topicSelect.value : "all";
    if (selectedTopic !== "all") {
        const allowedTags = neetcodeTopicTagMap[selectedTopic] || [];
        filtered = filtered.filter(p => {
            const pTags = p.tags || [];
            return pTags.some(t => allowedTags.includes(t.toLowerCase()));
        });
    }
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-slate-500 text-center py-10">No problems found matching filters.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = filtered.map(p => {
        let diffBadge = "text-brand-400 bg-brand-500/10 border-brand-500/20";
        if (p.difficulty === "medium") diffBadge = "text-amber-400 bg-amber-500/10 border border-amber-500/20";
        if (p.difficulty === "hard") diffBadge = "text-rose-400 bg-rose-500/10 border border-rose-500/20";
        
        const tagsHtml = (p.tags || []).map(t => `<span class="text-[11px] bg-slate-800 border border-slate-700/80 px-1.5 py-0.5 rounded text-slate-450 font-semibold">${t}</span>`).join(" ");
        
        const pIndex = problems.findIndex(prob => prob.id === p.id) + 1;
        
        return `
            <tr class="border-b border-slate-850 hover:bg-slate-900/20 transition group">
                <td class="py-3 px-3 font-bold text-slate-200 group-hover:text-brand-400 transition text-sm">#${pIndex}. ${p.title}</td>
                <td class="py-3 px-3">
                    <span class="text-[10px] uppercase font-bold px-2 py-0.5 border rounded ${diffBadge}">${p.difficulty}</span>
                </td>
                <td class="py-3 px-3 flex items-center flex-wrap gap-1.5">${tagsHtml}</td>
                <td class="py-3 px-3 text-right">
                    <button onclick="openWorkspace('${p.slug}')" class="px-3.5 py-1 bg-slate-800 hover:bg-brand-500 hover:text-dark-300 text-slate-300 text-sm font-bold rounded-lg transition active:scale-95 border border-slate-700 hover:border-transparent">
                        Solve
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

// --- LEETCODE-STYLE RESIZABLE WORKSPACE CONTROLS ---

async function openWorkspace(slug, initialCode = null) {
    try {
        currentProblem = await request(`/problems/${slug}`);
        
        const pIndex = problems.findIndex(prob => prob.id === currentProblem.id) + 1;
        
        // Hide top navigation and other views to maximize workspace area
        navigateTo("workspace");
        
        document.getElementById("workspace-problem-label").innerText = ` / #${pIndex}. ${currentProblem.title}`;
        
        // Render Details
        renderWorkspaceProblemDetails(pIndex);
        
        // Set starter template code with remote sync protection
        if (editorLoaded && window.editor) {
            isReceivingRemoteSync = true;
            if (initialCode !== null) {
                window.editor.setValue(initialCode);
            } else if (!isCollaborating) {
                window.editor.setValue(currentProblem.starter_code?.python || "");
            } else if (!window.editor.getValue() || window.editor.getValue().includes("Select a problem")) {
                window.editor.setValue(currentProblem.starter_code?.python || "");
            }
            setTimeout(() => { isReceivingRemoteSync = false; }, 150);
        }
        
        resetConsoleWorkspace();
        renderTestcasesTab();
        loadSubmissionHistoryWorkspace();
        loadDiscussionWorkspace();
        loadAIRecommendations();
        
        // Ensure Collab Chat tab is only shown if actively collaborating
        const chatTab = document.getElementById("wconsole-tab-chat");
        if (chatTab) {
            if (isCollaborating) {
                chatTab.classList.remove("hidden");
            } else {
                chatTab.classList.add("hidden");
                if (activeConsoleTab === "chat") {
                    switchConsoleTab("testcases");
                }
            }
        }
        
        // Reset left pane tab to description
        switchLeftTab("description");
        
        // Trigger resize layout to ensure editor bounds adapt
        setTimeout(() => {
            if (window.editor) window.editor.layout();
        }, 150);
        
    } catch (e) {
        alert("Failed to load problem: " + e.message);
    }
}

function switchTestcaseMode(mode) {
    currentTestcaseMode = mode;
    const samplesBtn = document.getElementById("tc-mode-samples-btn");
    const customBtn = document.getElementById("tc-mode-custom-btn");
    const samplesContainer = document.getElementById("tc-samples-container");
    const customContainer = document.getElementById("tc-custom-container");
    
    if (mode === "samples") {
        if (samplesBtn) samplesBtn.className = "px-3 py-1 bg-brand-500/15 text-brand-400 border border-brand-500/30 rounded-lg font-bold text-[10px] uppercase tracking-wider transition";
        if (customBtn) customBtn.className = "px-3 py-1 bg-dark-300 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-lg font-bold text-[10px] uppercase tracking-wider transition";
        if (samplesContainer) samplesContainer.classList.remove("hidden");
        if (customContainer) customContainer.classList.add("hidden");
    } else {
        if (customBtn) customBtn.className = "px-3 py-1 bg-brand-500/15 text-brand-400 border border-brand-500/30 rounded-lg font-bold text-[10px] uppercase tracking-wider transition";
        if (samplesBtn) samplesBtn.className = "px-3 py-1 bg-dark-300 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-lg font-bold text-[10px] uppercase tracking-wider transition";
        if (samplesContainer) samplesContainer.classList.add("hidden");
        if (customContainer) customContainer.classList.remove("hidden");
    }
}

function renderTestcasesTab() {
    if (!currentProblem) return;
    const list = document.getElementById("tc-samples-list");
    if (!list) return;
    const sampleCases = currentProblem.test_cases ? currentProblem.test_cases.filter(tc => tc.is_sample) : [];
    if (sampleCases.length === 0) {
        list.innerHTML = `<div class="text-slate-500 text-xs py-4 text-center">No sample cases available for this problem.</div>`;
        return;
    }
    
    list.innerHTML = sampleCases.map((tc, idx) => `
        <div class="glass-card p-3 rounded-lg border border-slate-800 space-y-2">
            <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Case ${idx + 1}</div>
            <div class="grid grid-cols-2 gap-3 text-xs font-mono">
                <div>
                    <span class="text-slate-500 text-[10px] block mb-1">Input:</span>
                    <pre class="bg-dark-300 p-2 rounded border border-slate-850 text-slate-300 overflow-x-auto text-[11px]">${escapeHtml(tc.input)}</pre>
                </div>
                <div>
                    <span class="text-slate-500 text-[10px] block mb-1">Expected Output:</span>
                    <pre class="bg-dark-300 p-2 rounded border border-slate-850 text-brand-400 overflow-x-auto text-[11px]">${escapeHtml(tc.expected_output)}</pre>
                </div>
            </div>
        </div>
    `).join("");
}

function resetStarterCode() {
    if (!currentProblem || !window.editor) return;
    const starter = currentProblem.starter_code?.python || "def solve():\n    # Read inputs\n    pass\n";
    window.editor.setValue(starter);
    if (isCollaborating && wsCollab && wsCollab.readyState === WebSocket.OPEN) {
        wsCollab.send(JSON.stringify({
            type: "sync-code",
            code: starter
        }));
    }
}

async function loadAIRecommendations() {
    if (!currentProblem) return;
    const container = document.getElementById("w-ai-recommendations-container");
    if (!container) return;
    
    try {
        const recs = await request(`/ai/recommend/${currentProblem.id}`);
        if (!recs || recs.length === 0) {
            container.innerHTML = "";
            return;
        }
        
        container.innerHTML = `
            <div class="glass-card p-4 rounded-xl border border-brand-500/20 bg-brand-500/5 space-y-3 mt-4">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold text-brand-400 uppercase tracking-widest flex items-center">
                        <i class="fa-solid fa-wand-magic-sparkles mr-1.5"></i>AI Recommended Challenges
                    </span>
                    <span class="text-[9px] text-slate-500 font-mono">Semantic RAG</span>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    ${recs.map(r => `
                        <div onclick="openWorkspace('${r.slug}')" class="bg-dark-300 p-2.5 rounded-lg border border-slate-850 hover:border-brand-500/40 cursor-pointer transition flex items-center justify-between group">
                            <div>
                                <div class="font-bold text-slate-200 group-hover:text-brand-400 text-xs transition">${r.title}</div>
                                <div class="text-[9px] text-slate-500 font-mono capitalize">${r.difficulty_str || r.difficulty}</div>
                            </div>
                            <span class="text-xs text-brand-500 group-hover:translate-x-1 transition"><i class="fa-solid fa-arrow-right"></i></span>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    } catch (e) {
        console.error("Failed to load recommendations:", e);
    }
}

function exitWorkspace() {
    navigateTo("dashboard");
    resetConsoleWorkspace();
    leaveCollaborationRoom();
}

function renderWorkspaceProblemDetails(pIndex) {
    const container = document.getElementById("workspace-description-container");
    let diffBadge = "text-brand-400 bg-brand-500/10 border border-brand-500/20";
    if (currentProblem.difficulty === "medium") diffBadge = "text-amber-400 bg-amber-500/10 border border-amber-500/20";
    if (currentProblem.difficulty === "hard") diffBadge = "text-rose-400 bg-rose-500/10 border border-rose-500/20";
    
    const tagsHtml = (currentProblem.tags || []).map(t => `<span class="text-[11px] bg-slate-800 border border-slate-700/80 px-2 py-0.5 rounded text-slate-400 font-semibold">${t}</span>`).join(" ");
    
    const sampleCases = (currentProblem.test_cases || []).filter(tc => tc.is_sample);
    const sampleCasesHtml = sampleCases.map((tc, idx) => `
        <div class="glass-card rounded-xl p-4 space-y-3 font-mono text-xs border-slate-850 select-text">
            <div class="flex items-center justify-between border-b border-slate-800/80 pb-2">
                <span class="font-sans font-bold text-slate-400 text-[11px]">Example ${idx + 1}</span>
            </div>
            <div>
                <div class="text-[11px] text-slate-500 mb-0.5">Input:</div>
                <pre class="bg-black/30 p-2 rounded border border-slate-850 text-slate-350 whitespace-pre overflow-x-auto select-all text-xs">${tc.input}</pre>
            </div>
            <div>
                <div class="text-[11px] text-slate-500 mb-0.5">Expected Output:</div>
                <pre class="bg-black/30 p-2 rounded border border-slate-850 text-brand-400 whitespace-pre overflow-x-auto select-all text-xs">${tc.expected_output}</pre>
            </div>
        </div>
    `).join("");

    container.innerHTML = `
        <div class="space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-lg font-bold text-slate-100 font-sans">#${pIndex}. ${currentProblem.title}</h2>
                <span class="text-[10px] uppercase font-bold px-2 py-0.5 border rounded ${diffBadge}">${currentProblem.difficulty}</span>
            </div>
            
            <div class="flex flex-wrap gap-1.5">
                ${tagsHtml}
            </div>
            
            <div class="flex items-center space-x-6 text-[10px] text-slate-500 py-2 border-y border-slate-800/50 font-mono">
                <span>Time Limit: <strong class="text-slate-400">${currentProblem.time_limit}s</strong></span>
                <span>Memory Limit: <strong class="text-slate-400">${currentProblem.memory_limit}MB</strong></span>
            </div>
            
            <div class="prose prose-invert text-sm max-w-none text-slate-350 leading-relaxed space-y-3 font-sans select-text">
                ${renderMarkdownAndMath(currentProblem.description)}
            </div>

            <div class="space-y-3 pt-2">
                <h3 class="font-bold text-slate-300 text-xs">Example Cases</h3>
                ${sampleCasesHtml}
            </div>
        </div>
    `;
}

function resetConsoleWorkspace() {
    document.getElementById("wconsole-default-msg").classList.remove("hidden");
    document.getElementById("wjudge-status-block").classList.add("hidden");
    document.getElementById("wjudge-error-block").classList.add("hidden");
    
    // Clear test cases visualizer
    const testcasesContainer = document.getElementById("wconsole-testcases-container");
    if (testcasesContainer) {
        testcasesContainer.innerHTML = "";
        testcasesContainer.classList.add("hidden");
    }
    
    // Ensure Collab Chat tab is only visible when actively collaborating
    const chatTab = document.getElementById("wconsole-tab-chat");
    if (chatTab) {
        if (!isCollaborating) {
            chatTab.classList.add("hidden");
            if (activeConsoleTab === "chat") {
                switchConsoleTab("testcases");
            }
        } else {
            chatTab.classList.remove("hidden");
        }
    }
    
    const btnReview = document.getElementById("wbtn-ai-review");
    if (btnReview) {
        btnReview.disabled = true;
        btnReview.classList.add("text-slate-500");
    }
    const btnHints = document.getElementById("wbtn-ai-hints");
    if (btnHints) {
        btnHints.disabled = true;
        btnHints.classList.add("text-slate-500");
    }
    
    lastSubmissionId = null;
    closeWebSocketSub();
}

// LeetCode-style Run code on samples or custom input
async function runCode() {
    if (!currentProblem) return;
    switchConsoleTab("result");
    
    document.getElementById("wconsole-default-msg").classList.add("hidden");
    document.getElementById("wjudge-status-block").classList.remove("hidden");
    document.getElementById("wjudge-error-block").classList.add("hidden");
    
    const isCustom = currentTestcaseMode === "custom" && document.getElementById("tc-custom-input") && document.getElementById("tc-custom-input").value.trim() !== "";
    const customVal = isCustom ? document.getElementById("tc-custom-input").value.trim() : null;
    
    setVerdictLabelWorkspace(isCustom ? "RUNNING CUSTOM INPUT" : "RUNNING SAMPLE CASES", "text-brand-400", "fa-solid fa-spinner animate-spin text-brand-400");
    document.getElementById("wverdict-runtime").innerText = "--";
    document.getElementById("wverdict-memory").innerText = "--";
    
    try {
        const bodyPayload = {
            code: window.editor.getValue(),
            language: "python"
        };
        if (customVal !== null) {
            bodyPayload.custom_input = customVal;
        }
        
        const results = await request(`/submissions/run/${currentProblem.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyPayload)
        });
        
        let overallVerdict = isCustom ? "FINISHED" : "ACCEPTED";
        let colorClass = "text-brand-400";
        let iconClass = "fa-solid fa-circle-check text-brand-400";
        let maxRuntime = 0;
        let maxMemory = 0;
        let errMsg = "";
        
        for (let res of results) {
            maxRuntime = Math.max(maxRuntime, res.runtime || 0);
            maxMemory = Math.max(maxMemory, res.memory || 0);
            
            if (res.status !== "accepted" && overallVerdict === "ACCEPTED") {
                overallVerdict = res.status.toUpperCase().replace("_", " ");
                colorClass = "text-amber-500";
                iconClass = "fa-solid fa-circle-xmark text-amber-500";
                errMsg = res.error || "Execution failed";
            }
        }
        
        const totalCases = results.length;
        const passedCases = results.filter(r => r.status === "accepted").length;
        let label = overallVerdict;
        if (!isCustom && totalCases > 0) {
            label += ` (${passedCases}/${totalCases} Cases Passed)`;
        } else if (isCustom) {
            label = "CUSTOM INPUT EXECUTED";
        }
        
        setVerdictLabelWorkspace(label, colorClass, iconClass);
        document.getElementById("wverdict-id").innerText = isCustom ? "Custom" : "Sample Run";
        document.getElementById("wverdict-runtime").innerText = `${maxRuntime.toFixed(3)}s`;
        document.getElementById("wverdict-memory").innerText = `${(maxMemory / 1024).toFixed(1)}MB`;
        
        if (errMsg) {
            document.getElementById("wjudge-error-block").classList.remove("hidden");
            document.getElementById("wjudge-error-text").innerText = errMsg;
        }
        
        // Render LeetCode-style test cases list
        renderTestcasesOutput(results);
    } catch (e) {
        setVerdictLabelWorkspace("RUN ERROR", "text-red-500", "fa-solid fa-circle-exclamation text-red-500");
        document.getElementById("wjudge-error-block").classList.remove("hidden");
        document.getElementById("wjudge-error-text").innerText = e.message;
    }
}

// LeetCode-style Submit code permanently
async function submitCode() {
    if (!currentProblem) return;
    switchConsoleTab("result");
    
    document.getElementById("wconsole-default-msg").classList.add("hidden");
    document.getElementById("wjudge-status-block").classList.remove("hidden");
    document.getElementById("wjudge-error-block").classList.add("hidden");
    
    setVerdictLabelWorkspace("QUEUED", "text-slate-450", "fa-solid fa-spinner animate-spin text-slate-450");
    document.getElementById("wverdict-runtime").innerText = "--";
    document.getElementById("wverdict-memory").innerText = "--";
    
    try {
        const sub = await request(`/submissions/submit/${currentProblem.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: window.editor.getValue(), language: "python" })
        });
        
        lastSubmissionId = sub.id;
        document.getElementById("wverdict-id").innerText = sub.id.substring(0, 8);
        
        listenForSubmissionUpdatesWorkspace(sub.id);
    } catch (e) {
        setVerdictLabelWorkspace("SUBMIT ERROR", "text-red-500", "fa-solid fa-circle-exclamation text-red-500");
        document.getElementById("wjudge-error-block").classList.remove("hidden");
        document.getElementById("wjudge-error-text").innerText = e.message;
    }
}

function setVerdictLabelWorkspace(text, colorClass, iconClass) {
    const label = document.getElementById("wverdict-label");
    const iconContainer = document.getElementById("wverdict-icon");
    
    label.innerText = text;
    label.className = `font-bold text-xs uppercase tracking-wider ${colorClass}`;
    
    iconContainer.innerHTML = `<i class="${iconClass}"></i>`;
    iconContainer.className = `h-9 w-9 rounded-lg flex items-center justify-center text-sm ${colorClass} bg-dark-300 border border-slate-800/40`;
}

function closeWebSocketSub() {
    if (wsSub) {
        wsSub.close();
        wsSub = null;
    }
}

function listenForSubmissionUpdatesWorkspace(submissionId) {
    closeWebSocketSub();
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/submissions/${submissionId}`;
    
    wsSub = new WebSocket(wsUrl);
    
    wsSub.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const status = data.status;
        
        if (status === "queued") {
            setVerdictLabelWorkspace("QUEUED", "text-slate-450", "fa-solid fa-spinner animate-spin text-slate-455");
        } else if (status === "running") {
            setVerdictLabelWorkspace("RUNNING SUITE", "text-brand-400", "fa-solid fa-spinner animate-spin text-brand-400");
        } else {
            // Completed
            displayFinalVerdictWorkspace(data);
            closeWebSocketSub();
            // Refresh tables and stats
            loadSubmissionHistoryWorkspace();
            calculateUserStats();
        }
    };
}

function displayFinalVerdictWorkspace(data) {
    const status = data.status;
    const runtime = data.runtime;
    const memory = data.memory;
    const error = data.error_message;
    
    // Always hide and reset error block first
    const errorBlock = document.getElementById("wjudge-error-block");
    const errorText = document.getElementById("wjudge-error-text");
    if (errorBlock) errorBlock.classList.add("hidden");
    if (errorText) errorText.innerText = "";
    
    const btnReview = document.getElementById("wbtn-ai-review");
    if (btnReview) {
        btnReview.disabled = false;
        btnReview.classList.remove("text-slate-500");
    }
    
    let colorClass = "text-red-400";
    let iconClass = "fa-solid fa-circle-xmark text-red-400";
    
    const totalCases = data.results ? data.results.length : 0;
    const passedCases = data.results ? data.results.filter(r => r.status === "accepted").length : 0;
    let label = status.toUpperCase().replace("_", " ");
    if (totalCases > 0) {
        label += ` (${passedCases}/${totalCases} Cases Passed)`;
    }
    
    const btnHints = document.getElementById("wbtn-ai-hints");
    if (status === "accepted") {
        colorClass = "text-brand-400";
        iconClass = "fa-solid fa-circle-check text-brand-400";
        setVerdictLabelWorkspace(label, colorClass, iconClass);
        const elRuntime = document.getElementById("wverdict-runtime");
        const elMemory = document.getElementById("wverdict-memory");
        if (elRuntime) elRuntime.innerText = runtime ? `${runtime}s` : "--";
        if (elMemory) elMemory.innerText = memory ? `${(memory / 1024).toFixed(1)}MB` : "--";
        
        // Disable debug hints on accepted submissions if element exists
        if (btnHints) {
            btnHints.disabled = true;
            btnHints.classList.add("text-slate-500");
        }
    } else {
        if (btnHints) {
            btnHints.disabled = false;
            btnHints.classList.remove("text-slate-500");
        }
        
        if (status === "wrong_answer") {
            colorClass = "text-amber-500";
            iconClass = "fa-solid fa-circle-xmark text-amber-500";
        }
        
        setVerdictLabelWorkspace(label, colorClass, iconClass);
        const elRuntime = document.getElementById("wverdict-runtime");
        const elMemory = document.getElementById("wverdict-memory");
        if (elRuntime) elRuntime.innerText = runtime ? `${runtime}s` : "--";
        if (elMemory) elMemory.innerText = memory ? `${(memory / 1024).toFixed(1)}MB` : "--";
        
        if (error && errorBlock && errorText) {
            errorBlock.classList.remove("hidden");
            errorText.innerText = error;
        }
    }
    
    // Reset RAG diagnostic banner
    const ragBanner = document.getElementById("wrag-diagnostic-banner");
    if (ragBanner) {
        if (status !== "accepted") {
            ragBanner.classList.remove("hidden");
        } else {
            ragBanner.classList.add("hidden");
        }
    }
    
    // Render LeetCode-style test cases list
    renderTestcasesOutput(data.results);
}

// Load Workspace Submission History logs
async function loadSubmissionHistoryWorkspace() {
    if (!currentProblem) return;
    const container = document.getElementById("whistory-list");
    container.innerHTML = `<div class="text-slate-500 text-xs py-4 text-center">Loading logs...</div>`;
    
    try {
        const list = await request(`/submissions/problem/${currentProblem.id}`);
        if (list.length === 0) {
            container.innerHTML = `<div class="text-slate-500 text-xs py-6 text-center">No submissions yet for this problem.</div>`;
            return;
        }
        
        window.historicalSubmissions = list;
        
        container.innerHTML = list.map(sub => {
            let statusColor = "text-red-400";
            if (sub.status === "accepted") statusColor = "text-brand-400";
            if (sub.status === "wrong_answer") statusColor = "text-amber-500";
            
            const timeStr = new Date(sub.created_at).toLocaleString();
            
            return `
                <div onclick="loadHistoricalCode('${sub.id}')" class="glass-card p-3 rounded-lg flex items-center justify-between cursor-pointer border-slate-850 hover:border-brand-500/30 transition">
                    <div class="flex items-center space-x-3">
                        <i class="fa-solid fa-code text-slate-600"></i>
                        <div>
                            <div class="text-xs font-bold ${statusColor} uppercase">${sub.status.replace("_", " ")}</div>
                            <div class="text-[9px] text-slate-500">${timeStr}</div>
                        </div>
                    </div>
                    <div class="text-right text-[10px] space-y-0.5 font-mono">
                        <div class="text-slate-300">${sub.runtime ? sub.runtime + 's' : '--'}</div>
                        <div class="text-slate-500">${sub.memory ? (sub.memory / 1024).toFixed(1) + 'MB' : '--'}</div>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        container.innerHTML = `<div class="text-red-400 text-xs text-center py-4">Error loading history: ${e.message}</div>`;
    }
}

// Workspace Console Tab switcher
function switchConsoleTab(tab) {
    activeConsoleTab = tab;
    const tabs = ["testcases", "result", "ai", "discussions", "chat"];
    
    if (tab === "chat") {
        collabChatUnreadCount = 0;
        updateCollabChatBadge();
    }
    if (tab === "testcases") {
        renderTestcasesTab();
    }
    
    tabs.forEach(t => {
        const btn = document.getElementById(`wconsole-tab-${t}`);
        const content = document.getElementById(`wconsole-content-${t}`);
        if (!btn || !content) return;
        
        const isChatHidden = (t === "chat" && !isCollaborating);
        const hiddenClass = isChatHidden ? "hidden " : "";
        
        if (t === tab) {
            btn.className = `${hiddenClass}px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider border-b-2 border-brand-500 text-brand-500 transition`;
            content.classList.remove("hidden");
        } else {
            btn.className = `${hiddenClass}px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition`;
            content.classList.add("hidden");
        }
    });
}

// AI panel integration workspace
async function triggerAIAction(action) {
    if (!currentProblem) return;
    const responseBox = document.getElementById("wai-response-box");
    switchConsoleTab("ai");
    
    responseBox.innerHTML = `
        <div class="flex items-center justify-center py-10 text-brand-400 text-xs">
            <i class="fa-solid fa-spinner animate-spin text-sm mr-2"></i>
            <span>AI Mentor is compiling answer...</span>
        </div>
    `;
    
    try {
        let endpoint = "";
        let body = {};
        
        if (action === "complexity") {
            endpoint = "/ai/analyze-complexity";
            body = {
                code: window.editor.getValue(),
                problem_id: currentProblem.id
            };
        } else if (action === "review") {
            if (!lastSubmissionId) return;
            endpoint = `/ai/code-review/${lastSubmissionId}`;
        } else if (action === "hints") {
            if (!lastSubmissionId) return;
            endpoint = `/ai/debug-hints/${lastSubmissionId}`;
        } else if (action === "rag-diagnose") {
            endpoint = "/ai/diagnose-failure";
            body = {
                problem_id: currentProblem.id,
                submission_id: lastSubmissionId,
                code: window.editor ? window.editor.getValue() : ""
            };
        } else if (action === "ask") {
            const input = document.getElementById("wai-chat-input");
            const question = input.value.trim();
            if (!question) return;
            
            endpoint = "/ai/ask";
            body = {
                question: question,
                problem_id: currentProblem.id,
                code: window.editor ? window.editor.getValue() : ""
            };
            input.value = "";
        }
        
        const data = await request(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: Object.keys(body).length ? JSON.stringify(body) : null
        });
        
        responseBox.innerHTML = `<div class="prose prose-invert text-sm max-w-none space-y-2 leading-relaxed font-sans select-text">${marked.parse(data.response)}</div>`;
        
        setTimeout(formatMathFormulas, 100);
        
    } catch (e) {
        responseBox.innerHTML = `<div class="text-red-400 text-xs py-4"><i class="fa-solid fa-circle-exclamation mr-2"></i>AI Error: ${e.message}</div>`;
    }
}

// Trigger Tiered Socratic Hints grounded in vector knowledge base
async function triggerSocraticHint(tier) {
    if (!currentProblem) return;
    const responseBox = document.getElementById("wai-response-box");
    switchConsoleTab("ai");
    
    const tierNames = { 1: "Tier 1: High-Level Intuition", 2: "Tier 2: State Invariant", 3: "Tier 3: Edge Cases" };
    responseBox.innerHTML = `
        <div class="flex items-center justify-center py-10 text-brand-400 text-xs">
            <i class="fa-solid fa-spinner animate-spin text-sm mr-2"></i>
            <span>Retrieving ${tierNames[tier] || `Tier ${tier}`} hint from vector knowledge base...</span>
        </div>
    `;
    
    try {
        const data = await request("/ai/socratic-hint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                problem_id: currentProblem.id,
                code: window.editor.getValue(),
                tier: tier
            })
        });
        
        responseBox.innerHTML = `
            <div class="mb-2 pb-2 border-b border-slate-800 flex items-center justify-between text-xs text-brand-400 font-semibold">
                <span><i class="fa-solid fa-lightbulb mr-1.5"></i>${data.title || `Tier ${tier} Socratic Hint`}</span>
                <span class="text-[10px] text-slate-500 uppercase tracking-wider">Non-Spoiling RAG</span>
            </div>
            <div class="prose prose-invert text-sm max-w-none space-y-2 leading-relaxed font-sans select-text">${marked.parse(data.response)}</div>
        `;
        setTimeout(formatMathFormulas, 100);
    } catch (e) {
        responseBox.innerHTML = `<div class="text-red-400 text-xs py-4"><i class="fa-solid fa-circle-exclamation mr-2"></i>AI Error: ${e.message}</div>`;
    }
}

// Discussions workspace
async function loadDiscussionWorkspace() {
    const container = document.getElementById("wdiscussions-container");
    container.innerHTML = `<div class="text-slate-500 text-xs py-4 text-center">Loading comments...</div>`;
    
    try {
        const comments = await request(`/discussion/problem/${currentProblem.id}`);
        if (comments.length === 0) {
            container.innerHTML = `<div class="text-slate-500 text-xs py-6 text-center">No comments posted yet.</div>`;
            return;
        }
        
        container.innerHTML = comments.map(c => `
            <div class="glass-card p-3 rounded-lg border-slate-850 space-y-1 text-xs">
                <div class="flex items-center justify-between text-[10px]">
                    <div class="flex items-center space-x-2">
                        <img src="${c.user.avatar_url || 'https://api.dicebear.com/7.x/bottts/svg?seed=' + c.user.username}" class="h-5 w-5 rounded-full bg-slate-800 border border-slate-700">
                        <span class="font-bold text-slate-300">${c.user.username}</span>
                    </div>
                    <span class="text-slate-500 font-mono">${new Date(c.created_at).toLocaleDateString()}</span>
                </div>
                <p class="text-slate-400 pl-7 whitespace-pre-wrap select-text">${c.content}</p>
            </div>
        `).join("");
    } catch (e) {
        container.innerHTML = `<div class="text-red-400 text-xs py-4 text-center">Failed to load: ${e.message}</div>`;
    }
}

async function postComment() {
    const input = document.getElementById("wcomment-input");
    const content = input.value.trim();
    if (!content) return;
    
    try {
        await request(`/discussion/problem/${currentProblem.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content })
        });
        
        input.value = "";
        loadDiscussionWorkspace();
    } catch (e) {
        alert("Comment failed: " + e.message);
    }
}

// --- COLLABORATION LOBBY ENDPOINTS ---

function populateLobbySelect() {
    const select = document.getElementById("lobby-collab-problem-select");
    if (!select) return;
    select.innerHTML = problems.map(p => `
        <option value="${p.slug}">${p.title} (${p.difficulty.toUpperCase()})</option>
    `).join("");
}

function createCollaborationRoom() {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "";
    for (let i = 0; i < 6; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    const select = document.getElementById("lobby-collab-problem-select");
    const problemSlug = select ? select.value : (problems[0] ? problems[0].slug : null);
    if (!problemSlug) {
        alert("Please select a problem to host.");
        return;
    }
    hostedProblemSlug = problemSlug;
    
    localStorage.setItem("submittery_collab_session", JSON.stringify({
        roomCode: code,
        isCreator: true,
        problemSlug: problemSlug
    }));
    
    const selectedProblem = problems.find(p => p.slug === problemSlug);
    const titleEl = document.getElementById("lobby-active-problem-title");
    if (titleEl) {
        titleEl.innerText = selectedProblem ? selectedProblem.title : problemSlug;
    }
    document.getElementById("lobby-room-code-display").innerText = code;
    document.getElementById("lobby-active-room-card").classList.remove("hidden");
    document.getElementById("ws-collab-active-indicator").classList.remove("hidden");
    
    connectCollabWS(code, true, problemSlug);
}

function enterHostedWorkspace() {
    const slug = hostedProblemSlug || (currentProblem ? currentProblem.slug : null);
    if (!slug) return;
    openWorkspace(slug);
    if (wsCollab && wsCollab.readyState === WebSocket.OPEN) {
        wsCollab.send(JSON.stringify({
            type: "sync-problem",
            slug: slug
        }));
        if (window.editor) {
            setTimeout(() => {
                if (wsCollab && wsCollab.readyState === WebSocket.OPEN) {
                    wsCollab.send(JSON.stringify({
                        type: "sync-code",
                        code: window.editor.getValue()
                    }));
                }
            }, 300);
        }
    }
}

async function joinCollaborationRoom(code = null) {
    if (!code) {
        code = document.getElementById("lobby-join-code-input").value.trim().toUpperCase();
    }
    
    if (!code || code.length < 4) {
        alert("Please input a valid room code!");
        return;
    }
    
    code = code.trim().toUpperCase();
    
    try {
        const roomInfo = await request(`/ws/room/${code}`);
        if (!roomInfo || !roomInfo.exists) {
            alert(`Collaboration session '${code}' was not found or has expired. Please verify the room code.`);
            return;
        }
        
        const problemSlug = roomInfo.problem_slug;
        hostedProblemSlug = problemSlug;
        
        localStorage.setItem("submittery_collab_session", JSON.stringify({
            roomCode: code,
            isCreator: false,
            problemSlug: problemSlug
        }));
        
        const selectedProblem = problems.find(p => p.slug === problemSlug);
        const titleEl = document.getElementById("lobby-active-problem-title");
        if (titleEl) {
            titleEl.innerText = selectedProblem ? selectedProblem.title : problemSlug;
        }
        document.getElementById("lobby-room-code-display").innerText = code;
        document.getElementById("lobby-active-room-card").classList.remove("hidden");
        document.getElementById("ws-collab-active-indicator").classList.remove("hidden");
        
        connectCollabWS(code, false, problemSlug);
        
        // Directly redirect joiner into the problem workspace with live code
        if (problemSlug) {
            await openWorkspace(problemSlug, roomInfo.current_code || null);
        }
    } catch (e) {
        alert("Error joining session: " + e.message);
    }
}

async function restoreCollabSession() {
    try {
        const saved = localStorage.getItem("submittery_collab_session");
        if (!saved) return;
        const session = JSON.parse(saved);
        if (!session || !session.roomCode) return;
        
        const code = session.roomCode.trim().toUpperCase();
        const roomInfo = await request(`/ws/room/${code}`);
        if (roomInfo && roomInfo.exists) {
            const slug = roomInfo.problem_slug || session.problemSlug;
            hostedProblemSlug = slug;
            
            const selectedProblem = problems.find(p => p.slug === slug);
            const titleEl = document.getElementById("lobby-active-problem-title");
            if (titleEl) {
                titleEl.innerText = selectedProblem ? selectedProblem.title : slug;
            }
            
            document.getElementById("lobby-room-code-display").innerText = code;
            document.getElementById("lobby-active-room-card").classList.remove("hidden");
            document.getElementById("ws-collab-active-indicator").classList.remove("hidden");
            
            connectCollabWS(code, session.isCreator, slug);
        } else {
            localStorage.removeItem("submittery_collab_session");
        }
    } catch (e) {
        console.log("Collab session restore note:", e);
    }
}

function connectCollabWS(roomCode, isCreator, problemSlug = null) {
    roomCode = roomCode.trim().toUpperCase();
    if (wsCollab && wsCollab.readyState === WebSocket.OPEN && currentRoomCode === roomCode) {
        return; // Already actively connected
    }
    
    if (wsCollab) {
        try { wsCollab.close(); } catch(e) {}
        wsCollab = null;
    }
    
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/collaboration/${roomCode}`;
    
    wsCollab = new WebSocket(wsUrl);
    isCollaborating = true;
    currentRoomCode = roomCode;
    
    wsCollab.onopen = () => {
        document.getElementById("lobby-room-code-display").innerText = roomCode;
        document.getElementById("lobby-active-room-card").classList.remove("hidden");
        document.getElementById("ws-collab-active-indicator").classList.remove("hidden");
        
        // Show Collab Chat tab in console
        const chatTab = document.getElementById("wconsole-tab-chat");
        if (chatTab) chatTab.classList.remove("hidden");
        const chatRoomBadge = document.getElementById("collab-chat-room-badge");
        if (chatRoomBadge) chatRoomBadge.innerText = roomCode;
        
        // Announce presence to peers
        wsCollab.send(JSON.stringify({
            type: "peer-join",
            user: currentUser?.username || "Peer"
        }));
        
        if (isCreator && problemSlug) {
            hostedProblemSlug = problemSlug;
            const selectedProblem = problems.find(p => p.slug === problemSlug);
            const starter = selectedProblem?.starter_code?.python || "";
            
            // Persist room metadata to Redis (preserving live code if already exists)
            wsCollab.send(JSON.stringify({
                type: "init-room",
                slug: problemSlug,
                user: currentUser?.username || "Host",
                code: starter
            }));
            console.log(`Hosted persistent room ${roomCode} for problem: ${problemSlug}`);
        } else {
            // Joiner requests immediate context sync
            wsCollab.send(JSON.stringify({
                type: "request-sync",
                user: currentUser?.username || "Peer"
            }));
        }
    };
    
    wsCollab.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === "sync-problem") {
                hostedProblemSlug = data.slug;
                if (!currentProblem || currentProblem.slug !== data.slug) {
                    openWorkspace(data.slug);
                }
            } else if (data.type === "room-closed") {
                alert(data.reason || "The collaboration session was ended.");
                leaveCollaborationRoom();
                navigateTo("collab");
            } else if (data.type === "request-sync" || data.type === "peer-join") {
                registerActivePeer(data.user);
                // Host/Peer broadcasts active problem and code to the joining peer
                const activeSlug = currentProblem?.slug || hostedProblemSlug;
                if (activeSlug && wsCollab && wsCollab.readyState === WebSocket.OPEN) {
                    wsCollab.send(JSON.stringify({
                        type: "sync-problem",
                        slug: activeSlug
                    }));
                    if (window.editor) {
                        const currentCode = window.editor.getValue();
                        setTimeout(() => {
                            if (wsCollab && wsCollab.readyState === WebSocket.OPEN) {
                                wsCollab.send(JSON.stringify({
                                    type: "sync-code",
                                    code: currentCode
                                }));
                            }
                        }, 250);
                    }
                }
            } else if (data.type === "sync-code" && window.editor) {
                const currentVal = window.editor.getValue();
                if (data.code !== currentVal) {
                    isReceivingRemoteSync = true;
                    const state = window.editor.saveViewState();
                    window.editor.setValue(data.code);
                    if (state) window.editor.restoreViewState(state);
                    setTimeout(() => { isReceivingRemoteSync = false; }, 100);
                }
            } else if (data.type === "chat-msg") {
                if (data.user !== currentUser?.username) {
                    renderCollabMessage({
                        user: data.user,
                        avatar: data.avatar,
                        text: data.text,
                        time: data.time,
                        isSelf: false
                    });
                    if (activeConsoleTab !== "chat") {
                        collabChatUnreadCount++;
                        updateCollabChatBadge();
                    }
                }
            } else if (data.type === "sync-cursor") {
                renderPeerCursor(data.user, data.position);
            } else if (data.type === "sync-selection") {
                renderPeerSelection(data.user, data.selection);
            } else if (data.type === "peer-leave") {
                activeRoomPeers.delete(data.user);
                if (peerCursorDecorations[data.user] && window.editor) {
                    peerCursorDecorations[data.user] = window.editor.deltaDecorations(peerCursorDecorations[data.user], []);
                }
                updatePeerBadge();
            }
        } catch (e) {
            console.error("Collab sync parse error:", e);
        }
    };
    
    wsCollab.onclose = () => {
        console.log("Collab connection offline");
    };
}

function sendCollabChatMessage() {
    const input = document.getElementById("collab-chat-input");
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    
    const user = currentUser?.username || "Guest";
    const avatar = currentUser?.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${user}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    if (wsCollab && wsCollab.readyState === WebSocket.OPEN) {
        wsCollab.send(JSON.stringify({
            type: "chat-msg",
            user: user,
            avatar: avatar,
            text: text,
            time: time
        }));
    }
    
    renderCollabMessage({ user, avatar, text, time, isSelf: true });
    input.value = "";
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function renderCollabMessage(msg) {
    const container = document.getElementById("collab-chat-messages");
    if (!container) return;
    
    // Remove placeholder if present
    if (container.children.length === 1 && container.children[0].innerText.includes("No messages yet")) {
        container.innerHTML = "";
    }
    
    const bubble = document.createElement("div");
    if (msg.isSelf) {
        bubble.className = "flex items-start justify-end space-x-2";
        bubble.innerHTML = `
            <div class="max-w-[75%] space-y-0.5 text-right">
                <div class="flex items-center justify-end space-x-1.5 text-[9px] text-slate-500 font-mono">
                    <span class="font-bold text-brand-400">You</span>
                    <span>${msg.time}</span>
                </div>
                <div class="bg-brand-500/20 text-slate-200 p-2 rounded-xl rounded-tr-none border border-brand-500/30 text-xs font-sans whitespace-pre-wrap break-words inline-block text-left">
                    ${escapeHtml(msg.text)}
                </div>
            </div>
            <img src="${msg.avatar}" class="h-6 w-6 rounded-full border border-brand-500/40 shrink-0 mt-1">
        `;
    } else {
        bubble.className = "flex items-start space-x-2";
        bubble.innerHTML = `
            <img src="${msg.avatar}" class="h-6 w-6 rounded-full border border-slate-700 shrink-0 mt-1">
            <div class="max-w-[75%] space-y-0.5">
                <div class="flex items-center space-x-1.5 text-[9px] text-slate-500 font-mono">
                    <span class="font-bold text-slate-300">${msg.user}</span>
                    <span>${msg.time}</span>
                </div>
                <div class="bg-dark-300 text-slate-200 p-2 rounded-xl rounded-tl-none border border-slate-800 text-xs font-sans whitespace-pre-wrap break-words inline-block">
                    ${escapeHtml(msg.text)}
                </div>
            </div>
        `;
    }
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function updateCollabChatBadge() {
    const badge = document.getElementById("collab-chat-unread-badge");
    if (!badge) return;
    if (collabChatUnreadCount > 0) {
        badge.innerText = collabChatUnreadCount;
        badge.classList.remove("hidden");
    } else {
        badge.classList.add("hidden");
    }
}

function leaveCollaborationRoom(isExplicitClose = false) {
    localStorage.removeItem("submittery_collab_session");
    
    if (wsCollab && wsCollab.readyState === WebSocket.OPEN) {
        try {
            if (isExplicitClose) {
                wsCollab.send(JSON.stringify({
                    type: "close-room",
                    roomCode: currentRoomCode,
                    user: currentUser?.username || "Peer"
                }));
            } else {
                wsCollab.send(JSON.stringify({
                    type: "peer-leave",
                    user: currentUser?.username || "Peer"
                }));
            }
        } catch (e) {}
    }
    
    isCollaborating = false;
    currentRoomCode = null;
    hostedProblemSlug = null;
    collabChatUnreadCount = 0;
    
    if (wsCollab) {
        wsCollab.close();
        wsCollab = null;
    }
    
    // Clean up all remote peer decorations
    if (window.editor) {
        Object.keys(peerCursorDecorations).forEach(user => {
            peerCursorDecorations[user] = window.editor.deltaDecorations(peerCursorDecorations[user], []);
        });
    }
    peerCursorDecorations = {};
    activeRoomPeers.clear();
    
    document.getElementById("lobby-active-room-card").classList.add("hidden");
    document.getElementById("ws-collab-active-indicator").classList.add("hidden");
    const peerBadge = document.getElementById("ws-peer-presence-badge");
    if (peerBadge) peerBadge.classList.add("hidden");
    
    // Hide Collab Chat Tab & Reset Chat
    const chatTab = document.getElementById("wconsole-tab-chat");
    if (chatTab) chatTab.classList.add("hidden");
    if (activeConsoleTab === "chat") {
        switchConsoleTab("testcases");
    }
    const chatMessages = document.getElementById("collab-chat-messages");
    if (chatMessages) {
        chatMessages.innerHTML = '<div class="text-slate-500 text-xs text-center py-4">No messages yet. Send a message to your pair programming partner!</div>';
    }
    collabChatUnreadCount = 0;
    updateCollabChatBadge();
}

function copyRoomCode() {
    if (!currentRoomCode) return;
    navigator.clipboard.writeText(currentRoomCode);
    alert("Room code copied: " + currentRoomCode);
}

function copyInviteLink() {
    if (!currentRoomCode) return;
    const shareLink = `${window.location.origin}/?room=${currentRoomCode}`;
    navigator.clipboard.writeText(shareLink);
    alert("Invite URL link copied to clipboard!");
}

// --- ADMIN WORKSPACE SUITE ---
let editingProblemId = null;
let activeAdminTab = "problems";

function switchAdminTab(tab) {
    activeAdminTab = tab;
    const tabProblemsBtn = document.getElementById("admin-tab-problems");
    const tabSubmissionsBtn = document.getElementById("admin-tab-submissions");
    const contentProblems = document.getElementById("admin-content-problems");
    const contentSubmissions = document.getElementById("admin-content-submissions");
    
    if (tab === "problems") {
        if (tabProblemsBtn) tabProblemsBtn.className = "px-4 py-2 text-xs font-bold uppercase tracking-wider border-b-2 border-brand-500 text-brand-500 transition";
        if (tabSubmissionsBtn) tabSubmissionsBtn.className = "px-4 py-2 text-xs font-bold uppercase tracking-wider border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition";
        if (contentProblems) contentProblems.classList.remove("hidden");
        if (contentSubmissions) contentSubmissions.classList.add("hidden");
        renderAdminProblemsTable();
    } else {
        if (tabSubmissionsBtn) tabSubmissionsBtn.className = "px-4 py-2 text-xs font-bold uppercase tracking-wider border-b-2 border-brand-500 text-brand-500 transition";
        if (tabProblemsBtn) tabProblemsBtn.className = "px-4 py-2 text-xs font-bold uppercase tracking-wider border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition";
        if (contentSubmissions) contentSubmissions.classList.remove("hidden");
        if (contentProblems) contentProblems.classList.add("hidden");
        loadAdminSubmissions();
    }
}

async function loadAdminData() {
    if (!problems || problems.length === 0) {
        await loadProblems();
    } else {
        renderAdminProblemsTable();
    }
    loadAdminSubmissions();
}

function renderAdminProblemsTable() {
    const tbody = document.getElementById("admin-problems-tbody-list");
    if (!tbody) return;
    
    const searchInput = document.getElementById("admin-problems-search-input");
    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const diffSelect = document.getElementById("admin-problems-diff-select");
    const selectedDiff = diffSelect ? diffSelect.value : "all";
    
    let filtered = Array.isArray(problems) ? [...problems] : [];
    if (selectedDiff !== "all") {
        filtered = filtered.filter(p => p.difficulty === selectedDiff);
    }
    if (query) {
        filtered = filtered.filter(p => 
            (p.title && p.title.toLowerCase().includes(query)) || 
            (p.tags && Array.isArray(p.tags) && p.tags.some(t => t.toLowerCase().includes(query)))
        );
    }
    
    // Update stats counter
    const probStatEl = document.getElementById("admin-stat-problems");
    if (probStatEl) probStatEl.innerText = problems.length;
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-slate-500 text-center py-8 text-xs">No problems found matching filters.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = filtered.map((p, idx) => {
        let diffBadge = "text-brand-400 bg-brand-500/10 border-brand-500/20";
        if (p.difficulty === "medium") diffBadge = "text-amber-400 bg-amber-500/10 border-amber-500/20";
        if (p.difficulty === "hard") diffBadge = "text-rose-400 bg-rose-500/10 border-rose-500/20";
        
        const tagsHtml = (p.tags && Array.isArray(p.tags) ? p.tags : []).map(t => `<span class="text-[10px] bg-slate-800 border border-slate-700/80 px-1.5 py-0.5 rounded text-slate-400 font-semibold">${escapeHtml(t)}</span>`).join(" ");
        const pIndex = problems.findIndex(prob => prob.id === p.id) + 1;
        
        return `
            <tr class="border-b border-slate-850 hover:bg-slate-900/20 transition group text-xs font-sans">
                <td class="py-3 px-3 font-bold font-mono text-slate-500">#${pIndex || (idx+1)}</td>
                <td class="py-3 px-3 font-bold text-slate-200 group-hover:text-brand-400 transition">${escapeHtml(p.title || '')}</td>
                <td class="py-3 px-3">
                    <span class="text-[10px] uppercase font-bold px-2 py-0.5 border rounded ${diffBadge}">${p.difficulty || 'easy'}</span>
                </td>
                <td class="py-3 px-3 font-mono text-slate-400 text-[11px]">
                    <span>${p.time_limit !== undefined ? p.time_limit : 1.0}s</span> / <span>${p.memory_limit !== undefined ? p.memory_limit : 256}MB</span>
                </td>
                <td class="py-3 px-3">
                    <div class="flex items-center flex-wrap gap-1">${tagsHtml || '<span class="text-slate-600">None</span>'}</div>
                </td>
                <td class="py-3 px-3 text-right">
                    <div class="flex items-center justify-end space-x-1.5">
                        <button onclick="openWorkspace('${p.slug}')" class="px-2.5 py-1 bg-slate-800 hover:bg-brand-500 hover:text-dark-300 text-slate-300 rounded font-semibold text-[11px] transition border border-slate-700 hover:border-transparent flex items-center" title="Solve / Preview Problem">
                            <i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>View
                        </button>
                        <button onclick="openEditProblemModal('${p.id}')" class="px-2.5 py-1 bg-brand-500/15 hover:bg-brand-500 text-brand-400 hover:text-dark-300 rounded font-semibold text-[11px] transition border border-brand-500/30 hover:border-transparent flex items-center" title="Edit Problem Details">
                            <i class="fa-solid fa-pen-to-square mr-1"></i>Edit
                        </button>
                        <button onclick="deleteProblem('${p.id}', '${escapeHtml(p.title || '')}')" class="px-2 py-1 bg-red-950/20 hover:bg-red-600 text-red-400 hover:text-white rounded font-semibold text-[11px] transition border border-red-500/20 hover:border-transparent flex items-center" title="Delete Problem">
                            <i class="fa-solid fa-trash mr-1"></i>Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

async function loadAdminSubmissions() {
    const tbody = document.getElementById("admin-submissions-tbody-log");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="6" class="text-slate-550 text-center py-6">Loading submissions queue...</td></tr>`;
    
    try {
        const subs = await request("/submissions/");
        
        // Update stats summary cards
        const subStatEl = document.getElementById("admin-stat-submissions");
        if (subStatEl) subStatEl.innerText = subs ? subs.length : 0;
        const probStatEl = document.getElementById("admin-stat-problems");
        if (probStatEl) probStatEl.innerText = problems.length;
        
        if (!subs || subs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-slate-500 text-center py-6">No historical runs logged yet.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = subs.map(s => {
            let color = "text-red-400";
            if (s.status === "accepted") color = "text-brand-400";
            if (s.status === "wrong_answer") color = "text-amber-500";
            
            const timeStr = new Date(s.created_at).toLocaleString();
            
            return `
                <tr class="border-b border-slate-850 hover:bg-slate-900/10 text-xs">
                    <td class="py-2.5 px-3 font-mono font-bold text-slate-350">${s.id ? s.id.substring(0,8) : '--'}</td>
                    <td class="py-2.5 px-3 font-mono text-slate-500">${s.user_id ? s.user_id.substring(0,6) : '--'}</td>
                    <td class="py-2.5 px-3 font-mono text-slate-500">${s.problem_id ? s.problem_id.substring(0,6) : '--'}</td>
                    <td class="py-2.5 px-3 text-slate-400 font-semibold">${s.language || 'python'}</td>
                    <td class="py-2.5 px-3 font-bold uppercase tracking-wider ${color}">${(s.status || 'unknown').replace("_", " ")}</td>
                    <td class="py-2.5 px-3 text-slate-500 text-right font-mono">${timeStr}</td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        console.error("Admin dashboard query failure:", e);
        tbody.innerHTML = `<tr><td colspan="6" class="text-red-400 text-center py-6">Failed to load submissions: ${e.message}</td></tr>`;
    }
}

// Problem creation & editing helpers
function openCreateProblemModal() {
    editingProblemId = null;
    
    const titleEl = document.getElementById("create-problem-modal-title");
    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-circle-plus text-brand-500 mr-2"></i><span>Create New Coding Problem</span>`;
    
    const submitBtn = document.getElementById("create-problem-submit-btn");
    if (submitBtn) submitBtn.innerText = "Save and Seed Problem";
    
    // Clear all inputs
    document.getElementById("prob-title").value = "";
    document.getElementById("prob-difficulty").value = "easy";
    document.getElementById("prob-description").value = "";
    document.getElementById("prob-timelimit").value = "1.0";
    document.getElementById("prob-memlimit").value = "256";
    document.getElementById("prob-tags").value = "";
    document.getElementById("prob-starter").value = "def solve():\n    # Read inputs\n    pass\n";
    
    // Reset testcase rows to 2 default rows
    const container = document.getElementById("testcase-rows-container");
    container.innerHTML = "";
    addTestCaseRow("", "", true);
    addTestCaseRow("", "", false);
    
    const modal = document.getElementById("create-problem-modal");
    modal.classList.remove("hidden");
    setTimeout(() => {
        modal.classList.remove("opacity-0");
        modal.querySelector("div").classList.remove("scale-95");
    }, 50);
}

async function openEditProblemModal(problemId) {
    const problem = problems.find(p => p.id === problemId);
    if (!problem) return;
    
    editingProblemId = problem.id;
    
    const titleEl = document.getElementById("create-problem-modal-title");
    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-pen-to-square text-brand-500 mr-2"></i><span>Edit Problem: ${escapeHtml(problem.title)}</span>`;
    
    const submitBtn = document.getElementById("create-problem-submit-btn");
    if (submitBtn) submitBtn.innerText = "Update Problem Details";
    
    // Pre-fill fields
    document.getElementById("prob-title").value = problem.title || "";
    document.getElementById("prob-difficulty").value = problem.difficulty || "easy";
    document.getElementById("prob-description").value = problem.description || "";
    document.getElementById("prob-timelimit").value = problem.time_limit || 1.0;
    document.getElementById("prob-memlimit").value = problem.memory_limit || 256;
    document.getElementById("prob-tags").value = (problem.tags || []).join(", ");
    document.getElementById("prob-starter").value = problem.starter_code?.python || "def solve():\n    # Read inputs\n    pass\n";
    
    // Fetch full problem details with all test cases
    const container = document.getElementById("testcase-rows-container");
    container.innerHTML = `<div class="text-center text-slate-500 py-3 text-xs"><i class="fa-solid fa-spinner animate-spin mr-1"></i>Loading test cases...</div>`;
    
    const modal = document.getElementById("create-problem-modal");
    modal.classList.remove("hidden");
    setTimeout(() => {
        modal.classList.remove("opacity-0");
        modal.querySelector("div").classList.remove("scale-95");
    }, 50);
    
    try {
        const fullProblem = await request(`/problems/${problem.slug}`);
        container.innerHTML = "";
        const testCases = fullProblem.test_cases || [];
        if (testCases.length > 0) {
            testCases.forEach(tc => {
                addTestCaseRow(tc.input, tc.expected_output, tc.is_sample);
            });
        } else {
            addTestCaseRow("", "", true);
        }
    } catch (e) {
        container.innerHTML = "";
        addTestCaseRow("", "", true);
    }
}

function hideCreateProblemModal() {
    const modal = document.getElementById("create-problem-modal");
    modal.classList.add("opacity-0");
    modal.querySelector("div").classList.add("scale-95");
    setTimeout(() => {
        modal.classList.add("hidden");
        editingProblemId = null;
    }, 300);
}

function addTestCaseRow(inputVal = "", outputVal = "", isSample = false) {
    const container = document.getElementById("testcase-rows-container");
    const div = document.createElement("div");
    div.className = "testcase-row glass-card p-3 rounded-lg border border-slate-800/80 grid grid-cols-12 gap-2 items-center";
    div.innerHTML = `
        <div class="col-span-5">
            <textarea placeholder="Input..." required class="tc-input w-full px-2 py-1 bg-dark-300 border border-slate-800 rounded text-slate-200 font-mono text-[10px]" rows="2">${escapeHtml(inputVal)}</textarea>
        </div>
        <div class="col-span-5">
            <textarea placeholder="Expected Output..." required class="tc-output w-full px-2 py-1 bg-dark-300 border border-slate-800 rounded text-slate-200 font-mono text-[10px]" rows="2">${escapeHtml(outputVal)}</textarea>
        </div>
        <div class="col-span-2 text-center flex flex-col items-center justify-between h-full py-0.5">
            <label class="flex items-center space-x-1 cursor-pointer">
                <input type="checkbox" class="tc-sample h-3.5 w-3.5 text-brand-500 bg-dark-300 rounded border-slate-800 focus:ring-brand-500" ${isSample ? 'checked' : ''}>
                <span class="text-[9px] text-slate-400 font-bold">Sample</span>
            </label>
            <button type="button" onclick="this.closest('.testcase-row').remove()" class="text-slate-500 hover:text-red-400 text-xs transition mt-1 p-0.5" title="Remove Testcase">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `;
    container.appendChild(div);
}

async function handleCreateProblemSubmit(e) {
    e.preventDefault();
    
    const title = document.getElementById("prob-title").value.trim();
    const difficulty = document.getElementById("prob-difficulty").value;
    const description = document.getElementById("prob-description").value.trim();
    const timeLimit = parseFloat(document.getElementById("prob-timelimit").value);
    const memoryLimit = parseInt(document.getElementById("prob-memlimit").value);
    const tags = document.getElementById("prob-tags").value.split(",").map(t => t.trim()).filter(t => t);
    const starterCode = document.getElementById("prob-starter").value;
    
    // Parse test cases
    const rows = document.querySelectorAll(".testcase-row");
    const testCases = [];
    rows.forEach(r => {
        const input = r.querySelector(".tc-input").value;
        const expectedOutput = r.querySelector(".tc-output").value;
        const isSample = r.querySelector(".tc-sample").checked;
        
        testCases.push({
            input,
            expected_output: expectedOutput,
            is_sample: isSample
        });
    });
    
    const payload = {
        title,
        description,
        difficulty,
        time_limit: timeLimit,
        memory_limit: memoryLimit,
        tags,
        starter_code: { python: starterCode },
        is_public: true,
        test_cases: testCases
    };
    
    try {
        if (editingProblemId) {
            // Update problem
            await request(`/problems/${editingProblemId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            alert("Problem successfully updated!");
        } else {
            // Create problem
            await request("/problems/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            alert("Problem successfully created and seeded!");
        }
        
        hideCreateProblemModal();
        await loadProblems();
        renderAdminProblemsTable();
    } catch (err) {
        alert((editingProblemId ? "Failed to update problem: " : "Failed to create problem: ") + err.message);
    }
}

async function deleteProblem(problemId, problemTitle) {
    if (!confirm(`Are you sure you want to permanently delete problem "${problemTitle}"?\n\nThis will remove the problem and all its testcases from the catalog.`)) {
        return;
    }
    
    try {
        await request(`/problems/${problemId}`, {
            method: "DELETE"
        });
        alert(`Problem "${problemTitle}" was deleted.`);
        await loadProblems();
        renderAdminProblemsTable();
    } catch (err) {
        alert("Failed to delete problem: " + err.message);
    }
}

// -------------------------------------------------------------
// ADVANCED RENDERERS: MATH & LEETCODE TEST CASES VISUALIZER
// -------------------------------------------------------------

function renderMarkdownAndMath(text) {
    if (!text) return "";
    
    const mathBlocks = [];
    let placeholderIndex = 0;
    
    // Extract display math ($$...$$) first to prevent marked corruption
    text = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, math) => {
        const placeholder = `MATHBLOCKDISPLAYXYZ${placeholderIndex}`;
        mathBlocks.push({ placeholder, math: math, display: true });
        placeholderIndex++;
        return placeholder;
    });
    
    // Extract inline math ($...$)
    text = text.replace(/\$([\s\S]+?)\$/g, (match, math) => {
        const placeholder = `MATHBLOCKINLINEXYZ${placeholderIndex}`;
        mathBlocks.push({ placeholder, math: math, display: false });
        placeholderIndex++;
        return placeholder;
    });
    
    // Parse Markdown
    let html = marked.parse(text);
    
    // Render KaTeX and replace placeholders
    mathBlocks.forEach(block => {
        try {
            const mathHtml = katex.renderToString(block.math, {
                displayMode: block.display,
                throwOnError: false
            });
            html = html.replace(block.placeholder, mathHtml);
        } catch (err) {
            console.error("KaTeX error:", err);
            html = html.replace(block.placeholder, block.math);
        }
    });
    
    return html;
}

function renderTestcasesOutput(results) {
    const container = document.getElementById("wconsole-testcases-container");
    if (!container) return;
    container.innerHTML = "";
    container.classList.remove("hidden");
    
    if (!results || results.length === 0) {
        container.classList.add("hidden");
        return;
    }
    
    // Create horizontal tab buttons container
    const tabsRow = document.createElement("div");
    tabsRow.className = "flex space-x-1.5 overflow-x-auto pb-1 border-b border-slate-800/80 shrink-0";
    
    // Details display panel
    const detailsBox = document.createElement("div");
    detailsBox.className = "space-y-3 pt-2 text-xs flex-grow select-text";
    
    function selectCaseTab(idx) {
        // Update selection styling on all tabs
        const tabButtons = tabsRow.querySelectorAll("button");
        tabButtons.forEach((btn, i) => {
            const res = results[i];
            const isPassed = res.status === "accepted";
            const isNotRun = res.status === "not_run";
            if (i === idx) {
                btn.className = `px-3 py-1.5 rounded-lg font-bold uppercase tracking-wider text-[10px] bg-dark-200 border border-brand-500 text-brand-500`;
            } else {
                let statusColor = "text-red-400 bg-red-500/5 hover:bg-red-500/10";
                if (isPassed) statusColor = "text-brand-500 bg-brand-500/5 hover:bg-brand-500/10";
                if (isNotRun) statusColor = "text-slate-500 bg-slate-800/20 hover:bg-slate-800/40";
                btn.className = `px-3 py-1.5 rounded-lg font-semibold uppercase tracking-wider text-[10px] ${statusColor} border border-transparent transition`;
            }
        });
        
        // Update details view
        const res = results[idx];
        const isPassed = res.status === "accepted";
        const isNotRun = res.status === "not_run";
        let statusBadgeColor = "text-red-400 bg-red-500/10 border-red-500/20";
        if (isPassed) statusBadgeColor = "text-brand-500 bg-brand-500/10 border-brand-500/20";
        if (isNotRun) statusBadgeColor = "text-slate-400 bg-slate-800/40 border-slate-750";
        
        // Fetch local input/output match
        const matchedCase = (currentProblem?.test_cases || []).find(tc => tc.id === res.id);
        const inputVal = matchedCase ? matchedCase.input : "[Hidden Test Case]";
        const expectedVal = matchedCase ? matchedCase.expected_output : "[Hidden Test Case]";
        
        let outputSection = "";
        if (res.status === "accepted") {
            outputSection = `
                <div>
                    <div class="text-[10px] text-slate-500 mb-0.5 font-bold uppercase">Stdout Output:</div>
                    <pre class="bg-black/40 p-2.5 rounded border border-slate-850 text-brand-400 font-mono whitespace-pre overflow-x-auto select-all">${expectedVal}</pre>
                </div>
            `;
        } else if (res.status === "wrong_answer") {
            outputSection = `
                <div>
                    <div class="text-[10px] text-slate-500 mb-0.5 font-bold uppercase">Your Output:</div>
                    <pre class="bg-black/40 p-2.5 rounded border border-red-500/10 text-red-400 font-mono whitespace-pre overflow-x-auto select-all">${res.error || "Wrong Answer"}</pre>
                </div>
            `;
        } else if (res.status === "not_run") {
            outputSection = `
                <div>
                    <div class="text-[10px] text-slate-500 mb-0.5 font-bold uppercase">Status:</div>
                    <div class="text-xs text-slate-500 italic bg-black/40 p-2.5 rounded border border-slate-850">Test case skipped because an earlier test case failed.</div>
                </div>
            `;
        } else {
            outputSection = `
                <div>
                    <div class="text-[10px] text-slate-500 mb-0.5 font-bold uppercase">Traceback Error:</div>
                    <pre class="bg-black/40 p-2.5 rounded border border-red-500/10 text-red-400 font-mono whitespace-pre-wrap overflow-x-auto select-all">${res.error || "Execution Error"}</pre>
                </div>
            `;
        }
        
        detailsBox.innerHTML = `
            <div class="flex items-center justify-between glass-card p-3 rounded-lg border-slate-800">
                <div class="flex items-center space-x-2">
                    <span class="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 border rounded ${statusBadgeColor}">${res.status.replace("_", " ")}</span>
                </div>
                <div class="flex space-x-4 text-[10px] font-mono">
                    <div><span class="text-slate-500">Runtime:</span> <strong class="text-slate-200">${res.runtime ? res.runtime.toFixed(3) + 's' : '--'}</strong></div>
                    <div class="border-l border-slate-800 pl-3"><span class="text-slate-500">Memory:</span> <strong class="text-slate-200">${res.memory ? (res.memory / 1024).toFixed(1) + 'MB' : '--'}</strong></div>
                </div>
            </div>
            
            <div class="space-y-3">
                <div>
                    <div class="text-[10px] text-slate-500 mb-0.5 font-bold uppercase">Input:</div>
                    <pre class="bg-black/40 p-2.5 rounded border border-slate-850 text-slate-350 font-mono whitespace-pre overflow-x-auto select-all">${inputVal}</pre>
                </div>
                <div>
                    <div class="text-[10px] text-slate-500 mb-0.5 font-bold uppercase">Expected Output:</div>
                    <pre class="bg-black/40 p-2.5 rounded border border-slate-850 text-brand-400 font-mono whitespace-pre overflow-x-auto select-all">${expectedVal}</pre>
                </div>
                ${outputSection}
            </div>
        `;
    }
    
    // Generate horizontal case buttons
    results.forEach((res, i) => {
        const btn = document.createElement("button");
        const isPassed = res.status === "accepted";
        const isNotRun = res.status === "not_run";
        let iconClass = "fa-solid fa-circle-xmark text-red-500 mr-1";
        if (isPassed) iconClass = "fa-solid fa-circle-check text-brand-500 mr-1";
        if (isNotRun) iconClass = "fa-solid fa-circle-minus text-slate-500 mr-1";
        btn.innerHTML = `<i class="${iconClass}"></i>Case ${i + 1}`;
        
        btn.addEventListener("click", () => selectCaseTab(i));
        tabsRow.appendChild(btn);
    });
    
    container.appendChild(tabsRow);
    container.appendChild(detailsBox);
    
    // Focus first test case by default
    selectCaseTab(0);
}

function switchLeftTab(tab) {
    activeLeftTab = tab;
    const tabs = ["description", "history", "explain"];
    
    tabs.forEach(t => {
        const btn = document.getElementById(`wleft-tab-${t}`);
        const content = document.getElementById(`wleft-content-${t}`);
        if (!btn || !content) return;
        
        if (t === tab) {
            btn.className = "px-3 py-1.5 text-[9px] font-bold uppercase tracking-wider border-b-2 border-brand-500 text-brand-500 transition";
            content.classList.remove("hidden");
        } else {
            btn.className = "px-3 py-1.5 text-[9px] font-bold uppercase tracking-wider border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition";
            content.classList.add("hidden");
        }
    });
    
    if (tab === "explain") {
        loadQuestionExplanation();
    }
}

function loadHistoricalCode(subId) {
    if (!window.historicalSubmissions) return;
    const sub = window.historicalSubmissions.find(s => s.id === subId);
    if (sub && window.editor) {
        window.editor.setValue(sub.code);
        lastSubmissionId = sub.id;
        
        // Switch to result console tab and show verdict / cases
        switchConsoleTab("result");
        document.getElementById("wconsole-default-msg").classList.add("hidden");
        document.getElementById("wjudge-status-block").classList.remove("hidden");
        document.getElementById("wverdict-id").innerText = sub.id.substring(0, 8);
        displayFinalVerdictWorkspace(sub);
    }
}

async function loadQuestionExplanation() {
    if (!currentProblem) return;
    const container = document.getElementById("wleft-content-explain");
    if (!container) return;
    
    container.innerHTML = `
        <div class="flex items-center justify-center py-20 text-brand-400 text-xs">
            <i class="fa-solid fa-spinner animate-spin text-sm mr-2"></i>
            <span>AI Mentor is explaining the problem...</span>
        </div>
    `;
    
    try {
        const data = await request("/ai/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: "Please explain this problem statement, constraints, example inputs/outputs, and outline the core algorithmic approach to solve it in simple terms.",
                problem_id: currentProblem.id
            })
        });
        
        container.innerHTML = `
            <div class="space-y-4 select-text">
                <h4 class="text-[10px] font-bold text-brand-500 uppercase tracking-widest font-mono"><i class="fa-solid fa-wand-magic-sparkles mr-1.5"></i>AI Explanation</h4>
                <div class="prose prose-invert text-sm max-w-none space-y-3 leading-relaxed font-sans select-text">
                    ${renderMarkdownAndMath(data.response)}
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = `
            <div class="text-red-400 text-xs py-4">
                <i class="fa-solid fa-circle-exclamation mr-2"></i>AI Error: ${e.message}
            </div>
        `;
    }
}

function toggleTheme() {
    const body = document.body;
    const currentTheme = body.classList.contains("light-mode") ? "dark" : "light";
    
    if (currentTheme === "light") {
        body.classList.add("light-mode");
        localStorage.setItem("theme", "light");
        if (window.editor) monaco.editor.setTheme("vs");
        // Update toggle icon to moon
        const toggleIcon = document.getElementById("theme-toggle-icon");
        if (toggleIcon) toggleIcon.className = "fa-solid fa-moon text-xs";
    } else {
        body.classList.remove("light-mode");
        localStorage.setItem("theme", "dark");
        if (window.editor) monaco.editor.setTheme("vs-dark");
        // Update toggle icon to sun
        const toggleIcon = document.getElementById("theme-toggle-icon");
        if (toggleIcon) toggleIcon.className = "fa-solid fa-sun text-xs";
    }
}

function openSettingsModal() {
    if (!currentUser) return;
    const modal = document.getElementById("profile-settings-modal");
    
    document.getElementById("settings-username").value = currentUser.username;
    document.getElementById("settings-email").value = currentUser.email;
    
    let seed = currentUser.username;
    if (currentUser.avatar_url && currentUser.avatar_url.includes("seed=")) {
        const parts = currentUser.avatar_url.split("seed=");
        if (parts.length > 1) {
            seed = decodeURIComponent(parts[1]);
        }
    }
    document.getElementById("settings-avatar-seed").value = seed;
    document.getElementById("settings-password").value = "";
    previewSettingsAvatar();
    
    modal.classList.remove("hidden");
    setTimeout(() => {
        modal.classList.remove("opacity-0");
        modal.querySelector("div").classList.remove("scale-95");
    }, 50);
}

function hideSettingsModal() {
    const modal = document.getElementById("profile-settings-modal");
    modal.classList.add("opacity-0");
    modal.querySelector("div").classList.add("scale-95");
    setTimeout(() => modal.classList.add("hidden"), 300);
}

function previewSettingsAvatar() {
    const seed = document.getElementById("settings-avatar-seed").value.trim() || "submitter";
    const previewContainer = document.getElementById("settings-avatar-preview-container");
    const avatarUrl = `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(seed)}`;
    previewContainer.innerHTML = `<img src="${avatarUrl}" class="h-full w-full rounded-xl">`;
}

async function handleProfileSettingsSubmit(e) {
    e.preventDefault();
    const username = document.getElementById("settings-username").value.trim();
    const email = document.getElementById("settings-email").value.trim();
    const seed = document.getElementById("settings-avatar-seed").value.trim();
    const password = document.getElementById("settings-password").value;
    
    const avatarUrl = `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(seed)}`;
    
    const body = {
        username,
        email,
        avatar_url: avatarUrl
    };
    if (password) {
        body.password = password;
    }
    
    try {
        currentUser = await request("/auth/profile", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        
        updateUIForAuth();
        hideSettingsModal();
    } catch (err) {
        alert("Failed to update profile: " + err.message);
    }
}



