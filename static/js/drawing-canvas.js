// Drawing canvas functionality for Pixel Plagiarist
class DrawingCanvas {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.copyingCanvas = null;
        this.copyingCtx = null;
        this.isDrawing = false;
        this.currentTool = GameConfig.TOOLS.BRUSH;
        this.currentColor = '#000000';
        this.brushSize = GameConfig.DEFAULT_BRUSH_SIZE;
        this.strokes = [];
        this.currentStroke = [];
    }

    init() {
        this.setupCanvas();
        this.setupEventListeners();
    }

    setupCanvas() {
        this.canvas = document.getElementById('drawingCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.lineWidth = this.brushSize;
        
        this.copyingCanvas = document.getElementById('copyingCanvas');
        this.copyingCtx = this.copyingCanvas.getContext('2d');
        this.copyingCtx.lineCap = 'round';
        this.copyingCtx.lineJoin = 'round';
        this.copyingCtx.lineWidth = this.brushSize;
    }

    setupEventListeners() {
        // Shared event handler methods
        const handleMouseDown = (e) => this.startDrawing(e);
        const handleMouseMove = (e) => this.draw(e);
        const handleMouseUp = () => this.stopDrawing();
        const handleTouchStart = (e) => this.handleTouch(e);
        const handleTouchMove = (e) => this.handleTouch(e);
        const handleTouchEnd = () => this.stopDrawing();
        
        // Apply to both canvases
        [this.canvas, this.copyingCanvas].forEach(canvas => {
            if (!canvas) return;
            
            // Mouse events
            canvas.addEventListener('mousedown', handleMouseDown);
            canvas.addEventListener('mousemove', handleMouseMove);
            canvas.addEventListener('mouseup', handleMouseUp);
            canvas.addEventListener('mouseout', handleMouseUp);
            
            // Touch events
            canvas.addEventListener('touchstart', handleTouchStart);
            canvas.addEventListener('touchmove', handleTouchMove);
            canvas.addEventListener('touchend', handleTouchEnd);
        });
    }

    handleTouch(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const rect = e.target.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        
        if (e.type === 'touchstart') {
            this.startDrawing({offsetX: x, offsetY: y});
        } else if (e.type === 'touchmove') {
            this.draw({offsetX: x, offsetY: y});
        }
    }

    startDrawing(e) {
        this.isDrawing = true;
        this.currentStroke = [];
        const activeCanvas = this.getActiveCanvas();
        const activeCtx = this.getActiveContext();
        
        activeCtx.beginPath();
        activeCtx.moveTo(e.offsetX, e.offsetY);
        this.currentStroke.push({
            x: e.offsetX, 
            y: e.offsetY, 
            tool: this.currentTool, 
            color: this.currentColor
        });
    }

    draw(e) {
        if (!this.isDrawing) return;
        
        const activeCtx = this.getActiveContext();
        
        if (this.currentTool === GameConfig.TOOLS.BRUSH) {
            activeCtx.globalCompositeOperation = 'source-over';
            activeCtx.strokeStyle = this.currentColor;
        } else if (this.currentTool === GameConfig.TOOLS.ERASER) {
            activeCtx.globalCompositeOperation = 'destination-out';
        }
        
        activeCtx.lineWidth = this.brushSize;
        activeCtx.lineTo(e.offsetX, e.offsetY);
        activeCtx.stroke();
        
        this.currentStroke.push({
            x: e.offsetX, 
            y: e.offsetY, 
            tool: this.currentTool, 
            color: this.currentColor
        });
    }

    stopDrawing() {
        if (this.isDrawing) {
            this.strokes.push([...this.currentStroke]);
            this.currentStroke = [];
        }
        this.isDrawing = false;
    }

    clearCanvas() {
        const activeCanvas = this.getActiveCanvas();
        const activeCtx = this.getActiveContext();
        activeCtx.clearRect(0, 0, activeCanvas.width, activeCanvas.height);
        this.strokes = [];
    }

    undoStroke() {
        this.strokes.pop();
        this.redrawCanvas();
    }

    redrawCanvas() {
        const activeCanvas = this.getActiveCanvas();
        const activeCtx = this.getActiveContext();
        activeCtx.clearRect(0, 0, activeCanvas.width, activeCanvas.height);
        
        this.strokes.forEach(stroke => {
            if (stroke.length > 0) {
                activeCtx.beginPath();
                activeCtx.moveTo(stroke[0].x, stroke[0].y);
                
                stroke.forEach(point => {
                    if (point.tool === GameConfig.TOOLS.BRUSH) {
                        activeCtx.globalCompositeOperation = 'source-over';
                        activeCtx.strokeStyle = point.color;
                    } else if (point.tool === GameConfig.TOOLS.ERASER) {
                        activeCtx.globalCompositeOperation = 'destination-out';
                    }
                    activeCtx.lineWidth = this.brushSize;
                    activeCtx.lineTo(point.x, point.y);
                });
                activeCtx.stroke();
            }
        });
    }

    getActiveCanvas() {
        return gameStateManager.getPhase() === GameConfig.PHASES.COPYING ? this.copyingCanvas : this.canvas;
    }

    getActiveContext() {
        return gameStateManager.getPhase() === GameConfig.PHASES.COPYING ? this.copyingCtx : this.ctx;
    }

    submitDrawing(type) {
        const activeCanvas = type === 'original' ? this.canvas : this.copyingCanvas;
        const dataURL = activeCanvas.toDataURL('image/png');
        
        if (type === 'original') {
            drawingManager.submitDrawing();
        } else {
            copyingManager.submitCurrentCopy();
        }
    }

    getCanvasData() {
        const activeCanvas = this.getActiveCanvas();
        return activeCanvas.toDataURL('image/png');
    }

    resetCanvas() {
        this.strokes = [];
        this.currentStroke = [];
        this.isDrawing = false;
        this.clearCanvas();
    }

    cleanup() {
        this.resetCanvas();
        this.isDrawing = false;
        this.currentStroke = [];
        this.currentTool = GameConfig.TOOLS.BRUSH;
        this.currentColor = '#000000';
        this.brushSize = GameConfig.DEFAULT_BRUSH_SIZE;
        
        if (this.canvas && this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        if (this.copyingCanvas && this.copyingCtx) {
            this.copyingCtx.clearRect(0, 0, this.copyingCanvas.width, this.copyingCanvas.height);
        }
    }
}

const drawingCanvas = new DrawingCanvas();