# Timer management for Pixel Plagiarist game phases
import time
import threading
from config import TIMER_CONFIG
from logging_utils import debug_log


class GameTimer:
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
        self.start_timer = None
        self.countdown_timer = None
        self.phase_timer = None
    
    def start_countdown(self, socketio):
        """Start countdown for more players using configured timer"""
        debug_log("Starting countdown timer", None, self.game.room_id,
                  {'countdown_seconds': TIMER_CONFIG['countdown'], 'player_count': len(self.game.players)})

        # Store countdown start time for late joiners
        self.game.countdown_start_time = time.time()
        self.game._stop_countdown = False

        def countdown():
            for i in range(TIMER_CONFIG['countdown']):
                if self.game._stop_countdown:
                    debug_log("Countdown cancelled", None, self.game.room_id)
                    return
                time.sleep(1)
            
            if (self.game.phase == "waiting" and 
                len(self.game.players) >= self.game.min_players and 
                not self.game._stop_countdown):
                debug_log("Countdown completed - starting game", None, self.game.room_id,
                          {'final_player_count': len(self.game.players)})
                self.game.start_game(socketio)

        self.start_timer = threading.Thread(target=countdown)
        self.start_timer.daemon = True  # Make it a daemon thread
        self.start_timer.start()

        # Store reference for countdown cancellation in socket handlers
        self.countdown_timer = self.start_timer

        # Emit countdown to all players in the room
        socketio.emit('countdown_started', {'seconds': TIMER_CONFIG['countdown']}, room=self.game.room_id)

    def stop_countdown(self):
        """Stop the current countdown timer"""
        if self.start_timer:
            self.game._stop_countdown = True
            self.start_timer = None

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
        def timer():
            time.sleep(seconds)
            callback()

        if self.phase_timer:
            self.phase_timer = None

        self.phase_timer = threading.Thread(target=timer)
        self.phase_timer.start()

        socketio.emit('phase_timer', {'seconds': seconds}, room=self.game.room_id)

    def cancel_phase_timer(self):
        """Cancel the current phase timer"""
        if self.phase_timer:
            self.phase_timer = None

    def get_betting_timer(self):
        """Get betting phase timer duration"""
        return TIMER_CONFIG['betting']

    def get_drawing_timer(self):
        """Get drawing phase timer duration"""
        return TIMER_CONFIG['drawing']

    def get_copying_timer(self):
        """Get copying phase timer duration"""
        return TIMER_CONFIG['copying']

    def get_voting_timer(self):
        """Get voting phase timer duration"""
        return TIMER_CONFIG['voting']