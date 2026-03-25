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
            // Show tool calls, charts, and A2UI surfaces
            addMessage("agent", data.reply, data.tool_calls || [], data.charts || [], data.a2ui_surfaces || []);

            // Check if OTP verification is required
            if (data.otp_required && data.otp_session_key) {
                showOtpModal(data.otp_session_key, data.otp_operation, data.otp_object, data.otp_record_id);
            }
        }

    } catch (e) {
        removeTyping(typingId);
        addMessage("agent", "**Error:** Could not reach the server. Make sure `python app.py` is running.", [], []);
    }

    isWaiting = false;
    updateSendBtn();
    input.focus();
}


// ── OTP Verification System ─────────────────────────────────

let currentOtpSessionKey = "";
let otpVerifying = false;

function showOtpModal(sessionKey, operation, objectName, recordId) {
    currentOtpSessionKey = sessionKey;
    const overlay = document.getElementById("otpModalOverlay");
    const badge = document.getElementById("otpOperationBadge");
    const badgeText = document.getElementById("otpOperationText");
    const statusMsg = document.getElementById("otpStatusMessage");
    const verifyBtn = document.getElementById("otpVerifyBtn");

    // Set operation badge
    const opLabel = operation === "delete" ? "DELETE" : "UPDATE";
    badgeText.textContent = `${opLabel} ${objectName} (${recordId})`;
    badge.className = `otp-operation-badge${operation === "delete" ? " delete" : ""}`;

    // Reset state
    statusMsg.textContent = "";
    statusMsg.className = "otp-status-message";
    verifyBtn.disabled = true;
    verifyBtn.classList.remove("loading");
    verifyBtn.textContent = "Verify & Proceed";

    // Clear OTP inputs
    const inputs = document.querySelectorAll(".otp-digit-input");
    inputs.forEach(inp => {
        inp.value = "";
        inp.classList.remove("error", "success");
    });

    // Show modal
    overlay.classList.add("active");

    // Focus first input
    setTimeout(() => inputs[0].focus(), 100);
}

function closeOtpModal() {
    const overlay = document.getElementById("otpModalOverlay");
    overlay.classList.remove("active");
    currentOtpSessionKey = "";
}

function getOtpValue() {
    const inputs = document.querySelectorAll(".otp-digit-input");
    return Array.from(inputs).map(i => i.value).join("");
}

