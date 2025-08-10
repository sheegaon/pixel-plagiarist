// Main initialization and orchestration for Pixel Plagiarist
class PixelPlagiarist {
    constructor() {
        this.initialized = false;
        this.modules = new Map();
        this.eventListeners = [];
    }

    async init() {
        if (this.initialized) return;
        
        try {
            // Load configuration first before initializing modules
            await this.loadConfiguration();
            
            this.initializeModules();
            this.setupEventListeners();
            this.setupInitialState();
            
            this.initialized = true;
            console.log('Pixel Plagiarist initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Pixel Plagiarist:', error);
            if (window.uiManager) {
                uiManager.handleError(error, 'initialization');
            }
        }
    }

    async loadConfiguration() {
        // Try multiple possible paths for the config file
        const configPaths = [
            '/util/config.json',
            '/static/util/config.json',
            '/static/js/util/config.json'
        ];
        
        for (const path of configPaths) {
            try {
                const response = await fetch(path);
                if (response.ok) {
                    const configData = await response.json();
                    
                    // Update GameConfig with values from JSON
                    Object.keys(configData).forEach(key => {
                        if (GameConfig.hasOwnProperty(key)) {
                            GameConfig[key] = configData[key];
                            debug(`Updated ${key}: ${configData[key]}`);
                        }
                    });
                    
                    // Also update the TIMERS object for convenience
                    const newTimers = {
                        JOINING: configData.JOINING_TIMER || GameConfig.TIMERS.JOINING,
                        DRAWING: configData.DRAWING_TIMER || GameConfig.TIMERS.DRAWING,
                        COPYING: configData.COPYING_TIMER || GameConfig.TIMERS.COPYING,
                        VOTING: configData.VOTING_TIMER || GameConfig.TIMERS.VOTING,
                        REVIEW: configData.REVIEW_TIMER || GameConfig.TIMERS.REVIEW
                    };
                    
                    // Replace the TIMERS object instead of reassigning
                    Object.keys(newTimers).forEach(key => {
                        GameConfig.TIMERS[key] = newTimers[key];
                    });
                    
                    debug(`Configuration loaded successfully from ${path}`);
                    return;
                }
            } catch (error) {
                debug(`Failed to load config from ${path}: ${error.message}`);
            }
        }
        
        console.warn('Could not load configuration from any path. Using default values.');
    }

    initializeModules() {
        // Create gameManager first, then initialize its managers
        window.gameManager = new GameManager();
        window.gameManager.initializeManagers();
        
        const initOrder = [
            { name: 'socketHandler', instance: socketHandler, init: () => socketHandler.init() },
            { name: 'drawingCanvas', instance: drawingCanvas, init: () => drawingCanvas.init() },
            { name: 'uiManager', instance: uiManager, init: () => {
                uiManager.initResponsive();
                uiManager.setupKeyboardNavigation();
            }},
            { name: 'gameManager', instance: window.gameManager, init: () => {
                // Game manager and its sub-managers are now properly initialized
                // Just need to set up any initial UI state
                window.gameManager.updateBalanceDisplay();
            }}
        ];

        initOrder.forEach(module => {
            try {
                module.init();
                this.modules.set(module.name, module.instance);
                debug(`Initialized module: ${module.name}`);
            } catch (error) {
                console.error(`Failed to initialize ${module.name}:`, error);
                throw error;
            }
        });
    }

    setupEventListeners() {
        const addTrackedListener = (target, event, handler, options = {}) => {
            target.addEventListener(event, handler, options);
            this.eventListeners.push({ target, event, handler, options });
        };

        this.setupFormHandlers();
        
        const beforeUnloadHandler = () => this.cleanup();
        addTrackedListener(window, 'beforeunload', beforeUnloadHandler);
        
        const errorHandler = (event) => {
            if (window.uiManager) {
                uiManager.handleError(event.error, 'global error handler');
            }
        };
        addTrackedListener(window, 'error', errorHandler);
        
        const gameBeforeUnloadHandler = (event) => {
            if (gameManager.gamePhase !== GameConfig.PHASES.WAITING && 
                gameManager.currentRoom) {
                event.preventDefault();
                event.returnValue = 'You are currently in a game. Are you sure you want to leave?';
                return event.returnValue;
            }
        };
        addTrackedListener(window, 'beforeunload', gameBeforeUnloadHandler);

        const rejectionHandler = (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            if (window.uiManager) {
                uiManager.handleError(event.reason, 'unhandled promise rejection');
            }
        };
        addTrackedListener(window, 'unhandledrejection', rejectionHandler);
    }

