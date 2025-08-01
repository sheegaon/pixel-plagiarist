# Core game state management for Pixel Plagiarist
import random
from datetime import datetime
from util.config import CONSTANTS, PROMPTS
from util.logging_utils import debug_log

# Import the modular components
from .timer import Timer
from .betting_phase import BettingPhase
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
    
    def __init__(self, room_id, min_stake=10):
        """
        Initialize a new game instance.
        
        Parameters
        ----------
        room_id : str
            Unique identifier for the game room
        min_stake : int, optional
            Minimum betting stake required for players, by default 10
        """
        self.room_id = room_id
        self.players = {}
        self.phase = "waiting"  # waiting, betting, drawing, copying_viewing, copying, voting, results
        self.prompt = None
        self.player_prompts = {}
        self.min_stake = min_stake
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

        # Countdown management
        self.start_timer = None
        self.countdown_timer = None
        self.countdown_start_time = None
        self._stop_countdown = False

        # Initialize modular components
        self.timer = Timer(self)
        self.betting_phase = BettingPhase(self)
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

        self.players[player_id] = {
            'id': player_id,
            'username': username,
            'balance': CONSTANTS['INITIAL_BALANCE'],
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
                  {'username': username, 'new_player_count': len(self.players)})

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
            del self.players[player_id]
            debug_log("Player removed from game", player_id, self.room_id,
                      {'username': username, 'players_remaining': len(self.players)})

        # Check if game should end due to insufficient players
        if len(self.players) < self.min_players and self.phase not in ["waiting", "results"]:
            debug_log("Ending game early - insufficient players", None, self.room_id,
                      {'players_remaining': len(self.players), 'min_required': self.min_players})
            self.end_game_early()

    def start_game(self, socketio):
        """Start the game with current players."""
        if len(self.players) < self.min_players:
            debug_log("Cannot start game - insufficient players", None, self.room_id,
                      {'current_players': len(self.players), 'min_required': self.min_players})
            return

        # Ensure countdown timer is stopped
        if self.timer:
            self.timer.stop_joining_countdown()

        # Debug log for phase transition
        debug_log("Transitioning to betting phase", None, self.room_id, {
            'current_phase': self.phase,
            'player_count': len(self.players)
        })

        # Update phase to betting
        self.phase = "betting"

        # Emit game started event to all players
        for player_id, prompt in self.player_prompts.items():
            socketio.emit('game_started', {
                'prompt': prompt,
                'min_stake': self.min_stake,
                'phase': 'betting',
                'timer': self.timer.get_betting_timer_duration()
            }, to=player_id)

        # Clear any existing timers using the flag system
        self.timer.stop_joining_countdown()

        # Create a new default room since this one is now in progress
        from socket_handlers import check_and_create_default_room
        check_and_create_default_room(socketio)

        # Assign different random prompts to each player
        self.player_prompts = {}
        available_prompts = PROMPTS.copy()
        random.shuffle(available_prompts)

        for i, player_id in enumerate(self.players.keys()):
            # Use modulo to cycle through prompts if we have more players than prompts
            prompt_index = i % len(available_prompts)
            self.player_prompts[player_id] = available_prompts[prompt_index]

        debug_log("Game started with individual prompts", None, self.room_id,
                  {'player_count': len(self.players), 'betting_timer': self.timer.get_betting_timer_duration()})

        # Send individual prompts to each player
        for player_id, prompt in self.player_prompts.items():
            socketio.emit('game_started', {
                'prompt': prompt,
                'min_stake': self.min_stake,
                'phase': 'betting',
                'timer': self.timer.get_betting_timer_duration()
            }, to=player_id)

        # Start betting phase
        self.betting_phase.start_phase(socketio)

    def end_game_early(self, socketio=None):
        """End game early due to insufficient players"""
        if len(self.players) < self.min_players:
            # Distribute remaining stakes equally
            remaining_players = list(self.players.keys())
            if remaining_players:
                total_stakes = sum(self.players[pid]['stake'] for pid in self.players if 'stake' in self.players[pid])
                stake_per_player = total_stakes // len(remaining_players) if remaining_players else 0

                for player_id in remaining_players:
                    self.players[player_id]['balance'] += stake_per_player

            self.phase = "ended_early"
            if socketio:
                socketio.emit('game_ended_early', {
                    'reason': 'Insufficient players',
                    'final_balance': {pid: self.players[pid]['balance'] for pid in self.players}
                }, room=self.room_id)
