const sessionToken = localStorage.getItem('session_token');
const playerRole = localStorage.getItem('player_role') || '-';
const playerName = localStorage.getItem('player_name') || '';
const playerId = localStorage.getItem('player_id');

if (!sessionToken) {
    window.location.href = '/';
} else {
    fetch(`/briefing-status?session_token=${encodeURIComponent(sessionToken)}`)
        .then((response) => (response.ok ? response.json() : null))
        .then((data) => {
            if (data && !data.briefing_released) {
                window.location.href = '/intro';
            }
        })
        .catch(() => {});
}

const roleLabel = document.getElementById('player-role');
const positionLabel = document.getElementById('position');
const currentCashLabel = document.getElementById('current-cash');
const expectedCashLabel = document.getElementById('expected-cash');
const unitEconomicsDiv = document.getElementById('unit-economics');
const unitLabel = document.getElementById('unit-label');
const unitValue = document.getElementById('unit-value');
const roundPnlLabel = document.getElementById('round-pnl');
const cumulativePnlLabel = document.getElementById('cumulative-pnl');
const breakEvenLabel = document.getElementById('break-even');
const statusIndicatorLabel = document.getElementById('status-indicator');
const newsHeadline = document.getElementById('news-headline');
const newsBody = document.getElementById('news-body');
const forecastCards = document.getElementById('forecast-cards');
const newsRoundLabel = document.getElementById('news-round-label');
const bidLabel = document.getElementById('bid-price');
const offerLabel = document.getElementById('offer-price');
const lastLabel = document.getElementById('last-price');
const timerLabel = document.getElementById('timer');
const messageBox = document.getElementById('message');
const resultPanel = document.getElementById('result-panel');
const summaryText = document.getElementById('summary-text');
const leaderboardContainer = document.getElementById('leaderboard');
const buyButton = document.getElementById('buy-button');
const sellButton = document.getElementById('sell-button');
const chartCanvas = document.getElementById('price-chart');
const chartContext = chartCanvas.getContext('2d');
const candleCanvas = document.getElementById('candle-chart');
const candleContext = candleCanvas.getContext('2d');
const themeToggle = document.getElementById('theme-toggle');
const tradeHistoryList = document.getElementById('trade-history-list');
const tradeHistoryPanel = document.getElementById('trade-history-panel');

const playerStartPosition = Number(localStorage.getItem('start_position') || '0');
let playerCurrentPosition = Number(localStorage.getItem('current_position') || String(playerStartPosition));
let playerCumulativePnl = Number(localStorage.getItem('cumulative_pnl') || '0');
let playerRoundPnl = Number(localStorage.getItem('round_pnl') || '0');
let currentBid = null;
let currentOffer = null;
let currentLastPrice = null;
let currentRemainingSeconds = 0;
let lineHistory = [];
let candleHistory = []; // Stores OHLC candles (5-second intervals, up to 120 for 10 minutes)
let roundActive = false;
let pricePointBuffer = []; // Buffer for building candles from price updates
let currentRoundTrades = []; // Track trades for current round display

// Theme management
const savedTheme = localStorage.getItem('theme') || 'white';
if (savedTheme === 'black') {
    document.body.classList.remove('white-theme');
    document.body.classList.add('black-theme');
}

function toggleTheme() {
    const isBlack = document.body.classList.contains('black-theme');
    if (isBlack) {
        document.body.classList.remove('black-theme');
        document.body.classList.add('white-theme');
        localStorage.setItem('theme', 'white');
    } else {
        document.body.classList.remove('white-theme');
        document.body.classList.add('black-theme');
        localStorage.setItem('theme', 'black');
    }
    // Re-render charts with new theme colors
    if (lineHistory.length > 0) {
        renderChart(lineHistory);
    }
    if (candleHistory.length > 0) {
        renderCandleChart(candleHistory);
    }
}

themeToggle.addEventListener('click', toggleTheme);

const widthToggle = document.getElementById('width-toggle');

function applyWideView(isWide) {
    document.body.classList.toggle('wide-view', isWide);
    widthToggle.textContent = isWide ? 'Compact view' : 'Wide view';
}

applyWideView(localStorage.getItem('wide_view') === '1');
widthToggle.addEventListener('click', () => {
    const isWide = !document.body.classList.contains('wide-view');
    localStorage.setItem('wide_view', isWide ? '1' : '0');
    applyWideView(isWide);
});

function getThemeColors() {
    const isBlack = document.body.classList.contains('black-theme');
    if (isBlack) {
        return {
            bg: '#1a1a1a',
            line: '#60a5fa',
            text: '#f0f0f0',
            grid: '#404040',
            candleUp: '#4ade80',
            candleDown: '#f87171',
            wick: '#a0a0a0'
        };
    }
    return {
        bg: '#ffffff',
        line: '#0d6efd',
        text: '#111827',
        grid: '#e2e8f0',
        candleUp: '#16a34a',
        candleDown: '#dc2626',
        wick: '#6b7280'
    };
}

