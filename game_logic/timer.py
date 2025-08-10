# Timer management for Pixel Plagiarist game phases
import time
import threading
from util.config import TIMER_CONFIG
from util.logging_utils import debug_log


class Timer:
    """
    Manages all timing functionality for game phases including countdown,
    phase timers, and early phase advancement checks.
    """
    
    def __init__(self, game):
        """
        Initialize the timer manager.
        
        Parameters
        ----------
        game : PixelPlagiarist
            Reference to the main game instance
        """
        self.game = game
        self.countdown_timer = None
        self.phase_timer = None
    
    def start_joining_countdown(self, socketio):
        """Start countdown for more players to join using configured timer"""
        # Prevent duplicate countdown starts
        if self.countdown_timer is not None:
            debug_log("Countdown already running, skipping duplicate start", None, self.game.room_id)
            return

        countdown_duration = TIMER_CONFIG['joining']
        
        debug_log("Starting joining countdown timer", None, self.game.room_id, {
            'countdown_seconds': countdown_duration,
            'player_count': len(self.game.players),
            'timer_type': 'joining_countdown'
        })
        
        # Set countdown start time for tracking
        import time
        self.game.countdown_start_time = time.time()
        
        # Start the countdown using threading.Timer
        self.countdown_timer = threading.Timer(countdown_duration, lambda: self._countdown_finished(socketio))
        self.countdown_timer.start()
        
        # Emit countdown to all players in room
        socketio.emit('joining_countdown_started', {
            'seconds': countdown_duration
        }, room=self.game.room_id)

    def stop_joining_countdown(self):
        """Stop the joining countdown timer"""
        debug_log("Stopping joining countdown", None, self.game.room_id, {
            'timer_was_active': self.countdown_timer is not None
        })
        
        if self.countdown_timer:
            self.countdown_timer.cancel()
            self.countdown_timer = None
        self.game.countdown_start_time = None

    def start_phase_timer(self, socketio, seconds, callback):
        """
        Start a countdown timer for the current game phase.
        
        Parameters
        ----------
        socketio : SocketIO
            Socket.IO instance for emitting events
        seconds : int
            Duration of the timer in seconds
        callback : callable
            Function to execute when timer expires
        """
        debug_log("Starting phase timer", None, self.game.room_id, {
            'duration_seconds': seconds,
            'phase': self.game.phase,
            'timer_type': 'phase_timer'
        })
        
        if self.phase_timer:
            debug_log("Cancelling existing phase timer before starting new one", None, self.game.room_id, {
                'previous_timer_active': True
            })
            self.phase_timer.cancel()
        
        # Use threading.Timer explicitly to avoid class name conflict
        self.phase_timer = threading.Timer(seconds, callback)
        self.phase_timer.start()

        socketio.emit('phase_timer', {'seconds': seconds}, room=self.game.room_id)

    def cancel_phase_timer(self):
        """Cancel the current phase timer with logging"""
        if self.phase_timer:
            debug_log("Cancelling phase timer", None, self.game.room_id, {
                'phase': self.game.phase,
                'timer_was_active': True
            })
            self.phase_timer.cancel()
            self.phase_timer = None
        else:
            debug_log("Attempted to cancel phase timer but no timer active", None, self.game.room_id, {
                'phase': self.game.phase
            })

    def _countdown_finished(self, socketio):
        """Handle countdown completion and start the game"""
        debug_log("Joining countdown completed - starting game", None, self.game.room_id, {
            'final_player_count': len(self.game.players)
        })
        
        # Clean up countdown timer
        self.countdown_timer = None
        self.game.countdown_start_time = None
        
        # Start the game
        self.game.start_game(socketio)

    @staticmethod
    def get_drawing_timer_duration():
        """Get drawing phase timer duration"""
        return TIMER_CONFIG['drawing']

    @staticmethod
    def get_copying_timer_duration():
        """Get copying phase timer duration"""
        return TIMER_CONFIG['copying']

    @staticmethod
    def get_voting_timer_duration():
        """Get voting phase timer duration"""
        return TIMER_CONFIG['voting']
