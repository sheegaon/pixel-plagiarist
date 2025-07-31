// Player management for Pixel Plagiarist
class PlayerManager {
    constructor() {
        this.playerId = null;
        this.currentBalance = GameConfig.STARTING_BALANCE;
        this.playerList = [];
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
            balanceElement.textContent = `Balance: $${this.currentBalance}`;
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
                <span class="player-balance">$${player.balance || 0}</span>
                ${player.ready ? '<span class="ready-indicator">✓</span>' : ''}
            </div>
        `).join('');
    }

    reset() {
        this.playerId = null;
        this.currentBalance = GameConfig.STARTING_BALANCE;
        this.playerList = [];
        this.updateBalanceDisplay();
    }
}