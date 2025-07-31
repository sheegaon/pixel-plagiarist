// UI management for Pixel Plagiarist
class UIManager {
    constructor() {
        this.currentView = 'home';
        // This manager should delegate to the main uiManager instance
        // since the main UI manager already handles screen management correctly
    }

    showView(viewName) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.showView) {
            window.uiManager.showView(viewName);
            this.currentView = viewName;
        }
    }

    getCurrentView() {
        return this.currentView;
    }

    showError(message, duration = 5000) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.showError) {
            window.uiManager.showError(message, duration);
        }
    }

    showSuccess(message, duration = 3000) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.showSuccess) {
            window.uiManager.showSuccess(message, duration);
        }
    }

    updateGameContent(content) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.updateGameContent) {
            window.uiManager.updateGameContent(content);
        }
    }

    enableElement(elementId) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.enableElement) {
            window.uiManager.enableElement(elementId);
        }
    }

    disableElement(elementId) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.disableElement) {
            window.uiManager.disableElement(elementId);
        }
    }

    showLoading(elementId) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.showLoading) {
            window.uiManager.showLoading(elementId);
        }
    }

    hideLoading(elementId) {
        // Delegate to the global uiManager instance
        if (window.uiManager && window.uiManager.hideLoading) {
            window.uiManager.hideLoading(elementId);
        }
    }

    reset() {
        this.showView('home');
        if (window.uiManager && window.uiManager.reset) {
            window.uiManager.reset();
        }
    }
}