    setupFormHandlers() {
        const roomCodeInput = document.getElementById('roomCodeInputModal');
        if (!roomCodeInput) {
            console.warn('Room code input not found during initialization');
            return;
        }
        
        const inputHandler = (e) => {
            e.target.value = e.target.value.toUpperCase();
        };
        roomCodeInput.addEventListener('input', inputHandler);
        this.eventListeners.push({ target: roomCodeInput, event: 'input', handler: inputHandler });
        
        const keypressHandler = (e) => {
            if (e.key === 'Enter') {
                if (uiManager.validateRoomForm()) {
                    gameManager.joinRoomByCode();
                }
            }
        };
        roomCodeInput.addEventListener('keypress', keypressHandler);
        this.eventListeners.push({ target: roomCodeInput, event: 'keypress', handler: keypressHandler });
    }

    setupInitialState() {
        // Ensure balance display is updated after all managers are initialized
        if (window.gameManager && window.gameManager.updateBalanceDisplay) {
            setTimeout(() => {
                window.gameManager.updateBalanceDisplay();
                debug(`Initial balance set to: ${GameConfig.INITIAL_BALANCE} Bits`);
            }, 10);
        }
        
        const stakeSlider = document.getElementById('stakeSlider');
        if (stakeSlider) {
            stakeSlider.dispatchEvent(new Event('input'));
        }
    }

    cleanup() {
        try {
            this.eventListeners.forEach(({ target, event, handler }) => {
                try {
                    target.removeEventListener(event, handler);
                } catch (error) {
                    console.warn('Error removing event listener:', error);
                }
            });
            this.eventListeners = [];

            const moduleCleanupOrder = ['gameManager', 'uiManager', 'drawingCanvas', 'socketHandler'];
            moduleCleanupOrder.forEach(moduleName => {
                const module = this.modules.get(moduleName);
                if (module && typeof module.cleanup === 'function') {
                    try {
                        module.cleanup();
                        debug(`Cleaned up module: ${moduleName}`);
                    } catch (error) {
                        console.warn(`Error cleaning up ${moduleName}:`, error);
                    }
                }
            });

            this.modules.clear();
            this.initialized = false;
            console.log('Application cleanup completed');
        } catch (error) {
            console.error('Error during cleanup:', error);
        }
    }

    getDebugInfo() {
        return {
            initialized: this.initialized,
            moduleCount: this.modules.size,
            eventListenerCount: this.eventListeners.length,
            gamePhase: gameManager ? gameManager.gamePhase : 'unknown',
            currentRoom: gameManager ? gameManager.currentRoom : null,
            playerId: gameManager ? gameManager.playerId : null,
            balance: gameManager ? gameManager.currentBalance : 0,
            copyTargets: gameManager ? gameManager.copyTargets.length : 0,
            canvasStrokes: drawingCanvas ? drawingCanvas.strokes.length : 0,
            activeTimers: uiManager ? uiManager.timers.size : 0,
            socketConnected: socketHandler ? socketHandler.connected : false
        };
    }

    quickJoin(roomCode) {
        const roomCodeInput = document.getElementById('roomCodeInputModal');
        if (roomCodeInput) {
            roomCodeInput.value = roomCode;
            gameManager.joinRoomByCode();
        }
    }

    reset() {
        try {
            this.cleanup();
            
            if (gameManager && typeof gameManager.returnHome === 'function') {
                gameManager.returnHome();
            }
            
            const roomCodeInput = document.getElementById('roomCodeInputModal');
            if (roomCodeInput) {
                roomCodeInput.value = '';
            }
            
            const stakeSlider = document.getElementById('stakeSlider');
            if (stakeSlider) {
                stakeSlider.value = '10';
                stakeSlider.dispatchEvent(new Event('input'));
            }
            
            this.init();
            
            console.log('Application reset completed');
        } catch (error) {
            console.error('Error during reset:', error);
        }
    }

    getModule(name) {
        return this.modules.get(name);
    }

    isModuleInitialized(name) {
        return this.modules.has(name);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    try {
        window.pixelPlagiarist = new PixelPlagiarist();
        window.pixelPlagiarist.init();
        
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.log('Debug mode enabled. Use pixelPlagiarist.getDebugInfo() for debugging.');
            window.debug = () => window.pixelPlagiarist.getDebugInfo();
        }
        else {
            window.debug = (message) => {};
        }
    } catch (error) {
        console.error('Critical initialization error:', error);
        document.body.innerHTML = `
            <div style="padding: 20px; background: #fee; border: 1px solid #fcc; margin: 10px;">
                <h2>Initialization Error</h2>
                <p>The application failed to initialize properly. Please refresh the page.</p>
                <details>
                    <summary>Error Details</summary>
                    <pre>${error.stack}</pre>
                </details>
            </div>
        `;
    }
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = PixelPlagiarist;
}