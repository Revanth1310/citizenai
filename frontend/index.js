let sessionId = null;
let sessionMap = {}; // session_id => topic

window.onload = async () => {
    await fetchSessions();       // Load previous sessions
    const ids = Object.keys(sessionMap);
    if (ids.length) {
        await loadSession(ids[0]); // Load the first session by default
    } else {
        await startNewSession();   // Or create a new one
    }
    await loadDashboardData();  // Pie + timeline chart
};


async function fetchSessions() {
    const res = await fetch("/sessions");
    const data = await res.json();
    data.forEach(({ id, title }) => {
        sessionMap[id] = title;
    });
    renderSessionList();
}

function showTab(tabName, event) {
    document.querySelectorAll('.tab-content').forEach(content =>
        content.classList.remove('active')
    );
    document.querySelectorAll('.tab').forEach(tab =>
        tab.classList.remove('active')
    );
    document.getElementById(tabName).classList.add('active');
    if (event) event.target.classList.add('active');
    
}

async function startNewSession() {
    const res = await fetch('/new-session');
    const data = await res.json();
    sessionId = data.session_id;
    sessionMap[sessionId] = 'New Session';
    renderSessionList();
    document.getElementById('chatMessages').innerHTML = '';
}

function renderSessionList() {
    const ul = document.getElementById('sessionList');
    ul.innerHTML = '';
    Object.keys(sessionMap).forEach(id => {
        const li = document.createElement('li');
        li.innerText = sessionMap[id];
        li.onclick = () => loadSession(id);
        ul.appendChild(li);
    });
}

async function loadSession(id) {
    const res = await fetch(`/history/${id}`);
    const data = await res.json();
    sessionId = id;
    const chatBox = document.getElementById('chatMessages');
    chatBox.innerHTML = '';
    data.messages.forEach(msg => addMessageToChat(msg.message, msg.role));
}

function handleChatKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    addMessageToChat(message, 'user');
    input.value = '';
    const loadingId = addLoadingMessage();

    const res = await fetch(`/chat/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: message })
    });
    const data = await res.json();
    removeLoadingMessage(loadingId);

    const aiResponse = data.response;
    const topic = aiResponse.split('\n')[0].replace(/^#+\s*/, '').trim();

    if (!sessionMap[sessionId] || sessionMap[sessionId] === 'New Session') {
        sessionMap[sessionId] = topic;
        renderSessionList();
    }

    addMessageToChat(aiResponse, 'ai');
}

function addMessageToChat(message, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    const avatarIcon = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
    const contentHtml = sender === 'ai' ? marked.parse(message) : `<p>${message}</p>`;

    messageDiv.innerHTML = `
        <div class="message-avatar"><i class="${avatarIcon}"></i></div>
        <div class="message-content">${contentHtml}</div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    const id = 'loading-' + Date.now();
    loadingDiv.id = id;
    loadingDiv.className = 'message ai';
    loadingDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content"><i class="fas fa-spinner fa-spin"></i> Typing...</div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

function removeLoadingMessage(loadingId) {
    const elem = document.getElementById(loadingId);
    if (elem) elem.remove();
}

async function submitFeedback(event) {
    event.preventDefault();
    const category = document.getElementById('feedbackCategory').value;
    const feedback = document.getElementById('feedbackText').value;

    const formData = new FormData();
    formData.append("category", category);
    formData.append("message", feedback);

    const res = await fetch("/submit-feedback", {
        method: "POST",
        body: formData
    });
    const data = await res.json();

    document.getElementById("sentimentResult").innerHTML = `
        <div class="sentiment-result sentiment-${data.sentiment}">
            Sentiment: ${data.sentiment}
        </div>
    `;

    document.getElementById("feedbackText").value = "";
    loadDashboardData(); // optionally refresh recent feedbacks
}



let sentimentChart = null;
let timeChart = null;

async function loadDashboardData() {
    const list = document.getElementById("recentFeedbackList");
    list.innerHTML = "<div class='loading'><i class='fas fa-spinner'></i> Loading...</div>";

    const res = await fetch("/feedbacks");
    const data = await res.json();
    list.innerHTML = "";

    if (data.feedbacks.length === 0) {
        list.innerHTML = "<p>No feedback available yet.</p>";
    } else {
        data.feedbacks.forEach(entry => {
            const div = document.createElement("div");
            div.className = "feedback-item";
            div.innerHTML = `<div>${entry}</div>`;
            list.appendChild(div);
        });
    }

    // Load sentiment pie chart
    const pie = await fetch("/sentiment-breakdown");
    const sentiment = await pie.json();

    const ctx = document.getElementById("feedbackSentimentChart").getContext("2d");
    if (sentimentChart) sentimentChart.destroy();
    sentimentChart = new Chart(ctx, {
        type: "pie",
        data: {
            labels: ["Positive", "Neutral", "Negative"],
            datasets: [{
                data: [
                    sentiment.positive || 0,
                    sentiment.neutral || 0,
                    sentiment.negative || 0
                ],
                backgroundColor: ["#10b981", "#fbbf24", "#ef4444"]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "bottom" }
            }
        }
    });

    // Load timeline chart
    const timelineRes = await fetch("/feedback-timeline");
    const timeline = await timelineRes.json();
    const months = Object.keys(timeline);
    const counts = Object.values(timeline);

    const timeCtx = document.getElementById("activityChart").getContext("2d");
    if (timeChart) timeChart.destroy();
    timeChart = new Chart(timeCtx, {
        type: "line",
        data: {
            labels: months,
            datasets: [{
                label: "Feedbacks per Month",
                data: counts,
                borderColor: "#667eea",
                fill: false,
                tension: 0.2
            }]
        },
        options: {
            responsive: true,
            scales: {
              y: {
                beginAtZero: true,
                min: 0,
                ticks: {
                  stepSize: 10
                }
              }
            }

        }
    });
}
