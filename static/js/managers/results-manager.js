// Results management for Pixel Plagiarist
class ResultsManager {
    constructor() {
        this.finalStandings = [];
    }

    displayResults(data) {
        this.processStandings(data);
        
        uiManager.showView('results');
        this.renderResultsInterface();
        
        // Update player's balance and save to database using final balance from payload
        const currentPlayer = this.finalStandings.find(p => p.id === playerManager.getPlayerId());
        if (currentPlayer) {
            playerManager.setBalance(currentPlayer.finalBalance);
            playerManager.updateBalanceDisplay(); // Force UI update
            
            // Save the updated balance to the database
            this.savePlayerBalance(currentPlayer.finalBalance);
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
                    console.log(`Saved balance for ${window.gameUserData.username}: ${balance} Bits`);
                } else {
                    console.warn('Failed to save player balance to server');
                }
            } catch (error) {
                console.warn('Error saving player balance:', error);
            }
        }
    }

    processStandings(data) {
        const totals = data.total_points_by_player || {};
        const netTokens = data.net_tokens_by_player || {};
        const finalBalances = data.final_balances || {};
        const names = data.player_names || {};

        // Build standings using total points (for ranking) and net tokens gained for display
        this.finalStandings = Object.keys(names).map(pid => ({
            id: pid,
            name: names[pid] || `Player ${pid}`,
            totalPoints: Math.round(totals[pid] || 0),
            netTokens: Math.round(netTokens[pid] || 0),
            finalBalance: Math.round(finalBalances[pid] || 0)
        }))
        .sort((a, b) => b.totalPoints - a.totalPoints);
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
            <div class="results-table">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th>Points</th>
                            <th>Net Bits</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        this.finalStandings.forEach((player, index) => {
            const isCurrentPlayer = player.id === playerManager.getPlayerId();
            const net = Math.round(player.netTokens);
            const netSign = net > 0 ? '+' : '';
            const rowClass = isCurrentPlayer ? 'current-player' : '';
            
            html += `
                        <tr class="${rowClass}">
                            <td class="rank">${index + 1}${index === 0 ? ' 👑' : ''}</td>
                            <td class="name">${player.name}${isCurrentPlayer ? ' (You)' : ''}</td>
                            <td class="points">${player.totalPoints}</td>
                            <td class="net-tokens">${netSign}${net}</td>
                        </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
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