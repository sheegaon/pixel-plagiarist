# Betting phase logic for Pixel Plagiarist
from logging_utils import debug_log


class BettingPhase:
    """
    Handles all betting phase logic including stake placement,
    validation, and phase transitions.
    """
    
    def __init__(self, game):
        """
        Initialize the betting phase handler.
        
        Parameters
        ----------
        game : PixelPlagiarist
            Reference to the main game instance
        """
        self.game = game

    def start_phase(self, socketio):
        """Start the betting phase"""
        self.game.phase = "betting"
        
        # Send individual prompts to each player
        for player_id, prompt in self.game.player_prompts.items():
            socketio.emit('game_started', {
                'prompt': prompt,
                'min_stake': self.game.min_stake,
                'phase': 'betting',
                'timer': self.game.timer.get_betting_timer()
            }, to=player_id)

        # Start betting timer
        self.game.timer.start_phase_timer(
            socketio, 
            self.game.timer.get_betting_timer(), 
            lambda: self.game.start_drawing_phase(socketio)
        )

    def place_bet(self, player_id, stake, socketio):
        """Process a player's betting stake for the current round."""
        debug_log("Player placing bet", player_id, self.game.room_id,
                  {'stake_requested': stake, 'min_stake': self.game.min_stake, 'phase': self.game.phase})

        if player_id in self.game.players and self.game.phase == "betting":
            original_stake = stake
            stake = max(stake, self.game.min_stake)
            old_balance = self.game.players[player_id]['balance']

            self.game.players[player_id]['stake'] = stake
            self.game.players[player_id]['balance'] -= stake
            self.game.players[player_id]['has_bet'] = True

            debug_log("Bet placed successfully", player_id, self.game.room_id, {
                'original_stake': original_stake,
                'final_stake': stake,
                'old_balance': old_balance,
                'new_balance': self.game.players[player_id]['balance']
            })

            socketio.emit('bet_placed', {
                'player_id': player_id,
                'stake': stake,
                'remaining_tokens': self.game.players[player_id]['balance']
            }, room=self.game.room_id)
            
            # Check if all players have bet - advance early if so
            self.game.check_early_phase_advance('betting', socketio)
        else:
            debug_log("Bet rejected - invalid conditions", player_id, self.game.room_id,
                      {'phase': self.game.phase, 'player_exists': player_id in self.game.players})

    def check_early_advance(self, socketio):
        """Check if all players have bet and advance early if possible"""
        all_bet = all(player.get('has_bet', False) for player in self.game.players.values())
        if all_bet:
            debug_log("All players have bet - advancing to drawing phase early", None, self.game.room_id)
            # Cancel current timer
            self.game.timer.cancel_phase_timer()
            socketio.emit('early_phase_advance', {
                'next_phase': 'drawing',
                'reason': 'All players have placed their bets'
            }, room=self.game.room_id)
            self.game.start_drawing_phase(socketio)
            return True
        return False

    def apply_default_stakes(self):
        """Apply default stakes for players who didn't bet"""
        default_stakes_applied = 0
        for player in self.game.players.values():
            if player['stake'] == 0:
                player['stake'] = self.game.min_stake
                player['balance'] -= self.game.min_stake
                default_stakes_applied += 1

        debug_log("Applied default stakes to unbetting players", None, self.game.room_id,
                  {'default_stakes_applied': default_stakes_applied, 'min_stake': self.game.min_stake})
        
        return default_stakes_applied