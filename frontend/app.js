/**
 * DevVibe Frontend Logic
 * Interactive dashboard rendering: Chart.js top languages, contribution heatmaps,
 * server-side Vibe Check compatibility, and AI Recruiter Chatbot.
 */

// Application State
let currentProfile = null;
let languagesChartInstance = null;
let activeUsername = "";

// Color palette for language charts
const LANG_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C#": "#178600",
    "C": "#555555",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Shell": "#89e051",
    "Other": "#8b5cf6"
};

// DOM Elements
const searchForm = document.getElementById("search-form");
const usernameInput = document.getElementById("username-input");
const searchBtn = document.getElementById("search-btn");
const refreshBtn = document.getElementById("refresh-btn");
const statusBanner = document.getElementById("status-banner");
const statusMessage = document.getElementById("status-message");
const closeBanner = document.getElementById("close-banner");

// Sections
const emptyState = document.getElementById("empty-state");
const profileSection = document.getElementById("profile-section");
const contributionsSection = document.getElementById("contributions-section");
const reposSection = document.getElementById("repos-section");
const repoGrid = document.getElementById("repo-grid");
const repoFilterInput = document.getElementById("repo-filter-input");

// Vibe Check
const vibeBadgeContainer = document.getElementById("vibe-badge-container");
const vibePillScore = document.getElementById("vibe-pill-score");
const vibeBadgePill = document.getElementById("vibe-badge-pill");
const matchedSkillsPreview = document.getElementById("matched-skills-preview");
const vibeToggleBtn = document.getElementById("vibe-toggle-btn");
const openVibeModalBtn = document.getElementById("open-vibe-modal-btn");
const vibeModal = document.getElementById("vibe-modal");
const closeVibeModal = document.getElementById("close-vibe-modal");
const jdTextarea = document.getElementById("jd-textarea");
const runVibeCheckBtn = document.getElementById("run-vibe-check-btn");
const vibeResultsPanel = document.getElementById("vibe-results-panel");

// Chatbot
const chatbotToggleBtn = document.getElementById("chatbot-toggle-btn");
const chatbotWindow = document.getElementById("chatbot-window");
const closeChatBtn = document.getElementById("close-chat-btn");
const chatTabs = document.querySelectorAll(".chat-tab-btn");
const tabPanes = document.querySelectorAll(".tab-pane");
const chatInputForm = document.getElementById("chat-input-form");
const chatUserInput = document.getElementById("chat-user-input");
const chatMessagesContainer = document.getElementById("chat-messages-container");
const quickPrompts = document.querySelectorAll(".p-chip");
const generateInterviewBtn = document.getElementById("generate-interview-btn");
const interviewOutput = document.getElementById("interview-output");

// Tooltip
const heatmapTooltip = document.getElementById("heatmap-tooltip");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    setupEventListeners();
    checkBackendHealth();
});

function setupEventListeners() {
    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const user = usernameInput.value.trim();
        if (user) loadDeveloperProfile(user, false);
    });

    refreshBtn.addEventListener("click", () => {
        const user = activeUsername || usernameInput.value.trim();
        if (user) loadDeveloperProfile(user, true);
    });

    closeBanner.addEventListener("click", () => {
        statusBanner.style.display = "none";
    });

    // Sample chips
    document.querySelectorAll(".chip-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const user = btn.dataset.user;
            usernameInput.value = user;
            loadDeveloperProfile(user, false);
        });
    });

    // Repo filter
    repoFilterInput.addEventListener("input", (e) => {
        filterRepositories(e.target.value.toLowerCase());
    });

    // Vibe Modal Controls
    vibeToggleBtn.addEventListener("click", openVibeCheckModal);
    openVibeModalBtn.addEventListener("click", openVibeCheckModal);
    closeVibeModal.addEventListener("click", () => { vibeModal.style.display = "none"; });
    vibeModal.addEventListener("click", (e) => {
        if (e.target === vibeModal) vibeModal.style.display = "none";
    });

    runVibeCheckBtn.addEventListener("click", executeVibeCheck);

    // Chatbot Controls
    chatbotToggleBtn.addEventListener("click", () => {
        chatbotWindow.style.display = chatbotWindow.style.display === "none" ? "flex" : "none";
    });
    closeChatBtn.addEventListener("click", () => { chatbotWindow.style.display = "none"; });

    chatTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            chatTabs.forEach(t => t.classList.remove("active"));
            tabPanes.forEach(p => p.style.display = "none");
            tab.classList.add("active");
            const targetPane = document.getElementById(`tab-${tab.dataset.tab}`);
            if (targetPane) targetPane.style.display = "flex";
        });
    });

    chatInputForm.addEventListener("submit", handleChatSubmit);

    quickPrompts.forEach(chip => {
        chip.addEventListener("click", () => {
            chatUserInput.value = chip.textContent.replace(/^[^\w]+/, "").trim();
            handleChatSubmit(new Event("submit"));
        });
    });

    generateInterviewBtn.addEventListener("click", handleInterviewGeneration);
}

