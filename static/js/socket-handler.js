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
        // Connection events
        this.socket.on('connect', this.registerHandler('connect', () => {
            this.connected = true;
            console.log('Connected to server');
            this.emit('request_room_list');
        }));

        this.socket.on('disconnect', this.registerHandler('disconnect', () => {
            this.connected = false;
            console.log('Disconnected from server');
        }));

        // Room management events - delegate to GameManager
        this.socket.on('room_created', this.registerHandler('room_created', (data) => {
            gameManager.handleRoomCreated(data);
        }));

        this.socket.on('joined_room', this.registerHandler('joined_room', (data) => {
            gameManager.handleJoinedRoom(data);
        }));

        this.socket.on('join_room_error', this.registerHandler('join_room_error', (data) => {
            gameManager.handleJoinRoomError(data);
        }));

        this.socket.on('room_list_updated', this.registerHandler('room_list_updated', (data) => {
            gameManager.updateRoomList(data.rooms);
        }));

        // Player management events - delegate to GameManager
        this.socket.on('players_updated', this.registerHandler('players_updated', (data) => {
            gameManager.handlePlayersUpdated(data);
        }));

        // Game flow events - delegate to GameManager
        this.socket.on('countdown_started', this.registerHandler('countdown_started', (data) => {
            gameManager.handleCountdownStarted(data);
        }));

        this.socket.on('countdown_cancelled', this.registerHandler('countdown_cancelled', (data) => {
            gameManager.handleCountdownCancelled(data);
        }));

        this.socket.on('game_started', this.registerHandler('game_started', (data) => {
            gameManager.handleGameStarted(data);
        }));

        this.socket.on('phase_changed', this.registerHandler('phase_changed', (data) => {
            gameManager.handlePhaseChanged(data);
        }));

        // Drawing and copying events - delegate to GameManager
        this.socket.on('copying_assignment', this.registerHandler('copying_assignment', (data) => {
            gameManager.handleCopyingAssignment(data);
        }));

        this.socket.on('copying_viewing_phase', this.registerHandler('copying_viewing_phase', (data) => {
            gameManager.handleCopyingViewingPhase(data);
        }));

        this.socket.on('copying_phase_started', this.registerHandler('copying_phase_started', (data) => {
            gameManager.handleCopyingPhaseStarted(data);
        }));

        // Submission acknowledgments - delegate to UIManager
        this.socket.on('drawing_submitted', this.registerHandler('drawing_submitted', (data) => {
            uiManager.showMessage('Drawing submitted successfully!', 'success');
        }));

        this.socket.on('copy_submitted', this.registerHandler('copy_submitted', (data) => {
            uiManager.showMessage(`Copy ${data.completed} of ${data.total} submitted!`, 'success');
        }));

        // Voting events - delegate to GameManager
        this.socket.on('voting_round', this.registerHandler('voting_round', (data) => {
            gameManager.handleVotingRound(data);
        }));

        this.socket.on('voting_round_excluded', this.registerHandler('voting_round_excluded', (data) => {
            gameManager.handleVotingRoundExcluded(data);
        }));

        // Game results - delegate to GameManager
        this.socket.on('game_results', this.registerHandler('game_results', (data) => {
            gameManager.handleGameResults(data);
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
            uiManager.showMessage(`Phase advancing early: ${data.reason}`, 'info');
        }));

        this.socket.on('game_ended_early', this.registerHandler('game_ended_early', (data) => {
            gameManager.handleGameEndedEarly(data);
        }));

        this.socket.on('room_left', this.registerHandler('room_left', (data) => {
            gameManager.handleRoomLeft(data);
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