// Results management for Pixel Plagiarist
class ResultsManager {
    constructor() {
        this.gameResults = null;
        this.finalStandings = [];
    }

    displayResults(data) {
        this.gameResults = data;
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
                tokens: tokens,
                score: data.final_scores[pid] || 0
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
        
        // Add detailed results if available
        if (this.gameResults.round_results) {
            const detailsDiv = document.createElement('div');
            detailsDiv.className = 'result-item details';
            detailsDiv.innerHTML = this.generateDetailsHTML();
            grid.appendChild(detailsDiv);
        }
        
        // Add return home button
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'result-actions';
        actionsDiv.innerHTML = `
            <button class="primary-btn" onclick="gameManager.returnHome()">
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

    generateDetailsHTML() {
        if (!this.gameResults.round_results) return '';
        
        let html = `
            <h4>🎯 Round Details</h4>
            <div class="round-details">
        `;
        
        this.gameResults.round_results.forEach((round, index) => {
            html += `
                <div class="round-summary">
                    <h5>Round ${index + 1}</h5>
                    <p><strong>Prompt:</strong> "${round.prompt}"</p>
                    <p><strong>Correct Votes:</strong> ${round.correct_votes}/${round.total_votes}</p>
                    <p><strong>Accuracy:</strong> ${Math.round((round.correct_votes / round.total_votes) * 100)}%</p>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }

    getWinner() {
        return this.finalStandings.length > 0 ? this.finalStandings[0] : null;
    }

    getPlayerRank(playerId) {
        const index = this.finalStandings.findIndex(p => p.id === playerId);
        return index >= 0 ? index + 1 : null;
    }

    getPlayerScore(playerId) {
        const player = this.finalStandings.find(p => p.id === playerId);
        return player ? player.score : 0;
    }

    getPlayerTokens(playerId) {
        const player = this.finalStandings.find(p => p.id === playerId);
        return player ? player.tokens : 0;
    }

    exportResults() {
        if (!this.gameResults) return null;
        
        return {
            timestamp: new Date().toISOString(),
            standings: this.finalStandings,
            gameData: this.gameResults
        };
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