// --- Backend Health Check ---
async function checkBackendHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (!data.github_token_configured) {
            showBanner("ℹ️ Running in public GitHub mode (60 requests/hr). SQLite local caching is active to prevent rate-limiting.");
        }
    } catch (e) {
        console.warn("Backend health check failed:", e);
    }
}

function showBanner(msg, isError = false) {
    statusMessage.textContent = msg;
    statusBanner.style.borderColor = isError ? "var(--danger)" : "var(--border-glass)";
    statusBanner.style.display = "flex";
}

// --- Load Profile ---
async function loadDeveloperProfile(username, forceRefresh = false) {
    activeUsername = username;
    setLoading(true);

    try {
        const url = `/api/profile/${encodeURIComponent(username)}${forceRefresh ? "?force_refresh=true" : ""}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server responded with ${response.status}`);
        }

        const data = await response.json();
        currentProfile = data;
        
        renderProfile(data);
        renderLanguagesChart(data.user.top_languages);
        renderContributionHeatmap(data.contributions, data.streaks);
        renderRepositories(data.repositories);

        emptyState.style.display = "none";
        profileSection.style.display = "block";
        contributionsSection.style.display = "block";
        reposSection.style.display = "block";

        if (data.source === "cache") {
            showBanner(`⚡ Data served instantly from local SQLite cache (Cached at ${data.user.cached_at || 'earlier'}). Click Sync to refresh.`);
        } else if (data.source === "cache_fallback") {
            showBanner(`⚠️ GitHub API rate limit reached. Displaying cached developer profile.`);
        } else {
            statusBanner.style.display = "none";
        }

        // Auto re-run Vibe Check if a JD was already entered
        if (jdTextarea.value.trim()) {
            executeVibeCheck();
        }

    } catch (error) {
        showBanner(`Error: ${error.message}`, true);
    } finally {
        setLoading(false);
    }
}

function setLoading(isLoading) {
    const btnText = searchBtn.querySelector(".btn-text");
    const btnSpinner = searchBtn.querySelector(".btn-spinner");
    if (isLoading) {
        btnText.textContent = "Loading...";
        btnSpinner.style.display = "inline-block";
        searchBtn.disabled = true;
    } else {
        btnText.textContent = "Load Profile";
        btnSpinner.style.display = "none";
        searchBtn.disabled = false;
    }
}

// --- Render Profile Header ---
function renderProfile(data) {
    const u = data.user;
    document.getElementById("user-avatar").src = u.avatar_url || "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png";
    document.getElementById("user-name").textContent = u.name || u.username;
    
    const ghLink = document.getElementById("user-github-link");
    ghLink.textContent = `@${u.username}`;
    ghLink.href = `https://github.com/${u.username}`;

    document.getElementById("user-bio").textContent = u.bio || "No bio published on GitHub.";
    
    // Meta
    setMeta("meta-company", u.company);
    setMeta("meta-location", u.location);
    if (u.blog) {
        const blogElem = document.getElementById("meta-blog");
        const a = blogElem.querySelector("a");
        a.href = u.blog.startsWith("http") ? u.blog : `https://${u.blog}`;
        a.textContent = u.blog;
        blogElem.style.display = "inline-flex";
    } else {
        document.getElementById("meta-blog").style.display = "none";
    }

    // Stats
    document.getElementById("stat-total-stars").textContent = (u.total_stars || 0).toLocaleString();
    document.getElementById("stat-total-forks").textContent = (u.total_forks || 0).toLocaleString();
    document.getElementById("stat-followers").textContent = (u.followers || 0).toLocaleString();
    document.getElementById("stat-public-repos").textContent = (data.repositories ? data.repositories.length : u.public_repos || 0).toLocaleString();
}

function setMeta(elemId, value) {
    const elem = document.getElementById(elemId);
    if (value) {
        elem.querySelector(".val").textContent = value;
        elem.style.display = "inline-flex";
    } else {
        elem.style.display = "none";
    }
}

