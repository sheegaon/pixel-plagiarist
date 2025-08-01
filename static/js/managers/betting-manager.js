// Betting management for Pixel Plagiarist
class BettingManager {
    constructor() {
        this.currentStake = 0;
        this.minStake = 0;
        this.betPlaced = false;
    }

    initializeBetting(data) {
        this.minStake = data.min_stake;
        this.currentStake = this.minStake;
        this.betPlaced = false;
        
        this.setupStakeButtons();
        this.updateStakeDisplay(this.minStake);
        
        const betButton = document.getElementById('betButton');
        if (betButton) {
            betButton.disabled = false;
            betButton.textContent = 'Place Bet';
        }
        
        uiManager.showView('betting');
    }

    setupStakeButtons() {
        const stakeButtonsContainer = document.getElementById('stakeButtons');
        if (!stakeButtonsContainer) {
            console.warn('Stake buttons container not found');
            return;
        }
        
        // Define multipliers for stake buttons (1x, 2x, 3x, 5x, 10x)
        const multipliers = [1, 2, 3, 5, 10];
        
        // Clear existing buttons
        stakeButtonsContainer.innerHTML = '';
        
        // Create buttons for each multiplier
        multipliers.forEach(multiplier => {
            const stakeAmount = this.minStake * multiplier;
            
            // Only show button if player can afford it
            if (stakeAmount <= playerManager.getBalance()) {
                const button = document.createElement('button');
                button.className = 'stake-option-btn';
                button.textContent = `${multiplier}x ($${stakeAmount})`;
                // button.setAttribute('data-stake', stakeAmount); // Add data attribute for exact matching
                button.onclick = () => this.selectStake(stakeAmount);
                stakeButtonsContainer.appendChild(button);
            }
        });
        
        // Select the minimum stake by default
        // this.selectStake(this.minStake);
    }

    selectStake(stake) {
        this.currentStake = stake;
        this.updateStakeDisplay(stake);
        
        // Update button selection visual feedback
        const buttons = document.querySelectorAll('.stake-option-btn');
        buttons.forEach(btn => {
            btn.classList.remove('selected');
            if (btn.textContent === `$${stake}`) {
                btn.classList.add('selected');
            }
        });
    }

    updateStakeDisplay(stake) {
        this.currentStake = stake;
        
        const stakeAmount = document.getElementById('stakeAmount');
        const remainingTokens = document.getElementById('remainingTokens');
        
        if (stakeAmount) {
            stakeAmount.textContent = stake;
        }
        if (remainingTokens) {
            remainingTokens.textContent = playerManager.getBalance() - stake;
        }
    }

    placeBet() {
        // Validate phase before placing bet
        if (gameStateManager.getPhase() !== GameConfig.PHASES.BETTING) {
            uiManager.showError('Cannot place bet during this phase');
            return;
        }

        if (this.betPlaced) {
            uiManager.showError('Bet already placed');
            return;
        }

        const stakeValue = parseInt(this.currentStake);
        if (isNaN(stakeValue) || stakeValue < this.minStake) {
            uiManager.showError(`Minimum stake is $${this.minStake}`);
            return;
        }

        if (stakeValue > playerManager.getBalance()) {
            uiManager.showError('Insufficient balance');
            return;
        }
        
        socketHandler.emit('place_bet', { stake: stakeValue });

        this.betPlaced = true;
        
        const betButton = document.getElementById('betButton');
        if (betButton) {
            betButton.disabled = true;
            betButton.textContent = 'Bet Placed';
        }
        
        const stakeSlider = document.getElementById('stakeSlider');
        if (stakeSlider) {
            stakeSlider.disabled = true;
        }
        
        uiManager.showSuccess(`Bet of $${stakeValue} placed successfully!`);
    }

    autoPlaceBet() {
        if (!this.betPlaced) {
            if (this.currentStake >= this.minStake) {
                this.placeBet();
            }
        }
    }

    getCurrentStake() {
        return this.currentStake;
    }

    isBetPlaced() {
        return this.betPlaced;
    }

    reset() {
        this.currentStake = 0;
        this.minStake = 0;
        this.betPlaced = false;
        
        const betButton = document.getElementById('betButton');
        if (betButton) {
            betButton.disabled = false;
            betButton.textContent = 'Place Bet';
        }
        
        // Clear stake buttons
        const stakeButtonsContainer = document.getElementById('stakeButtons');
        if (stakeButtonsContainer) {
            stakeButtonsContainer.innerHTML = '';
        }
    }
}