// Copying phase management for Pixel Plagiarist
class CopyingManager {
    constructor() {
        this.copyTargets = [];
        this.currentCopyIndex = 0;
        this.currentTargetId = null;
        this.submittedCopies = 0;
        this.isInViewingPhase = false;
        this.drawing = null;
        this.total_timer = 0;
        this.remaining_time = 0;
        this.initialized = false;  // Prevent duplicate initializations
    }

    initializeCopyingViewingPhase(data) {
        // Prevent duplicate initializations
        if (this.initialized && this.copyTargets.length > 0) {
            console.log('Copying phase already initialized, skipping duplicate');
            return;
        }
        
        this.copyTargets = data.targets || [];
        this.currentCopyIndex = 0;
        this.submittedCopies = 0;
        this.isInViewingPhase = true;
        this.initialized = true;
        
        uiManager.showView('copying');
        this.displayViewingPhase();
        
        const submitButton = document.getElementById('submitCopyBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Viewing...';
        }
        
        if (data.total_timer) {
            gameStateManager.startTimer(data.total_timer);
        }
    }

    displayViewingPhase() {
        const copyTargets = document.getElementById('copyTargets');
        if (!copyTargets) return;
        
        copyTargets.innerHTML = '<h3>Viewing Period</h3><p>Study this drawing carefully!</p>';
        
        if (this.copyTargets.length > 0) {
            const target = this.copyTargets[0];
            const targetDiv = document.createElement('div');
            targetDiv.className = 'copying-target';
            targetDiv.innerHTML = `
                <h4>Drawing 1 of ${this.copyTargets.length}</h4>
                <img src="${target.drawing}" alt="Target drawing" style="max-width: 300px; border: 2px solid #4299e1; border-radius: 8px;">
                <button class="flag-btn" onclick="socketHandler.flagImage('original_${target.target_id}', 'copying')">
                    🚩 Flag
                </button>
            `;
            copyTargets.appendChild(targetDiv);
        }
    }

    startCopyingPhase(data) {
        this.isInViewingPhase = false;
        this.startNextCopy();
        
        if (data.remaining_time) {
            gameStateManager.startTimer(data.remaining_time);
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
                        <p>Recreate the drawing you saw during the viewing phase.</p>
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
        }
    }

    submitCurrentCopy() {
        // Validate phase before submission
        if (gameStateManager.getPhase() !== GameConfig.PHASES.COPYING) {
            uiManager.showError('Cannot submit copy during this phase');
            return;
        }
        
        if (this.isInViewingPhase) {
            uiManager.showError('Cannot submit during viewing phase');
            return;
        }

        if (this.currentCopyIndex >= this.copyTargets.length) {
            uiManager.showError('No more copies to submit');
            return;
        }

        if (!window.drawingCanvas) {
            uiManager.showError('Drawing canvas not available');
            return;
        }

        const target = this.copyTargets[this.currentCopyIndex];
        const drawingData = drawingCanvas.getCanvasData() || this.createEmptyCanvas();

        socketHandler.emit('submit_copy', {
            target_id: target.target_id,
            drawing_data: drawingData
        });

        this.submittedCopies++;
        this.currentCopyIndex++;
        
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
            this.showReviewOverlay(targetDrawing.drawing);
        }
    }

    showReviewOverlay(drawingUrl) {
        const overlay = document.getElementById('originalOverlay');
        const image = document.getElementById('originalImage');
        const countdown = document.getElementById('originalCountdown');
        
        if (!overlay || !image || !countdown) return;
        
        image.src = drawingUrl;
        overlay.style.display = 'flex';
        
        let timeLeft = 5;
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

    isViewingPhase() {
        return this.isInViewingPhase;
    }

    reset() {
        this.copyTargets = [];
        this.currentCopyIndex = 0;
        this.currentTargetId = null;
        this.submittedCopies = 0;
        this.isInViewingPhase = false;
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