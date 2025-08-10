// Main game coordinator for Pixel Plagiarist
class GameManager {
    constructor() {
        this.username = window.gameUserData ? window.gameUserData.username : 'Anonymous';
        
        // Don't initialize managers in constructor - wait for explicit initialization
        this.managersInitialized = false;
    }

    initializeManagers() {
        if (this.managersInitialized) return;
        
        // Create global instances of all managers
        window.roomManager = new RoomManager();
        window.playerManager = new PlayerManager();
        window.gameStateManager = new GameStateManager();
        window.drawingManager = new DrawingManager();
        window.copyingManager = new CopyingManager();
        window.votingManager = new VotingManager();
        window.resultsManager = new ResultsManager();
        
        this.managersInitialized = true;
    }

    // Delegation methods for room management
    createRoomWithStake(stake) {
        roomManager.createRoomWithStake(stake);
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

    // Delegation methods for copying
    submitCurrentCopy() {
        copyingManager.submitCurrentCopy();
    }

    submitVote() {
        votingManager.submitVote();
    }

    // Socket event handlers - coordinate between managers
    handleRoomCreated(data) {
        if (data.success) {
            roomManager.setCurrentRoom(data.room_id);
            playerManager.setPlayerId(socketHandler.socket.id);
            playerManager.updatePlayerList([]);
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
        gameStateManager.setPhase(GameConfig.PHASES.DRAWING);
        gameStateManager.setGameData(data);
        
        // Set prompt in UI
        const promptText = document.getElementById('promptText');
        if (promptText) {
            promptText.textContent = data.prompt;
        }
    }

    handlePhaseChanged(data) {
        gameStateManager.setPhase(data.phase);
        
        if (data.phase === GameConfig.PHASES.DRAWING) {
            // Choose this client's prompt from prompts_by_player if provided
            if (data.prompts_by_player && window.playerManager) {
                const pid = (typeof playerManager.getPlayerId === 'function') ? playerManager.getPlayerId() : null;
                const ownPrompt = pid ? data.prompts_by_player[pid] : undefined;
                if (ownPrompt) {
                    data.prompt = ownPrompt;
                } else if (!data.prompt) {
                    console.warn('Prompt for this player not found in prompts_by_player; using generic prompt.');
                    data.prompt = 'Draw something creative!';
                }
            }

            drawingManager.initializeDrawing(data);
            
            // Start drawing timer with auto-submit callback
            uiManager.startTimer('drawingTimer', data.timer, () => {
                if (gameStateManager.getPhase() === GameConfig.PHASES.DRAWING) {
                    drawingManager.autoSubmitDrawing();
                    uiManager.showMessage('Time up! Drawing submitted automatically.', 'info');
                }
            });
        }
        
        if (data.phase === GameConfig.PHASES.COPYING) {
            // Handle direct transition to copying phase
            copyingManager.initializeCopyingPhase(data);
            
            // Start copying timer with auto-submit callback
            uiManager.startTimer('copyingTimer', data.timer, () => {
                if (gameStateManager.getPhase() === GameConfig.PHASES.COPYING) {
                    copyingManager.autoSubmitRemainingCopies();
                    uiManager.showMessage('Time up! Remaining copies submitted automatically.', 'info');
                }
            });
        }
    }

    handleCopyingAssignment(data) {
        // Only process if we're not already in copying phase
        if (gameStateManager.getPhase() === GameConfig.PHASES.COPYING) {
            console.log('Already in copying phase, ignoring duplicate assignment');
            return;
        }
        
        console.log('Handling copying assignment:', data);
        
        gameStateManager.setPhase(GameConfig.PHASES.COPYING);
        copyingManager.initializeCopyingViewingPhase(data);
        
        // Start copying timer with auto-submit callback
        uiManager.startTimer('copyingTimer', data.timer, () => {
            if (gameStateManager.getPhase() === GameConfig.PHASES.COPYING) {
                copyingManager.autoSubmitRemainingCopies();
                uiManager.showMessage('Time up! Remaining copies submitted automatically.', 'info');
            }
        });
    }

    handleCopyingViewingPhase(data) {
        // Transition to copying phase and initialize viewing
        console.log('Handling copying viewing phase:', data);
        
        gameStateManager.setPhase(GameConfig.PHASES.COPYING);
        copyingManager.initializeCopyingViewingPhase(data);
        
        // Start copying timer with auto-submit callback
        uiManager.startTimer('copyingTimer', data.total_timer, () => {
            if (gameStateManager.getPhase() === GameConfig.PHASES.COPYING) {
                copyingManager.autoSubmitRemainingCopies();
                uiManager.showMessage('Time up! Remaining copies submitted automatically.', 'info');
            }
        });
    }

    handleCopyingPhaseStarted(data) {
        // Only transition if we're in the correct phase
        console.log('Handling copying phase started:', data);
        
        if (gameStateManager.getPhase() !== GameConfig.PHASES.COPYING) {
            gameStateManager.setPhase(GameConfig.PHASES.COPYING);
        }
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
        if (data.final_balances && playerManager.getPlayerId() in data.final_balances) {
            playerManager.setBalance(data.final_balances[playerManager.getPlayerId()]);
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

        // Reload the correct balance from the server
        playerManager.loadPlayerBalance();
        
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
        drawingManager.reset();
        copyingManager.reset();
        votingManager.reset();
        resultsManager.reset();
    }

    updateBalanceDisplay() {
        playerManager.updateBalanceDisplay();
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
                else if (id === 'balanceInfo') element.textContent = `Balance: ${GameConfig.INITIAL_BALANCE} Bits`;
                else element.textContent = '';
            }
        });
    }
}

// Don't create global instance immediately - let main.js handle this
let gameManager = null;