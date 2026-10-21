const sessionToken = sessionStorage.getItem('session_token');
if (!sessionToken) {
    window.location.href = '/';
}

const checkbox = document.getElementById('read-checkbox');
const statusBox = document.getElementById('intro-status');
const roleName = document.getElementById('intro-role-name');

const ROLE_LABELS = { Generator: 'Termelő', Retailer: 'Kiskereskedő', Trader: 'Kereskedő' };
const playerRole = sessionStorage.getItem('player_role');
roleName.textContent = ROLE_LABELS[playerRole] ? `${ROLE_LABELS[playerRole]} (${playerRole})` : '-';
document.querySelectorAll('.intro-roles li').forEach((item) => {
    item.classList.toggle('highlight', item.dataset.role === playerRole);
});

function setStatus(text, isError = false) {
    statusBox.textContent = text;
    statusBox.className = isError ? 'error' : 'info';
}

function updateWaitingText() {
    setStatus(checkbox.checked
        ? 'Köszönjük! Várakozás a játékvezetőre, amíg mindenki elolvassa a leírást...'
        : '');
}

function goToGame() {
    window.location.href = '/game';
}

function clearSessionAndRejoin() {
    ['session_token', 'player_id', 'player_name', 'player_role'].forEach((key) => sessionStorage.removeItem(key));
    window.location.href = '/';
}

async function refreshStatus() {
    try {
        const response = await fetch(`/briefing-status?session_token=${encodeURIComponent(sessionToken)}`);
        if (response.status === 404) {
            clearSessionAndRejoin();
            return;
        }
        const data = await response.json();
        if (data.briefing_released) {
            goToGame();
            return;
        }
        checkbox.checked = data.ready;
        updateWaitingText();
    } catch (error) {
        setStatus('A szerver nem érhető el.', true);
    }
}

checkbox.addEventListener('change', async () => {
    checkbox.disabled = true;
    try {
        const response = await fetch('/briefing/ready', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: sessionToken, ready: checkbox.checked }),
        });
        if (!response.ok) {
            throw new Error('A jelölés nem sikerült.');
        }
        const data = await response.json();
        if (data.briefing_released) {
            goToGame();
            return;
        }
        updateWaitingText();
    } catch (error) {
        checkbox.checked = !checkbox.checked;
        setStatus(error.message || 'A jelölés nem sikerült.', true);
    } finally {
        checkbox.disabled = false;
    }
});

function connectWebSocket() {
    const ws = new WebSocket((window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws');
    ws.addEventListener('open', refreshStatus);
    ws.addEventListener('message', (event) => {
        const { type } = JSON.parse(event.data);
        if (type === 'briefing_released') {
            goToGame();
        } else if (type === 'game_restarted') {
            clearSessionAndRejoin();
        }
    });
    ws.addEventListener('close', () => setTimeout(connectWebSocket, 2000));
}

refreshStatus();
connectWebSocket();