// --- Render Top Languages Pie Chart ---
function renderLanguagesChart(topLanguages) {
    const canvas = document.getElementById("languages-chart");
    const legendContainer = document.getElementById("chart-legend");
    legendContainer.innerHTML = "";

    if (!topLanguages || Object.keys(topLanguages).length === 0) {
        topLanguages = { "No data": 100 };
    }

    const labels = Object.keys(topLanguages).slice(0, 6);
    const dataVals = labels.map(l => topLanguages[l]);
    const bgColors = labels.map(l => LANG_COLORS[l] || "#6366f1");

    if (languagesChartInstance) {
        languagesChartInstance.destroy();
    }

    languagesChartInstance = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataVals,
                backgroundColor: bgColors,
                borderWidth: 2,
                borderColor: '#0f172a',
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '68%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: ${ctx.raw}%`
                    }
                }
            }
        }
    });

    // Custom Legend
    labels.forEach((label, idx) => {
        const item = document.createElement("div");
        item.className = "legend-item";
        item.innerHTML = `
            <span class="legend-dot" style="background-color: ${bgColors[idx]}"></span>
            <span>${label} <strong style="color:#fff;">${dataVals[idx]}%</strong></span>
        `;
        legendContainer.appendChild(item);
    });
}

// --- Render Contribution Heatmap & Streaks ---
function renderContributionHeatmap(contributions, streaks) {
    document.getElementById("current-streak-val").textContent = streaks.current_streak || 0;
    document.getElementById("longest-streak-val").textContent = streaks.longest_streak || 0;
    document.getElementById("total-contributions-val").textContent = (streaks.total_contributions || 0).toLocaleString();

    const grid = document.getElementById("heatmap-grid");
    grid.innerHTML = "";

    if (!contributions || contributions.length === 0) {
        grid.innerHTML = "<p style='color:var(--text-muted); padding:20px;'>No contribution data available.</p>";
        return;
    }

    // Render cells in order
    contributions.forEach(day => {
        const cell = document.createElement("div");
        cell.className = `day-cell level-${Math.min(day.intensity || 0, 4)}`;
        cell.dataset.date = day.date;
        cell.dataset.count = day.count || 0;

        cell.addEventListener("mouseenter", (e) => {
            const count = cell.dataset.count;
            const date = cell.dataset.date;
            heatmapTooltip.innerHTML = `<strong>${count} contribution${count == 1 ? '' : 's'}</strong> on ${date}`;
            heatmapTooltip.style.display = "block";
            positionTooltip(e);
        });

        cell.addEventListener("mousemove", positionTooltip);

        cell.addEventListener("mouseleave", () => {
            heatmapTooltip.style.display = "none";
        });

        grid.appendChild(cell);
    });
}

function positionTooltip(e) {
    heatmapTooltip.style.left = `${e.clientX + 10}px`;
    heatmapTooltip.style.top = `${e.clientY - 35}px`;
}

// --- Render Repositories ---
function renderRepositories(repos) {
    repoGrid.innerHTML = "";
    if (!repos || repos.length === 0) {
        repoGrid.innerHTML = "<p style='color:var(--text-muted);'>No public repositories found for this account.</p>";
        return;
    }

    repos.forEach(repo => {
        const card = document.createElement("div");
        card.className = "repo-card";
        card.dataset.title = repo.name.toLowerCase();
        card.dataset.desc = (repo.description || "").toLowerCase();
        card.dataset.lang = (repo.language || "").toLowerCase();

        const topicsHtml = (repo.topics || []).slice(0, 4).map(t => `<span class="topic-tag">${t}</span>`).join("");
        const langColor = LANG_COLORS[repo.language] || "#94a3b8";

        card.innerHTML = `
            <div>
                <div class="repo-header">
                    <a href="${repo.html_url}" target="_blank" class="repo-title">${repo.name} ↗</a>
                </div>
                <p class="repo-desc">${repo.description || "No description provided."}</p>
                ${topicsHtml ? `<div class="repo-topics">${topicsHtml}</div>` : ""}
            </div>
            <div class="repo-footer">
                <span class="repo-lang">
                    <span class="lang-circle" style="background-color: ${langColor};"></span>
                    ${repo.language || "Other"}
                </span>
                <div class="repo-counts">
                    <span title="Stars">⭐ ${repo.stars}</span>
                    <span title="Forks">🍴 ${repo.forks}</span>
                </div>
            </div>
        `;
        repoGrid.appendChild(card);
    });
}

function filterRepositories(query) {
    const cards = repoGrid.querySelectorAll(".repo-card");
    cards.forEach(card => {
        const match = card.dataset.title.includes(query) || 
                      card.dataset.desc.includes(query) || 
                      card.dataset.lang.includes(query);
        card.style.display = match ? "flex" : "none";
    });
}

// --- The Vibe Check Engine ---
function openVibeCheckModal() {
    vibeModal.style.display = "flex";
}