roleLabel.textContent = playerRole;
positionLabel.textContent = playerCurrentPosition;
if (currentCashLabel) currentCashLabel.textContent = '0.00';
if (expectedCashLabel) expectedCashLabel.textContent = '0.00';
if (breakEvenLabel) breakEvenLabel.textContent = '-';
if (statusIndicatorLabel) statusIndicatorLabel.textContent = '-';
roundPnlLabel.textContent = playerRoundPnl.toFixed(2);
cumulativePnlLabel.textContent = playerCumulativePnl.toFixed(2);
bidLabel.textContent = '-';
offerLabel.textContent = '-';
lastLabel.textContent = '-';
timerLabel.textContent = '-';
if (newsHeadline) newsHeadline.textContent = 'Waiting for the next round...';
if (newsBody) newsBody.textContent = '';
if (forecastCards) forecastCards.innerHTML = '';
updateButtonState();
showMessage('Waiting for the game master to start the round.', false);
renderTradeHistory();

function showMessage(text, isError = false) {
    messageBox.textContent = text;
    messageBox.className = isError ? 'error' : 'info';
}

function updateButtonState() {
    const enabled = roundActive && currentBid !== null && currentOffer !== null && currentRemainingSeconds > 0;
    buyButton.disabled = !enabled;
    sellButton.disabled = !enabled;
    buyButton.textContent = currentOffer !== null ? `Buy 1 MWh at offer ${formatMoney(currentOffer)}` : 'Buy 1 MWh at offer';
    sellButton.textContent = currentBid !== null ? `Sell 1 MWh at bid ${formatMoney(currentBid)}` : 'Sell 1 MWh at bid';
}

function resetSummary() {
    resultPanel.classList.add('hidden');
    summaryText.textContent = '';
    leaderboardContainer.innerHTML = '';
}

function renderTradeHistory() {
    if (!tradeHistoryList) return;

    if (currentRoundTrades.length === 0) {
        tradeHistoryList.innerHTML = '<p class="empty-message">No trades yet this round.</p>';
        return;
    }

    let html = '<table class="trade-history-table"><thead><tr>' +
        '<th>#</th><th>Side</th><th>Qty</th><th>Price</th><th>Trade P&L</th><th>Position</th><th>Type</th>' +
        '</tr></thead><tbody>';

    currentRoundTrades.forEach((trade, index) => {
        const sideClass = trade.direction === 'buy' ? 'buy-side' : 'sell-side';
        const typeLabel = trade.is_auto_closeout ? '<span class="auto-label">Auto close-out</span>' : 'Manual';
        const pnlClass = trade.pnl_contribution >= 0 ? 'positive-pnl' : 'negative-pnl';
        const pnlSign = trade.pnl_contribution >= 0 ? '+' : '';

        html += `<tr class="${trade.is_auto_closeout ? 'auto-trade' : ''}">` +
            `<td>${index + 1}</td>` +
            `<td class="${sideClass}">${trade.direction.toUpperCase()}</td>` +
            `<td>${trade.quantity}</td>` +
            `<td>${formatMoney(trade.price)}</td>` +
            `<td class="${pnlClass}">${pnlSign}${formatMoney(trade.pnl_contribution)}</td>` +
            `<td>${trade.resulting_position}</td>` +
            `<td>${typeLabel}</td>` +
            `</tr>`;
    });

    html += '</tbody></table>';
    tradeHistoryList.innerHTML = html;
}

function addTradeToHistory(trade) {
    // Simple deduplication: skip if last trade has same direction, price, and position
    const last = currentRoundTrades[currentRoundTrades.length - 1];
    if (last && last.direction === trade.direction && last.price === trade.price && last.resulting_position === trade.resulting_position) {
        return;
    }
    currentRoundTrades.push(trade);
    renderTradeHistory();
}

function scrollChartsToEnd() {
    document.querySelectorAll('.chart-scroll-wrapper').forEach(wrapper => {
        wrapper.scrollLeft = wrapper.scrollWidth;
    });
}

function renderChart(points) {
    const width = chartCanvas.width;
    const height = chartCanvas.height;
    const colors = getThemeColors();

    // Clear and fill background
    chartContext.clearRect(0, 0, width, height);
    chartContext.fillStyle = colors.bg;
    chartContext.fillRect(0, 0, width, height);

    if (points.length < 2) {
        return;
    }

    const mids = points.map((p) => p.mid);
    const min = Math.min(...mids);
    const max = Math.max(...mids);
    const range = Math.max(max - min, 1);
    const padding = 20;

    // Draw grid lines
    chartContext.strokeStyle = colors.grid;
    chartContext.lineWidth = 1;
    chartContext.beginPath();
    for (let i = 0; i <= 4; i++) {
        const y = padding + (i / 4) * (height - 2 * padding);
        chartContext.moveTo(padding, y);
        chartContext.lineTo(width - padding, y);
    }
    chartContext.stroke();

    // Draw price line
    chartContext.strokeStyle = colors.line;
    chartContext.lineWidth = 2;
    chartContext.beginPath();
    points.forEach((point, index) => {
        const x = (index / (points.length - 1)) * (width - 2 * padding) + padding;
        const y = height - ((point.mid - min) / range) * (height - 2 * padding) - padding;
        if (index === 0) {
            chartContext.moveTo(x, y);
        } else {
            chartContext.lineTo(x, y);
        }
    });
    chartContext.stroke();

    // Draw min/max labels
    chartContext.fillStyle = colors.text;
    chartContext.font = '11px sans-serif';
    chartContext.textAlign = 'right';
    chartContext.fillText(max.toFixed(2), width - 5, padding + 10);
    chartContext.fillText(min.toFixed(2), width - 5, height - padding - 5);
}

