// ── Salesforce AI Agent — OAuth Setup Script ───────────────
// Handles the 3-step OAuth onboarding wizard

const API_BASE = "";

// ── Step Navigation ────────────────────────────────────────
let currentStep = 1;

function goToStep(step) {
    // Hide all panels
    document.querySelectorAll(".step-panel").forEach(p => p.classList.remove("active"));

    // Update progress steps
    for (let i = 1; i <= 3; i++) {
        const stepEl = document.getElementById(`progressStep${i}`);
        const lineEl = document.getElementById(`progressLine${i - 1}`);
        stepEl.classList.remove("active", "completed");

        if (i < step) {
            stepEl.classList.add("completed");
        } else if (i === step) {
            stepEl.classList.add("active");
        }

        if (lineEl) {
            lineEl.classList.toggle("active", i < step);
        }
    }

    // Show target panel
    const panel = document.getElementById(`stepPanel${step}`);
    if (panel) {
        panel.classList.add("active");
    }

    currentStep = step;

    // Scroll to top smoothly
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Copy Text Helper ────────────────────────────────────────
function copyText(el) {
    const text = el.textContent.trim();
    navigator.clipboard.writeText(text).then(() => {
        el.classList.add("copied");
        showTooltip("Copied to clipboard!");
        setTimeout(() => el.classList.remove("copied"), 1500);
    });
}

function showTooltip(msg) {
    const existing = document.querySelector(".copy-tooltip");
    if (existing) existing.remove();

    const tip = document.createElement("div");
    tip.className = "copy-tooltip";
    tip.textContent = msg;
    document.body.appendChild(tip);
    setTimeout(() => tip.remove(), 2000);
}

// ── Toggle Password Visibility ──────────────────────────────
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === "password") {
        input.type = "text";
        btn.title = "Hide";
    } else {
        input.type = "password";
        btn.title = "Show";
    }
}

// ── Input Validation ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    checkOAuthStatus();

    const keyInput = document.getElementById("consumerKey");
    const secretInput = document.getElementById("consumerSecret");
    const urlInput = document.getElementById("orgUrl");

    keyInput.addEventListener("input", () => {
        const status = document.getElementById("keyStatus");
        if (keyInput.value.trim().length > 10) {
            status.className = "input-status valid";
        } else if (keyInput.value.trim().length > 0) {
            status.className = "input-status invalid";
        } else {
            status.className = "input-status";
        }
    });

    secretInput.addEventListener("input", () => {
        const status = document.getElementById("secretStatus");
        if (secretInput.value.trim().length > 5) {
            status.className = "input-status valid";
        } else if (secretInput.value.trim().length > 0) {
            status.className = "input-status invalid";
        } else {
            status.className = "input-status";
        }
    });

    urlInput.addEventListener("input", () => {
        const status = document.getElementById("urlStatus");
        const val = urlInput.value.trim();
        try {
            const url = new URL(val);
            if (url.hostname.includes("salesforce.com") || url.hostname.includes("force.com")) {
                status.className = "input-status valid";
            } else {
                status.className = "input-status invalid";
            }
        } catch {
            status.className = val.length > 0 ? "input-status invalid" : "input-status";
        }
    });
});

// ── Check OAuth Status on Load ──────────────────────────────
async function checkOAuthStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/oauth/status`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.connected) {
            // Already connected — go straight to chat
            window.location.href = "/";
        } else if (data.configured) {
            // Credentials configured but not connected — go to step 2
            goToStep(2);
        }
    } catch (e) {
        // Server may not be running yet — stay on step 1
        console.warn("Could not check OAuth status:", e);
    }
}

// ── Save Credentials & Start OAuth ──────────────────────────
async function saveAndConnect() {
    const key = document.getElementById("consumerKey").value.trim();
    const secret = document.getElementById("consumerSecret").value.trim();
    const orgUrl = document.getElementById("orgUrl").value.trim();

    // Validate
    if (!key || key.length < 10) {
        shakeInput("consumerKey");
        return;
    }
    if (!secret || secret.length < 5) {
        shakeInput("consumerSecret");
        return;
    }
    if (!orgUrl) {
        shakeInput("orgUrl");
        return;
    }

    // Disable button
    const btn = document.getElementById("connectBtn");
    btn.classList.add("loading");
    btn.innerHTML = `
        <div class="spinner-ring" style="width:20px;height:20px;border-width:2px;margin:0;"></div>
        Saving credentials...
    `;

    try {
        // Step 1: Save credentials to .env
        const saveRes = await fetch(`${API_BASE}/api/oauth/save-config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                consumer_key: key,
                consumer_secret: secret,
                login_url: orgUrl,
            }),
        });

        const saveData = await saveRes.json();

        if (!saveRes.ok || saveData.error) {
            throw new Error(saveData.error || "Failed to save credentials");
        }

        // Step 2: Move to step 3 (connecting animation)
        goToStep(3);

        // Step 3: Redirect to Salesforce OAuth
        // Small delay so user sees the "Connecting..." UI
        setTimeout(() => {
            window.location.href = `${API_BASE}/api/oauth/authorize`;
        }, 1200);

    } catch (err) {
        btn.classList.remove("loading");
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
            Connect with Salesforce
        `;
        showTooltip("Error: " + err.message);
    }
}

function shakeInput(inputId) {
    const input = document.getElementById(inputId);
    input.style.animation = "errorShake 0.4s ease";
    input.style.borderColor = "var(--error)";
    input.focus();
    setTimeout(() => {
        input.style.animation = "";
        input.style.borderColor = "";
    }, 500);
}

// ── Go to Chat ──────────────────────────────────────────────
function goToChat() {
    window.location.href = "/";
}

// ── Handle OAuth Callback Result ────────────────────────────
// When Salesforce redirects back, the backend handles the code exchange
// and redirects to /setup?status=success or /setup?status=error
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get("status");

    if (status === "success") {
        goToStep(3);
        document.getElementById("connectLoading").style.display = "none";
        document.getElementById("connectSuccess").style.display = "flex";
        const orgUrl = params.get("instance_url") || "";
        if (orgUrl) {
            const shortUrl = orgUrl.replace("https://", "").split(".")[0];
            document.getElementById("successOrgUrl").textContent =
                `Connected to ${shortUrl}. Your Salesforce org is now linked.`;
        }
    } else if (status === "error") {
        goToStep(3);
        document.getElementById("connectLoading").style.display = "none";
        document.getElementById("connectError").style.display = "flex";
        const msg = params.get("message") || "Authentication failed. Please check your Connected App settings.";
        document.getElementById("errorMessage").textContent = msg;
    }
});
