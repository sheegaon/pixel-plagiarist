# Scoring and token distribution logic for Pixel Plagiarist
from util.logging_utils import debug_log, save_drawing
from util.config import CONSTANTS


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
        self.results_calculated = False  # Prevent duplicate calculations

    def calculate_results(self, socketio):
        """
        Calculate scores and distribute tokens for all drawing sets.

        Parameters
        ----------
        socketio : SocketIO
        """
        # Prevent duplicate calculations
        if self.results_calculated:
            debug_log("Results already calculated, skipping duplicate call", None, self.game.room_id)
            return

        debug_log("Calculating game results", None, self.game.room_id, {
            'total_drawing_sets': len(self.game.drawing_sets),
            'total_votes_collected': sum(len(votes) for votes in self.game.votes.values())
        })

        self.game.phase = "results"
        self.results_calculated = True  # Mark as calculated

        # Calculate scores for each player
        vote_details = []

        # Process each set of drawings
        for set_index in range(len(self.game.drawing_sets)):
            vote_details.append(self.calculate_drawing_set_scores(set_index))
            scores = vote_details[-1]['scores']
            self.distribute_tokens(set_index, scores)

        # Log game summary to global log file
        self._log_game_summary()

        # Send results
        results = {
            'final_balances': {pid: self.game.players[pid]['balance'] for pid in self.game.players},
            'vote_details': vote_details,  # Detailed scores for each drawing set, need to add code to show in UI
            'player_names': {pid: self.game.players[pid]['username'] for pid in self.game.players}
        }

        debug_log("Game results calculated and sent", None, self.game.room_id, {
            'final_balances': results['final_balances'],
        })

        socketio.emit('game_results', results, room=self.game.room_id)

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

        # Award points - only for players still in the game
        scores = {player_id: 0 for player_id in self.game.players}
        points_awarded = {}
        for drawing in drawing_set['drawings']:
            drawing_id = drawing['id']
            player_id = drawing['player_id']
            votes_received = vote_counts[drawing_id]

            # Skip scoring for players who have left the game
            if player_id not in self.game.players:
                debug_log("Skipping scoring for disconnected player", player_id, self.game.room_id, {
                    'drawing_id': drawing_id,
                    'votes_received': votes_received
                })
                continue

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

        # Award points to voters who correctly identified original - only for remaining players
        original_drawing_id = f"original_{original_id}"
        for voter_id, voted_drawing_id in votes_for_set.items():
            if voter_id in self.game.players and voted_drawing_id == original_drawing_id:
                scores[voter_id] += 25
                points_awarded[voter_id] = points_awarded.get(voter_id, 0) + 25

        debug_log("Drawing set scoring complete", None, self.game.room_id, {
            'set_index': set_index,
            'points_awarded': points_awarded,
        })

        return {
            'set_index': set_index,
            'original_player': self.game.players.get(original_id, {}).get('username', f'Player {original_id}'),
            'vote_counts': vote_counts,
            'drawings': drawing_set['drawings'],
            'scores': scores,
        }

    def distribute_tokens(self, set_index, scores):
        """Distribute token rewards based on scores for a given drawing set."""
        if not self.game.players:
            return

        total_score = sum(scores.values())
        if total_score == 0:
            return

        # Find all artists in this set
        drawing_set = self.game.drawing_sets[set_index]
        artists_in_set = {drawing['player_id'] for drawing in drawing_set['drawings']}

        # Calculate minimum stake among artists in this set
        artists_stakes = {pid: self.game.players[pid]['stake'] for pid in artists_in_set}
        if not artists_stakes:
            return

        debug_log("Tokens available for distribution for set", None, self.game.room_id, {
            'set_index': set_index,
            'artists_in_set': len(artists_in_set),
            'prize_per_player': self.game.prize_per_player,
            'total_score': total_score,
        })

        # Distribute pool based on point percentages
        for player_id in self.game.players:
            score_reward = (scores[player_id] / total_score) * self.game.prize_per_player
            starting_balance = self.game.players[player_id]['balance']
            self.game.players[player_id]['balance'] += score_reward

            debug_log("Awarded tokens to player for drawing set", player_id, self.game.room_id, {
                'set_index': set_index,
                'points_earned': scores[player_id],
                'starting_balance': starting_balance,
                'score_reward': score_reward,
                'ending_balance': self.game.players[player_id]['balance'],
            })

    def _log_game_summary(self):
        """Log game summary to global log file and record in database"""
        from util.game_logging import log_game_summary
        log_game_summary(
            room_id=self.game.room_id,
            drawing_sets=self.game.drawing_sets,
            votes=self.game.votes,
            players=self.game.players,
            player_prompts=self.game.player_prompts
        )

        # Record game completion in database for each player
        try:
            from util.db import record_game_completion

            for player_id, player_data in self.game.players.items():
                balance_before = self.game.player_balances_before_game.get(player_id, player_data['balance'])
                balance_after = player_data['balance']
                stake = player_data.get('stake', 0)

                # Calculate statistics for this player
                originals_drawn = 1 if player_id in self.game.original_drawings else 0
                copies_made = sum(1 for drawing_set in self.game.drawing_sets
                                  for drawing in drawing_set['drawings']
                                  if drawing['type'] == 'copy' and drawing['player_id'] == player_id)

                votes_cast = sum(1 for votes in self.game.votes.values() if player_id in votes)

                # Count correct votes (voted for original drawings)
                correct_votes = 0
                for set_index, votes_for_set in self.game.votes.items():
                    if player_id in votes_for_set:
                        drawing_set = self.game.drawing_sets[set_index]
                        voted_drawing_id = votes_for_set[player_id]
                        original_drawing_id = f"original_{drawing_set['original_id']}"
                        if voted_drawing_id == original_drawing_id:
                            correct_votes += 1

                # Calculate points earned (simplified - could be more detailed)
                points_earned = max(0, balance_after - balance_before + stake)  # Net gain plus stake back

                record_game_completion(
                    username=player_data['username'],
                    room_id=self.game.room_id,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    stake=stake,
                    points_earned=points_earned,
                    originals_drawn=originals_drawn,
                    copies_made=copies_made,
                    votes_cast=votes_cast,
                    correct_votes=correct_votes
                )

                debug_log("Recorded game completion for player", player_id, self.game.room_id, {
                    'balance_change': balance_after - balance_before,
                    'originals_drawn': originals_drawn,
                    'copies_made': copies_made,
                    'votes_cast': votes_cast,
                    'correct_votes': correct_votes
                })

        except Exception as e:
            debug_log("Failed to record game completion in database", None, self.game.room_id,
                      {'error': str(e)})


