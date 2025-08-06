// Configuration and constants for Pixel Plagiarist
const GameConfig = {

    JOINING_TIMER: 0,
    DRAWING_TIMER: 0,
    COPYING_TIMER: 0,
    VOTING_TIMER: 0,
    REVIEW_TIMER: 0,
    MIN_PLAYERS: 0,
    MAX_PLAYERS: 0,
    MIN_STAKE: 0,
    MAX_STAKE: 0,
    INITIAL_BALANCE: 0,
    ENTRY_FEE: 0,

    TIMERS: {
        JOINING: 0,
        DRAWING: 0,
        COPYING: 0,
        VOTING: 0,
        REVIEW: 0
    },

    // Drawing settings
    DEFAULT_BRUSH_SIZE: 3,
    CANVAS_WIDTH: 400,
    CANVAS_HEIGHT: 300,
    
    // Drawing tools
    TOOLS: {
        BRUSH: 'brush',
        ERASER: 'eraser'
    },
    
    // Game phases
    PHASES: {
        WAITING: 'waiting',
        DRAWING: 'drawing',
        COPYING: 'copying',
        VOTING: 'voting',
        RESULTS: 'results'
    },
    
    // Default colors for the color picker
    COLORS: [
        '#000000', '#ff0000', '#00ff00', '#0000ff', '#ffff00',
        '#ff00ff', '#00ffff', '#ffa500', '#800080', '#8b4513'
    ]
};

// Export for use in other modules (only in Node.js environment)
if (typeof window === 'undefined' && typeof module !== 'undefined' && module.exports) {
    module.exports = GameConfig;
}