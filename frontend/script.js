// ── Salesforce AI Agent — Frontend Script ───────────────────

const API_BASE = "";
let isWaiting = false;

// ── Initialize ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    checkStatus();
    document.getElementById("messageInput").focus();
});

// ── Check Server Status ─────────────────────────────────────
async function checkStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();

        const statusEl = document.getElementById("connectionStatus");
        const headerStatus = document.getElementById("headerStatus");
        const knowledgeInfo = document.getElementById("knowledgeInfo");

        if (data.connected) {
            const shortUrl = data.instance_url.replace("https://", "").split(".")[0];
            statusEl.innerHTML = `<div class="status-dot connected"></div><span>Connected to ${shortUrl}</span>`;
            headerStatus.textContent = `Connected to Salesforce`;
            headerStatus.style.color = "#10b981";
        } else {
            statusEl.innerHTML = `<div class="status-dot disconnected"></div><span>Not connected</span>`;
            headerStatus.textContent = "Not connected to Salesforce";
            headerStatus.style.color = "#f59e0b";
        }

        knowledgeInfo.innerHTML = `<span class="knowledge-count">${data.knowledge_files}</span> skill files loaded`;

    } catch (e) {
        document.getElementById("headerStatus").textContent = "Server offline";
        document.getElementById("headerStatus").style.color = "#ef4444";
    }
}

// ── Send Message ────────────────────────────────────────────
async function sendMessage() {
    const input = document.getElementById("messageInput");
    const message = input.value.trim();

    if (!message || isWaiting) return;

    // Hide welcome screen
    const welcome = document.getElementById("welcomeScreen");
    if (welcome) welcome.style.display = "none";

    // Add user message
    addMessage("user", message);

    // Clear input
    input.value = "";
    input.style.height = "auto";
    updateSendBtn();

    // Show typing indicator
    const typingId = showTyping();
    isWaiting = true;
    updateSendBtn();

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });

        const data = await res.json();

        // Remove typing indicator
        removeTyping(typingId);

        if (data.error) {
            addMessage("agent", `**Error:** ${data.error}`, [], []);
        } else {
            // Show tool calls and charts
            addMessage("agent", data.reply, data.tool_calls || [], data.charts || []);
        }

    } catch (e) {
        removeTyping(typingId);
        addMessage("agent", "**Error:** Could not reach the server. Make sure `python app.py` is running.", [], []);
    }

    isWaiting = false;
    updateSendBtn();
    input.focus();
}

// ── Quick Message ───────────────────────────────────────────
function sendQuickMessage(text) {
    const input = document.getElementById("messageInput");
    input.value = text;
    sendMessage();

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        document.getElementById("sidebar").classList.remove("open");
    }
}

// ── Add Message to Chat ─────────────────────────────────────
let chartCounter = 0;