async function executeVibeCheck() {
    const jdText = jdTextarea.value.trim();
    if (!jdText) {
        alert("Please paste a Job Description first.");
        return;
    }
    if (!activeUsername) {
        alert("Please load a GitHub profile first.");
        return;
    }

    runVibeCheckBtn.disabled = true;
    runVibeCheckBtn.textContent = "Analyzing Compatibility...";

    try {
        const res = await fetch("/api/vibe-check", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: activeUsername,
                job_description: jdText
            })
        });

        if (!res.ok) throw new Error("Failed to calculate vibe check.");
        const result = await res.json();

        // Update Top Sticky Badge
        vibeBadgeContainer.style.display = "block";
        vibePillScore.textContent = `${result.match_percentage}%`;
        vibeBadgePill.style.backgroundColor = result.badge_color || "#10b981";
        document.getElementById("vibe-badge-title").textContent = `Tech Stack Compatibility: ${result.badge_level}`;
        document.getElementById("vibe-badge-subtitle").textContent = `${result.matched_skills.length} matched skills out of ${result.total_jd_skills} identified in Job Description`;

        // Preview chips on top banner
        matchedSkillsPreview.innerHTML = result.matched_skills.slice(0, 4).map(s => `<span class="preview-tag">✓ ${s}</span>`).join("");

        // Update Modal Results Panel
        vibeResultsPanel.style.display = "block";
        const scoreCircle = document.getElementById("score-circle");
        scoreCircle.style.backgroundColor = result.badge_color || "#10b981";
        document.getElementById("vibe-calc-percent").textContent = `${result.match_percentage}%`;
        document.getElementById("vibe-calc-badge").textContent = result.badge_level;
        document.getElementById("vibe-calc-recommendation").textContent = result.recommendation;

        // Skill Chips
        document.getElementById("matched-count").textContent = result.matched_skills.length;
        document.getElementById("missing-count").textContent = result.missing_skills.length;

        const matchedContainer = document.getElementById("matched-chips-container");
        matchedContainer.innerHTML = result.matched_skills.length 
            ? result.matched_skills.map(s => `<span class="skill-chip matched">✓ ${s}</span>`).join("")
            : "<span style='color:var(--text-muted); font-size:0.8rem;'>No exact skills matched yet.</span>";

        const missingContainer = document.getElementById("missing-chips-container");
        missingContainer.innerHTML = result.missing_skills.length
            ? result.missing_skills.map(s => `<span class="skill-chip missing">✗ ${s}</span>`).join("")
            : "<span style='color:var(--text-muted); font-size:0.8rem;'>All detected JD skills are covered!</span>";

    } catch (err) {
        alert(err.message);
    } finally {
        runVibeCheckBtn.disabled = false;
        runVibeCheckBtn.textContent = "Calculate Compatibility Score";
    }
}

// --- Chatbot Feature 1: Ask Codebase ---
async function handleChatSubmit(e) {
    if (e) e.preventDefault();
    const query = chatUserInput.value.trim();
    if (!query) return;

    if (!activeUsername) {
        appendChatMessage("Please load a developer profile above first!", "bot");
        return;
    }

    appendChatMessage(query, "user");
    chatUserInput.value = "";

    try {
        const res = await fetch("/api/chat/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: activeUsername,
                question: query
            })
        });
        const data = await res.json();
        appendChatMessage(data.reply, "bot");
    } catch (err) {
        appendChatMessage("Sorry, I had trouble analyzing the repository context right now.", "bot");
    }
}

function appendChatMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = `chat-msg ${sender}`;
    // Simple markdown link converter
    const formatted = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:#38bdf8;">$1</a>')
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/\n/g, '<br>');
    msg.innerHTML = formatted;
    chatMessagesContainer.appendChild(msg);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

// --- Chatbot Feature 2: AI Mock Interviewer ---
async function handleInterviewGeneration() {
    if (!activeUsername) {
        alert("Please load a developer profile first.");
        return;
    }
    const jd = jdTextarea.value.trim() || "Full-stack software engineering position with requirements in Python, APIs, and modern databases.";

    generateInterviewBtn.disabled = true;
    generateInterviewBtn.textContent = "Analyzing Repositories & JD...";

    try {
        const res = await fetch("/api/chat/interview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: activeUsername,
                job_description: jd
            })
        });
        const data = await res.json();

        const qList = document.getElementById("interview-questions-list");
        qList.innerHTML = "";

        data.interview_questions.forEach(q => {
            const card = document.createElement("div");
            card.className = "interview-q-card";
            card.innerHTML = `
                <div class="q-badge">${q.type} • Target: ${q.skill}</div>
                <div class="q-text">"${q.question}"</div>
            `;
            qList.appendChild(card);
        });

        document.getElementById("interview-coaching-box").textContent = `💡 Pro Tip: ${data.coaching_tip}`;
        interviewOutput.style.display = "block";
    } catch (err) {
        alert("Failed to generate mock interview questions.");
    } finally {
        generateInterviewBtn.disabled = false;
        generateInterviewBtn.textContent = "Generate Tailored Interview Questions";
    }
}
