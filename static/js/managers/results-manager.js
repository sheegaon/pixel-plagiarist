// Results management for Pixel Plagiarist
class ResultsManager {
    constructor() {
        this.finalStandings = [];
    }

    displayResults(data) {
        this.processStandings(data);
        
        uiManager.showView('results');
        this.renderResultsInterface();
        
        // Update player's balance and save to database
        const currentPlayer = this.finalStandings.find(p => p.id === playerManager.getPlayerId());
        if (currentPlayer) {
            playerManager.setBalance(currentPlayer.tokens);
            playerManager.updateBalanceDisplay(); // Force UI update
            
            // Save the updated balance to the database
            this.savePlayerBalance(currentPlayer.tokens);
        }
    }

    async savePlayerBalance(balance) {
        // Save player balance to server based on username
        if (window.gameUserData && window.gameUserData.username) {
            try {
                const response = await fetch(`/api/player/balance/${encodeURIComponent(window.gameUserData.username)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ balance: balance })
                });
                if (response.ok) {
                    console.log(`Saved balance for ${window.gameUserData.username}: ${balance} Pixel Pts`);
                } else {
                    console.warn('Failed to save player balance to server');
                }
            } catch (error) {
                console.warn('Error saving player balance:', error);
            }
        }
    }

    processStandings(data) {
        this.finalStandings = Object.entries(data.final_balances)
            .map(([pid, tokens]) => ({
                id: pid,
                name: data.player_names[pid] || `Player ${pid}`,
                tokens: Math.round(tokens)
            }))
            .sort((a, b) => b.tokens - a.tokens);
    }

    renderResultsInterface() {
        const grid = document.getElementById('resultsGrid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        // Create standings display
        const standingsDiv = document.createElement('div');
        standingsDiv.className = 'result-item standings';
        standingsDiv.innerHTML = this.generateStandingsHTML();
        grid.appendChild(standingsDiv);
        
        // Add return home button
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'result-actions';
        actionsDiv.innerHTML = `
            <button class="primary-btn" onclick="window.gameManager.returnHome()">
                🏠 Return Home
            </button>
        `;
        grid.appendChild(actionsDiv);
    }

    generateStandingsHTML() {
        const playerRank = this.finalStandings.findIndex(p => p.id === playerManager.getPlayerId()) + 1;
        const totalPlayers = this.finalStandings.length;
        
        let html = `
            <h3>🏆 Final Results</h3>
            <div class="your-rank">
                <p>Your Rank: <strong>${playerRank}/${totalPlayers}</strong></p>
            </div>
            <div class="standings-list">
        `;
        
        this.finalStandings.forEach((player, index) => {
            const isCurrentPlayer = player.id === playerManager.getPlayerId();
            const rankClass = index === 0 ? 'first-place' : (index < 3 ? 'top-three' : '');
            const currentPlayerClass = isCurrentPlayer ? 'current-player' : '';
            
            html += `
                <div class="standing-item ${rankClass} ${currentPlayerClass}">
                    <div class="rank">${index + 1}</div>
                    <div class="player-info">
                        <span class="name">${player.name}${isCurrentPlayer ? ' (You)' : ''}</span>
                        <span class="tokens">${Math.round(player.tokens)} Pixel Pts</span>
                    </div>
                    ${index === 0 ? '<div class="crown">👑</div>' : ''}
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }

    reset() {
        this.gameResults = null;
        this.finalStandings = [];
        
        const grid = document.getElementById('resultsGrid');
        if (grid) {
            grid.innerHTML = '';
        }
    }
}