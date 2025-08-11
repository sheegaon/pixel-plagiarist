# Core game state management for Pixel Plagiarist
import random
from datetime import datetime
from util.config import CONSTANTS, PROMPTS
from util.logging_utils import debug_log
from util.db import get_or_create_player, update_player_balance

# Import the modular components
from .timer import Timer
from .drawing_phase import DrawingPhase
from .copying_phase import CopyingPhase
from .voting_phase import VotingPhase
from .scoring_engine import ScoringEngine


class GameStateGL:
    """
    Core game logic for a Pixel Plagiarist game room.
    
    Manages the complete game flow from waiting for players through final results,
    coordinating with specialized phase handlers for each game stage.
    """
    
    def __init__(self, room_id, prize_per_player=CONSTANTS['MIN_STAKE'], entry_fee=CONSTANTS['ENTRY_FEE']):
        """
        Initialize a new game instance.
        
        Parameters
        ----------
        room_id : str
            Unique identifier for the game room
        prize_per_player : int, optional
            Player's contribution to the prize pool, default is minimum stake
        """
        self.room_id = room_id
        self.players = {}
        self.phase = "waiting"  # waiting, drawing, copying, voting, results
        self.prompt = None
        self.player_prompts = {}
        self.prize_per_player = prize_per_player
        self.entry_fee = entry_fee
        self.max_players = CONSTANTS['MAX_PLAYERS']
        self.min_players = 3

        # Game state
        self.original_drawings = {}
        self.copied_drawings = {}
        self.copy_assignments = {}
        self.votes = {}
        self.idx_current_drawing_set = 0
        self.drawing_sets = []
        self.created_at = datetime.now()
        self.percentage_penalties = {}

        # Player balance tracking for this game session
        self.player_balances_before_game = {}

        # Countdown management
        self.countdown_timer = None
        self.countdown_start_time = None
        self._stop_countdown = False

        # Initialize modular components
        self.timer = Timer(self)
        self.drawing_phase = DrawingPhase(self)
        self.copying_phase = CopyingPhase(self)
        self.voting_phase = VotingPhase(self)
        self.scoring_engine = ScoringEngine(self)

    def add_player(self, player_id, username):
        """
        Add a new player to the game room.
        
        Attempts to add a player to the game if there's space available.
        Automatically triggers game countdown or start based on player count.
        
        Parameters
        ----------
        player_id : str
            Unique identifier for the player (typically socket session ID)
        username : str
            Display name chosen by the player
            
        Returns
        -------
        bool
            True if player was successfully added, False if room is full
        """
        if not isinstance(username, str):
            debug_log("Invalid username type", player_id, self.room_id, {'username_type': type(username)})
            return False
        
        username = username.strip()
        if not username:
            debug_log("Empty username provided", player_id, self.room_id)
            return False
        
        import re
        username = re.sub(r'[^\w\s\-]', '', username)  # allow alphanum, underscore, space, dash
        username = username[:32]  # Limit length

        debug_log("Player attempting to join game", player_id, self.room_id,
                  {'username': username, 'current_players': len(self.players), 'phase': self.phase})

        # Prevent duplicate additions
        if player_id in self.players:
            debug_log("Player already in game, updating username only", player_id, self.room_id,
                      {'old_username': self.players[player_id]['username'], 'new_username': username})
            self.players[player_id]['username'] = username
            return True

        if len(self.players) >= self.max_players:
            debug_log("Player join rejected - room full", player_id, self.room_id, {'max_players': self.max_players})
            return False

        try:
            # Get or create player from database using username
            db_player = get_or_create_player(username)
        except Exception as e:
            debug_log("Failed to add player to game", player_id, self.room_id,
                      {'error': str(e), 'username': username})
            return False

        if db_player['balance'] < self.prize_per_player + self.entry_fee:
            debug_log("Player balance too low to join game", player_id, self.room_id,
                      {'balance': db_player['balance'], 'required': self.prize_per_player + self.entry_fee})
            return False

        # Store the player's balance before the game starts for tracking
        self.player_balances_before_game[player_id] = db_player['balance']

        # Create in-memory player state for this game session
        self.players[player_id] = {
            'id': player_id,
            'username': username,
            'balance': db_player['balance'],  # Initial balance from database
            'stake': 0,
            'connected': True,
            'has_drawn_original': False,
            'has_copied': False,
            'copies_to_make': [],
            'completed_copies': 0,
            'votes_cast': 0,
            'has_bet': False
        }

        debug_log("Player successfully added to game", player_id, self.room_id,
                  {'username': username, 'new_player_count': len(self.players),
                   'balance': db_player['balance']})

        return True
            
    def remove_player(self, player_id):
        """
        Remove a player from the game and handle cleanup.
        
        Parameters
        ----------
        player_id : str
            Unique identifier of the player to remove
        """
        debug_log("Player disconnecting from game", player_id, self.room_id,
                  {'players_before': len(self.players), 'phase': self.phase})

        if player_id in self.players:
            username = self.players[player_id]['username']
            
            # If game is in progress, update their balance in the database
            if self.phase not in ["waiting", "results"]:
                current_balance = self.players[player_id]['balance']
                try:
                    update_player_balance(username, current_balance)
                    debug_log("Updated player balance on disconnect", player_id, self.room_id,
                              {'username': username, 'balance': current_balance})
                except Exception as e:
                    debug_log("Failed to update player balance on disconnect", player_id, self.room_id,
                              {'error': str(e), 'username': username})
            
            del self.players[player_id]
            debug_log("Player removed from game", player_id, self.room_id,
                      {'username': username, 'players_remaining': len(self.players)})

        # Check if game should end due to insufficient players
        if len(self.players) < self.min_players and self.phase not in ["waiting", "results"]:
            debug_log("Ending game early - insufficient players", None, self.room_id,
                      {'players_remaining': len(self.players), 'min_required': self.min_players,
                       'removal_source': 'game_state_remove_player'})
            self.end_game_early()

    def start_game(self, socketio):
        """Start the game with current players."""
        if len(self.players) < self.min_players:
            debug_log("Cannot start game - insufficient players", None, self.room_id,
                      {'current_players': len(self.players), 'min_required': self.min_players})
            return

        debug_log("Game phase transition", None, self.room_id, {
            'from_phase': self.phase,
            'to_phase': 'drawing',
            'trigger': 'start_game',
            'player_count': len(self.players)
        })

        # Store initial balances for all players and deduct fee before game starts
        for player_id in self.players:
            self.player_balances_before_game[player_id] = self.players[player_id]['balance']
            # Deduct the game entry fee from each player's balance
            self.players[player_id]['balance'] -= self.entry_fee
            debug_log("Deducted entry fee", player_id, self.room_id,
                      {'entry_fee': self.entry_fee, 'new_balance': self.players[player_id]['balance']})

        # Ensure joining countdown timer is stopped
        self.timer.stop_joining_countdown()
        
        # Reset per-game state for a fresh start
        self.original_drawings = {}
        self.copied_drawings = {}
        self.copy_assignments = {}
        self.votes = {}
        self.idx_current_drawing_set = 0
        self.drawing_sets = []
        self.percentage_penalties = {}
        
        # Reset phase handlers for new game
        self.copying_phase.reset_for_new_game()
        self.voting_phase.reset_for_new_game()
        self.scoring_engine.results_calculated = False
        
        # Update phase to drawing
        self.phase = "drawing"

        # Assign different random prompts to each player
        self.player_prompts = {}
        available_prompts = PROMPTS.copy()
        random.shuffle(available_prompts)

        for i, player_id in enumerate(self.players.keys()):
            # Use modulo to cycle through prompts if we have more players than prompts
            prompt_index = i % len(available_prompts)
            self.player_prompts[player_id] = available_prompts[prompt_index]

        debug_log("Game started with individual prompts", None, self.room_id,
                  {'player_count': len(self.players), 'drawing_timer': self.timer.get_drawing_timer_duration()})

        # Start drawing phase (clients will receive prompts within the phase_changed broadcast)
        self.drawing_phase.start_phase(socketio)

        # Create a new default room since this one is now in progress
        from socket_handlers import check_and_create_default_room
        check_and_create_default_room(socketio)

    def end_game_early(self, socketio=None):
        """End game early due to insufficient players"""
        # Cancel all active timers to prevent further phase transitions
        if hasattr(self, 'timer'):
            self.timer.cancel_phase_timer()
            self.timer.stop_joining_countdown()
        
        if len(self.players) < self.min_players:
            remaining_players = list(self.players.keys())
            
            # Return stakes to all players (but keep entry fee deducted)
            for player_id in remaining_players:
                stake = self.players[player_id].get('stake', 0)
                if stake > 0:
                    # Return the stake amount to player's balance
                    self.players[player_id]['balance'] += stake
                    debug_log("Returned stake for early game end", player_id, self.room_id, {
                        'stake_returned': stake,
                        'new_balance': self.players[player_id]['balance']
                    })

            # Save player balances to database
            try:
                from util.db import update_player_balance, record_game_completion
                
                for player_id, player_data in self.players.items():
                    username = player_data['username']
                    balance_before = self.player_balances_before_game.get(player_id, player_data['balance'])
                    balance_after = player_data['balance']
                    stake = player_data.get('stake', 0)
                    
                    # Update balance in database
                    update_player_balance(username, balance_after)
                    
                    # Record game completion with early end stats
                    record_game_completion(
                        username=username,
                        room_id=self.room_id,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        stake=stake,
                        points_earned=0,  # No points for early end
                        originals_drawn=1 if player_id in self.original_drawings else 0,
                        copies_made=0,  # No copies in early end
                        votes_cast=0,   # No votes in early end
                        correct_votes=0
                    )
                    
                    debug_log("Saved player data for early game end", player_id, self.room_id, {
                        'username': username,
                        'balance_change': balance_after - balance_before,
                        'stake_returned': stake
                    })
                    
            except Exception as e:
                debug_log("Failed to save player data on early game end", None, self.room_id, {
                    'error': str(e)
                })

            self.phase = "ended_early"
            if socketio:
                socketio.emit('game_ended_early', {
                    'reason': 'Insufficient players',
                    'final_balances': {pid: self.players[pid]['balance'] for pid in self.players},
                    'stakes_returned': True
                }, room=self.room_id)

    def room_level(self):
        if self.prize_per_player == CONSTANTS['MIN_STAKE']:
            return 'Bronze'
        elif self.prize_per_player == CONSTANTS['MAX_STAKE']:
            return 'Gold'
        else:
            print(self.prize_per_player)
            return 'Silver'