function aggregateCandles(pricePoints, intervalSeconds = 5, maxCandles = 120) {
    if (pricePoints.length === 0) return [];

    const candles = [];
    let currentCandle = null;
    let currentBucketStart = 0;

    for (let i = 0; i < pricePoints.length; i++) {
        const point = pricePoints[i];
        // Use timestamp-based bucketing if available, otherwise use array index
        const bucketIndex = Math.floor(i / intervalSeconds);

        if (!currentCandle || bucketIndex > currentBucketStart) {
            // Start a new candle
            currentCandle = {
                open: point.mid,
                high: point.mid,
                low: point.mid,
                close: point.mid,
                bucketIndex: bucketIndex
            };
            candles.push(currentCandle);
            currentBucketStart = bucketIndex;
        } else {
            // Update current candle
            currentCandle.high = Math.max(currentCandle.high, point.mid);
            currentCandle.low = Math.min(currentCandle.low, point.mid);
            currentCandle.close = point.mid;
        }
    }

    // Return only the most recent candles
    return candles.slice(-maxCandles);
}

function renderCandleChart(candles) {
    const width = candleCanvas.width;
    const height = candleCanvas.height;
    const colors = getThemeColors();

    // Clear and fill background
    candleContext.clearRect(0, 0, width, height);
    candleContext.fillStyle = colors.bg;
    candleContext.fillRect(0, 0, width, height);

    if (candles.length === 0) {
        return;
    }

    // Calculate price range
    const allPrices = candles.flatMap(c => [c.open, c.high, c.low, c.close]);
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const range = Math.max(max - min, 0.01);
    const padding = 20;

    const chartWidth = width - 2 * padding;
    const chartHeight = height - 2 * padding;
    const candleWidth = Math.max(4, Math.min(30, (chartWidth / candles.length) * 0.7));
    const gap = chartWidth / candles.length;

    // Draw grid lines
    candleContext.strokeStyle = colors.grid;
    candleContext.lineWidth = 1;
    candleContext.beginPath();
    for (let i = 0; i <= 4; i++) {
        const y = padding + (i / 4) * chartHeight;
        candleContext.moveTo(padding, y);
        candleContext.lineTo(width - padding, y);
    }
    candleContext.stroke();

    // Draw candles
    candles.forEach((candle, i) => {
        const x = padding + i * gap + gap / 2;
        const yOpen = padding + chartHeight - ((candle.open - min) / range) * chartHeight;
        const yClose = padding + chartHeight - ((candle.close - min) / range) * chartHeight;
        const yHigh = padding + chartHeight - ((candle.high - min) / range) * chartHeight;
        const yLow = padding + chartHeight - ((candle.low - min) / range) * chartHeight;

        const isUp = candle.close >= candle.open;
        const candleColor = isUp ? colors.candleUp : colors.candleDown;

        // Draw wick
        candleContext.strokeStyle = colors.wick;
        candleContext.lineWidth = 1;
        candleContext.beginPath();
        candleContext.moveTo(x, yHigh);
        candleContext.lineTo(x, yLow);
        candleContext.stroke();

        // Draw body
        candleContext.fillStyle = candleColor;
        const bodyTop = Math.min(yOpen, yClose);
        const bodyHeight = Math.max(1, Math.abs(yClose - yOpen));
        candleContext.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    });

    // Draw min/max labels
    candleContext.fillStyle = colors.text;
    candleContext.font = '11px sans-serif';
    candleContext.textAlign = 'right';
    candleContext.fillText(max.toFixed(2), width - 5, padding + 10);
    candleContext.fillText(min.toFixed(2), width - 5, height - padding - 5);
}

function formatMoney(value) {
    return Number(value).toFixed(2);
}

function getRoleStartingPosition(role) {
    switch(role) {
        case 'Generator':
            return 10;
        case 'Retailer':
            return -10;
        case 'Trader':
            return 0;
        default:
            return 0;
    }
}

