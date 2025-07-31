# Scoring and token distribution logic for Pixel Plagiarist
from logging_utils import debug_log
from config import CONSTANTS


class ScoringEngine:
    """
    Handles all scoring calculations and token distribution logic
    for the game results phase.
    """
    
    def __init__(self, game):
        """
        Initialize the scoring engine.
        
        Parameters
        ----------
        game : PixelPlagiarist
            Reference to the main game instance
        """
        self.game = game

    def calculate_results(self, socketio):
        """
        Calculate scores and distribute tokens for all drawing sets.

        Parameters
        ----------
        socketio : SocketIO
        """
        debug_log("Calculating game results", None, self.game.room_id, {
            'total_drawing_sets': len(self.game.drawing_sets),
            'total_votes_collected': sum(len(votes) for votes in self.game.votes.values())
        })

        self.game.phase = "results"

        self.calculate_penalties()

        # Calculate scores for each player
        vote_details = []

        # Process each set of drawings
        for set_index in range(len(self.game.drawing_sets)):
            vote_details.append(self.calculate_drawing_set_scores(set_index))
            scores = vote_details[-1]['scores']
            debug_log("Drawing set scores calculated", None, self.game.room_id, {'scores': scores})

            self.distribute_tokens(set_index, scores)

        # Log game summary to global log file
        self._log_game_summary()

        # Send results
        results = {
            'final_balance': {pid: self.game.players[pid]['balance'] for pid in self.game.players},
            'vote_details': vote_details,
            'player_names': {pid: self.game.players[pid]['username'] for pid in self.game.players}
        }

        debug_log("Game results calculated and sent", None, self.game.room_id, {
            'final_balances': results['final_balance'],
        })

        socketio.emit('game_results', results, room=self.game.room_id)

    def calculate_penalties(self):
        # Process each set of drawings
        for set_index in range(len(self.game.drawing_sets)):
            # Apply a 5% penalty for blank images
            drawing_set = self.game.drawing_sets[set_index]
            # Check for blank images in this set
            for drawing in drawing_set['drawings']:
                if is_blank_image(drawing['drawing']):
                    player_id = drawing['player_id']
                    if player_id not in self.game.percentage_penalties:
                        self.game.percentage_penalties[player_id] = 0
                    self.game.percentage_penalties[player_id] += CONSTANTS['blank_image_penalty']

            # Apply a 2% penalty for non-artist players who did not vote
            votes_for_set = self.game.votes.get(set_index, {})
            artists_in_set = {drawing['player_id'] for drawing in drawing_set['drawings']}
            for player_id in self.game.players:
                if player_id not in votes_for_set and player_id not in artists_in_set:
                    if player_id not in self.game.percentage_penalties:
                        self.game.percentage_penalties[player_id] = 0
                    self.game.percentage_penalties[player_id] += CONSTANTS['non_voting_penalty']

    def calculate_drawing_set_scores(self, set_index):
        drawing_set = self.game.drawing_sets[set_index]
        original_id = drawing_set['original_id']
        votes_for_set = self.game.votes.get(set_index, {})

        vote_counts = {}
        for drawing in drawing_set['drawings']:
            vote_counts[drawing['id']] = 0

        # Count votes
        for voter_id, voted_drawing_id in votes_for_set.items():
            if voted_drawing_id in vote_counts:
                vote_counts[voted_drawing_id] += 1

        debug_log("Processing drawing set results", None, self.game.room_id, {
            'set_index': set_index,
            'original_player': original_id,
            'total_votes': len(votes_for_set),
            'vote_distribution': vote_counts
        })

        # Award points
        scores = {player_id: 0 for player_id in self.game.players}
        points_awarded = {}
        for drawing in drawing_set['drawings']:
            drawing_id = drawing['id']
            player_id = drawing['player_id']
            votes_received = vote_counts[drawing_id]

            if drawing['type'] == 'original':
                # +100 points per vote for original
                points = votes_received * 100
                scores[player_id] += points
                points_awarded[player_id] = points_awarded.get(player_id, 0) + points
            else:
                # +150 points per vote for copy (mistaken as original)
                points = votes_received * 150
                scores[player_id] += points
                points_awarded[player_id] = points_awarded.get(player_id, 0) + points

        # Award points to voters who correctly identified original
        original_drawing_id = f"original_{original_id}"
        for voter_id, voted_drawing_id in votes_for_set.items():
            if voted_drawing_id == original_drawing_id:
                scores[voter_id] += 25
                points_awarded[voter_id] = points_awarded.get(voter_id, 0) + 25

        debug_log("Drawing set scoring complete", None, self.game.room_id, {
            'set_index': set_index,
            'points_awarded': points_awarded,
        })

        return {
            'set_index': set_index,
            'original_player': self.game.players[original_id]['username'],
            'vote_counts': vote_counts,
            'drawings': drawing_set['drawings'],
            'scores': scores,
        }

    def distribute_tokens(self, set_index, scores):
        """Distribute token rewards based on scores for a given drawing set."""
        if not self.game.players:
            return

        debug_log("Starting token distribution", None, self.game.room_id, {
            'total_players': len(self.game.players),
            'total_drawing_sets': len(self.game.drawing_sets)
        })

        # Find all artists in this set
        drawing_set = self.game.drawing_sets[set_index]
        artists_in_set = {drawing['player_id'] for drawing in drawing_set['drawings']}

        # Calculate minimum stake among artists in this set
        artists_stakes = {pid: self.game.players[pid]['stake'] for pid in artists_in_set}
        if not artists_stakes:
            return
        total_pool_for_set = min(artists_stakes.values())

        # Calculate contribution per artist based on number of artists
        contribution_per_artist = total_pool_for_set / len(artists_in_set)
        excess_stakes = {pid: self.game.players[pid]['stake'] - contribution_per_artist for pid in artists_in_set}
        penalty_pool = 0
        for player_id in self.game.percentage_penalties:
            if player_id in excess_stakes:
                penalty = excess_stakes[player_id] * self.game.percentage_penalties[player_id]
                penalty_pool += penalty
                excess_stakes[player_id] -= penalty

        total_score = sum(scores.values())

        debug_log("Processing set for token distribution", None, self.game.room_id, {
            'set_index': set_index,
            'artists_in_set': len(artists_in_set),
            'contribution_per_artist': contribution_per_artist,
            'total_pool_for_set': total_pool_for_set,
            'total_score': total_score,
            'penalty_pool': penalty_pool,
        })

        if total_score == 0:
            return

        # Distribute pool based on point percentages
        penalty_distribution = penalty_pool / len(scores)
        for player_id in scores:
            reward = (scores[player_id] / total_score) * total_pool_for_set
            starting_balance = self.game.players[player_id]['balance']
            self.game.players[player_id]['balance'] += reward + penalty_distribution + excess_stakes.get(player_id, 0)

            debug_log("Awarded tokens from drawing set", player_id, self.game.room_id, {
                'set_index': set_index,
                'points_earned': scores[player_id],
                'starting_balance': starting_balance,
                'reward': reward,
                'penalty_distribution': penalty_distribution,
                'excess_stake_returned': excess_stakes.get(player_id, 0),
                'ending_balance': self.game.players[player_id]['balance'],
            })

        debug_log("Token distribution complete", None, self.game.room_id, {
            'final_balances': {pid: self.game.players[pid]['balance'] for pid in self.game.players}
        })

    def _log_game_summary(self):
        """Log game summary to global log file"""
        try:
            from game_logging import log_game_summary
            log_game_summary(
                room_id=self.game.room_id,
                drawing_sets=self.game.drawing_sets,
                votes=self.game.votes,
                players=self.game.players,
                player_prompts=self.game.player_prompts
            )
        except ImportError:
            debug_log("Game logging module not available", None, self.game.room_id)


def is_blank_image(base64_data):
    from PIL import Image
    import io
    import base64

    image_data = base64.b64decode(base64_data.split(',')[1])
    img = Image.open(io.BytesIO(image_data)).convert('RGBA')
    # Check if all pixels are white or transparent
    return all(pixel[3] == 0 or pixel[:3] == (255, 255, 255) for pixel in img.getdata())
