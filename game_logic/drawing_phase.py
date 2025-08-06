# Drawing phase logic for Pixel Plagiarist
from util.logging_utils import debug_log, save_drawing


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
                  {'timer': self.game.timer.get_drawing_timer_duration(), 'player_count': len(self.game.players)})
        self.game.phase = "drawing"

        # Apply stakes
        for player in self.game.players.values():
            if player['stake'] == 0:
                player['stake'] = self.game.prize_per_player
                player['balance'] -= self.game.prize_per_player
                debug_log("Applied stake", player['id'], self.game.room_id, {
                    'stake': player['stake'],
                    'new_balance': player['balance']
                })

        # Emit individual phase change events with prompts to each player
        for player_id in self.game.players:
            player_prompt = self.game.player_prompts.get(player_id, "Draw something creative!")
            socketio.emit('phase_changed', {
                'phase': 'drawing',
                'prompt': player_prompt,
                'timer': self.game.timer.get_drawing_timer_duration()
            }, to=player_id)

        self.game.timer.start_phase_timer(
            socketio, 
            self.game.timer.get_drawing_timer_duration(),
            lambda: self.game.copying_phase.start_phase(socketio)
        )

    def submit_drawing(self, player_id, drawing_data, socketio, check_early_advance=True):
        """Accept and store a player's original drawing submission."""
        debug_log("Player submitting original drawing", player_id, self.game.room_id,
                  {'phase': self.game.phase, 'data_length': len(drawing_data) if drawing_data else 0})

        # Validate phase
        if self.game.phase != "drawing":
            debug_log("Drawing submission rejected - wrong phase", player_id, self.game.room_id, {
                'current_phase': self.game.phase
            })
            return False

        # Validate player exists
        if player_id not in self.game.players:
            debug_log("Drawing submission rejected - player not in game", player_id, self.game.room_id)
            return False

        # Prevent duplicate submissions
        if self.game.players[player_id]['has_drawn_original']:
            debug_log("Drawing submission rejected - already submitted", player_id, self.game.room_id)
            return False

        # Save image to logs for debugging
        image_path = save_drawing(drawing_data, player_id, self.game.room_id, 'original')

        self.game.original_drawings[player_id] = drawing_data
        self.game.players[player_id]['has_drawn_original'] = True

        debug_log("Original drawing submitted successfully", player_id, self.game.room_id, {
            'total_drawings': len(self.game.original_drawings),
            'total_players': len(self.game.players),
            'image_saved_to': image_path
        })

        socketio.emit('original_submitted', {
            'player_id': player_id,
            'total_submitted': len(self.game.original_drawings),
            'total_players': len(self.game.players)
        }, room=self.game.room_id)

        # Check if all players have drawn - advance early if so
        if check_early_advance:
            self.check_early_advance(socketio)
        return True

    def check_early_advance(self, socketio):
        """Check if all players have drawn and advance early if possible"""
        all_drawn = all(player.get('has_drawn_original', False) for player in self.game.players.values())
        
        players_status = {pid: player.get('has_drawn_original', False) for pid, player in self.game.players.items()}
        debug_log("Checking early advance from drawing phase", None, self.game.room_id, {
            'all_players_drawn': all_drawn,
            'drawings_submitted': len(self.game.original_drawings),
            'total_players': len(self.game.players),
            'players_status': players_status
        })
        
        if all_drawn:
            debug_log("All players have drawn - advancing to copying phase early", None, self.game.room_id)
            # Cancel current timer
            self.game.timer.cancel_phase_timer()
            socketio.emit('early_phase_advance', {
                'next_phase': 'copying',
                'reason': 'All players have submitted their drawings'
            }, room=self.game.room_id)
            self.game.copying_phase.start_phase(socketio)
            return True
        return False
