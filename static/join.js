const form = document.getElementById('join-form');
const errorBox = document.getElementById('error');

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.textContent = '';
    const nameInput = document.getElementById('name');
    const name = nameInput.value.trim();
    if (!name) {
        errorBox.textContent = 'Please enter your name.';
        return;
    }
    try {
        const response = await fetch('/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        if (!response.ok) {
            const body = await response.json();
            throw new Error(body.detail || 'Unable to join the game');
        }
        const payload = await response.json();
        localStorage.setItem('session_token', payload.session_token);
        localStorage.setItem('player_role', payload.role);
        localStorage.setItem('player_name', name);
        localStorage.setItem('player_id', payload.player_id);
        window.location.href = '/game';
    } catch (error) {
        errorBox.textContent = error.message || 'Join failed.';
    }
});
