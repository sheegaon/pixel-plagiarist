// Socket.IO event handling for Pixel Plagiarist
class SocketHandler {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.eventHandlers = new Map(); // Track registered handlers
    }

    init() {
        this.socket = io();
        this.setupSocketEvents();
    }

    emit(event, data) {
        if (!this.socket || !this.connected) {
            console.warn(`Cannot emit ${event}: socket not connected`);
            uiManager.showMessage('Connection error. Please refresh the page.', 'error');
            return;
        }
        
        try {
            this.socket.emit(event, data);
            debug(`Emitted ${event}:`, data);
        } catch (error) {
            console.error(`Error emitting ${event}:`, error);
            uiManager.showMessage('Communication error occurred', 'error');
        }
    }

    // Centralized event handler registration
    registerHandler(event, handler, context = 'global') {
        const key = `${event}_${context}`;
        if (this.eventHandlers.has(key)) {
            console.warn(`Duplicate handler registration for ${event} in ${context}`);
        }
        this.eventHandlers.set(key, handler);
        return handler;
    }

    setupSocketEvents() {
        // Debug helpers for detailed console logging
        const debugSnapshot = () => {
            try {
                const hasGameManager = typeof window !== 'undefined' && typeof window.gameManager !== 'undefined';
                const hasUI = typeof uiManager !== 'undefined';
                const hasRoom = typeof roomManager !== 'undefined';
                const hasPlayer = typeof playerManager !== 'undefined';
                return {
                    phase: hasGameManager ? window.gameManager.gamePhase : 'unknown',
                    view: hasUI ? uiManager.getCurrentView() : 'unknown',
                    room: hasRoom ? roomManager.getCurrentRoom() : null,
                    playerId: hasPlayer ? playerManager.getPlayerId() : null,
                    socketId: this.socket ? this.socket.id : null,
                    timers: hasUI ? Array.from(uiManager.timers.keys()) : []
                };
            } catch (e) {
                return { error: e.message };
            }
        };
        const logEvent = (name, data) => {
            try {
                console.log(`📡 Socket event received: ${name}`, data);
                console.log('🧭 UI snapshot:', debugSnapshot());
            } catch (e) {
                console.warn('Logging error:', e);
            }
        };

        // Connection events
        this.socket.on('connect', this.registerHandler('connect', () => {
            this.connected = true;
            console.log('Connected to server');
            console.log('🧭 UI snapshot (on connect):', debugSnapshot());

            // Always refresh room list
            this.emit('request_room_list');

            // Auto-rejoin if we have a known room locally (helps after reconnect on macOS)
            try {
                const currentRoom =
                    (typeof roomManager !== 'undefined' && typeof roomManager.getCurrentRoom === 'function')
                        ? roomManager.getCurrentRoom()
                        : (typeof window !== 'undefined' && window.gameManager ? window.gameManager.currentRoom : null);

                if (currentRoom) {
                    const username =
                        (typeof window !== 'undefined' && window.gameManager && window.gameManager.username)
                            ? window.gameManager.username
                            : (typeof window !== 'undefined' && window.gameUserData ? window.gameUserData.username : 'Anonymous');

                    console.log('🔁 Attempting auto-rejoin to room:', currentRoom);
                    this.emit('join_room', { room_id: currentRoom, username });
                }
            } catch (e) {
                console.warn('Auto-rejoin attempt failed:', e);
            }
        }));

        // Reconnect diagnostics
        if (this.socket && this.socket.io) {
            this.socket.io.on('reconnect', (attempt) => {
                console.log(`🔌 Reconnected after ${attempt} attempt(s)`, debugSnapshot());
            });
            this.socket.io.on('reconnect_attempt', (attempt) => {
                console.log(`🔎 Reconnect attempt ${attempt}`, debugSnapshot());
            });
            this.socket.io.on('reconnect_error', (err) => {
                console.warn('⚠️ Reconnect error:', err && err.message ? err.message : err);
            });
        }

        this.socket.on('disconnect', this.registerHandler('disconnect', () => {
            this.connected = false;
            console.log('Disconnected from server');
        }));

        // Room management events - delegate to GameManager
        this.socket.on('room_created', this.registerHandler('room_created', (data) => {
            if (window.gameManager) window.gameManager.handleRoomCreated(data);
        }));

        this.socket.on('joined_room', this.registerHandler('joined_room', (data) => {
            if (window.gameManager) window.gameManager.handleJoinedRoom(data);
        }));

        this.socket.on('join_room_error', this.registerHandler('join_room_error', (data) => {
            if (window.gameManager) window.gameManager.handleJoinRoomError(data);
        }));

        this.socket.on('room_list_updated', this.registerHandler('room_list_updated', (data) => {
            if (window.gameManager) window.gameManager.updateRoomList(data.rooms);
        }));

        // Player management events - delegate to GameManager
        this.socket.on('players_updated', this.registerHandler('players_updated', (data) => {
            if (window.gameManager) window.gameManager.handlePlayersUpdated(data);
        }));

        // Game flow events - delegate to GameManager
        this.socket.on('joining_countdown_started', this.registerHandler('joining_countdown_started', (data) => {
            if (typeof logEvent === 'function') logEvent('joining_countdown_started', data);
            if (typeof logEvent === 'function') logEvent('joining_countdown_started', data);
            if (window.gameManager) window.gameManager.handleCountdownStarted(data);
        }));

        this.socket.on('countdown_cancelled', this.registerHandler('countdown_cancelled', (data) => {
            if (window.gameManager) window.gameManager.handleCountdownCancelled(data);
        }));

        this.socket.on('countdown_finished', this.registerHandler('countdown_finished', (data) => {
            // Handle countdown completion from server - this ensures proper synchronization
            console.log('Server countdown completed, game should start shortly...');
            const timer = document.getElementById('joiningTimer');
            if (timer) {
                timer.textContent = data.message || "Starting...";
            }
            // Clear any client-side countdown timers to prevent conflicts
            if (window.uiManager && uiManager.timers.has('joiningTimer')) {
                clearInterval(uiManager.timers.get('joiningTimer'));
                uiManager.timers.delete('joiningTimer');
            }
        }));

        this.socket.on('game_start_error', this.registerHandler('game_start_error', (data) => {
            // Handle game start errors - helps debug timing issues
            console.error('Game failed to start:', data.message);
            uiManager.showError(data.message);
            // Reset the timer display
            const timer = document.getElementById('joiningTimer');
            if (timer) {
                timer.textContent = "Error starting game";
            }
        }));

        this.socket.on('game_started', this.registerHandler('game_started', (data) => {
            if (typeof logEvent === 'function') logEvent('game_started', data);
            if (window.gameManager) {
                window.gameManager.handleGameStarted(data);
                // Log post-handler state
                console.log('✅ game_started handled. Post-state snapshot:', {
                    view: window.uiManager ? uiManager.getCurrentView() : 'unknown',
                    phase: window.gameManager ? window.gameManager.gamePhase : 'unknown'
                });
            } else {
                console.warn('gameManager not initialized when game_started received');
            }
        }));

        this.socket.on('phase_changed', this.registerHandler('phase_changed', (data) => {
            if (typeof logEvent === 'function') logEvent('phase_changed', data);
            if (window.gameManager) {
                window.gameManager.handlePhaseChanged(data);
                console.log('✅ phase_changed handled. New phase/view:', {
                    phase: window.gameManager ? window.gameManager.gamePhase : 'unknown',
                    view: window.uiManager ? uiManager.getCurrentView() : 'unknown'
                });
            } else {
                console.warn('gameManager not initialized when phase_changed received');
            }
        }));

        // Drawing and copying events - delegate to GameManager
        this.socket.on('copying_phase', this.registerHandler('copying_phase', (data) => {
            if (window.gameManager) window.gameManager.handleCopyingAssignment(data);
        }));

        this.socket.on('copying_phase_started', this.registerHandler('copying_phase_started', (data) => {
            if (window.gameManager) window.gameManager.handleCopyingPhaseStarted(data);
        }));

        // Submission acknowledgments - delegate to UIManager
        this.socket.on('original_submitted', this.registerHandler('original_submitted', (data) => {
            uiManager.showMessage('Drawing submitted successfully!', 'success');
        }));

        this.socket.on('copy_submitted', this.registerHandler('copy_submitted', (data) => {
            console.log(`🎨 Game Progress: Copy ${data.completed}/${data.total} submitted by player`);
            
            // Log when all copies are done for this player
            if (data.completed === data.total) {
                console.log(`✅ Player completed all ${data.total} copies`);
            }
        }));

        // Voting events - delegate to GameManager
        this.socket.on('voting_round', this.registerHandler('voting_round', (data) => {
            if (window.gameManager) window.gameManager.handleVotingRound(data);
        }));

        this.socket.on('voting_round_excluded', this.registerHandler('voting_round_excluded', (data) => {
            if (window.gameManager) window.gameManager.handleVotingRoundExcluded(data);
        }));

        this.socket.on('vote_cast', this.registerHandler('vote_cast', (data) => {
            // Handle vote cast confirmation - this helps track voting progress
            console.log(`🗳️ Game Progress: Vote cast by player for set ${data.set_index + 1}`);
        }));

        // Game results - delegate to GameManager
        this.socket.on('game_results', this.registerHandler('game_results', (data) => {
            if (window.gameManager) window.gameManager.handleGameResults(data);
        }));

        // Review functionality - delegate to UIManager
        this.socket.on('review_drawing', this.registerHandler('review_drawing', (data) => {
            uiManager.showReviewOverlay(data.drawing, data.duration);
        }));

        // Flagging response - delegate to UIManager
        this.socket.on('image_flagged', this.registerHandler('image_flagged', (data) => {
            if (data.success) {
                uiManager.showMessage(data.message, 'success');
            } else {
                uiManager.showMessage(data.message, 'error');
            }
        }));

        // System events
        this.socket.on('early_phase_advance', this.registerHandler('early_phase_advance', (data) => {
            console.log(`⚡ Game Progress: Phase advancing early - ${data.reason}`);
            uiManager.showMessage(`Phase advancing early: ${data.reason}`, 'info');
        }));

        this.socket.on('game_ended_early', this.registerHandler('game_ended_early', (data) => {
            if (window.gameManager) window.gameManager.handleGameEndedEarly(data);
        }));

        this.socket.on('room_left', this.registerHandler('room_left', (data) => {
            if (window.gameManager) window.gameManager.handleRoomLeft(data);
        }));

        // Error handling
        this.socket.on('error', this.registerHandler('error', (data) => {
            uiManager.showMessage(data.message || 'An error occurred', 'error');
        }));
    }

    // Utility methods
    requestRoomList() {
        this.emit('request_room_list');
    }

    flagImage(drawingId, phase) {
        debug('Flagging image', { drawingId, phase });
        this.emit('flag_image', {
            drawing_id: drawingId,
            phase: phase
        });
    }

    // Cleanup method for proper resource management
    cleanup() {
        if (this.socket) {
            this.socket.disconnect();
        }
        this.eventHandlers.clear();
        this.connected = false;
    }
}

// Create global instance
const socketHandler = new SocketHandler();