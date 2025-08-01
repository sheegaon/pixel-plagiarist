# Game action handlers for socket events
from flask import request
from flask_socketio import emit

from .game_state import game_state_sh


class GameHandlers:
    """Handles in-game actions like betting, drawing, voting, etc."""
    
    def __init__(self, socketio):
        self.socketio = socketio
    
    def handle_place_bet(self, data):
        """Handle betting"""
        player_id = request.sid
        stake = data.get('stake', 10)

        room_id = game_state_sh.get_player_room(player_id)
        if room_id:
            game = game_state_sh.get_game(room_id)
            if game:
                game.betting_phase.place_bet(player_id, stake, self.socketio)

    def handle_submit_original(self, data):
        """Handle drawing submission"""
        player_id = request.sid
        drawing_data = data.get('drawing_data')

        if drawing_data:
            room_id = game_state_sh.get_player_room(player_id)
            if room_id:
                game = game_state_sh.get_game(room_id)
                if game:
                    game.drawing_phase.submit_drawing(player_id, drawing_data, self.socketio)

    def handle_submit_copy(self, data):
        """Handle copy submission"""
        player_id = request.sid
        target_id = data.get('target_id')
        drawing_data = data.get('drawing_data')

        if target_id and drawing_data:
            room_id = game_state_sh.get_player_room(player_id)
            if room_id:
                game = game_state_sh.get_game(room_id)
                if game:
                    game.copying_phase.submit_drawing(player_id, target_id, drawing_data, self.socketio)

    def handle_submit_vote(self, data):
        """Handle vote submission"""
        player_id = request.sid
        drawing_id = data.get('drawing_id')

        if drawing_id:
            room_id = game_state_sh.get_player_room(player_id)
            if room_id:
                game = game_state_sh.get_game(room_id)
                if game:
                    game.voting_phase.submit_vote(player_id, drawing_id, self.socketio)

    def handle_request_review(self, data):
        """Handle review request"""
        player_id = request.sid
        target_id = data.get('target_id')

        if target_id:
            room_id = game_state_sh.get_player_room(player_id)
            if room_id:
                game = game_state_sh.get_game(room_id)
                if game and target_id in game.original_drawings:
                    # Send the original drawing for 5-second review
                    emit('review_drawing', {
                        'drawing': game.original_drawings[target_id],
                        'duration': 5000  # 5 seconds in milliseconds
                    }, to=player_id)