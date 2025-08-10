// UI management and utilities for Pixel Plagiarist
class UIManager {
    constructor() {
        this.timers = new Map();
        this.currentView = 'home';
    }

    // Screen/View management
    showScreen(screenId) {
        const screens = document.querySelectorAll('.screen');
        const target = document.getElementById(screenId);
        console.log(`🖥️ showScreen: switching to ${screenId}, foundScreens=${screens.length}, targetFound=${!!target}`);
        screens.forEach(screen => {
            screen.classList.remove('active');
        });
        if (!target) {
            console.warn(`⚠️ showScreen: target ${screenId} not found`);
            return;
        }
        target.classList.add('active');
        this.currentView = screenId.replace('Screen', '');
    }

    showView(viewName) {
        const prevView = this.getCurrentView();
                const prevViewName = this.getCurrentView();
                const screenId = viewName + 'Screen';
                this.showScreen(screenId);
                try {
                    const phase = (typeof window !== 'undefined' && typeof window.gameManager !== 'undefined')
                        ? window.gameManager.gamePhase
                        : 'unknown';
                    console.log(`🧩 UI view change: ${prevViewName} -> ${viewName} (phase: ${phase})`);
            } catch (e) {
                console.warn('Error logging view change:', e);
            }
        try {
            const phase = window.gameManager ? window.gameManager.gamePhase : 'unknown';
            console.log(`🧩 UI view change: ${prevView} -> ${viewName} (phase: ${phase})`);
        } catch (e) {
            console.warn('Error logging view change:', e);
        }
    }

    getCurrentView() {
        return this.currentView;
    }

