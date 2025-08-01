// UI management and utilities for Pixel Plagiarist
class UIManager {
    constructor() {
        this.timers = new Map();
        this.currentView = 'home';
    }

    // Screen/View management
    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
        this.currentView = screenId.replace('Screen', '');
    }

    showView(viewName) {
        const screenId = viewName + 'Screen';
        this.showScreen(screenId);
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
        let timeLeft = seconds;
        
        const interval = setInterval(() => {
            timer.textContent = timeLeft;
            timeLeft--;
            
            if (timeLeft < 0) {
                clearInterval(interval);
                timer.textContent = "Starting...";
            }
        }, 1000);
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
    }

    reset() {
        this.showScreen('homeScreen');
        this.clearAllTimers();
        
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