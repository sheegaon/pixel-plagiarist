# Betting phase logic for Pixel Plagiarist
from util.logging_utils import debug_log


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
                'timer': self.game.timer.get_betting_timer_duration()
            }, to=player_id)

        # Start betting timer
        self.game.timer.start_phase_timer(
            socketio, 
            self.game.timer.get_betting_timer_duration(),
            lambda: self.game.drawing_phase.start_phase(socketio)
        )

    def place_bet(self, player_id, stake, socketio, check_early_advance=True):
        """Record a player's betting stake."""
        debug_log("Player placing bet", player_id, self.game.room_id, {
            'stake': stake,
            'phase': self.game.phase,
            'min_stake': self.game.min_stake
        })

        # Validate phase
        if self.game.phase != "betting":
            debug_log("Bet submission rejected - wrong phase", player_id, self.game.room_id, {
                'current_phase': self.game.phase,
                'stake': stake
            })
            return False

        # Validate player exists
        if player_id not in self.game.players:
            debug_log("Bet submission rejected - player not in game", player_id, self.game.room_id, {
                'stake': stake
            })
            return False

        # Prevent duplicate betting
        if self.game.players[player_id]['has_bet']:
            debug_log("Bet submission rejected - already placed bet", player_id, self.game.room_id, {
                'existing_stake': self.game.players[player_id]['stake'],
                'new_stake': stake
            })
            return False

        # Validate stake amount
        if stake < self.game.min_stake:
            debug_log("Bet submission rejected - stake too low", player_id, self.game.room_id, {
                'stake': stake,
                'min_stake': self.game.min_stake
            })
            return False

        if stake > self.game.players[player_id]['balance']:
            debug_log("Bet submission rejected - insufficient balance", player_id, self.game.room_id, {
                'stake': stake,
                'balance': self.game.players[player_id]['balance']
            })
            return False

        # Deduct stake from balance and record bet
        self.game.players[player_id]['balance'] -= stake
        self.game.players[player_id]['stake'] = stake
        self.game.players[player_id]['has_bet'] = True

        debug_log("Bet placed successfully", player_id, self.game.room_id, {
            'stake': stake,
            'new_balance': self.game.players[player_id]['balance'],
            'players_bet': sum(1 for p in self.game.players.values() if p['has_bet']),
            'total_players': len(self.game.players)
        })

        socketio.emit('bet_placed', {
            'player_id': player_id,
            'stake': stake,
            'new_balance': self.game.players[player_id]['balance']
        }, room=self.game.room_id)

        # Check if all players have bet - advance early if so
        if check_early_advance:
            self.check_early_advance(socketio)
        return True

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
            self.game.drawing_phase.start_phase(socketio)
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
