// Drawing phase management for Pixel Plagiarist
class DrawingManager {
    constructor() {
        this.currentPrompt = '';
        this.drawingSubmitted = false;
        this.timeRemaining = 0;
    }

    initializeDrawing(data) {
        this.currentPrompt = data.prompt;
        this.drawingSubmitted = false;
        
        const promptElement = document.getElementById('drawingPromptText');
        if (promptElement) {
            promptElement.textContent = data.prompt;
        }
        
        const submitButton = document.getElementById('submitDrawingBtn');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Drawing';
        }
        
        // Clear the canvas for new drawing
        if (window.drawingCanvas) {
            drawingCanvas.clearCanvas();
        }
        
        uiManager.showView('drawing');
        
        // Start the drawing timer
        if (data.timer) {
            gameStateManager.startTimer(data.timer);
        }
    }

    submitDrawing() {
        if (this.drawingSubmitted) {
            uiManager.showError('Drawing already submitted');
            return;
        }

        if (!window.drawingCanvas) {
            uiManager.showError('Drawing canvas not available');
            return;
        }

        const drawingData = drawingCanvas.getCanvasData();
        if (!drawingData) {
            uiManager.showError('No drawing to submit');
            return;
        }

        const submitButton = document.getElementById('submitDrawingBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Submitted';
        }

        socketHandler.emit('submit_drawing', {
            drawing_data: drawingData,
            type: 'original'
        });

        this.drawingSubmitted = true;
        uiManager.showSuccess('Drawing submitted successfully!');
    }

    autoSubmitDrawing() {
        if (!this.drawingSubmitted) {
            // Auto-submit current drawing or empty canvas
            this.submitDrawing();
        }
    }

    getCurrentPrompt() {
        return this.currentPrompt;
    }

    isDrawingSubmitted() {
        return this.drawingSubmitted;
    }

    reset() {
        this.currentPrompt = '';
        this.drawingSubmitted = false;
        this.timeRemaining = 0;
        
        const submitButton = document.getElementById('submitDrawingBtn');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Drawing';
        }
        
        const promptElement = document.getElementById('drawingPromptText');
        if (promptElement) {
            promptElement.textContent = '';
        }
    }
}