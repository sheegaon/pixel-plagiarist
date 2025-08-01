// Results management for Pixel Plagiarist
class ResultsManager {
    constructor() {
        this.finalStandings = [];
    }

    displayResults(data) {
        this.processStandings(data);
        
        uiManager.showView('results');
        this.renderResultsInterface();
        
        // Update player's balance
        const myTokens = this.finalStandings.find(p => p.id === playerManager.getPlayerId())?.tokens || playerManager.getBalance();
        playerManager.setBalance(myTokens);
    }

    processStandings(data) {
        this.finalStandings = Object.entries(data.final_balance)
            .map(([pid, tokens]) => ({
                id: pid,
                name: data.player_names[pid] || `Player ${pid}`,
                tokens: Math.round(tokens * 100) / 100  // Round to nearest cent
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
                        <span class="tokens">$${player.tokens}</span>
                        <span class="score">${player.score} points</span>
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