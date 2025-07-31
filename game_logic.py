# Core game logic for Pixel Plagiarist - Modular Architecture
import random
from datetime import datetime
from config import CONSTANTS, PROMPTS
from logging_utils import debug_log

# Import the modular components
from game_logic.game_timer import GameTimer
from game_logic.betting_phase import BettingPhase
from game_logic.drawing_phase import DrawingPhase
from game_logic.copying_phase import CopyingPhase
from game_logic.voting_phase import VotingPhase
from game_logic.scoring import ScoringEngine


class PixelPlagiarist:
    """
    Core game logic for a Pixel Plagiarist game room.
    
    Manages the complete game flow from waiting for players through final results,
    using a modular architecture with specialized phase handlers.
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
        self.phase = "waiting"
        self.prompt = None
        self.player_prompts = {}
        self.min_stake = min_stake
        self.max_players = CONSTANTS['max_players']
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
        self.timer = GameTimer(self)
        self.betting_phase = BettingPhase(self)
        self.drawing_phase = DrawingPhase(self)
        self.copying_phase = CopyingPhase(self)
        self.voting_phase = VotingPhase(self)
        self.scoring_engine = ScoringEngine(self)

    def add_player(self, player_id, username):
        """Add a new player to the game room."""
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
        """Remove a player from the game and handle cleanup."""
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
        """Start countdown for more players"""
        return self.timer.start_countdown(socketio)

    def start_game(self, socketio):
        """Start the game with current players."""
        if len(self.players) < self.min_players:
            debug_log("Cannot start game - insufficient players", None, self.room_id,
                      {'current_players': len(self.players), 'min_required': self.min_players})
            return

        self.phase = "betting"
        debug_log("Game started", None, self.room_id, {'player_count': len(self.players)})

        # Clear any existing timers using the flag system
        if self.start_timer:
            self._stop_countdown = True
            self.start_timer = None

        # Create a new default room since this one is now in progress
        from socket_handlers import check_and_create_default_room
        check_and_create_default_room(socketio)

        # Assign different random prompts to each player
        self._assign_player_prompts()

        debug_log("Game started with individual prompts", None, self.room_id,
                  {'player_count': len(self.players), 'betting_timer': self.timer.get_betting_timer()})

        # Send individual prompts to each player
        for player_id, prompt in self.player_prompts.items():
            socketio.emit('game_started', {
                'prompt': prompt,
                'min_stake': self.min_stake,
                'phase': 'betting',
                'timer': self.timer.get_betting_timer()
            }, to=player_id)

        # Start betting phase
        self.betting_phase.start_phase(socketio)

    def _assign_player_prompts(self):
        """Assign different random prompts to each player"""
        self.player_prompts = {}
        available_prompts = PROMPTS.copy()
        random.shuffle(available_prompts)
        
        for i, player_id in enumerate(self.players.keys()):
            # Use modulo to cycle through prompts if we have more players than prompts
            prompt_index = i % len(available_prompts)
            self.player_prompts[player_id] = available_prompts[prompt_index]

    # Phase-specific methods that delegate to specialized handlers
    def place_bet(self, player_id, stake, socketio):
        """Process a player's betting stake for the current round."""
        return self.betting_phase.place_bet(player_id, stake, socketio)

    def start_drawing_phase(self, socketio):
        """Start the drawing phase"""
        return self.drawing_phase.start_phase(socketio)

    def submit_original_drawing(self, player_id, drawing_data, socketio):
        """Accept and store a player's original drawing submission."""
        return self.drawing_phase.submit_drawing(player_id, drawing_data, socketio)

    def start_copying_phase(self, socketio):
        """Start the copying phase"""
        return self.copying_phase.start_phase(socketio)

    def submit_copied_drawing(self, player_id, target_id, drawing_data, socketio):
        """Accept and store a player's copied drawing submission."""
        return self.copying_phase.submit_copied_drawing(player_id, target_id, drawing_data, socketio)

    def start_voting_phase(self, socketio):
        """Start the voting phase"""
        return self.voting_phase.start_phase(socketio)

    def start_voting_on_set(self, socketio):
        """Start voting on current set"""
        return self.voting_phase.start_voting_on_set(socketio)

    def submit_vote(self, player_id, drawing_id, socketio):
        """Record a player's vote for which drawing they think is original."""
        return self.voting_phase.submit_vote(player_id, drawing_id, socketio)

    def next_voting_set(self, socketio):
        """Move to next voting set"""
        return self.voting_phase.next_voting_set(socketio)

    def calculate_results(self, socketio):
        """Calculate final scores and distribute tokens"""
        return self.scoring_engine.calculate_results(socketio)

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
        """
        if phase == 'betting':
            return self.betting_phase.check_early_advance(socketio)
        elif phase == 'drawing':
            return self.drawing_phase.check_early_advance(socketio)
        elif phase == 'copying':
            return self.copying_phase.check_early_advance(socketio)
        elif phase == 'voting':
            return self.voting_phase.check_early_advance(socketio)
        return False
