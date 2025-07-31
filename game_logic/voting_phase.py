# Voting phase logic for Pixel Plagiarist
import random
from logging_utils import debug_log

# Create a simple 400x300 white canvas as base64 PNG
BLANK_CANVAS = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAAEsCAYAAADtt+XCAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAA"
    "AHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAFYSURBVHic7cExAQAAAMKg9U9tCj+gAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAA/wMaogABCUUNmgAAAABJRU5ErkJggg==")


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

    def start_phase(self, socketio):
        """Start the voting phase"""
        debug_log("Starting voting phase", None, self.game.room_id,
                  {'drawing_sets_to_create': len(self.game.original_drawings)})

        self.game.phase = "voting"
        self.game.idx_current_drawing_set = 0

        # Create voting sets (original + copies for each original)
        self._create_voting_sets()

        debug_log("Voting phase setup complete", None, self.game.room_id,
                  {'total_drawing_sets': len(self.game.drawing_sets)})

        # Start voting on first set
        self.start_voting_on_set(socketio)

    def _create_voting_sets(self):
        """Create voting sets with originals and copies"""
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
                    # Player didn't submit a copy - add blank canvas
                    drawing_set['drawings'].append({
                        'id': f"copy_{copier_id}_{original_player_id}",
                        'player_id': copier_id,
                        'type': 'copy',
                        'target_id': original_player_id,
                        'drawing': BLANK_CANVAS,
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
        debug_log("Starting voting on set", None, self.game.room_id, {
            'set_index': self.game.idx_current_drawing_set,
            'total_sets': len(self.game.drawing_sets)
        })

        if self.game.idx_current_drawing_set >= len(self.game.drawing_sets):
            debug_log("All voting sets completed - calculating results", None, self.game.room_id)
            self.game.calculate_results(socketio)
            return

        current_set = self.game.drawing_sets[self.game.idx_current_drawing_set]
        original_player_id = current_set['original_id']
        original_prompt = self.game.player_prompts.get(original_player_id, "Unknown prompt")

        # Determine who can vote on this set
        excluded_players = set()
        for drawing in current_set['drawings']:
            excluded_players.add(drawing['player_id'])

        eligible_voters = [pid for pid in self.game.players if pid not in excluded_players]

        debug_log("Voting eligibility determined", None, self.game.room_id, {
            'excluded_players': len(excluded_players),
            'eligible_voters': len(eligible_voters),
            'drawings_in_set': len(current_set['drawings']),
            'original_prompt': original_prompt
        })

        # Send voting data to eligible players
        for player_id in self.game.players:
            if player_id not in excluded_players:
                # Randomize order for each player to prevent collusion
                shuffled_drawings = current_set['drawings'].copy()
                random.shuffle(shuffled_drawings)

                debug_log("Sending voting round to eligible player", player_id, self.game.room_id, {
                    'set_index': self.game.idx_current_drawing_set,
                    'drawings_count': len(shuffled_drawings)
                })

                socketio.emit('voting_round', {
                    'set_index': self.game.idx_current_drawing_set,
                    'total_sets': len(self.game.drawing_sets),
                    'drawings': shuffled_drawings,
                    'prompt': original_prompt,  # Add the original prompt
                    'timer': self.game.timer.get_voting_timer()
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
                    'timer': self.game.timer.get_voting_timer()
                }, to=player_id)

        self.game.timer.start_phase_timer(
            socketio,
            self.game.timer.get_voting_timer(),
            lambda: self.next_voting_set(socketio)
        )

    def submit_vote(self, player_id, drawing_id, socketio):
        """Record a player's vote for which drawing they think is original."""
        debug_log("Player submitting vote", player_id, self.game.room_id, {
            'drawing_id': drawing_id,
            'set_index': self.game.idx_current_drawing_set,
            'phase': self.game.phase
        })

        if self.game.phase == "voting" and player_id in self.game.players:
            set_index = self.game.idx_current_drawing_set

            if set_index not in self.game.votes:
                self.game.votes[set_index] = {}

            # Check if player already voted for this set
            previous_vote = self.game.votes[set_index].get(player_id)

            self.game.votes[set_index][player_id] = drawing_id
            self.game.players[player_id]['votes_cast'] += 1

            debug_log("Vote recorded successfully", player_id, self.game.room_id, {
                'drawing_id': drawing_id,
                'set_index': set_index,
                'previous_vote': previous_vote,
                'total_votes_cast': self.game.players[player_id]['votes_cast']
            })

            socketio.emit('vote_cast', {
                'player_id': player_id,
                'set_index': set_index
            }, room=self.game.room_id)

            # Check if all eligible voters have voted - advance early if so
            self.game.check_early_phase_advance('voting', socketio)
            return True
        else:
            debug_log("Vote submission rejected", player_id, self.game.room_id, {
                'drawing_id': drawing_id,
                'phase': self.game.phase,
                'player_exists': player_id in self.game.players
            })
            return False

    def next_voting_set(self, socketio):
        """Move to next voting set"""
        debug_log("Moving to next voting set", None, self.game.room_id, {
            'completed_set': self.game.idx_current_drawing_set,
            'votes_received': len(self.game.votes.get(self.game.idx_current_drawing_set, {}))
        })

        self.game.idx_current_drawing_set += 1
        self.start_voting_on_set(socketio)

    def check_early_advance(self, socketio):
        """Check if all eligible voters have voted and advance early if possible"""
        n = len(self.game.drawing_sets)
        # Check if all eligible voters have voted for current set
        current_set = (self.game.drawing_sets[self.game.idx_current_drawing_set]
                       if self.game.idx_current_drawing_set < n else None)
        if current_set:
            # Find eligible voters (those who didn't draw or copy in this set)
            excluded_players = set()
            for drawing in current_set['drawings']:
                excluded_players.add(drawing['player_id'])

            eligible_voters = [pid for pid in self.game.players if pid not in excluded_players]
            set_votes = self.game.votes.get(self.game.idx_current_drawing_set, {})

            # Check if all eligible voters have voted
            all_voted = all(voter_id in set_votes for voter_id in eligible_voters)
            if all_voted and len(eligible_voters) > 0:
                debug_log(
                    "All eligible players have voted - advancing to next voting set early", None, self.game.room_id)
                # Cancel current timer
                self.game.timer.cancel_phase_timer()
                socketio.emit('early_phase_advance', {
                    'next_phase': 'next_voting_set' if self.game.idx_current_drawing_set + 1 < n else 'results',
                    'reason': 'All eligible players have voted'
                }, room=self.game.room_id)
                self.next_voting_set(socketio)
                return True
        return False
