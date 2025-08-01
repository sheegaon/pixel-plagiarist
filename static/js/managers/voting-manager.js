// Voting management for Pixel Plagiarist
class VotingManager {
    constructor() {
        this.selectedDrawingId = null;
        this.voteSubmitted = false;
        this.total_sets = 0;
        this.set_index = 0;
        this.drawings = [];
    }

    initializeVoting(data) {
        this.selectedDrawingId = null;
        this.voteSubmitted = false;
        this.set_index = data.set_index;
        
        uiManager.showView('voting');
        this.displayVotingInterface(data);
        
        const submitButton = document.getElementById('submitVoteBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Select a drawing first';
        }
        
        if (data.timer) {
            gameStateManager.startTimer(data.timer);
        }
    }

    displayVotingInterface(data) {
        const votingInstructions = document.getElementById('votingInstructions');
        if (votingInstructions) {
            if (data.prompt) {
                votingInstructions.innerHTML = `
                    <div class="voting-prompt-display">
                        <h4>The original prompt was:</h4>
                        <p>"${data.prompt}"</p>
                    </div>
                    <h3>Which drawing is the ORIGINAL?</h3>
                    <p>Set ${data.set_index + 1} of ${data.total_sets}</p>
                `;
            } else {
                votingInstructions.innerHTML = `
                    <h3>Which drawing is the ORIGINAL?</h3>
                    <p>Set ${data.set_index + 1} of ${data.total_sets}</p>
                `;
            }
        }
        
        this.displayVotingOptions(data.drawings);
    }

    displayVotingOptions(drawings, observationOnly = false) {
        const votingGrid = document.getElementById('votingGrid');
        if (!votingGrid) return;
        
        votingGrid.innerHTML = '';
        
        drawings.forEach(drawing => {
            const option = document.createElement('div');
            option.className = observationOnly ? 'voting-option observation-only' : 'voting-option';
            option.setAttribute('data-drawing-id', drawing.id);
            option.innerHTML = `
                <img src="${drawing.drawing}" alt="Drawing option">
                <button class="flag-btn" onclick="socketHandler.flagImage('${drawing.id}', 'voting')">
                    🚩 Flag
                </button>
                ${observationOnly ? '<div class="observation-label">Observation Only</div>' : ''}
            `;
            
            if (!observationOnly) {
                option.addEventListener('click', () => {
                    this.selectDrawing(drawing.id, option);
                });
            }
            
            votingGrid.appendChild(option);
        });
    }

    selectDrawing(drawingId, element) {
        // Remove selection from all options
        document.querySelectorAll('.voting-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        
        // Select the clicked option
        element.classList.add('selected');
        this.selectedDrawingId = drawingId;
        
        // Enable submit button
        const submitButton = document.getElementById('submitVoteBtn');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Vote';
        }
    }

    submitVote() {
        // Validate current phase before allowing vote submission
        if (gameStateManager.getPhase() !== GameConfig.PHASES.VOTING) {
            uiManager.showError('Cannot vote during this phase');
            return;
        }

        if (!this.selectedDrawingId) {
            uiManager.showError('Please select a drawing first');
            return;
        }

        if (this.voteSubmitted) {
            uiManager.showError('Vote already submitted');
            return;
        }

        socketHandler.emit('submit_vote', { 
            drawing_id: this.selectedDrawingId 
        });

        this.voteSubmitted = true;
        
        const submitButton = document.getElementById('submitVoteBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Vote Submitted';
        }
        
        // Disable all voting options
        document.querySelectorAll('.voting-option').forEach(opt => {
            opt.style.pointerEvents = 'none';
            opt.style.opacity = '0.7';
        });
        
        uiManager.showSuccess('Vote submitted successfully!');
    }

    autoSubmitRandomVote() {
        if (this.voteSubmitted) return;
        
        const drawings = this.drawings;
        if (!drawings || drawings.length === 0) return;
        
        // Select random drawing
        const randomIndex = Math.floor(Math.random() * drawings.length);
        const randomDrawing = drawings[randomIndex];
        
        const votingOptions = document.querySelectorAll('.voting-option');
        if (votingOptions[randomIndex]) {
            this.selectDrawing(randomDrawing.id, votingOptions[randomIndex]);
            this.submitVote();
        }
    }

    handleVotingExclusion(data) {
        gameStateManager.setPhase(GameConfig.PHASES.VOTING);
        uiManager.showView('voting');
        
        // Show the excluded message with proper voting interface
        const votingInstructions = document.getElementById('votingInstructions');
        if (votingInstructions) {
            votingInstructions.innerHTML = `
                <div class="voting-excluded-notice">
                    <h3>⚠️ Cannot Vote - ${data.reason}</h3>
                    <p>You can observe this voting round but cannot participate.</p>
                    <p>Set ${data.set_index + 1} of ${data.total_sets}</p>
                    ${data.prompt ? `
                        <div class="voting-prompt-display">
                            <h4>The original prompt was:</h4>
                            <p>"${data.prompt}"</p>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Display the voting options for observation if provided
        if (data.drawings) {
            this.displayVotingOptions(data.drawings, true); // true = observation only
        }
        
        const submitButton = document.getElementById('submitVoteBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Cannot Vote';
        }
        
        // Start the timer to keep excluded players synchronized with voting phase
        if (data.timer) {
            gameStateManager.startTimer(data.timer);
        }
    }

    isVoteSubmitted() {
        return this.voteSubmitted;
    }

    reset() {
        this.selectedDrawingId = null;
        this.voteSubmitted = false;
        this.total_sets = 0;
        this.set_index = 0;
        this.drawings = [];
        
        const submitButton = document.getElementById('submitVoteBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Select a drawing first';
        }
        
        const votingGrid = document.getElementById('votingGrid');
        if (votingGrid) {
            votingGrid.innerHTML = '';
        }
        
        const votingInstructions = document.getElementById('votingInstructions');
        if (votingInstructions) {
            votingInstructions.innerHTML = '';
        }
    }
}