function updatePlayerDisplay(payload) {
    playerCurrentPosition = payload.new_position;
    playerRoundPnl = Number(payload.round_pnl || 0);
    playerCumulativePnl = Number(payload.cumulative_pnl || playerCumulativePnl);

    positionLabel.textContent = playerCurrentPosition;
    roundPnlLabel.textContent = formatMoney(playerRoundPnl);
    cumulativePnlLabel.textContent = formatMoney(playerCumulativePnl);

    if (currentCashLabel && payload.current_cash !== undefined) {
        currentCashLabel.textContent = formatMoney(payload.current_cash);
    }
    if (expectedCashLabel && payload.expected_cash !== undefined) {
        expectedCashLabel.textContent = formatMoney(payload.expected_cash);
    }
    if (breakEvenLabel && payload.break_even_price !== undefined) {
        breakEvenLabel.textContent = payload.break_even_price !== null ? formatMoney(payload.break_even_price) : 'Position flat — P&L locked';
    }
    if (statusIndicatorLabel && payload.status_indicator !== undefined) {
        statusIndicatorLabel.textContent = payload.status_indicator;
    }

    // Unit economics display
    if (unitEconomicsDiv && unitLabel && unitValue) {
        if (payload.cost_basis !== undefined) {
            unitLabel.textContent = 'Cost Basis:';
            unitValue.textContent = formatMoney(payload.cost_basis);
            unitEconomicsDiv.classList.remove('hidden');
        } else if (payload.tariff !== undefined) {
            unitLabel.textContent = 'Tariff:';
            unitValue.textContent = formatMoney(payload.tariff);
            unitEconomicsDiv.classList.remove('hidden');
        } else {
            unitEconomicsDiv.classList.add('hidden');
        }
    }

    if (payload.last_traded_price !== undefined) {
        lastLabel.textContent = formatMoney(payload.last_traded_price);
    }
    localStorage.setItem('current_position', String(playerCurrentPosition));
}

async function sendTrade(direction) {
    if (!sessionToken) {
        showMessage('Session expired. Please rejoin.', true);
        console.error('sendTrade: no sessionToken');
        return;
    }
    if (!roundActive || currentBid === null || currentOffer === null || currentRemainingSeconds <= 0) {
        showMessage('Cannot trade until market prices are visible and the round is active.', true);
        console.error('sendTrade blocked:', { roundActive, currentBid, currentOffer, currentRemainingSeconds });
        return;
    }
    if (direction === 'buy' && currentOffer === null) {
        showMessage('Offer price not available yet.', true);
        return;
    }
    if (direction === 'sell' && currentBid === null) {
        showMessage('Bid price not available yet.', true);
        return;
    }
    showMessage('Sending trade...', false);
    try {
        const response = await fetch('/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: sessionToken, direction }),
        });
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            console.error('Trade rejected:', response.status, body);
            throw new Error(body.detail || `Trade failed (${response.status})`);
        }
        const payload = await response.json();
        updatePlayerDisplay(payload);

        // Update trade history immediately from HTTP response
        addTradeToHistory({
            direction: direction,
            price: payload.last_traded_price,
            quantity: 1,
            pnl_contribution: payload.trade_pnl_contribution || 0,
            is_auto_closeout: payload.is_auto_closeout || false,
            resulting_position: payload.new_position
        });

        showMessage('Trade executed.', false);
    } catch (error) {
        showMessage(error.message || 'Trade failed', true);
    }
}

buyButton.addEventListener('click', () => sendTrade('buy'));
sellButton.addEventListener('click', () => sendTrade('sell'));

function updatePriceState(payload) {
    currentBid = payload.bid ?? null;
    currentOffer = payload.offer ?? null;
    currentLastPrice = payload.last_traded_price ?? null;
    currentRemainingSeconds = Number(payload.remaining_seconds || 0);

    bidLabel.textContent = currentBid !== null ? formatMoney(currentBid) : '-';
    offerLabel.textContent = currentOffer !== null ? formatMoney(currentOffer) : '-';
    lastLabel.textContent = currentLastPrice !== null ? formatMoney(currentLastPrice) : '-';
    timerLabel.textContent = `${currentRemainingSeconds}s`;
    if (payload.price_history && payload.price_history.length) {
        // Line chart: latest 30 seconds (30 points at 1 point/sec)
        lineHistory = payload.price_history.slice(-30).map((p) => ({ mid: p.mid }));
        renderChart(lineHistory);

        // Candle chart: latest 10 minutes with 5-second candles (max 120 candles)
        candleHistory = aggregateCandles(payload.price_history, 5, 120);
        renderCandleChart(candleHistory);

        // Scroll to show the latest (rightmost) part of the charts
        scrollChartsToEnd();
    }
    if (!roundActive) {
        showMessage('Round active. Market prices are live.', false);
    }
    if (currentBid === null || currentOffer === null) {
        showMessage('Waiting for market prices.', false);
    }
    updateButtonState();
}

function renderMarketSignals(marketSignals, roundNumber, phaseNumber) {
    if (!marketSignals) return;

    if (newsHeadline) {
        newsHeadline.textContent = marketSignals.headline || 'Market Update';
    }
    if (newsBody) {
        newsBody.textContent = marketSignals.body || '';
    }

    if (newsRoundLabel) {
        newsRoundLabel.textContent = phaseNumber === 2
            ? `Round ${roundNumber} · Second Phase`
            : `Round ${roundNumber} Bulletin`;
    }

    // Render forecast cards
    if (forecastCards && marketSignals.cards) {
        renderForecastCards(marketSignals.cards);
    }
}

