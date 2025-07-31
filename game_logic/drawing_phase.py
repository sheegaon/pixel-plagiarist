# Drawing phase logic for Pixel Plagiarist
from logging_utils import debug_log


class DrawingPhase:
    """
    Handles all drawing phase logic including original drawing submissions,
    validation, and phase transitions.
    """
    
    def __init__(self, game):
        """
        Initialize the drawing phase handler.
        
        Parameters
        ----------
        game : PixelPlagiarist
            Reference to the main game instance
        """
        self.game = game

    def start_phase(self, socketio):
        """Start the drawing phase using configured timer"""
        debug_log("Starting drawing phase", None, self.game.room_id,
                  {'timer': self.game.timer.get_drawing_timer(), 'player_count': len(self.game.players)})

        self.game.phase = "drawing"

        # Set default stakes for players who didn't bet
        self.game.betting.apply_default_stakes()

        # Send individual prompts to each player
        for player_id, prompt in self.game.player_prompts.items():
            socketio.emit('phase_changed', {
                'phase': 'drawing',
                'prompt': prompt,
                'timer': self.game.timer.get_drawing_timer()
            }, to=player_id)

        self.game.timer.start_phase_timer(
            socketio, 
            self.game.timer.get_drawing_timer(), 
            lambda: self.game.start_copying_phase(socketio)
        )

    def submit_original_drawing(self, player_id, drawing_data, socketio):
        """Accept and store a player's original drawing submission."""
        debug_log("Player submitting original drawing", player_id, self.game.room_id,
                  {'phase': self.game.phase, 'data_length': len(drawing_data) if drawing_data else 0})

        if player_id in self.game.players and self.game.phase == "drawing":
            self.game.original_drawings[player_id] = drawing_data
            self.game.players[player_id]['has_drawn_original'] = True

            debug_log("Original drawing submitted successfully", player_id, self.game.room_id,
                      {'total_originals': len(self.game.original_drawings)})

            socketio.emit('drawing_submitted', {
                'player_id': player_id,
                'type': 'original'
            }, room=self.game.room_id)
            
            # Check if all players have drawn - advance early if so
            self.game.check_early_phase_advance('drawing', socketio)
            return True
        else:
            debug_log("Original drawing submission rejected", player_id, self.game.room_id,
                      {'phase': self.game.phase, 'player_exists': player_id in self.game.players})
            return False

    def check_early_advance(self, socketio):
        """Check if all players have drawn and advance early if possible"""
        all_drawn = all(player.get('has_drawn_original', False) for player in self.game.players.values())
        if all_drawn:
            debug_log("All players have drawn - advancing to copying phase early", None, self.game.room_id)
            # Cancel current timer
            self.game.timer.cancel_phase_timer()
            socketio.emit('early_phase_advance', {
                'next_phase': 'copying',
                'reason': 'All players have submitted their drawings'
            }, room=self.game.room_id)
            self.game.start_copying_phase(socketio)
            return True
        return False