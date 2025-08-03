// Game state management for Pixel Plagiarist
class GameStateManager {
    constructor() {
        this.currentPhase = 'waiting';
        this.gameData = {};
        this.timeRemaining = 0;
        this.timer = null;
    }

    setPhase(phase) {
        this.currentPhase = phase;
        this.updatePhaseDisplay();
    }

    getPhase() {
        return this.currentPhase;
    }

    setGameData(data) {
        this.gameData = { ...this.gameData, ...data };
    }

    startTimer(duration) {
        this.clearTimer();
        this.timeRemaining = duration;
        
        this.timer = setInterval(() => {
            this.timeRemaining--;
            this.updateTimerDisplay();
            
            if (this.timeRemaining <= 0) {
                this.clearTimer();
            }
        }, 1000);
    }

    clearTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    updateTimerDisplay() {
        const timerElement = document.getElementById('gameTimer');
        if (timerElement) {
            const minutes = Math.floor(this.timeRemaining / 60);
            const seconds = this.timeRemaining % 60;
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    updatePhaseDisplay() {
        const phaseElement = document.getElementById('currentPhase');
        if (phaseElement) {
            phaseElement.textContent = this.currentPhase.replace('_', ' ').toUpperCase();
        }
    }

    reset() {
        this.currentPhase = 'waiting';
        this.gameData = {};
        this.clearTimer();
        this.timeRemaining = 0;
    }
}