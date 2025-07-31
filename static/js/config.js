// Configuration and constants for Pixel Plagiarist
const GameConfig = {
    // Drawing settings
    DEFAULT_BRUSH_SIZE: 3,
    CANVAS_WIDTH: 400,
    CANVAS_HEIGHT: 300,
    
    // Game timing (in seconds)
    TIMERS: {
        BETTING: 10,
        DRAWING: 60,
        COPYING: 60,
        VOTING: 10,
        REVIEW: 5,
        COUNTDOWN: 20
    },
    
    // Game constraints
    MIN_PLAYERS: 3,
    MAX_PLAYERS: 12,
    MIN_STAKE: 10,
    MAX_STAKE: 100,
    STARTING_BALANCE: 100,
    
    // Drawing tools
    TOOLS: {
        BRUSH: 'brush',
        ERASER: 'eraser'
    },
    
    // Game phases
    PHASES: {
        WAITING: 'waiting',
        BETTING: 'betting',
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

// Debug function for development
function debug(...args) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('[DEBUG]', ...args);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameConfig;
}