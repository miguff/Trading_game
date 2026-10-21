import http from 'k6/http';
import ws from 'k6/ws';
import { check } from 'k6';
import { Counter, Rate } from 'k6/metrics';

const baseUrl = (__ENV.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const players = Number(__ENV.PLAYERS || 50);
const durationSeconds = Number(__ENV.DURATION_SECONDS || 900);
const tradeMinMs = Number(__ENV.TRADE_MIN_MS || 500);
const tradeMaxMs = Number(__ENV.TRADE_MAX_MS || 1500);
const unexpectedErrors = new Rate('unexpected_errors');
const socketDisconnects = new Counter('unexpected_socket_disconnects');
const successfulTrades = new Counter('successful_trades');
const receivedPrices = new Rate('players_received_prices');
const tradedPlayers = new Rate('players_completed_trades');

if (!/^https?:\/\//.test(baseUrl)) {
    throw new Error('BASE_URL must start with http:// or https://');
}
if (!Number.isInteger(players) || players < 1 || players > 100) {
    throw new Error('PLAYERS must be an integer between 1 and 100');
}
if (!Number.isInteger(durationSeconds) || durationSeconds < 10) {
    throw new Error('DURATION_SECONDS must be an integer of at least 10');
}
if (!Number.isInteger(tradeMinMs) || !Number.isInteger(tradeMaxMs)
    || tradeMinMs < 100 || tradeMaxMs < tradeMinMs) {
    throw new Error('Trade intervals must be integer milliseconds: 100 <= TRADE_MIN_MS <= TRADE_MAX_MS');
}

export const options = {
    scenarios: {
        players: {
            executor: 'per-vu-iterations',
            vus: players,
            iterations: 1,
            maxDuration: `${durationSeconds + 60}s`,
        },
    },
    thresholds: {
        checks: ['rate==1'],
        unexpected_errors: ['rate==0'],
        unexpected_socket_disconnects: ['count==0'],
        successful_trades: ['count>0'],
        players_received_prices: ['rate==1'],
        players_completed_trades: ['rate==1'],
        'http_req_duration{endpoint:trade}': ['p(95)<500'],
    },
};

const expectedRejections = new Set([
    'No active round. Trading is not allowed.',
    'Trading is paused',
    'No active round',
    'Position limit exceeded',
]);

function post(path, body, endpoint) {
    return http.post(`${baseUrl}${path}`, JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        tags: { endpoint, name: path },
        timeout: '10s',
    });
}

function parseJson(text) {
    try {
        return JSON.parse(text);
    } catch (_) {
        return null;
    }
}

export default function () {
    let sawPrice = false;
    let completedTrade = false;
    const join = post('/join', {
        name: `LoadTest-${__ENV.RUN_ID || 'run'}-${__VU}`,
    }, 'join');
    const player = parseJson(join.body);
    const joined = check(join, {
        'player joined with an identity': (response) => response.status === 200
            && !!player && !!player.session_token && !!player.player_id,
    });
    unexpectedErrors.add(!joined);
    if (!joined) {
        receivedPrices.add(false);
        tradedPlayers.add(false);
        return;
    }

    const ready = post('/briefing/ready', {
        session_token: player.session_token,
        ready: true,
    }, 'ready');
    unexpectedErrors.add(!check(ready, {
        'player marked ready': (response) => response.status === 200,
    }));

    let active = false;
    let paused = false;
    let finished = false;
    let direction = player.role === 'Generator' ? 'sell' : 'buy';
    const socketResponse = ws.connect(`${baseUrl.replace(/^http/, 'ws')}/ws`, {}, (socket) => {
        socket.on('message', (text) => {
            const message = parseJson(text);
            if (!message) {
                unexpectedErrors.add(true);
                return;
            }
            if (message.type === 'round_started') {
                active = true;
                paused = false;
            } else if (message.type === 'round_paused') {
                paused = true;
            } else if (message.type === 'round_resumed') {
                paused = false;
            } else if (message.type === 'round_ended' || message.type === 'game_reset') {
                active = false;
            } else if (message.type === 'price_update') {
                sawPrice = true;
            }
        });
        socket.on('error', () => unexpectedErrors.add(true));
        socket.on('close', () => {
            if (!finished) {
                socketDisconnects.add(1);
            }
        });

        function scheduleTrade() {
            socket.setTimeout(() => {
                if (active && !paused) {
                    const response = post('/trade', {
                        session_token: player.session_token,
                        direction,
                    }, 'trade');
                    const body = parseJson(response.body);
                    const succeeded = response.status === 200 && body && body.status === 'ok';
                    const expected = response.status === 400 && body
                        && expectedRejections.has(body.detail);
                    unexpectedErrors.add(!succeeded && !expected);
                    if (succeeded) {
                        successfulTrades.add(1);
                        completedTrade = true;
                    }
                    if (succeeded || (body && body.detail === 'Position limit exceeded')) {
                        direction = direction === 'buy' ? 'sell' : 'buy';
                    }
                }
                scheduleTrade();
            }, tradeMinMs + Math.random() * (tradeMaxMs - tradeMinMs));
        }

        scheduleTrade();
        socket.setTimeout(() => {
            finished = true;
            socket.close();
        }, durationSeconds * 1000);
    });

    unexpectedErrors.add(!check(socketResponse, {
        'WebSocket connected': (response) => response && response.status === 101,
    }));
    socketDisconnects.add(0);
    successfulTrades.add(0);
    receivedPrices.add(sawPrice);
    tradedPlayers.add(completedTrade);
}