    // Message display
    showMessage(message, type) {
        const errorDiv = document.getElementById('errorDisplay');
        errorDiv.className = type === 'error' ? 'error-message' : 'success-message';
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 3000);
    }

    showError(message, duration = 5000) {
        this.showMessage(message, 'error');
    }

    showSuccess(message, duration = 3000) {
        this.showMessage(message, 'success');
    }

    startTimer(elementId, seconds, onExpireCallback = null) {
        const timer = document.getElementById(elementId);
        if (!timer) {
            console.warn(`Timer element ${elementId} not found`);
            return;
        }
        
        let timeLeft = seconds;
        
        if (this.timers.has(elementId)) {
            clearInterval(this.timers.get(elementId));
        }
        
        // Set initial value
        timer.textContent = timeLeft;
        
        const interval = setInterval(() => {
            timeLeft--;
            timer.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(interval);
                timer.textContent = "Time's up!";
                this.timers.delete(elementId);
                
                if (onExpireCallback && typeof onExpireCallback === 'function') {
                    onExpireCallback();
                }
            }
        }, 1000);
        
        this.timers.set(elementId, interval);
    }

    startCountdown(seconds) {
        const timer = document.getElementById('joiningTimer');
        if (!timer) {
            console.warn('Joining timer element not found');
            return;
        }
        
        let timeLeft = seconds;
        
        // Clear any existing countdown timer
        if (this.timers.has('joiningTimer')) {
            clearInterval(this.timers.get('joiningTimer'));
        }
        
        // Set initial value immediately
        timer.textContent = timeLeft;
        
        const interval = setInterval(() => {
            timeLeft--;
            timer.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(interval);
                this.timers.delete('joiningTimer');
                timer.textContent = "Starting...";
                
                // Add a small delay before assuming the game should start
                // This helps with timing synchronization between client and server
                setTimeout(() => {
                    // If we're still showing "Starting..." after a reasonable delay,
                    // it might indicate a timing issue - log it for debugging
                    if (timer.textContent === "Starting...") {
                        console.log('Countdown completed, waiting for server to start game...');
                    }
                }, 2000);
            }
        }, 1000);
        
        // Store the interval so it can be properly cleared
        this.timers.set('joiningTimer', interval);
    }

    showReviewOverlay(drawing, duration) {
        const overlay = document.getElementById('reviewOverlay');
        const image = document.getElementById('reviewImage');
        const countdown = document.getElementById('reviewCountdown');
        
        image.src = drawing;
        overlay.style.display = 'flex';
        
        let timeLeft = duration / 1000;
        countdown.textContent = timeLeft;
        
        const countdownInterval = setInterval(() => {
            timeLeft--;
            countdown.textContent = timeLeft;
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                overlay.style.display = 'none';
            }
        }, 1000);
    }

    showJoinCodeModal() {
        const modal = document.getElementById('joinCodeModal');
        const input = document.getElementById('roomCodeInputModal');
        const errorDisplay = document.getElementById('modalErrorDisplay');
        
        modal.style.display = 'block';
        input.value = '';
        input.focus();
        errorDisplay.style.display = 'none';
    }

    hideJoinCodeModal() {
        const modal = document.getElementById('joinCodeModal');
        modal.style.display = 'none';
    }

    showModalError(message) {
        const errorDisplay = document.getElementById('modalErrorDisplay');
        errorDisplay.textContent = message;
        errorDisplay.style.display = 'block';
    }

    clearAllTimers() {
        this.timers.forEach((interval, elementId) => {
            clearInterval(interval);
        });
        this.timers.clear();
        
        // Reset timer displays to default state
        const timerElements = ['gameTimer', 'joiningTimer', 'drawingTimer', 'copyingTimer', 'votingTimer'];
        timerElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '0:00';
            }
        });
    }

    reset() {
        this.showScreen('homeScreen');
        this.clearAllTimers();
        
        // Clear canvas if it exists
        if (window.drawingCanvas) {
            drawingCanvas.clearCanvas();
        }
        
        const modal = document.getElementById('joinCodeModal');
        if (modal) {
            modal.style.display = 'none';
        }
        
        const overlays = ['reviewOverlay', 'originalOverlay'];
        overlays.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
            }
        });
        
        const errorDisplay = document.getElementById('errorDisplay');
        const modalErrorDisplay = document.getElementById('modalErrorDisplay');
        if (errorDisplay) errorDisplay.style.display = 'none';
        if (modalErrorDisplay) modalErrorDisplay.style.display = 'none';
        
        // Hide countdown display
        const countdownDisplay = document.getElementById('countdownDisplay');
        if (countdownDisplay) {
            countdownDisplay.style.display = 'none';
        }
    }

    validateRoomForm() {
        const roomCode = document.getElementById('roomCodeInputModal').value.trim();
        
        if (!roomCode) {
            this.showMessage('Please enter a room code', 'error');
            return false;
        }
        
        return true;
    }

    validateCreateRoomForm() {
        const minStakeInput = document.getElementById('minStakeInput');
        if (!minStakeInput) return true;
        
        const minStake = parseInt(minStakeInput.value);
        
        if (minStake && (minStake < 1 || minStake > 50)) {
            this.showMessage('Minimum stake must be between $1 and $50', 'error');
            return false;
        }
        
        return true;
    }

    animateButton(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.style.transform = 'scale(0.95)';
            setTimeout(() => {
                button.style.transform = 'scale(1)';
            }, 150);
        }
    }

    updateCanvasSize() {
        const canvas = document.getElementById('drawingCanvas');
        const copyingCanvas = document.getElementById('copyingCanvas');
        
        if (window.innerWidth <= 768) {
            canvas.style.maxWidth = '100%';
            canvas.style.height = '300px';
            copyingCanvas.style.maxWidth = '100%';
            copyingCanvas.style.height = '300px';
        }
    }

    initResponsive() {
        window.addEventListener('resize', () => {
            this.updateCanvasSize();
        });
        
        this.updateCanvasSize();
    }

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const overlay = document.getElementById('reviewOverlay');
                if (overlay.style.display === 'flex') {
                    overlay.style.display = 'none';
                }
            }
            
            if (e.key === 'Enter') {
                if (document.getElementById('homeScreen').classList.contains('active')) {
                    const roomCodeInput = document.getElementById('roomCodeInputModal');
                    if (roomCodeInput === document.activeElement) {
                        gameManager.joinRoomByCode();
                    }
                }
            }
        });
    }

    handleError(error, context = '') {
        console.error(`Error in ${context}:`, error);
        this.showMessage(`An error occurred: ${error.message || error}`, 'error');
    }

    // Element management
    enableElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.disabled = false;
            element.classList.remove('disabled');
        }
    }

    disableElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.disabled = true;
            element.classList.add('disabled');
        }
    }

    showLoading(elementId, isLoading = true) {
        const element = document.getElementById(elementId);
        if (element) {
            if (isLoading) {
                element.disabled = true;
                element.textContent = 'Loading...';
                element.classList.add('loading');
            } else {
                element.disabled = false;
                element.classList.remove('loading');
            }
        }
    }

    hideLoading(elementId) {
        this.showLoading(elementId, false);
    }

    updateGameContent(content) {
        const gameContentElement = document.getElementById('gameContent');
        if (gameContentElement) {
            gameContentElement.innerHTML = content;
        }
    }
}

const uiManager = new UIManager();