/**
 * Admin Panel JavaScript for Energy Trading Game
 * Module A: Admin / Game Master Panel
 */

(function() {
    'use strict';

    // DOM Elements (will be assigned after DOM loads)
    let loginSection = null;
    let adminPanel = null;
    let adminPinInput = null;
    let loginButton = null;
    let loginMessage = null;
    let logoutButton = null;

    let statusText = null;
    let timerDisplay = null;
    let roundProgress = null;
    let currentScenario = null;
    let messageBox = null;

    let startButton = null;
    let pauseButton = null;
    let resumeButton = null;
    let endButton = null;
    let restartButton = null;
    let shockPositiveButton = null;
    let shockNegativeButton = null;
    let totalRoundsInput = null;
    let durationSecondsInput = null;
    let nextScenarioSelect = null;
    let nextScenario2Select = null;
    let priceModeSelect = null;
    let priceModeHint = null;
    let durationHint = null;
    let scenarioHint = null;

    let playerCount = null;
    let playersTbody = null;

    let releaseBriefingButton = null;
    let briefingReadyCount = null;
    let briefingTotalCount = null;
    let briefingHint = null;
    // State
    let isAuthenticated = false;
    let gameStatus = null;
    let userEditedDuration = false;
    let userEditedTotalRounds = false;
    let pollingInterval = null;

    // ============================================================================
    // DOM Initialization
    // ============================================================================

    function initDOMElements() {
        console.log('[Admin] Initializing DOM elements...');

        loginSection = document.getElementById('login-section');
        adminPanel = document.getElementById('admin-panel');
        adminPinInput = document.getElementById('admin-pin');
        loginButton = document.getElementById('login-button');
        loginMessage = document.getElementById('login-message');
        logoutButton = document.getElementById('logout-button');

        statusText = document.getElementById('status-text');
        timerDisplay = document.getElementById('timer-display');
        roundProgress = document.getElementById('round-progress');
        currentScenario = document.getElementById('current-scenario');
        messageBox = document.getElementById('admin-message');

        startButton = document.getElementById('start-round');
        pauseButton = document.getElementById('pause-round');
        resumeButton = document.getElementById('resume-round');
        endButton = document.getElementById('end-round');
        restartButton = document.getElementById('restart-game');
        shockPositiveButton = document.getElementById('shock-positive');
        shockNegativeButton = document.getElementById('shock-negative');

        totalRoundsInput = document.getElementById('total-rounds');
        durationSecondsInput = document.getElementById('duration-seconds');
        nextScenarioSelect = document.getElementById('next-scenario');
        nextScenario2Select = document.getElementById('next-scenario-2');
        priceModeSelect = document.getElementById('price-mode');
        priceModeHint = document.getElementById('price-mode-hint');
        durationHint = document.getElementById('duration-hint');
        scenarioHint = document.getElementById('scenario-hint');

        playerCount = document.getElementById('player-count');
        playersTbody = document.getElementById('players-tbody');

        releaseBriefingButton = document.getElementById('release-briefing');
        briefingReadyCount = document.getElementById('briefing-ready-count');
        briefingTotalCount = document.getElementById('briefing-total-count');
        briefingHint = document.getElementById('briefing-hint');

        // Log what we found
        console.log('[Admin] loginButton:', loginButton);
        console.log('[Admin] adminPinInput:', adminPinInput);
        console.log('[Admin] loginSection:', loginSection);
        console.log('[Admin] adminPanel:', adminPanel);

        // Defensive checks
        if (!loginButton) {
            console.error('[Admin] CRITICAL: login-button element not found!');
        }
        if (!adminPinInput) {
            console.error('[Admin] CRITICAL: admin-pin element not found!');
        }
        if (!loginSection) {
            console.error('[Admin] CRITICAL: login-section element not found!');
        }
        if (!adminPanel) {
            console.error('[Admin] CRITICAL: admin-panel element not found!');
        }
    }

    function attachEventListeners() {
        console.log('[Admin] Attaching event listeners...');

        if (loginButton) {
            loginButton.addEventListener('click', handleLoginClick);
            console.log('[Admin] Login button click listener attached');
        } else {
            console.error('[Admin] Cannot attach listener: loginButton is null');
        }

        if (adminPinInput) {
            adminPinInput.addEventListener('keypress', handlePinKeypress);
            console.log('[Admin] PIN input keypress listener attached');
        }

        if (logoutButton) {
            logoutButton.addEventListener('click', logout);
        }

        if (startButton) {
            startButton.addEventListener('click', startRound);
        }

        if (pauseButton) {
            pauseButton.addEventListener('click', pauseRound);
        }

        if (resumeButton) {
            resumeButton.addEventListener('click', resumeRound);
        }

        if (endButton) {
            endButton.addEventListener('click', endRound);
        }

        if (restartButton) {
            restartButton.addEventListener('click', restartGame);
        }

        if (releaseBriefingButton) {
            releaseBriefingButton.addEventListener('click', releaseBriefing);
        }

        if (shockPositiveButton) {
            shockPositiveButton.addEventListener('click', () => triggerShock('positive'));
        }

        if (shockNegativeButton) {
            shockNegativeButton.addEventListener('click', () => triggerShock('negative'));
        }

        if (durationSecondsInput) {
            durationSecondsInput.addEventListener('input', () => {
                userEditedDuration = true;
            });
        }

        if (totalRoundsInput) {
            totalRoundsInput.addEventListener('input', () => {
                userEditedTotalRounds = true;
            });
        }
    }

    // ============================================================================
    // Authentication
    // ============================================================================

    async function handleLoginClick(event) {
        console.log('[Admin] Login button clicked');

        // Prevent any default form submission
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        await login();
    }

    function handlePinKeypress(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            login();
        }
    }

    async function login() {
        console.log('[Admin] login() function called');

        if (!adminPinInput) {
            console.error('[Admin] adminPinInput is null');
            return;
        }

        const pin = adminPinInput.value.trim();
        console.log('[Admin] PIN entered:', pin ? '(hidden)' : '(empty)');

        if (!pin) {
            showLoginMessage('Please enter PIN', 'error');
            return;
        }

        console.log('[Admin] Sending POST /api/admin/login...');

        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ pin: pin })
            });

            console.log('[Admin] Login response status:', response.status);

            const data = await response.json();
            console.log('[Admin] Login response data:', data);

            if (response.ok && data.authenticated) {
                console.log('[Admin] Login successful');
                isAuthenticated = true;
                showAdminPanel();
                showMessage('Login successful', 'success');
                startPolling();
            } else {
                console.log('[Admin] Login failed:', data.error);
                showLoginMessage(data.error || 'Invalid admin PIN', 'error');
            }
        } catch (error) {
            console.error('[Admin] Login request failed:', error);
            showLoginMessage('Login failed. Please try again.', 'error');
        }
    }

    async function logout() {
        console.log('[Admin] logout() called');

        try {
            await fetch('/api/admin/logout', {
                method: 'POST',
                credentials: 'same-origin'
            });
        } catch (error) {
            console.error('[Admin] Logout error:', error);
        }

        isAuthenticated = false;
        stopPolling();
        showLoginPanel();

        if (adminPinInput) {
            adminPinInput.value = '';
        }
    }

    function showLoginPanel() {
        console.log('[Admin] Showing login panel');
        if (loginSection) {
            loginSection.classList.remove('hidden');
        }
        if (adminPanel) {
            adminPanel.classList.add('hidden');
        }
    }

    function showAdminPanel() {
        console.log('[Admin] Showing admin panel');
        if (loginSection) {
            loginSection.classList.add('hidden');
        }
        if (adminPanel) {
            adminPanel.classList.remove('hidden');
        }
    }

    function showLoginMessage(text, type) {
        console.log('[Admin] Login message:', text, '(' + type + ')');
        if (loginMessage) {
            loginMessage.textContent = text;
            loginMessage.className = type || 'info';
        }
    }

    // ============================================================================
    // Status Polling
    // ============================================================================

    async function fetchStatus() {
        try {
            const response = await fetch('/api/admin/status', {
                credentials: 'same-origin'
            });

            if (response.status === 401) {
                console.log('[Admin] Session expired (401)');
                if (isAuthenticated) {
                    isAuthenticated = false;
                    stopPolling();
                    showLoginPanel();
                    showLoginMessage('Session expired. Please log in again.', 'error');
                }
                return;
            }

            if (!response.ok) {
                console.error('[Admin] Failed to fetch status:', response.status);
                return;
            }

            gameStatus = await response.json();
            updateUI();
        } catch (error) {
            console.error('[Admin] Status fetch error:', error);
        }
    }

    async function fetchPlayers() {
        try {
            const response = await fetch('/api/admin/players', {
                credentials: 'same-origin'
            });

            if (response.status === 401) {
                return;
            }

            if (!response.ok) {
                console.error('[Admin] Failed to fetch players:', response.status);
                return;
            }

            const data = await response.json();
            updatePlayerTable(data.players);
        } catch (error) {
            console.error('[Admin] Players fetch error:', error);
        }
    }

    function startPolling() {
        console.log('[Admin] Starting polling');
        fetchStatus();
        fetchPlayers();

        pollingInterval = setInterval(() => {
            fetchStatus();
            fetchPlayers();
        }, 1000);
    }

    function stopPolling() {
        console.log('[Admin] Stopping polling');
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    // ============================================================================
    // UI Updates
    // ============================================================================

    function updateUI() {
        if (!gameStatus) return;

        const { round_active, round_paused, current_round, next_round_number, total_rounds, scenario, scenario2, duration_seconds, remaining_seconds, game_complete } = gameStatus;

        // Update status text
        if (game_complete) {
            if (statusText) statusText.textContent = 'Game Complete';
            if (timerDisplay) timerDisplay.textContent = '-';
        } else if (round_active && round_paused) {
            if (statusText) statusText.textContent = `Round ${current_round} Paused`;
            if (timerDisplay) timerDisplay.textContent = `${remaining_seconds}s`;
        } else if (round_active) {
            if (statusText) statusText.textContent = `Round ${current_round} Active`;
            if (timerDisplay) timerDisplay.textContent = `${remaining_seconds}s`;
        } else if (next_round_number > 1) {
            if (statusText) statusText.textContent = 'Between Rounds';
            if (timerDisplay) timerDisplay.textContent = '-';
        } else {
            if (statusText) statusText.textContent = 'Game Not Started';
            if (timerDisplay) timerDisplay.textContent = '-';
        }

        // Update progress
        if (current_round && roundProgress) {
            roundProgress.textContent = `Round ${current_round} of ${total_rounds}`;
        } else if (roundProgress) {
            roundProgress.textContent = `${total_rounds} rounds configured`;
        }

        // Between rounds, show the dropdown selection for the next round, not the finished round's pair.
        if (currentScenario) {
            const scenarioNames = { up: 'Up ↑', down: 'Down ↓', oscillate: 'Oscillate ~' };
            const label = (value) => scenarioNames[value] || value;
            if (round_active && scenario) {
                currentScenario.textContent = `${label(scenario)} → ${label(scenario2 || scenario)}`;
            } else if (!game_complete && nextScenarioSelect && nextScenario2Select) {
                currentScenario.textContent = `Next: ${label(nextScenarioSelect.value)} → ${label(nextScenario2Select.value)}`;
            } else {
                currentScenario.textContent = '-';
            }
        }

        // Update buttons visibility
        updateBriefingPanel();

        if (!startButton || !pauseButton || !resumeButton || !endButton) {
            return; // Elements not found
        }

        if (game_complete) {
            startButton.classList.add('hidden');
            pauseButton.classList.add('hidden');
            resumeButton.classList.add('hidden');
            endButton.classList.add('hidden');
        } else if (round_active && round_paused) {
            startButton.classList.add('hidden');
            pauseButton.classList.add('hidden');
            resumeButton.classList.remove('hidden');
            endButton.classList.remove('hidden');
        } else if (round_active) {
            startButton.classList.add('hidden');
            pauseButton.classList.remove('hidden');
            resumeButton.classList.add('hidden');
            endButton.classList.remove('hidden');
        } else {
            startButton.classList.remove('hidden');
            pauseButton.classList.add('hidden');
            resumeButton.classList.add('hidden');
            endButton.classList.add('hidden');
        }

        // Update configuration inputs
        const shockVisible = round_active && !round_paused;
        [shockPositiveButton, shockNegativeButton].forEach((button) => {
            if (!button) return;
            button.classList.toggle('hidden', !shockVisible);
            button.disabled = !!gameStatus.shock_active;
        });
        if (!userEditedTotalRounds && totalRoundsInput) {
            totalRoundsInput.value = total_rounds;
        }
        if (!userEditedDuration && durationSecondsInput) {
            durationSecondsInput.value = duration_seconds;
        }

        // Game mode is fixed once the first round has started
        if (priceModeSelect) {
            const modeLocked = round_active || next_round_number > 1;
            priceModeSelect.disabled = modeLocked;
            if (modeLocked && gameStatus.price_mode) {
                priceModeSelect.value = gameStatus.price_mode;
            }
            if (priceModeHint) priceModeHint.classList.toggle('hidden', !modeLocked);
        }

        // Disable configuration during active round
        if (durationSecondsInput && nextScenarioSelect && nextScenario2Select && totalRoundsInput) {
            if (round_active) {
                durationSecondsInput.disabled = true;
                nextScenarioSelect.disabled = true;
                nextScenario2Select.disabled = true;
                totalRoundsInput.disabled = true;
                if (durationHint) durationHint.classList.remove('hidden');
                if (scenarioHint) scenarioHint.classList.remove('hidden');
            } else {
                durationSecondsInput.disabled = false;
                nextScenarioSelect.disabled = false;
                nextScenario2Select.disabled = false;
                if (next_round_number <= 1) {
                    totalRoundsInput.disabled = false;
                }
                if (durationHint) durationHint.classList.add('hidden');
                if (scenarioHint) scenarioHint.classList.add('hidden');
            }
        }
    }

    function updatePlayerTable(players) {
        if (!playerCount || !playersTbody) return;

        playerCount.textContent = players.length;

        if (players.length === 0) {
            playersTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="7">No players connected</td>
                </tr>
            `;
            return;
        }

        const rows = players.map(player => {
            const roundPnlClass = player.round_pnl >= 0 ? 'positive' : 'negative';
            const cumulativePnlClass = player.cumulative_pnl >= 0 ? 'positive' : 'negative';
            const roundPnlSign = player.round_pnl >= 0 ? '+' : '';
            const cumulativePnlSign = player.cumulative_pnl >= 0 ? '+' : '';

            return `
                <tr>
                    <td>${escapeHtml(player.name)}</td>
                    <td>${player.role}</td>
                    <td>${player.briefing_ready ? '✓' : '–'}</td>
                    <td>${player.position}</td>
                    <td class="${roundPnlClass}">${roundPnlSign}${player.round_pnl.toFixed(2)}</td>
                    <td class="${cumulativePnlClass}">${cumulativePnlSign}${player.cumulative_pnl.toFixed(2)}</td>
                    <td>${player.trade_count}</td>
                </tr>
            `;
        }).join('');

        playersTbody.innerHTML = rows;
    }

    function updateBriefingPanel() {
        const { briefing_released, players_ready, players_total } = gameStatus;
        const allReady = players_total > 0 && players_ready === players_total;

        if (briefingReadyCount) briefingReadyCount.textContent = players_ready;
        if (briefingTotalCount) briefingTotalCount.textContent = players_total;

        if (releaseBriefingButton) {
            releaseBriefingButton.disabled = briefing_released || !allReady;
            releaseBriefingButton.classList.toggle('hidden', briefing_released);
        }
        if (briefingHint) {
            briefingHint.textContent = briefing_released
                ? 'Briefing released. Players are in the game lobby; you can start the game.'
                : (allReady ? 'Everyone has confirmed.' : 'Waiting for all players to tick the checkbox.');
        }
        if (startButton) {
            startButton.disabled = !briefing_released;
            startButton.title = briefing_released ? '' : 'Release the briefing first';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showMessage(text, type) {
        if (messageBox) {
            messageBox.textContent = text;
            messageBox.className = type || 'info';

            setTimeout(() => {
                if (messageBox.textContent === text) {
                    messageBox.textContent = '';
                    messageBox.className = 'info';
                }
            }, 5000);
        }
    }

    // ============================================================================
    // Admin Actions
    // ============================================================================

    async function releaseBriefing() {
        try {
            const response = await fetch('/api/admin/release-briefing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to release briefing', 'error');
                return;
            }

            showMessage('Players moved to the game lobby. You can start the game.', 'success');
            fetchStatus();
        } catch (error) {
            showMessage('Failed to release briefing', 'error');
            console.error('[Admin] Release briefing error:', error);
        }
    }

    async function startRound() {
        const totalRounds = totalRoundsInput ? parseInt(totalRoundsInput.value, 10) : 5;
        const durationSeconds = durationSecondsInput ? parseInt(durationSecondsInput.value, 10) : 90;
        const scenario = nextScenarioSelect ? nextScenarioSelect.value : 'oscillate';
        const scenario2 = nextScenario2Select ? nextScenario2Select.value : 'down';
        const priceMode = priceModeSelect ? priceModeSelect.value : 'hard';

        if (isNaN(totalRounds) || totalRounds < 1) {
            showMessage('Total rounds must be at least 1', 'error');
            return;
        }
        if (isNaN(durationSeconds) || durationSeconds < 10) {
            showMessage('Round duration must be at least 10 seconds', 'error');
            return;
        }

        try {
            const response = await fetch('/api/admin/start-round', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    scenario,
                    scenario2,
                    duration_seconds: durationSeconds,
                    total_rounds: totalRounds,
                    price_mode: priceMode
                })
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to start round', 'error');
                return;
            }

            showMessage(`Round ${data.round_number} started (${data.scenario} → ${data.scenario2}, ${data.duration_seconds}s)`, 'success');
            userEditedDuration = false;
            userEditedTotalRounds = false;
        } catch (error) {
            showMessage('Failed to start round', 'error');
            console.error('[Admin] Start round error:', error);
        }
    }

    async function triggerShock(direction) {
        try {
            const response = await fetch('/api/admin/trigger-shock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ direction })
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to trigger shock', 'error');
                return;
            }

            showMessage(`${direction === 'positive' ? 'Positive' : 'Negative'} shock triggered (${data.duration_seconds}s)`, 'success');
            fetchStatus();
        } catch (error) {
            showMessage('Failed to trigger shock', 'error');
            console.error('[Admin] Trigger shock error:', error);
        }
    }

    async function pauseRound() {
        try {
            const response = await fetch('/api/admin/pause-round', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to pause round', 'error');
                return;
            }

            showMessage(`Round paused (${data.remaining_seconds}s remaining)`, 'success');
        } catch (error) {
            showMessage('Failed to pause round', 'error');
            console.error('[Admin] Pause round error:', error);
        }
    }

    async function resumeRound() {
        try {
            const response = await fetch('/api/admin/resume-round', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to resume round', 'error');
                return;
            }

            showMessage(`Round resumed (${data.remaining_seconds}s remaining)`, 'success');
        } catch (error) {
            showMessage('Failed to resume round', 'error');
            console.error('[Admin] Resume round error:', error);
        }
    }

    async function endRound() {
        try {
            const response = await fetch('/api/admin/end-round', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to end round', 'error');
                return;
            }

            showMessage(`Round ${data.round_number} ended (close price: ${data.close_price.toFixed(2)})`, 'success');
        } catch (error) {
            showMessage('Failed to end round', 'error');
            console.error('[Admin] End round error:', error);
        }
    }

    async function restartGame() {
        const confirmed = confirm('Are you sure you want to restart the game? This will remove all players and reset scores.');
        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch('/admin/restart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.detail || 'Failed to restart game', 'error');
                return;
            }

            showMessage('Game restarted successfully', 'success');
            userEditedDuration = false;
            userEditedTotalRounds = false;
        } catch (error) {
            showMessage('Failed to restart game', 'error');
            console.error('[Admin] Restart game error:', error);
        }
    }

    // ============================================================================
    // Initialization
    // ============================================================================

    function init() {
        console.log('[Admin] ===========================================');
        console.log('[Admin] Admin panel JavaScript initializing...');
        console.log('[Admin] ===========================================');

        initDOMElements();
        attachEventListeners();

        // Check initial auth state
        console.log('[Admin] Checking initial authentication state...');
        fetchStatus();

        console.log('[Admin] Initialization complete');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already loaded
        init();
    }

})();