def is_blank_image(base64_data, player_id=None, room_id=None, drawing_id=None):
    """
    Check if an image is blank (all white/transparent pixels).
    
    Parameters
    ----------
    base64_data : str
        Base64 encoded image data
    player_id : str, optional
        Player ID for logging purposes
    room_id : str, optional  
        Room ID for logging purposes
    drawing_id : str, optional
        Drawing ID for logging purposes
        
    Returns
    -------
    bool
        True if image is blank or invalid, False otherwise
    """
    from PIL import Image
    import io
    import base64

    try:
        # Ensure base64_data is valid and contains a comma
        if not base64_data or ',' not in base64_data:
            debug_log("Invalid base64 image data format in is_blank_image", player_id, room_id, {
                'drawing_id': drawing_id,
                'data_preview': str(base64_data)[:100] if base64_data else 'None'
            })
            return True
        
        # Save the problematic image for debugging
        image_path = 'not_saved'
        if player_id and room_id:
            image_path = save_drawing(base64_data, player_id, room_id, 'blank_check', drawing_id)
            
        image_data = base64.b64decode(base64_data.split(',')[1])
        img = Image.open(io.BytesIO(image_data)).convert('RGBA')
        
        # Check if all pixels are white or transparent
        is_blank = all(pixel[3] == 0 or pixel[:3] == (255, 255, 255) for pixel in img.getdata())
        
        if is_blank and player_id and room_id:
            debug_log("Image determined to be blank", player_id, room_id, {
                'drawing_id': drawing_id,
                'image_saved_to': image_path,
                'image_size': f"{img.width}x{img.height}"
            })
            
        return is_blank
        
    except (OSError, Exception) as e:
        # Save the problematic image for debugging if possible
        image_path = None
        if player_id and room_id:
            try:
                image_path = save_drawing(base64_data, player_id, room_id, 'error_check', drawing_id)
            except:
                pass
        
        # Log the error and treat as blank/invalid image
        debug_log("Error decoding image in is_blank_image", player_id, room_id, {
            'error': str(e),
            'drawing_id': drawing_id,
            'image_saved_to': image_path or 'failed_to_save'
        })
        return True