function addMessage(role, content, toolCalls = [], charts = []) {
    const container = document.getElementById("messagesContainer");

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "Y" : "AI";

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    // Show tool calls
    if (toolCalls && toolCalls.length > 0) {
        toolCalls.forEach(tc => {
            const toolDiv = document.createElement("div");
            toolDiv.className = "tool-indicator done";
            const argStr = tc.args.query || tc.args.search || tc.args.object_name || tc.args.title || "";
            toolDiv.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                ${tc.name}${argStr ? ": " + truncate(argStr, 60) : ""}
            `;
            contentDiv.appendChild(toolDiv);
        });
    }

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "agent") {
        bubble.innerHTML = renderMarkdown(content);
    } else {
        bubble.textContent = content;
    }

    contentDiv.appendChild(bubble);

    // Render charts if any
    if (charts && charts.length > 0) {
        charts.forEach(chartConfig => {
            const chartWrapper = renderChart(chartConfig);
            contentDiv.appendChild(chartWrapper);
        });
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// ── Chart Rendering ─────────────────────────────────────────
// Register the datalabels plugin globally
Chart.register(ChartDataLabels);

const CHART_COLORS = [
    '#6366f1', // indigo
    '#06b6d4', // cyan
    '#10b981', // emerald
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#14b8a6', // teal
    '#f97316', // orange
    '#3b82f6', // blue
    '#84cc16', // lime
    '#a855f7', // purple
    '#e11d48', // rose
    '#0ea5e9', // sky
    '#22c55e', // green
];

const CHART_BG_COLORS = CHART_COLORS.map(c => c + '33'); // 20% opacity

function renderChart(config) {
    const wrapper = document.createElement("div");
    wrapper.className = "chart-container";

    const header = document.createElement("div");
    header.className = "chart-header";
    header.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
        <span>${config.title}</span>
    `;
    wrapper.appendChild(header);

    const canvasWrapper = document.createElement("div");
    canvasWrapper.className = "chart-canvas-wrapper";
    const canvas = document.createElement("canvas");
    const chartId = `chart-${++chartCounter}`;
    canvas.id = chartId;
    canvasWrapper.appendChild(canvas);
    wrapper.appendChild(canvasWrapper);

    // Determine Chart.js type
    let chartType = config.chart_type;
    let indexAxis = undefined;
    if (chartType === "horizontalBar") {
        chartType = "bar";
        indexAxis = "y";
    }

    const isPieType = (chartType === "pie" || chartType === "doughnut");
    const totalValue = config.data.reduce((a, b) => a + b, 0);

    // Build dataset
    const dataset = {
        label: config.dataset_label,
        data: config.data,
        borderWidth: isPieType ? 2 : 2,
        borderRadius: isPieType ? 0 : 6,
        borderSkipped: false,
    };

    if (isPieType) {
        dataset.backgroundColor = config.data.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
        dataset.borderColor = '#1a1a24';
    } else if (chartType === "line") {
        dataset.borderColor = CHART_COLORS[0];
        dataset.backgroundColor = CHART_BG_COLORS[0];
        dataset.fill = true;
        dataset.tension = 0.4;
        dataset.pointBackgroundColor = CHART_COLORS[0];
        dataset.pointBorderColor = '#fff';
        dataset.pointBorderWidth = 2;
        dataset.pointRadius = 5;
        dataset.pointHoverRadius = 7;
    } else {
        // Bar
        dataset.backgroundColor = config.data.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
        dataset.borderColor = config.data.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
    }

    // Smart datalabels config based on chart type
    let datalabelsConfig;
    if (isPieType) {
        // Pie/Doughnut: show "count (percent%)" inside slices
        datalabelsConfig = {
            color: '#fff',
            font: { family: "'Inter', sans-serif", weight: '600', size: 12 },
            textShadowColor: 'rgba(0,0,0,0.5)',
            textShadowBlur: 4,
            formatter: (value) => {
                const pct = ((value / totalValue) * 100).toFixed(1);
                return `${value}\n(${pct}%)`;
            },
            // Hide label if slice is too small (<5%)
            display: (context) => {
                const pct = (context.dataset.data[context.dataIndex] / totalValue) * 100;
                return pct >= 5;
            },
            anchor: 'center',
            align: 'center',
            textAlign: 'center',
        };
    } else if (chartType === "line") {
        // Line: show value above each point
        datalabelsConfig = {
            color: '#e8e8f0',
            font: { family: "'Inter', sans-serif", weight: '600', size: 11 },
            anchor: 'end',
            align: 'top',
            offset: 4,
            formatter: (value) => value,
        };
    } else {
        // Bar: show count on top of each bar
        datalabelsConfig = {
            color: '#e8e8f0',
            font: { family: "'Inter', sans-serif", weight: '600', size: 12 },
            anchor: indexAxis === 'y' ? 'end' : 'end',
            align: indexAxis === 'y' ? 'right' : 'top',
            offset: 4,
            formatter: (value) => value,
        };
    }

    // After appending to DOM, create the chart
    setTimeout(() => {
        const ctx = document.getElementById(chartId);
        if (!ctx) return;

        new Chart(ctx, {
            type: chartType,
            data: {
                labels: config.labels,
                datasets: [dataset],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: indexAxis || 'x',
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                },
                layout: {
                    padding: { top: isPieType ? 10 : 20, right: indexAxis === 'y' ? 40 : 10 },
                },
                plugins: {
                    legend: {
                        display: isPieType,
                        position: 'bottom',
                        labels: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 12 },
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                        },
                    },
                    tooltip: {
                        backgroundColor: '#1a1a24',
                        titleColor: '#e8e8f0',
                        bodyColor: '#9494a8',
                        borderColor: '#2a2a3a',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { family: "'Inter', sans-serif", weight: '600' },
                        bodyFont: { family: "'Inter', sans-serif" },
                        displayColors: true,
                        boxPadding: 4,
                        callbacks: isPieType ? {
                            label: (context) => {
                                const val = context.parsed;
                                const pct = ((val / totalValue) * 100).toFixed(1);
                                return ` ${context.label}: ${val} (${pct}%)`;
                            }
                        } : {},
                    },
                    datalabels: datalabelsConfig,
                },
                scales: isPieType ? {} : {
                    x: {
                        grid: { color: '#2a2a3a22', drawBorder: false },
                        ticks: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 11 },
                            maxRotation: 45,
                        },
                        border: { display: false },
                    },
                    y: {
                        grid: { color: '#2a2a3a44', drawBorder: false },
                        ticks: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 11 },
                            precision: 0,
                        },
                        border: { display: false },
                        beginAtZero: true,
                    },
                },
            },
        });
    }, 50);

    return wrapper;
}

