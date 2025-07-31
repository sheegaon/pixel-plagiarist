# Copying phase logic for Pixel Plagiarist
import random
import time
import threading
from logging_utils import debug_log


class CopyingPhase:
    """
    Handles all copying phase logic including copy assignments,
    viewing periods, submissions, and phase transitions.
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

    def start_phase(self, socketio):
        """Start the copying phase with 10-second viewing period"""
        debug_log("Starting copying phase with viewing period", None, self.game.room_id,
                  {'timer': self.game.timer.get_copying_timer(), 'player_count': len(self.game.players)})

        self.game.phase = "copying_viewing"  # New sub-phase for viewing

        # Assign copying tasks
        self._assign_copying_tasks()

        # Send assignments to players for 10-second viewing
        self._send_viewing_phase(socketio)

        # After 10 seconds, start actual copying phase
        self._schedule_copying_start(socketio)

        # Set overall copying timer (including viewing time)
        self.game.timer.start_phase_timer(
            socketio, 
            self.game.timer.get_copying_timer(), 
            lambda: self.game.start_voting_phase(socketio)
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
        
        # Create a list of all possible (copier, target) pairs
        possible_assignments = []
        for copier in player_ids:
            for target in player_ids:
                if copier != target and target in self.game.original_drawings:
                    possible_assignments.append((copier, target))
        
        # Shuffle to randomize assignments
        random.shuffle(possible_assignments)
        
        # Track assignments per player and globally
        player_assignment_counts = {pid: 0 for pid in player_ids}
        assigned_targets = set()
        
        # Assign copies ensuring no duplicates
        for copier, target in possible_assignments:
            # Skip if this player already has enough copies
            if player_assignment_counts[copier] >= copies_per_player:
                continue
                
            # Skip if this target is already assigned (prevents multiple players copying same original)
            if target in assigned_targets:
                continue
                
            # Make the assignment
            if copier not in self.game.copy_assignments:
                self.game.copy_assignments[copier] = []
                self.game.players[copier]['copies_to_make'] = []
                
            self.game.copy_assignments[copier].append(target)
            self.game.players[copier]['copies_to_make'].append(target)
            player_assignment_counts[copier] += 1
            assigned_targets.add(target)

        # Log final assignments
        for player_id in player_ids:
            targets = self.game.copy_assignments.get(player_id, [])
            debug_log("Copying assignment created", player_id, self.game.room_id,
                      {'targets': targets, 'target_count': len(targets)})

    def _send_viewing_phase(self, socketio):
        """Send viewing phase data to players"""
        for player_id, target_ids in self.game.copy_assignments.items():
            target_drawings = []
            for target_id in target_ids:
                if target_id in self.game.original_drawings:
                    target_drawings.append({
                        'target_id': target_id,
                        'drawing': self.game.original_drawings[target_id]
                    })

            debug_log("Sending copying viewing phase to player", player_id, self.game.room_id,
                      {'target_count': len(target_drawings)})

            socketio.emit('copying_viewing_phase', {
                'targets': target_drawings,
                'viewing_duration': 10,  # 10 seconds viewing
                'total_timer': self.game.timer.get_copying_timer()
            }, to=player_id)

        socketio.emit('phase_changed', {
            'phase': 'copying_viewing',
            'viewing_duration': 10,
            'timer': self.game.timer.get_copying_timer()
        }, room=self.game.room_id)

    def _schedule_copying_start(self, socketio):
        """Schedule the start of actual copying after viewing period"""
        def start_actual_copying():
            time.sleep(10)
            self.game.phase = "copying"
            
            debug_log("Viewing period ended - starting copying", None, self.game.room_id)
            
            # Hide drawings and allow copying to begin
            socketio.emit('copying_phase_started', {
                'phase': 'copying',
                'remaining_time': self.game.timer.get_copying_timer() - 10
            }, room=self.game.room_id)

        viewing_timer = threading.Thread(target=start_actual_copying)
        viewing_timer.start()

    def submit_copied_drawing(self, player_id, target_id, drawing_data, socketio):
        """Accept and store a player's copied drawing submission."""
        debug_log("Player submitting copied drawing", player_id, self.game.room_id,
                  {'target_id': target_id, 'phase': self.game.phase,
                   'data_length': len(drawing_data) if drawing_data else 0})

        if player_id in self.game.players and self.game.phase == "copying":
            if player_id not in self.game.copied_drawings:
                self.game.copied_drawings[player_id] = {}

            self.game.copied_drawings[player_id][target_id] = drawing_data
            self.game.players[player_id]['completed_copies'] += 1

            debug_log("Copied drawing submitted successfully", player_id, self.game.room_id, {
                'target_id': target_id,
                'completed_copies': self.game.players[player_id]['completed_copies'],
                'total_required': len(self.game.players[player_id]['copies_to_make'])
            })

            socketio.emit('copy_submitted', {
                'player_id': player_id,
                'target_id': target_id,
                'completed': self.game.players[player_id]['completed_copies'],
                'total': len(self.game.players[player_id]['copies_to_make'])
            }, room=self.game.room_id)
            
            # Check if all players have completed copying - advance early if so
            self.game.check_early_phase_advance('copying', socketio)
            return True
        else:
            debug_log(
                "Copied drawing submission rejected", player_id, self.game.room_id,
                {'target_id': target_id, 'phase': self.game.phase, 'player_exists': player_id in self.game.players})
            return False

    def check_early_advance(self, socketio):
        """Check if all players have completed copying and advance early if possible"""
        all_copied = all(
            player.get('completed_copies', 0) >= len(player.get('copies_to_make', []))
            for player in self.game.players.values()
        )
        if all_copied:
            debug_log("All players have completed copying - advancing to voting phase early", None, self.game.room_id)
            # Cancel current timer
            self.game.timer.cancel_phase_timer()
            socketio.emit('early_phase_advance', {
                'next_phase': 'voting',
                'reason': 'All players have completed their copies'
            }, room=self.game.room_id)
            self.game.start_voting_phase(socketio)
            return True
        return False
