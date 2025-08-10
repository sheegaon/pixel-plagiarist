# Voting phase logic for Pixel Plagiarist
import random
from PIL import Image
import io
import base64
from util.logging_utils import debug_log


class VotingPhase:
    """
    Handles all voting phase logic including voting set creation,
    vote collection, and phase transitions.
    """

    def __init__(self, game):
        """
        Initialize the voting phase handler.
        
        Parameters
        ----------
        game : PixelPlagiarist
            Reference to the main game instance
        """
        self.game = game
        self.drawing_sets_created = False  # Prevent duplicate set creation
        self.current_set_started = False  # Prevent duplicate set starts
        self.set_start_time = None  # Track when the current set started

    def start_phase(self, socketio):
        """Start the voting phase"""
        # Check if game has ended early - if so, don't start voting phase
        if self.game.phase == "ended_early":
            debug_log("Skipping voting phase - game has ended early", None, self.game.room_id)
            return
            
        # Prevent duplicate phase starts
        if self.game.phase == "voting" and self.drawing_sets_created:
            debug_log("Voting phase already started, skipping duplicate call", None, self.game.room_id)
            return
            
        debug_log("Starting voting phase", None, self.game.room_id,
                  {'drawing_sets_to_create': len(self.game.original_drawings)})

        self.game.phase = "voting"
        self.game.idx_current_drawing_set = 0

        # Create voting sets (original + copies for each original) - only once
        if not self.drawing_sets_created:
            self._create_drawing_sets()
            self.drawing_sets_created = True

        debug_log("Voting phase setup complete", None, self.game.room_id,
                  {'total_drawing_sets': len(self.game.drawing_sets)})

        # Start voting on first set
        self.start_voting_on_set(socketio)

    def _create_drawing_sets(self):
        """Create drawing sets with originals and copies"""
        self.game.drawing_sets = []

        for original_player_id in self.game.original_drawings:
            drawing_set = {
                'original_id': original_player_id,
                'drawings': [
                    {
                        'id': f"original_{original_player_id}",
                        'player_id': original_player_id,
                        'type': 'original',
                        'drawing': self.game.original_drawings[original_player_id]
                    }
                ]
            }

            # Find all players who were supposed to copy this original
            expected_copiers = []
            for player_id, targets in self.game.copy_assignments.items():
                if original_player_id in targets:
                    expected_copiers.append(player_id)

            # Add copies (both submitted and missing ones)
            copies_found = 0
            for copier_id in expected_copiers:
                if (copier_id in self.game.copied_drawings and
                        original_player_id in self.game.copied_drawings[copier_id]):
                    # Player submitted a copy
                    drawing_set['drawings'].append({
                        'id': f"copy_{copier_id}_{original_player_id}",
                        'player_id': copier_id,
                        'type': 'copy',
                        'target_id': original_player_id,
                        'drawing': self.game.copied_drawings[copier_id][original_player_id],
                    })
                    copies_found += 1
                else:
                    # Create a simple 400x300 white canvas as base64 PNG
                    img = Image.new('RGB', (400, 300), 'white')
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    buffer.seek(0)
                    img_str = base64.b64encode(buffer.getvalue()).decode()

                    # Player didn't submit a copy - add blank canvas
                    drawing_set['drawings'].append({
                        'id': f"copy_{copier_id}_{original_player_id}",
                        'player_id': copier_id,
                        'type': 'copy',
                        'target_id': original_player_id,
                        'drawing': f'data:image/png;base64,{img_str}',
                    })
                    copies_found += 1

            # Randomize order within set
            random.shuffle(drawing_set['drawings'])
            self.game.drawing_sets.append(drawing_set)

            debug_log("Created drawing set", None, self.game.room_id, {
                'original_player': original_player_id,
                'total_drawings': len(drawing_set['drawings']),
                'copies_found': copies_found,
                'expected_copiers': len(expected_copiers)
            })

    def start_voting_on_set(self, socketio):
        """Start voting on current set using configured timer"""
        # Prevent duplicate set starts
        if self.current_set_started:
            debug_log("Current voting set already started, skipping duplicate call", None, self.game.room_id, {
                'set_index': self.game.idx_current_drawing_set
            })
            return
            
        debug_log("Starting voting on set", None, self.game.room_id, {
            'set_index': self.game.idx_current_drawing_set,
            'total_sets': len(self.game.drawing_sets)
        })

        if self.game.idx_current_drawing_set >= len(self.game.drawing_sets):
            debug_log("All voting sets completed - calculating results", None, self.game.room_id)
            self.game.scoring_engine.calculate_results(socketio)
            return

        self.current_set_started = True
        # Reset the timer for this new voting set
        import time
        self.set_start_time = time.time()
        
        current_set = self.game.drawing_sets[self.game.idx_current_drawing_set]
        original_player_id = current_set['original_id']
        original_prompt = self.game.player_prompts.get(original_player_id, "Unknown prompt")

        # Prepare shuffled drawings for all players
        shuffled_drawings = current_set['drawings'].copy()
        random.shuffle(shuffled_drawings)

        eligible_voters = self.get_eligible_voters_for_set(current_set)

        debug_log("Voting eligibility determined", None, self.game.room_id, {
            'eligible_voters': len(eligible_voters),
            'drawings_in_set': len(current_set['drawings']),
            'original_prompt': original_prompt
        })

        # Send voting data to eligible players
        for player_id in self.game.players:
            if player_id in eligible_voters:
                # Randomize order for each player to prevent collusion
                debug_log("Sending voting round to eligible player", player_id, self.game.room_id, {
                    'set_index': self.game.idx_current_drawing_set,
                    'drawings_count': len(shuffled_drawings)
                })

                socketio.emit('voting_round', {
                    'set_index': self.game.idx_current_drawing_set,
                    'total_sets': len(self.game.drawing_sets),
                    'drawings': shuffled_drawings,
                    'prompt': original_prompt,  # Add the original prompt
                    'timer': self.game.timer.get_voting_timer_duration()
                }, to=player_id)
            else:
                debug_log("Player excluded from voting round", player_id, self.game.room_id, {
                    'set_index': self.game.idx_current_drawing_set,
                    'reason': 'drew_or_copied_in_set'
                })

                # Add voting drawings and prompt data to the excluded player event
                socketio.emit('voting_round_excluded', {
                    'set_index': self.game.idx_current_drawing_set,
                    'total_sets': len(self.game.drawing_sets),
                    'reason': 'You drew or copied in this set',
                    'drawings': shuffled_drawings,  # Add drawings for observation
                    'prompt': original_prompt,  # Add the original prompt
                    'timer': self.game.timer.get_voting_timer_duration()
                }, to=player_id)

        self.game.timer.start_phase_timer(
            socketio,
            self.game.timer.get_voting_timer_duration(),
            lambda: self.next_voting_set(socketio)
        )

    def get_eligible_voters_for_set(self, drawing_set):
        # Determine who can vote on this set
        excluded_players = set()
        for drawing in drawing_set['drawings']:
            excluded_players.add(drawing['player_id'])

        return [pid for pid in self.game.players if pid not in excluded_players]

    def submit_vote(self, player_id, drawing_id, socketio, check_early_advance=True):
        """Record a player's vote for which drawing they think is original."""
        debug_log("Player submitting vote", player_id, self.game.room_id, {
            'drawing_id': drawing_id,
            'set_index': self.game.idx_current_drawing_set,
            'phase': self.game.phase
        })

        # Comprehensive vote validation with detailed logging
        validation_result = self._validate_vote(player_id, drawing_id)
        if not validation_result['valid']:
            debug_log("Vote submission rejected", player_id, self.game.room_id, {
                'drawing_id': drawing_id,
                'set_index': self.game.idx_current_drawing_set,
                'rejection_reason': validation_result['reason'],
                'validation_details': validation_result['details']
            })
            return False

        set_index = self.game.idx_current_drawing_set

        if set_index not in self.game.votes:
            self.game.votes[set_index] = {}

        self.game.votes[set_index][player_id] = drawing_id
        self.game.players[player_id]['votes_cast'] += 1

        debug_log("Vote recorded successfully", player_id, self.game.room_id, {
            'drawing_id': drawing_id,
            'set_index': set_index,
            'total_votes_cast': self.game.players[player_id]['votes_cast'],
            'votes_in_set': len(self.game.votes[set_index])
        })

        socketio.emit('vote_cast', {
            'player_id': player_id,
            'set_index': set_index
        }, room=self.game.room_id)

        # Check if all eligible voters have voted - advance early if so
        if check_early_advance:
            self.check_early_advance(socketio)
        return True

    def _validate_vote(self, player_id, drawing_id):
        """
        Comprehensive vote validation with detailed logging.
        
        Returns
        -------
        dict
            Validation result with 'valid', 'reason', and 'details' keys
        """
        # Check phase
        if self.game.phase != "voting":
            return {
                'valid': False,
                'reason': 'wrong_phase',
                'details': {'current_phase': self.game.phase, 'expected_phase': 'voting'}
            }
            
        # Check if player exists
        if player_id not in self.game.players:
            return {
                'valid': False,
                'reason': 'player_not_in_game',
                'details': {'player_id': player_id}
            }

        # Check voting set index validity
        if self.game.idx_current_drawing_set >= len(self.game.drawing_sets):
            return {
                'valid': False,
                'reason': 'invalid_set_index',
                'details': {
                    'set_index': self.game.idx_current_drawing_set,
                    'total_sets': len(self.game.drawing_sets)
                }
            }

        current_set = self.game.drawing_sets[self.game.idx_current_drawing_set]
        
        # Check if player is eligible to vote (didn't draw or copy in this set)
        eligible_voters = self.get_eligible_voters_for_set(current_set)
        if player_id not in eligible_voters:
            # Find out why they're not eligible
            exclusion_reason = []
            for drawing in current_set['drawings']:
                if drawing['player_id'] == player_id:
                    if drawing['type'] == 'original':
                        exclusion_reason.append('drew_original')
                    elif drawing['type'] == 'copy':
                        exclusion_reason.append('made_copy')
            
            return {
                'valid': False,
                'reason': 'player_not_eligible',
                'details': {
                    'set_index': self.game.idx_current_drawing_set,
                    'exclusion_reasons': exclusion_reason,
                    'eligible_voters': len(eligible_voters)
                }
            }

        # Check if player already voted for this set
        set_index = self.game.idx_current_drawing_set
        if set_index in self.game.votes and player_id in self.game.votes[set_index]:
            return {
                'valid': False,
                'reason': 'already_voted',
                'details': {
                    'set_index': set_index,
                    'previous_vote': self.game.votes[set_index][player_id]
                }
            }

        # Check if drawing_id exists in current set
        valid_drawing_ids = [drawing['id'] for drawing in current_set['drawings']]
        if drawing_id not in valid_drawing_ids:
            return {
                'valid': False,
                'reason': 'invalid_drawing_id',
                'details': {
                    'submitted_drawing_id': drawing_id,
                    'valid_drawing_ids': valid_drawing_ids,
                    'set_index': set_index
                }
            }

        # All validations passed
        return {
            'valid': True,
            'reason': None,
            'details': {
                'set_index': set_index,
                'eligible_voters_count': len(eligible_voters),
                'drawings_in_set': len(current_set['drawings'])
            }
        }

    def next_voting_set(self, socketio):
        """Move to next voting set"""
        debug_log("Moving to next voting set", None, self.game.room_id, {
            'completed_set': self.game.idx_current_drawing_set,
            'votes_received': len(self.game.votes.get(self.game.idx_current_drawing_set, {}))
        })

        self.current_set_started = False  # Reset for next set
        self.game.idx_current_drawing_set += 1
        self.start_voting_on_set(socketio)

    def check_early_advance(self, socketio):
        """Check if all eligible voters have voted and advance early if possible"""
        n = len(self.game.drawing_sets)
        current_set = (self.game.drawing_sets[self.game.idx_current_drawing_set]
                       if self.game.idx_current_drawing_set < n else None)
        if current_set:
            # Find eligible voters (those who didn't draw or copy in this set)
            eligible_voters = self.get_eligible_voters_for_set(current_set)
            set_votes = self.game.votes.get(self.game.idx_current_drawing_set, {})

            # Check if all eligible voters have voted
            all_voted = all(voter_id in set_votes for voter_id in eligible_voters)
            
            # Advance immediately if all eligible voters have voted, or if there are no eligible voters
            if all_voted or len(eligible_voters) == 0:
                debug_log(
                    "All eligible players have voted - advancing to next voting set early", None, self.game.room_id)
                # Cancel current timer
                self.game.timer.cancel_phase_timer()
                socketio.emit('early_phase_advance', {
                    'next_phase': 'next_voting_set' if self.game.idx_current_drawing_set + 1 < n else 'results',
                    'reason': 'All eligible players have voted' if len(eligible_voters) > 0 else 'No eligible voters in this set'
                }, room=self.game.room_id)
                self.next_voting_set(socketio)
                return True
        return False