// ── Typing Indicator ────────────────────────────────────────
let typingCounter = 0;

function showTyping() {
    const container = document.getElementById("messagesContainer");
    const id = `typing-${++typingCounter}`;

    const messageDiv = document.createElement("div");
    messageDiv.className = "message agent";
    messageDiv.id = id;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "AI";

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;

    contentDiv.appendChild(bubble);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;

    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Markdown Renderer (Simple) ──────────────────────────────
function renderMarkdown(text) {
    if (!text) return "";

    let html = text;

    // Code blocks (```...```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang}">${escapeHtml(code.trim())}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    // Italic
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

    // Headers
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

    // Tables
    html = renderTables(html);

    // Unordered lists
    html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

    // Blockquotes
    html = html.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // Line breaks (double newline = paragraph)
    html = html.replace(/\n\n/g, "</p><p>");

    // Single newline = <br> (but not inside pre/code)
    html = html.replace(/(?<!<\/pre>|<\/code>|<\/h[1-3]>|<\/li>|<\/ul>|<\/table>|<\/blockquote>)\n(?!<)/g, "<br>");

    // Wrap in paragraph
    if (!html.startsWith("<")) {
        html = `<p>${html}</p>`;
    }

    return html;
}

function renderTables(text) {
    const tableRegex = /(\|.+\|)\n(\|[\s\-:|]+\|)\n((?:\|.+\|\n?)+)/g;

    return text.replace(tableRegex, (match, headerRow, separator, bodyRows) => {
        const headers = headerRow.split("|").filter(c => c.trim()).map(c => c.trim());
        const rows = bodyRows.trim().split("\n").map(row =>
            row.split("|").filter(c => c.trim()).map(c => c.trim())
        );

        let table = "<table><thead><tr>";
        headers.forEach(h => { table += `<th>${h}</th>`; });
        table += "</tr></thead><tbody>";
        rows.forEach(row => {
            table += "<tr>";
            row.forEach(cell => { table += `<td>${cell}</td>`; });
            table += "</tr>";
        });
        table += "</tbody></table>";
        return table;
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function truncate(str, len) {
    return str.length > len ? str.substring(0, len) + "..." : str;
}

// ── Input Handling ──────────────────────────────────────────
function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    updateSendBtn();
}

function updateSendBtn() {
    const btn = document.getElementById("sendBtn");
    const input = document.getElementById("messageInput");
    btn.disabled = !input.value.trim() || isWaiting;
}

// Listen for input changes
document.addEventListener("input", (e) => {
    if (e.target.id === "messageInput") {
        updateSendBtn();
    }
});

// ── Clear Chat ──────────────────────────────────────────────
async function clearChat() {
    try {
        await fetch(`${API_BASE}/api/clear`, { method: "POST" });
    } catch (e) {
        // Ignore
    }

    const container = document.getElementById("messagesContainer");
    container.innerHTML = `
        <div class="welcome-screen" id="welcomeScreen">
            <div class="welcome-icon">
                <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="url(#gradient)" stroke-width="1.5">
                    <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" style="stop-color:#6366f1"/>
                            <stop offset="100%" style="stop-color:#06b6d4"/>
                        </linearGradient>
                    </defs>
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
            </div>
            <h2>Welcome to Salesforce AI Agent</h2>
            <p>I'm connected to your Salesforce org and can answer questions, run SOQL queries, describe objects, and help with Apex development.</p>
            <div class="welcome-suggestions">
                <button class="suggestion-chip" onclick="sendQuickMessage('Show me all leads with their status')">Show me all leads</button>
                <button class="suggestion-chip" onclick="sendQuickMessage('What is the difference between SOQL and SOSL?')">SOQL vs SOSL</button>
                <button class="suggestion-chip" onclick="sendQuickMessage('Write an Apex trigger for Account')">Write Apex trigger</button>
                <button class="suggestion-chip" onclick="sendQuickMessage('Explain governor limits')">Governor limits</button>
            </div>
        </div>
    `;
}

// ── Sidebar Toggle ──────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("open");
}

// Close sidebar when clicking outside on mobile
document.addEventListener("click", (e) => {
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById("sidebar");
        const toggle = document.getElementById("menuToggle");
        if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
            sidebar.classList.remove("open");
        }
    }
});
