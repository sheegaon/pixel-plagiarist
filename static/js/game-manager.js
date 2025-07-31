// Main game coordinator for Pixel Plagiarist
class GameManager {
    constructor() {
        this.username = window.gameUserData ? window.gameUserData.username : 'Anonymous';
        
        // Initialize specialized managers
        this.initializeManagers();
    }

    initializeManagers() {
        // Create global instances of all managers
        window.roomManager = new RoomManager();
        window.playerManager = new PlayerManager();
        window.gameStateManager = new GameStateManager();
        window.bettingManager = new BettingManager();
        window.drawingManager = new DrawingManager();
        window.copyingManager = new CopyingManager();
        window.votingManager = new VotingManager();
        window.resultsManager = new ResultsManager();
    }

    // Delegation methods for room management
    createRoomWithStake(minStake) {
        roomManager.createRoomWithStake(minStake);
    }

    joinRoom(roomId = null) {
        roomManager.joinRoom(roomId);
    }

    joinRoomFromList(roomId) {
        roomManager.joinRoomFromList(roomId);
    }

    joinRoomByCode() {
        roomManager.joinRoomByCode();
    }

    refreshRoomList() {
        roomManager.refreshRoomList();
    }

    updateRoomList(rooms) {
        roomManager.updateRoomList(rooms);
    }

    leaveRoom() {
        roomManager.leaveRoom();
    }

    // Delegation methods for betting
    placeBet() {
        bettingManager.placeBet();
    }

    setupStakeSlider() {
        // This is called during initialization but actual setup is handled by betting manager
        console.log('Stake slider will be set up when betting phase starts');
    }

    // Delegation methods for drawing
    submitDrawing() {
        drawingManager.submitDrawing();
    }

    // Delegation methods for copying
    submitCurrentCopy() {
        copyingManager.submitCurrentCopy();
    }

    requestReview(targetId) {
        copyingManager.requestReview(targetId);
    }

    // Delegation methods for voting
    selectVote(drawingId, element) {
        votingManager.selectDrawing(drawingId, element);
    }

    submitVote() {
        votingManager.submitVote();
    }

    // Socket event handlers - coordinate between managers
    handleRoomCreated(data) {
        if (data.success) {
            roomManager.setCurrentRoom(data.room_id);
            playerManager.setPlayerId(socketHandler.socket.id);
            gameStateManager.setPhase(GameConfig.PHASES.WAITING);
            uiManager.showSuccess(data.message);
            uiManager.showView('waiting');
            roomManager.updateRoomDisplay(data.room_id);
        } else {
            uiManager.showError(data.message);
        }
    }

    handleJoinedRoom(data) {
        if (data.success) {
            roomManager.setCurrentRoom(data.room_id);
            playerManager.setPlayerId(data.player_id);
            playerManager.updatePlayerList(data.players);
            gameStateManager.setPhase(GameConfig.PHASES.WAITING);
            uiManager.showSuccess(data.message);
            uiManager.showView('waiting');
            roomManager.updateRoomDisplay(data.room_id);
        }
    }

    handleJoinRoomError(data) {
        uiManager.showError(data.message);
    }

    handlePlayersUpdated(data) {
        playerManager.updatePlayerList(data.players);
    }

    handleCountdownStarted(data) {
        const countdownDisplay = document.getElementById('countdownDisplay');
        if (countdownDisplay) {
            countdownDisplay.style.display = 'block';
        }
        uiManager.startCountdown(data.seconds);
    }

    handleCountdownCancelled(data) {
        const countdownDisplay = document.getElementById('countdownDisplay');
        if (countdownDisplay) {
            countdownDisplay.style.display = 'none';
        }
        uiManager.showError(data.message);
    }

    handleGameStarted(data) {
        gameStateManager.setPhase(GameConfig.PHASES.BETTING);
        gameStateManager.setGameData(data);
        
        // Set prompt in UI
        const promptText = document.getElementById('promptText');
        if (promptText) {
            promptText.textContent = data.prompt;
        }
        
        bettingManager.initializeBetting(data);
        
        // Start betting timer with auto-submit callback
        uiManager.startTimer('bettingTimer', data.timer, () => {
            if (gameStateManager.getPhase() === GameConfig.PHASES.BETTING) {
                bettingManager.autoPlaceBet();
                uiManager.showError('Time up! Bet placed automatically.');
            }
        });
    }