function renderForecastCards(cards) {
    if (!forecastCards || !cards || cards.length === 0) {
        if (forecastCards) forecastCards.innerHTML = '';
        return;
    }

    let html = '';
    cards.forEach((card, index) => {
        const chartSvg = renderMiniChart(card.chart_type, card.values, card.color);
        const probLabel = card.value_label || (card.probability != null ? `${card.probability}%` : '');

        html += `
            <div class="forecast-card ${card.type}-card">
                <div class="forecast-card-header">
                    <span class="forecast-title">${card.title}</span>
                    ${probLabel ? `<span class="forecast-probability">${probLabel}</span>` : ''}
                </div>
                ${chartSvg ? `<div class="forecast-chart">${chartSvg}</div>` : ''}
                <div class="forecast-summary">${card.summary}</div>
            </div>
        `;
    });

    forecastCards.innerHTML = html;
}

function renderMiniChart(chartType, values, color) {
    if (!values || values.length === 0) return '';

    const width = 100;
    const height = 40;
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = max - min || 1;

    if (chartType === 'gauge') {
        // Simple gauge for single value
        const val = values[0] || 0;
        const pct = Math.min(100, Math.max(0, val));
        const angle = (pct / 100) * 180; // 0-180 degrees
        const rad = (angle - 90) * Math.PI / 180;
        const cx = 50;
        const cy = 35;
        const r = 25;
        const x2 = cx + r * Math.cos(rad);
        const y2 = cy + r * Math.sin(rad);

        return `<svg width="${width}" height="${height}" class="mini-chart gauge-chart">
            <path d="M 15 35 A 35 35 0 0 1 85 35" fill="none" stroke="var(--border-color, #ccc)" stroke-width="6" stroke-linecap="round"/>
            <path d="M 15 35 A 35 35 0 0 1 ${15 + (70 * pct / 100)} 35" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round"/>
            <line x1="${cx}" y1="${cy}" x2="${x2}" y2="${y2}" stroke="var(--text-primary, #333)" stroke-width="2" stroke-linecap="round"/>
            <circle cx="${cx}" cy="${cy}" r="3" fill="var(--text-primary, #333)"/>
        </svg>`;
    }

    // Line, area, or bar chart
    const points = values.map((v, i) => {
        const x = (i / (values.length - 1 || 1)) * (width - 10) + 5;
        const y = height - 5 - ((v - min) / range) * (height - 10);
        return `${x},${y}`;
    }).join(' ');

    if (chartType === 'bar') {
        const barWidth = (width - 10) / values.length - 2;
        let bars = '';
        values.forEach((v, i) => {
            const x = (i / values.length) * (width - 10) + 5;
            const barHeight = ((v - min) / range) * (height - 10);
            const y = height - 5 - barHeight;
            bars += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="2"/>`;
        });
        return `<svg width="${width}" height="${height}" class="mini-chart bar-chart">${bars}</svg>`;
    }

    if (chartType === 'area') {
        const areaPath = `M 5,${height - 5} L ${points} L ${width - 5},${height - 5} Z`;
        return `<svg width="${width}" height="${height}" class="mini-chart area-chart">
            <path d="${areaPath}" fill="${color}" opacity="0.3"/>
            <polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
    }

    // Default line chart
    return `<svg width="${width}" height="${height}" class="mini-chart line-chart">
        <polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
}

function setRoundStarted(payload) {
    roundActive = true;
    resetSummary();

    // Render market signals if available
    if (payload.market_signals) {
        renderMarketSignals(payload.market_signals, payload.round_number, payload.phase_number);
    } else if (payload.news) {
        if (newsHeadline) newsHeadline.textContent = payload.news;
        if (newsBody) newsBody.textContent = '';
    }
    currentRemainingSeconds = Number(payload.remaining_seconds || 0);
    timerLabel.textContent = `${currentRemainingSeconds}s`;

    // Use the server's carried-forward position and new round allocation.
    const roleStartPosition = getRoleStartingPosition(playerRole);
    const roundPlayerState = payload.player_state && payload.player_state[playerId];
    playerCurrentPosition = roundPlayerState ? Number(roundPlayerState.position) : roleStartPosition;
    playerRoundPnl = roundPlayerState ? Number(roundPlayerState.round_pnl) : 0.0;
    if (roundPlayerState && roundPlayerState.cumulative_pnl !== undefined) {
        playerCumulativePnl = Number(roundPlayerState.cumulative_pnl);
    }

    // Update localStorage with reset values
    localStorage.setItem('current_position', String(playerCurrentPosition));
    localStorage.setItem('round_pnl', String(playerRoundPnl));
    localStorage.setItem('cumulative_pnl', String(playerCumulativePnl));

    // Update displayed position and round PnL
    positionLabel.textContent = playerCurrentPosition;
    roundPnlLabel.textContent = formatMoney(playerRoundPnl);
    cumulativePnlLabel.textContent = formatMoney(playerCumulativePnl);

    // Reset cash, expected cash, break-even, status for new round
    if (currentCashLabel) currentCashLabel.textContent = formatMoney(roundPlayerState ? roundPlayerState.current_cash : 0);
    if (expectedCashLabel) expectedCashLabel.textContent = formatMoney(roundPlayerState ? roundPlayerState.expected_cash : 0);
    if (breakEvenLabel) breakEvenLabel.textContent = '-';
    if (statusIndicatorLabel) statusIndicatorLabel.textContent = '-';
    if (unitEconomicsDiv && unitLabel && unitValue) {
        if (roundPlayerState && roundPlayerState.cost_basis !== null && roundPlayerState.cost_basis !== undefined) {
            unitLabel.textContent = 'Cost Basis:';
            unitValue.textContent = formatMoney(roundPlayerState.cost_basis);
            unitEconomicsDiv.classList.remove('hidden');
        } else if (roundPlayerState && roundPlayerState.tariff !== null && roundPlayerState.tariff !== undefined) {
            unitLabel.textContent = 'Tariff:';
            unitValue.textContent = formatMoney(roundPlayerState.tariff);
            unitEconomicsDiv.classList.remove('hidden');
        } else {
            unitEconomicsDiv.classList.add('hidden');
        }
    }

    // Clear trade history for new round
    currentRoundTrades = [];
    renderTradeHistory();

    // NOTE: Chart history (lineHistory, candleHistory) is NOT reset
    // Charts continue across rounds for game-level price continuity

    if (payload.start_price !== undefined) {
        currentLastPrice = null;
        lastLabel.textContent = '-';
    }
    updateButtonState();
}

function signedMoney(value) {
    return value < 0 ? `− ${formatMoney(-value)}` : `+ ${formatMoney(value)}`;
}

function buildRoundPnlExplanation(p) {
    const isGenerator = p.cost_basis !== null && p.cost_basis !== undefined;
    const isRetailer = p.tariff !== null && p.tariff !== undefined;
    let allocationItems = '';
    if (isGenerator || isRetailer) {
        // Each MWh is measured against the cost basis / tariff of the round its lot came from.
        const groups = new Map();
        (p.trade_history || []).forEach((t) => {
            const key = `${t.direction}|${t.reference_price}`;
            const group = groups.get(key) || { direction: t.direction, reference: t.reference_price, quantity: 0 };
            group.quantity += t.quantity;
            groups.set(key, group);
        });
        const unitName = isGenerator ? 'önköltség' : 'tarifa';
        groups.forEach((g) => {
            const amount = (g.direction === 'buy' ? 1 : -1) * g.quantity * g.reference;
            const verb = g.direction === 'buy' ? 'vásárolt' : 'eladott';
            allocationItems += `<li><strong>Kiosztás pénzárama</strong> (${verb} mennyiség): ${g.quantity} MWh × ${formatMoney(g.reference)} EUR (${unitName}) = ${formatMoney(amount)} EUR</li>`;
        });
    }
    const equation = allocationItems
        ? `${formatMoney(p.trading_cash)} ${signedMoney(p.allocation_cash)}`
        : formatMoney(p.trading_cash);
    return '<h4>Hogyan számoltuk a kör P&L-t?</h4>' +
        '<p>Kör P&L = kereskedési pénzáram' + (allocationItems ? ' + kiosztás pénzárama' : '') + '.</p>' +
        '<ul>' +
        `<li><strong>Kereskedési pénzáram</strong> (eladások összege − vásárlások összege): ${formatMoney(p.trading_cash)} EUR</li>` +
        allocationItems +
        '</ul>' +
        `<p><strong>Eredmény:</strong> ${equation} = <strong>${formatMoney(p.round_pnl)} EUR</strong></p>` +
        '<p><em>Megjegyzés: a még el nem adott (nyitott) pozíció a következő körre átkerül, és a játék végén az elszámolóáron számoljuk el. Az átvitt MWh azon kör önköltségével / tarifájával számol, amelyikben kapta.</em></p>';
}

function buildSettlementHtml(settlement) {
    const me = settlement.players.find((p) => p.player_id === playerId);
    const clearing = settlement.clearing_price;
    let html = `<h3>Játék végi elszámolás</h3>` +
        `<p>Az utolsó kör záróára (<strong>${formatMoney(clearing)} EUR</strong>) az elszámolóár: a még nyitott pozíciót ezen az áron számoltuk el az önköltséghez / tarifához képest. ` +
        'Összehasonlítottuk, mi történt volna, ha nem kereskedsz, hanem a kapott kiosztás teljes mennyiségét tartod az elszámolásig.</p>';

    if (me) {
        const priceTerm = me.reference_price > 0
            ? `(${formatMoney(clearing)} − ${formatMoney(me.reference_price)})`
            : formatMoney(clearing);

        html += '<h4>Az eredményed összetétele</h4>' +
            '<table class="summary-table"><thead><tr><th>Kör</th><th>Kör P&L</th></tr></thead><tbody>' +
            me.rounds.map((r) => `<tr><td>${r.round_number}</td><td>${formatMoney(r.pnl)} EUR</td></tr>`).join('') +
            '</tbody></table>' +
            `<p><strong>Kereskedésekből realizált P&L (összesen):</strong> ${formatMoney(me.realized_pnl)} EUR</p>` +
            `<p><strong>Nyitott pozíció elszámolása:</strong> ${me.final_position} MWh × ${priceTerm} = ${formatMoney(me.settlement_pnl)} EUR</p>` +
            `<p><strong>Összesen:</strong> ${formatMoney(me.realized_pnl)} ${signedMoney(me.settlement_pnl)} = <strong>${formatMoney(me.actual_pnl)} EUR</strong></p>` +
            '<h4>Ha nem kereskedtél volna</h4>' +
            '<table class="summary-table"><thead><tr><th>Kör</th><th>Kiosztás (MWh)</th><th>Önköltség / tarifa</th><th>Érték az elszámolóáron</th></tr></thead><tbody>' +
            me.allocations.map((a) =>
                `<tr><td>${a.round_number}</td><td>${a.allocation}</td><td>${formatMoney(a.reference_price)}</td>` +
                `<td>${a.allocation} × (${formatMoney(clearing)} − ${formatMoney(a.reference_price)}) = ${formatMoney(a.value)} EUR</td></tr>`
            ).join('') +
            '</tbody></table>' +
            `<p><strong>Semmittevés eredménye:</strong> ${formatMoney(me.do_nothing_pnl)} EUR | ` +
            `<strong>A te eredményed:</strong> ${formatMoney(me.actual_pnl)} EUR | ` +
            `<strong>Különbség:</strong> ${formatMoney(me.difference)} EUR</p>`;

        if (me.trades.length > 0) {
            html += '<h4>Ügyleteid</h4>' +
                '<table class="summary-trade-table"><thead><tr><th>Kör</th><th>Irány</th><th>Ár</th><th>Ügylet P&L (EUR)</th></tr></thead><tbody>' +
                me.trades.map((t) =>
                    `<tr><td>${t.round_number}</td><td>${t.direction.toUpperCase()}</td><td>${formatMoney(t.price)}</td><td>${formatMoney(t.pnl_contribution)}</td></tr>`
                ).join('') +
                '</tbody></table>' +
                '<p><em>Az ügylet P&L az önköltséghez / tarifához viszonyított eltérés (eladott MWh: eladási ár − önköltség). A körönkénti P&L ezek összege.</em></p>';
        }
    }

    html += '<h4>Mindenki elszámolása</h4>' +
        '<table class="summary-table"><thead><tr><th>Név</th><th>Szerep</th><th>Semmittevés</th><th>Tényleges</th><th>Különbség</th></tr></thead><tbody>' +
        settlement.players.map((p) =>
            `<tr><td>${p.name}</td><td>${p.role}</td><td>${formatMoney(p.do_nothing_pnl)} EUR</td><td>${formatMoney(p.actual_pnl)} EUR</td>` +
            `<td>${formatMoney(p.difference)} EUR</td></tr>`
        ).join('') +
        '</tbody></table>';
    return html;
}

function setRoundEnded(payload) {
    roundActive = false;
    currentBid = null;
    currentOffer = null;
    currentRemainingSeconds = 0;
    bidLabel.textContent = '-';
    offerLabel.textContent = '-';
    timerLabel.textContent = '0s';
    updateButtonState();

    const isGameOver = payload.game_over;
    const closePrice = payload.close_price;
    showMessage(isGameOver ? 'Game over. All rounds complete.' : `Round ${payload.round_number} ended. Waiting for next round...`, false);

    resultPanel.classList.remove('hidden');

    // Update trade history from server data if available
    const myPlayerData = payload.player_summary.find(p => p.player_id === playerId);
    if (myPlayerData && myPlayerData.trade_history) {
        currentRoundTrades = myPlayerData.trade_history;
        renderTradeHistory();
    }

    if (isGameOver) {
        summaryText.innerHTML = '<strong>Game Complete!</strong> All rounds finished. Final standings below.';
    } else {
        summaryText.innerHTML = `<strong>Round ${payload.round_number} Complete</strong><br>Close price: ${formatMoney(closePrice)} EUR<br>Waiting for game master to start the next round...`;
    }

    const playerSummary = document.getElementById('player-summary');

    // Build detailed player summary with trade history
    let mySummaryHtml = '<h3>Your Round Summary</h3>';

    if (myPlayerData) {
        mySummaryHtml += `<p><strong>Role:</strong> ${myPlayerData.role} | <strong>Final Position:</strong> ${myPlayerData.final_position} MWh</p>`;
        mySummaryHtml += `<p><strong>Round P&L:</strong> ${formatMoney(myPlayerData.round_pnl)} EUR | <strong>Cumulative P&L:</strong> ${formatMoney(myPlayerData.cumulative_pnl)} EUR | <strong>Rank:</strong> ${myPlayerData.rank}</p>`;

        // The header must show the same final value as the summary.
        playerRoundPnl = Number(myPlayerData.round_pnl);
        roundPnlLabel.textContent = formatMoney(playerRoundPnl);
        localStorage.setItem('round_pnl', String(playerRoundPnl));

        mySummaryHtml += buildRoundPnlExplanation(myPlayerData);

        // Show trade history in summary
        if (myPlayerData.trade_history && myPlayerData.trade_history.length > 0) {
            mySummaryHtml += '<h4>Your Trades This Round</h4>' +
                '<table class="summary-trade-table"><thead><tr><th>#</th><th>Side</th><th>Price</th><th>Type</th></tr></thead><tbody>';

            myPlayerData.trade_history.forEach((trade, index) => {
                const typeLabel = trade.is_auto_closeout ? 'Auto close-out' : 'Manual';
                mySummaryHtml += `<tr class="${trade.is_auto_closeout ? 'auto-trade' : ''}">` +
                    `<td>${index + 1}</td>` +
                    `<td>${trade.direction.toUpperCase()}</td>` +
                    `<td>${formatMoney(trade.price)}</td>` +
                    `<td>${typeLabel}</td>` +
                    `</tr>`;
            });

            mySummaryHtml += '</tbody></table>';
        }
    }

    // All players summary table
    mySummaryHtml += '<h4>All Players Summary</h4>' +
        '<table class="summary-table"><thead><tr><th>Rank</th><th>Name</th><th>Role</th><th>Round P&L</th><th>Cumulative P&L</th></tr></thead><tbody>' +
        payload.player_summary.map((player) =>
            `<tr><td>${player.rank}</td><td>${player.name}</td><td>${player.role}</td><td>${formatMoney(player.round_pnl)} EUR</td><td>${formatMoney(player.cumulative_pnl)} EUR</td></tr>`
        ).join('') +
        '</tbody></table>';

    playerSummary.innerHTML = mySummaryHtml;
    if (payload.settlement) {
        playerSummary.innerHTML += buildSettlementHtml(payload.settlement);
    }

    const leaderboardTitle = isGameOver ? 'Final Leaderboard' : 'Leaderboard';
    leaderboardContainer.innerHTML = `<h3>${leaderboardTitle}</h3>` +
        '<ol>' +
        payload.leaderboard.map((player) => `<li>${player.name}: ${formatMoney(player.cumulative_pnl)} EUR</li>`).join('') +
        '</ol>';
}

function handleGameRestarted(payload) {
    // Clear all player state from localStorage
    localStorage.removeItem('session_token');
    localStorage.removeItem('player_id');
    localStorage.removeItem('player_name');
    localStorage.removeItem('player_role');
    localStorage.removeItem('start_position');
    localStorage.removeItem('current_position');
    localStorage.removeItem('round_pnl');
    localStorage.removeItem('cumulative_pnl');

    // Clear chart history
    lineHistory = [];
    candleHistory = [];
    pricePointBuffer = [];

    // Clear chart canvases
    if (chartContext) {
        chartContext.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
    }
    if (candleContext) {
        candleContext.clearRect(0, 0, candleCanvas.width, candleCanvas.height);
    }

    // Show restart message
    showMessage('Game restarted by admin. Please join again.', true);

    // Redirect to join page after short delay
    setTimeout(() => {
        window.location.href = '/';
    }, 2000);
}

function handleMessage(event) {
    const message = JSON.parse(event.data);
    const { type, payload } = message;
    if (type === 'round_started') {
        setRoundStarted(payload);
    } else if (type === 'price_update') {
        updatePriceState(payload);
    } else if (type === 'trade_executed') {
        if (payload.player_id === playerId) {
            updatePlayerDisplay(payload);

            // Add trade to history immediately
            addTradeToHistory({
                direction: payload.direction,
                price: payload.price,
                quantity: 1,
                pnl_contribution: payload.trade_pnl_contribution || 0,
                is_auto_closeout: payload.is_auto_closeout || false,
                resulting_position: payload.new_position
            });
        }
    } else if (type === 'round_ended') {
        setRoundEnded(payload);
    } else if (type === 'market_signal_update') {
        renderMarketSignals(payload.market_signals, payload.round_number, payload.phase_number);
    } else if (type === 'game_restarted') {
        handleGameRestarted(payload);
    } else if (type === 'error') {
        showMessage(payload.message || 'Error received', true);
    }
}

function connectWebSocket() {
    const ws = new WebSocket((window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws');
    ws.addEventListener('message', handleMessage);
    ws.addEventListener('close', () => {
        showMessage('Disconnected from server; reconnecting...', true);
        setTimeout(connectWebSocket, 2000);
    });
}

connectWebSocket();
