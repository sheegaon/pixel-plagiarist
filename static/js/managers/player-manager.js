// Player management for Pixel Plagiarist
class PlayerManager {
    constructor() {
        this.playerId = null;
        this.currentBalance = GameConfig.INITIAL_BALANCE;
        this.playerList = [];
        
        // Initialize balance display after a short delay to ensure DOM is ready
        setTimeout(() => this.loadPlayerBalance(), 100);
    }

    async loadPlayerBalance() {
        // Load player balance from server based on username
        if (window.gameUserData && window.gameUserData.username) {
            try {
                const response = await fetch(`/api/player/balance/${encodeURIComponent(window.gameUserData.username)}`);
                if (response.ok) {
                    const data = await response.json();
                    this.currentBalance = data.balance;
                    this.updateBalanceDisplay();
                    console.log(`Loaded balance for ${window.gameUserData.username}: ${this.currentBalance} Pixel Pts`);
                } else {
                    console.warn('Failed to load player balance, using default');
                    this.updateBalanceDisplay();
                }
            } catch (error) {
                console.warn('Error loading player balance:', error);
                this.updateBalanceDisplay();
            }
        } else {
            this.updateBalanceDisplay();
        }
    }

    setPlayerId(playerId) {
        this.playerId = playerId;
    }

    getPlayerId() {
        return this.playerId;
    }

    setBalance(balance) {
        this.currentBalance = balance;
        this.updateBalanceDisplay();
    }

    getBalance() {
        return this.currentBalance;
    }

    adjustBalance(amount) {
        this.currentBalance += amount;
        this.updateBalanceDisplay();
    }

    updateBalanceDisplay() {
        const balanceElement = document.getElementById('balanceInfo');
        if (balanceElement) {
            balanceElement.textContent = `Balance: ${Math.round(this.currentBalance)} Pixel Pts`;
        }
    }

    updatePlayerList(players) {
        this.playerList = players;
        const playerListElement = document.getElementById('playerList');
        if (!playerListElement) return;

        if (!players || players.length === 0) {
            playerListElement.innerHTML = '<p>No players in room</p>';
            return;
        }

        playerListElement.innerHTML = players.map(player => `
            <div class="player-item ${player.id === this.playerId ? 'current-player' : ''}">
                <span class="player-name">${player.username || `Player ${player.id}`}</span>
                <span class="player-balance">${Math.round(player.balance || 0)} Pixel Pts</span>
                ${player.ready ? '<span class="ready-indicator">✓</span>' : ''}
            </div>
        `).join('');
    }

    reset() {
        this.playerId = null;
        this.currentBalance = GameConfig.INITIAL_BALANCE;
        this.playerList = [];
        this.updateBalanceDisplay();
    }
}