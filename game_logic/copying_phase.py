# Copying phase logic for Pixel Plagiarist
import random
from util.logging_utils import debug_log, save_drawing
import time


class CopyingPhase:
    """
    Handles all copying phase logic including copy assignments,
    submissions, and phase transitions.
    """
    
    def __init__(self, game):
        """
        Initialize the copying phase handler.
        
        Parameters
        ----------
        game : PixelPlagiarist
            Reference to the main game instance
        """
        self.game = game
        self.phase_started = False  # Prevent duplicate phase starts
        self.assignments_made = False  # Prevent duplicate assignments
        self.phase_start_time = None  # Track when copying phase started

    def start_phase(self, socketio):
        """Start the copying phase with immediate review overlay"""
        # Check if game has ended early - if so, don't start copying phase
        if self.game.phase == "ended_early":
            debug_log("Skipping copying phase - game has ended early", None, self.game.room_id)
            return
            
        # Allow restarting for new games - only prevent duplicate calls within same game
        if self.phase_started and self.game.phase == "copying":
            debug_log("Copying phase already started, skipping duplicate call", None, self.game.room_id)
            return

        debug_log("Starting copying phase", None, self.game.room_id,
                  {'timer': self.game.timer.get_copying_timer_duration(), 'player_count': len(self.game.players)})

        self.game.phase = "copying"
        self.phase_started = True
        
        # Set phase start time for early advance checking
        self.phase_start_time = time.time()

        # Assign copying tasks - only once per game
        if not self.assignments_made:
            self._assign_copying_tasks()
            self.assignments_made = True

        # Reset copy progress for this copying phase
        for pid in self.game.players:
            self.game.players[pid]['completed_copies'] = 0
        # Clear any previous copied drawings from earlier phases/games
        self.game.copied_drawings = {}

        # Send assignments to players and start copying immediately
        self._send_copying_phase(socketio)

        # Set copying timer
        self.game.timer.start_phase_timer(
            socketio, 
            self.game.timer.get_copying_timer_duration(),
            lambda: self.game.voting_phase.start_phase(socketio)
        )

    def _assign_copying_tasks(self):
        """Assign copying tasks to players"""
        player_ids = list(self.game.players.keys())
        random.shuffle(player_ids)

        num_players = len(player_ids)
        copies_per_player = 1 if num_players == 3 else 2

        debug_log("Assigning copying tasks", None, self.game.room_id,
                  {'num_players': num_players, 'copies_per_player': copies_per_player})

        # Clear previous assignments
        self.game.copy_assignments = {}

        for p, pid in enumerate(player_ids):
            self.game.copy_assignments[pid] = []
            for i in range(copies_per_player):
                self.game.copy_assignments[pid].append(player_ids[(p + 1 + i) % num_players])
            
            # Set copies_to_make for each player so we can track progress properly
            self.game.players[pid]['copies_to_make'] = self.game.copy_assignments[pid].copy()
        
        # Log final assignments
        for player_id in player_ids:
            targets = self.game.copy_assignments.get(player_id, [])
            debug_log("Copying assignment created", player_id, self.game.room_id,
                      {'targets': targets, 'target_count': len(targets)})

    def _send_copying_phase(self, socketio):
        """Send copying phase data to players with first drawing for review"""
        for player_id, target_ids in self.game.copy_assignments.items():
            target_drawings = []
            for target_id in target_ids:
                if target_id in self.game.original_drawings:
                    target_drawings.append({
                        'target_id': target_id,
                        'drawing': self.game.original_drawings[target_id]
                    })

            debug_log("Sending copying phase to player", player_id, self.game.room_id,
                      {'target_count': len(target_drawings)})

            socketio.emit('copying_phase', {
                'targets': target_drawings,
                'timer': self.game.timer.get_copying_timer_duration()
            }, to=player_id)

        socketio.emit('phase_changed', {
            'phase': 'copying',
            'timer': self.game.timer.get_copying_timer_duration()
        }, room=self.game.room_id)

    def submit_drawing(self, player_id, target_id, drawing_data, socketio, check_early_advance=True):
        """Accept and store a player's copied drawing submission."""
        debug_log("Player submitting copied drawing", player_id, self.game.room_id,
                  {'target_id': target_id, 'phase': self.game.phase,
                   'data_length': len(drawing_data) if drawing_data else 0})

        if player_id in self.game.players and self.game.phase == "copying":
            if player_id not in self.game.copied_drawings:
                self.game.copied_drawings[player_id] = {}

            # Save image to logs for debugging
            image_path = save_drawing(drawing_data, player_id, self.game.room_id, 'copy', target_id)

            self.game.copied_drawings[player_id][target_id] = drawing_data
            self.game.players[player_id]['completed_copies'] += 1

            debug_log("Copied drawing submitted successfully", player_id, self.game.room_id, {
                'target_id': target_id,
                'completed_copies': self.game.players[player_id]['completed_copies'],
                'total_required': len(self.game.players[player_id]['copies_to_make']),
                'image_saved_to': image_path
            })

            socketio.emit('copy_submitted', {
                'player_id': player_id,
                'target_id': target_id,
                'completed': self.game.players[player_id]['completed_copies'],
                'total': len(self.game.players[player_id]['copies_to_make'])
            }, room=self.game.room_id)
            
            # Check if all players have completed copying - advance early if so
            if check_early_advance:
                self.check_early_advance(socketio)
            return True
        else:
            debug_log(
                "Copied drawing submission rejected", player_id, self.game.room_id,
                {'target_id': target_id, 'phase': self.game.phase, 'player_exists': player_id in self.game.players})
            return False

    def check_early_advance(self, socketio):
        """Check if all players have completed copying and advance early if possible"""
        # Calculate completion status for each player
        player_completion = {}
        for player_id, player in self.game.players.items():
            completed = player.get('completed_copies', 0)
            copies_list = player.get('copies_to_make', [])
            # Only count targets that actually have an original drawing available
            valid_targets = [tid for tid in copies_list if tid in self.game.original_drawings]
            required = len(valid_targets)
            player_completion[player_id] = {
                'completed': completed,
                'required': required,
                'finished': completed >= required
            }
        
        all_copied = all(status['finished'] for status in player_completion.values())
        
        debug_log("Checking early advance from copying phase", None, self.game.room_id, {
            'all_players_completed': all_copied,
            'player_completion_status': player_completion,
            'phase_start_time_set': hasattr(self, 'phase_start_time')
        })
        
        if all_copied:
            import time
            current_time = time.time()
            if not hasattr(self, 'phase_start_time'):
                self.phase_start_time = current_time
            
            debug_log("All players have completed copying - advancing to voting phase early", None, self.game.room_id,
                      {'time_elapsed': current_time - self.phase_start_time})
            # Cancel current timer
            self.game.timer.cancel_phase_timer()
            socketio.emit('early_phase_advance', {
                'next_phase': 'voting',
                'reason': 'All players have completed their copies'
            }, room=self.game.room_id)
            self.game.voting_phase.start_phase(socketio)
            return True

        return False

    def reset_for_new_game(self):
        """Reset flags for a new game"""
        self.phase_started = False
        self.assignments_made = False
