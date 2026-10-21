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
        sessionStorage.setItem('session_token', payload.session_token);
        sessionStorage.setItem('player_role', payload.role);
        sessionStorage.setItem('player_name', name);
        sessionStorage.setItem('player_id', payload.player_id);
        window.location.href = '/intro';
    } catch (error) {
        errorBox.textContent = error.message || 'Join failed.';
    }
});
