// Copying phase management for Pixel Plagiarist
class CopyingManager {
    constructor() {
        this.copyTargets = [];
        this.currentCopyIndex = 0;
        this.currentTargetId = null;
        this.submittedCopies = 0;
        this.drawing = null;
        this.total_timer = 0;
        this.remaining_time = 0;
        this.initialized = false;  // Prevent duplicate initializations
    }

    initializeCopyingPhase(data) {
        // If we already have targets and the new data doesn't have targets, skip reinitialization
        if (this.initialized && this.copyTargets.length > 0 && (!data.targets || data.targets.length === 0)) {
            console.log('Copying phase already initialized with targets, skipping reinit without targets');
            return;
        }
        
        // Allow reinitialization for new games, but prevent duplicate calls within same game
        if (this.initialized && this.copyTargets.length > 0 && data.targets && 
            JSON.stringify(this.copyTargets) === JSON.stringify(data.targets)) {
            console.log('Copying phase already initialized with same targets, skipping duplicate');
            return;
        }
        
        // Only set copyTargets if the data actually contains targets
        if (data.targets && data.targets.length > 0) {
            this.copyTargets = data.targets;
            this.currentCopyIndex = 0;
            this.submittedCopies = 0;
            this.initialized = true;

            uiManager.showView('copying');
            
            // Start the first copy immediately with review overlay
            this.startNextCopy();
        }
        
        if (data.timer) {
            gameStateManager.startTimer(data.timer);
        }
    }

    initializeCopyingViewingPhase(data) {
        // This is an alias for initializeCopyingPhase to maintain compatibility
        this.initializeCopyingPhase(data);
    }

    startCopyingPhase(data) {
        // This method is called when copying phase officially starts after viewing
        // Just ensure we're in the right state - the copying should already be initialized
        if (!this.initialized) {
            this.initializeCopyingPhase(data);
        }
    }

    startNextCopy() {
        if (this.currentCopyIndex < this.copyTargets.length) {
            const target = this.copyTargets[this.currentCopyIndex];
            const copyTargets = document.getElementById('copyTargets');
            
            if (copyTargets) {
                copyTargets.innerHTML = `
                    <h3>Copy Drawing ${this.currentCopyIndex + 1} of ${this.copyTargets.length}</h3>
                    <div class="copying-target">
                        <button class="view-again-btn" onclick="copyingManager.requestReview('${target.target_id}')">
                            👁️ View Again (5s)
                        </button>
                        <p>Recreate the drawing you saw during the review period.</p>
                    </div>
                `;
            }
            
            const submitButton = document.getElementById('submitCopyBtn');
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = `Submit Copy`;
            }
            
            if (window.drawingCanvas) {
                drawingCanvas.clearCanvas();
            }
            
            this.currentTargetId = target.target_id;
            
            // Show the review overlay immediately for this drawing
            const reviewDuration = (GameConfig.TIMERS && GameConfig.TIMERS.REVIEW) 
                ? GameConfig.TIMERS.REVIEW * 1000 
                : 5000; // Fallback to 5 seconds
            this.showReviewOverlay(target.drawing, reviewDuration);
        }
    }

    submitCurrentCopy() {
        // Validate phase before submission
        if (gameStateManager.getPhase() !== GameConfig.PHASES.COPYING) {
            uiManager.showError('Cannot submit copy during this phase');
            return;
        }

        if (this.currentCopyIndex >= this.copyTargets.length) {
            console.log(`No more copies to submit: ${this.currentCopyIndex} >= ${this.copyTargets.length}`);
            uiManager.showError('No more copies to submit');
            return;
        }

        if (!window.drawingCanvas) {
            uiManager.showError('Drawing canvas not available');
            return;
        }

        const target = this.copyTargets[this.currentCopyIndex];
        const drawingData = drawingCanvas.getCanvasData() || this.createEmptyCanvas();

        console.log(`Submitting copy ${this.currentCopyIndex + 1} of ${this.copyTargets.length}`);

        socketHandler.emit('submit_copy', {
            target_id: target.target_id,
            drawing_data: drawingData
        });

        this.submittedCopies++;
        this.currentCopyIndex++;
        
        console.log(`Advanced to copy index: ${this.currentCopyIndex}, total copies: ${this.copyTargets.length}`);
        
        if (this.currentCopyIndex < this.copyTargets.length) {
            this.startNextCopy();
        } else {
            const submitButton = document.getElementById('submitCopyBtn');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'All Copies Submitted';
            }
            uiManager.showSuccess('All copies submitted!');
        }
    }

    requestReview(targetId) {
        socketHandler.emit('request_review', { target_id: targetId });
        
        const targetDrawing = this.copyTargets.find(t => t.target_id === targetId);
        if (targetDrawing) {
            this.showReviewOverlay(targetDrawing.drawing, 5000); // 5 second "view again"
        }
    }

    showReviewOverlay(drawingUrl, duration = 5000) {
        const overlay = document.getElementById('reviewOverlay');
        const image = document.getElementById('reviewImage');
        const countdown = document.getElementById('reviewCountdown');
        
        if (!overlay || !image || !countdown) return;
        
        image.src = drawingUrl;
        overlay.style.display = 'flex';
        
        let timeLeft = Math.floor(duration / 1000);
        countdown.textContent = timeLeft;
        
        const countdownInterval = setInterval(() => {
            timeLeft--;
            countdown.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                overlay.style.display = 'none';
            }
        }, 1000);
        
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                clearInterval(countdownInterval);
                overlay.style.display = 'none';
            }
        };
    }

    autoSubmitRemainingCopies() {
        while (this.currentCopyIndex < this.copyTargets.length) {
            const target = this.copyTargets[this.currentCopyIndex];
            const emptyCanvas = this.createEmptyCanvas();
            
            socketHandler.emit('submit_copy', {
                target_id: target.target_id,
                drawing_data: emptyCanvas
            });
            
            this.currentCopyIndex++;
            this.submittedCopies++;
        }
        
        const submitButton = document.getElementById('submitCopyBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'All Copies Submitted';
        }
    }

    createEmptyCanvas() {
        const canvas = document.createElement('canvas');
        canvas.width = GameConfig.CANVAS_WIDTH;
        canvas.height = GameConfig.CANVAS_HEIGHT;
        return canvas.toDataURL('image/png');
    }

    getCopyTargets() {
        return this.copyTargets;
    }

    getCurrentCopyIndex() {
        return this.currentCopyIndex;
    }

    getSubmittedCopies() {
        return this.submittedCopies;
    }

    reset() {
        this.copyTargets = [];
        this.currentCopyIndex = 0;
        this.currentTargetId = null;
        this.submittedCopies = 0;
        this.initialized = false;
        
        const submitButton = document.getElementById('submitCopyBtn');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Copy';
        }
        
        const copyTargets = document.getElementById('copyTargets');
        if (copyTargets) {
            copyTargets.innerHTML = '';
        }
    }
}