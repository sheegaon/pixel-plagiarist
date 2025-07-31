# Core game state management for Pixel Plagiarist
import random
from datetime import datetime
from config import CONSTANTS, PROMPTS
from logging_utils import debug_log
from .game_timer import GameTimer
from .betting_phase import BettingPhase
from .drawing_phase import DrawingPhase
from .copying_phase import CopyingPhase
from .voting_phase import VotingPhase
from .scoring import ScoringEngine


class PixelPlagiarist:
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
        self.phase = "waiting"  # waiting, betting, drawing, copying, voting, results
        self.prompt = None
        self.player_prompts = {}
        self.min_stake = min_stake
        self.max_players = CONSTANTS['max_players']
        self.min_players = 3
        self.original_drawings = {}
        self.copied_drawings = {}
        self.copy_assignments = {}
        self.votes = {}
        self.idx_current_drawing_set = 0
        self.drawing_sets = []
        self.created_at = datetime.now()
        self.countdown_start_time = None
        self._stop_countdown = False  # Flag to stop countdown

        # Initialize phase handlers
        self.timer = GameTimer(self)
        self.betting = BettingPhase(self)
        self.drawing = DrawingPhase(self)
        self.copying = CopyingPhase(self)
        self.voting = VotingPhase(self)
        self.scoring = ScoringEngine(self)

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

        if len(self.players) >= self.max_players:
            debug_log("Player join rejected - room full", player_id, self.room_id, {'max_players': self.max_players})
            return False

        self.players[player_id] = {
            'id': player_id,
            'username': username,
            'balance': CONSTANTS['initial_balance'],
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

    def start_countdown(self, socketio):
        """Start countdown for more players using configured timer"""
        self.timer.start_countdown(socketio)

    def start_game(self, socketio):
        """Start the game with current players."""
        if len(self.players) < self.min_players:
            debug_log("Cannot start game - insufficient players", None, self.room_id,
                      {'current_players': len(self.players), 'min_required': self.min_players})
            return

        self.phase = "betting"
        debug_log("Game started", None, self.room_id, {'player_count': len(self.players)})

        # Clear any existing timers using the flag system
        self.timer.stop_countdown()

        # Create a new default room since this one is now in progress
        from socket_handlers import check_and_create_default_room
        check_and_create_default_room(socketio)

        # Assign different random prompts to each player
        self._assign_prompts()

        debug_log("Game started with individual prompts", None, self.room_id,
                  {'player_count': len(self.players), 'betting_timer': self.timer.get_betting_timer()})

        # Start betting phase
        self.betting.start_phase(socketio)

    def _assign_prompts(self):
        """Assign different random prompts to each player"""
        self.player_prompts = {}
        available_prompts = PROMPTS.copy()
        random.shuffle(available_prompts)
        
        for i, player_id in enumerate(self.players.keys()):
            # Use modulo to cycle through prompts if we have more players than prompts
            prompt_index = i % len(available_prompts)
            self.player_prompts[player_id] = available_prompts[prompt_index]

    def place_bet(self, player_id, stake, socketio):
        """Process a player's betting stake for the current round."""
        return self.betting.place_bet(player_id, stake, socketio)

    def start_drawing_phase(self, socketio):
        """Start the drawing phase using configured timer"""
        self.drawing.start_phase(socketio)

    def submit_original_drawing(self, player_id, drawing_data, socketio):
        """Accept and store a player's original drawing submission."""
        return self.drawing.submit_original_drawing(player_id, drawing_data, socketio)

    def start_copying_phase(self, socketio):
        """Start the copying phase with 10-second viewing period"""
        self.copying.start_phase(socketio)

    def submit_copied_drawing(self, player_id, target_id, drawing_data, socketio):
        """Accept and store a player's copied drawing submission."""
        return self.copying.submit_copied_drawing(player_id, target_id, drawing_data, socketio)

    def start_voting_phase(self, socketio):
        """Start the voting phase"""
        self.voting.start_phase(socketio)

    def start_voting_on_set(self, socketio):
        """Start voting on current set using configured timer"""
        return self.voting.start_voting_on_set(socketio)

    def submit_vote(self, player_id, drawing_id, socketio):
        """Record a player's vote for which drawing they think is original."""
        return self.voting.submit_vote(player_id, drawing_id, socketio)

    def next_voting_set(self, socketio):
        """Move to next voting set"""
        return self.voting.next_voting_set(socketio)

    def calculate_results(self, socketio):
        """Calculate final scores and distribute tokens"""
        return self.scoring.calculate_results(socketio)

    def distribute_tokens(self, scores):
        """Distribute token rewards based on final scores"""
        return self.scoring.distribute_tokens(scores)

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

    def check_early_phase_advance(self, phase, socketio):
        """
        Check if all players have completed their actions for the current phase
        and advance early if possible.
        
        Parameters
        ----------
        phase : str
            The current phase to check ('betting', 'drawing', 'copying', 'voting')
        socketio : SocketIO
            Socket.IO instance for emitting events
        """
        if phase == 'betting':
            return self.betting.check_early_advance(socketio)
        elif phase == 'drawing':
            return self.drawing.check_early_advance(socketio)
        elif phase == 'copying':
            return self.copying.check_early_advance(socketio)
        elif phase == 'voting':
            return self.voting.check_early_advance(socketio)