async function verifyOtp() {
    if (otpVerifying) return;
    const otp = getOtpValue();
    if (otp.length !== 6) return;

    otpVerifying = true;
    const verifyBtn = document.getElementById("otpVerifyBtn");
    const statusMsg = document.getElementById("otpStatusMessage");
    const inputs = document.querySelectorAll(".otp-digit-input");

    verifyBtn.classList.add("loading");
    verifyBtn.textContent = "Verifying...";
    statusMsg.textContent = "";
    statusMsg.className = "otp-status-message info";

    try {
        const res = await fetch(`${API_BASE}/api/otp/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_key: currentOtpSessionKey, otp: otp }),
        });

        const data = await res.json();

        if (data.verified && data.success) {
            // Success
            inputs.forEach(inp => inp.classList.add("success"));
            statusMsg.textContent = "✅ Verification successful!";
            statusMsg.className = "otp-status-message success";
            verifyBtn.textContent = "✅ Verified";

            // Add success message to chat
            addOtpResultMessage(data.message, "success");

            // Close modal after brief delay
            setTimeout(() => closeOtpModal(), 1200);
        } else {
            // Failed
            inputs.forEach(inp => inp.classList.add("error"));
            statusMsg.textContent = data.error || "Verification failed.";
            statusMsg.className = "otp-status-message error";
            verifyBtn.textContent = "Verify & Proceed";
            verifyBtn.classList.remove("loading");

            // Remove error styling after animation
            setTimeout(() => {
                inputs.forEach(inp => {
                    inp.classList.remove("error");
                    inp.value = "";
                });
                inputs[0].focus();
                verifyBtn.disabled = true;
            }, 800);
        }
    } catch (e) {
        statusMsg.textContent = "Network error. Please try again.";
        statusMsg.className = "otp-status-message error";
        verifyBtn.textContent = "Verify & Proceed";
        verifyBtn.classList.remove("loading");
    }

    otpVerifying = false;
}

async function resendOtp() {
    const statusMsg = document.getElementById("otpStatusMessage");
    const resendBtn = document.getElementById("otpResendBtn");
    const inputs = document.querySelectorAll(".otp-digit-input");

    resendBtn.disabled = true;
    resendBtn.textContent = "Sending...";
    statusMsg.textContent = "";

    try {
        const res = await fetch(`${API_BASE}/api/otp/resend`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_key: currentOtpSessionKey }),
        });

        const data = await res.json();

        if (data.success) {
            statusMsg.textContent = "📧 New code sent! Check your email.";
            statusMsg.className = "otp-status-message success";
            // Clear inputs
            inputs.forEach(inp => { inp.value = ""; inp.classList.remove("error", "success"); });
            inputs[0].focus();
            document.getElementById("otpVerifyBtn").disabled = true;
        } else {
            statusMsg.textContent = data.error || "Failed to resend code.";
            statusMsg.className = "otp-status-message error";
        }
    } catch (e) {
        statusMsg.textContent = "Network error. Please try again.";
        statusMsg.className = "otp-status-message error";
    }

    resendBtn.disabled = false;
    resendBtn.textContent = "Resend Code";
}

function cancelOtp() {
    closeOtpModal();
    addOtpResultMessage("⚠️ Operation cancelled — verification was not completed.", "denied");
}

function addOtpResultMessage(text, type) {
    const container = document.getElementById("messagesContainer");
    const msgDiv = document.createElement("div");
    msgDiv.className = `otp-result-message ${type}`;
    msgDiv.textContent = text;

    // Find the last agent message and append to its content
    const messages = container.querySelectorAll(".message.agent");
    if (messages.length > 0) {
        const lastAgent = messages[messages.length - 1];
        const contentDiv = lastAgent.querySelector(".message-content");
        if (contentDiv) {
            contentDiv.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
            return;
        }
    }

    // Fallback: add as standalone
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

// ── OTP Input Handlers (auto-focus, paste support) ──────────
document.addEventListener("DOMContentLoaded", () => {
    const inputs = document.querySelectorAll(".otp-digit-input");

    inputs.forEach((input, idx) => {
        input.addEventListener("input", (e) => {
            const val = e.target.value.replace(/[^0-9]/g, "");
            e.target.value = val;

            if (val && idx < inputs.length - 1) {
                inputs[idx + 1].focus();
            }

            // Enable verify button when all 6 digits are entered
            const otp = getOtpValue();
            document.getElementById("otpVerifyBtn").disabled = otp.length !== 6;
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && !e.target.value && idx > 0) {
                inputs[idx - 1].focus();
                inputs[idx - 1].value = "";
            }
            if (e.key === "Enter") {
                const otp = getOtpValue();
                if (otp.length === 6) verifyOtp();
            }
        });

        // Handle paste
        input.addEventListener("paste", (e) => {
            e.preventDefault();
            const pasted = (e.clipboardData.getData("text") || "").replace(/[^0-9]/g, "").slice(0, 6);
            for (let i = 0; i < pasted.length && i < inputs.length; i++) {
                inputs[i].value = pasted[i];
            }
            const focusIdx = Math.min(pasted.length, inputs.length - 1);
            inputs[focusIdx].focus();
            document.getElementById("otpVerifyBtn").disabled = pasted.length !== 6;
        });
    });
});

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


function addMessage(role, content, toolCalls = [], charts = [], a2uiSurfaces = []) {
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

    // Render charts via A2UI pipeline
    if (charts && charts.length > 0) {
        charts.forEach(chartConfig => {
            // Convert legacy chart config to A2UI messages and render
            const a2uiSurface = window.A2UI.renderChart(chartConfig);
            contentDiv.appendChild(a2uiSurface);
        });
    }

    // Render any raw A2UI surfaces directly from the backend
    if (a2uiSurfaces && a2uiSurfaces.length > 0) {
        a2uiSurfaces.forEach(surfaceMessages => {
            const surfaceEl = window.A2UI.renderSurface(surfaceMessages);
            if (surfaceEl) {
                contentDiv.appendChild(surfaceEl);
            }
        });
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// ── Chart Rendering (now via A2UI) ──────────────────────────
// Charts are rendered through the A2UI pipeline.
// The ChartDataLabels plugin is registered globally for Chart.js.
Chart.register(ChartDataLabels);

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