    handlePhaseChanged(data) {
        gameStateManager.setPhase(data.phase);
        
        if (data.phase === GameConfig.PHASES.DRAWING) {
            drawingManager.initializeDrawing(data);
            
            // Start drawing timer with auto-submit callback
            uiManager.startTimer('drawingTimer', data.timer, () => {
                if (gameStateManager.getPhase() === GameConfig.PHASES.DRAWING) {
                    drawingManager.autoSubmitDrawing();
                    uiManager.showError('Time up! Drawing submitted automatically.');
                }
            });
        }
    }

    handleCopyingAssignment(data) {
        gameStateManager.setPhase(GameConfig.PHASES.COPYING);
        copyingManager.initializeCopyingViewingPhase(data);
        
        // Start copying timer with auto-submit callback
        uiManager.startTimer('copyingTimer', data.timer, () => {
            if (gameStateManager.getPhase() === GameConfig.PHASES.COPYING) {
                copyingManager.autoSubmitRemainingCopies();
                uiManager.showError('Time up! Remaining copies submitted automatically.');
            }
        });
    }

    handleCopyingViewingPhase(data) {
        copyingManager.initializeCopyingViewingPhase(data);
    }

    handleCopyingPhaseStarted(data) {
        gameStateManager.setPhase(GameConfig.PHASES.COPYING);
        copyingManager.startCopyingPhase(data);
    }

    handleVotingRound(data) {
        gameStateManager.setPhase(GameConfig.PHASES.VOTING);
        votingManager.initializeVoting(data);
        
        // Start voting timer with auto-submit callback
        uiManager.startTimer('votingTimer', data.timer, () => {
            if (gameStateManager.getPhase() === GameConfig.PHASES.VOTING && !votingManager.isVoteSubmitted()) {
                votingManager.autoSubmitRandomVote();
                uiManager.showError('Time up! Random vote submitted automatically.');
            }
        });
    }

    handleVotingRoundExcluded(data) {
        votingManager.handleVotingExclusion(data);
    }

    handleGameResults(data) {
        gameStateManager.setPhase(GameConfig.PHASES.RESULTS);
        resultsManager.displayResults(data);
    }

    handleGameEndedEarly(data) {
        uiManager.showError(`Game ended: ${data.reason}`);
        if (data.final_balance && playerManager.getPlayerId() in data.final_balance) {
            playerManager.setBalance(data.final_balance[playerManager.getPlayerId()]);
        }
        setTimeout(() => this.returnHome(), 3000);
    }

    handleRoomLeft(data) {
        if (data.success) {
            this.resetAllManagers();
            uiManager.showView('home');
            uiManager.showSuccess(data.message);
            roomManager.updateRoomDisplay(null);
            socketHandler.requestRoomList();
        } else {
            uiManager.showError(data.message);
        }
    }

    // Utility methods
    returnHome() {
        // Leave current room on server side first
        if (roomManager.getCurrentRoom()) {
            socketHandler.emit('leave_room');
        }
        
        this.resetAllManagers();
        uiManager.showView('home');
        
        // Clear drawing canvas
        if (window.drawingCanvas) {
            drawingCanvas.resetCanvas();
        }
        
        // Clear any active timers
        uiManager.clearAllTimers();
        
        // Request fresh room list
        setTimeout(() => {
            socketHandler.requestRoomList();
        }, 100);
    }

    resetAllManagers() {
        roomManager.reset();
        playerManager.reset();
        gameStateManager.reset();
        bettingManager.reset();
        drawingManager.reset();
        copyingManager.reset();
        votingManager.reset();
        resultsManager.reset();
    }

    updateBalanceDisplay() {
        playerManager.updateBalanceDisplay();
    }

    updateRoomDisplay(roomId) {
        roomManager.updateRoomDisplay(roomId);
    }

    // Getters for backward compatibility and external access
    get currentRoom() {
        return roomManager.getCurrentRoom();
    }

    get playerId() {
        return playerManager.getPlayerId();
    }

    get gamePhase() {
        return gameStateManager.getPhase();
    }

    get currentBalance() {
        return playerManager.getBalance();
    }

    get copyTargets() {
        return copyingManager.getCopyTargets();
    }

    // Cleanup
    cleanup() {
        this.resetAllManagers();
        
        // Clear UI elements
        const elements = [
            'roomInfo', 'balanceInfo', 'promptText', 
            'drawingPromptText', 'roomList', 'playerList'
        ];
        
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                if (id === 'roomInfo') element.textContent = 'Room: -';
                else if (id === 'balanceInfo') element.textContent = `Balance: $${GameConfig.STARTING_BALANCE}`;
                else element.textContent = '';
            }
        });
    }
}

// Create global instance
const gameManager = new GameManager();